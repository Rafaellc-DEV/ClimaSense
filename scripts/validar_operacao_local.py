"""ETL com GETs reais, Postgres fixo descartável e Bronze mongomock (sem Atlas).

Não lê .env. Migra SOMENTE climasense_operacao_teste em 127.0.0.1:55432, previamente criado.
Guarda evidências e respostas para a verificação visual em tmp/operacao-local.json.
Não usa dados artificiais de clima, exposição ou COP; a conta de teste é exclusivamente local.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "backend"))
for nome in (
    "DATABASE_URL",
    "DATABASE_URL_MIGRACOES",
    "DATABASE_URL_TESTE",
    "NEON_URL",
    "MONGO_URI",
):
    os.environ.pop(nome, None)
os.environ["AMBIENTE"] = "teste"

from climasense.config import Configuracao

Configuracao.model_config["env_file"] = None

import mongomock
from alembic import command
from alembic.config import Config as ConfigAlembic
from climasense.api.main import criar_app
from climasense.etl import execucao, gold
from climasense.infra.postgres import criar_engine, fabrica_sessoes, obter_sessao
from climasense.ml.alagamento import armazenamento
from climasense.ml.alagamento.prever import persistir
from climasense.servicos.usuarios import ServicoUsuarios
from climasense.territorio import carga
from fastapi.testclient import TestClient
from sqlalchemy import text

URL_LOCAL = "postgresql://climasense@127.0.0.1:55432/climasense_operacao_teste"
SAIDA = RAIZ / "tmp" / "operacao-local.json"


def validar_evidencias(evidencias: dict) -> list[str]:
    falhas = []
    if any(e["status"] != "sucesso" for e in evidencias["etl"]):
        falhas.append("Uma das fontes falhou na coleta real.")
    distritos = evidencias.get("distritos", [])
    if {d["id"] for d in distritos} != {f"ds-{k}" for k in range(1, 9)}:
        falhas.append("Cobertura territorial incompleta.")
    if any(
        d["avaliacao"]["acumulados_previstos_mm"].get("72") is None
        or len(d["avaliacao"]["serie_chuva"]) != 72
        or len(d["avaliacao"]["serie_mare"]) != 72
        for d in distritos
    ):
        falhas.append("Cobertura meteorológica de 72 h incompleta.")
    if any(evidencias["gold_diferencas"].values()):
        falhas.append("Gold divergente da Silver.")
    if any(c != 200 for c in evidencias["http"].values()):
        falhas.append("Uma das APIs locais falhou.")
    if evidencias.get("repeticao_persistencia") != 0:
        falhas.append("Persistência não idempotente.")
    return falhas


def main() -> int:
    config = Configuracao(
        _env_file=None,
        ambiente="teste",
        database_url=URL_LOCAL,
        database_url_migracoes=URL_LOCAL,
        mongo_uri="mongodb://127.0.0.1:27018/",
        session_secret="chave-publica-exclusiva-do-teste-local-0123456789",
    )
    cfg = ConfigAlembic(str(RAIZ / "backend" / "alembic.ini"))
    cfg.set_main_option("script_location", str(RAIZ / "backend" / "migrations"))
    cfg.cmd_opts = type("Opcoes", (), {"x": [f"url={URL_LOCAL}"]})()
    command.upgrade(cfg, "head")
    engine = criar_engine(URL_LOCAL)
    fabrica = fabrica_sessoes(engine)
    mongo = mongomock.MongoClient(tz_aware=True)
    evidencias = {
        "ambiente": "local-descartavel",
        "bronze": "mongomock; não comprova durabilidade Atlas",
        "etl": [],
    }
    try:
        carga.salvar_atlas(mongo, carga.geo_local(), config.mongo_db_territorio)
        with fabrica() as db:
            carga.sincronizar_territorios(db, carga.geo_local())
        for fonte in (
            "open-meteo-previsao",
            "open-meteo-mare",
            "apac-chuva",
            "apac-previsao",
            "alertas-oficiais",
        ):
            eid = execucao.iniciar(engine, fonte)
            r = execucao.executar(engine, mongo, config, fonte, eid)
            evidencias["etl"].append(
                {
                    "fonte": fonte,
                    **{k: v for k, v in r.items() if k != "execucao_id"},
                    "bronze_documentos": mongo["bronze"][
                        fonte.replace("-", "_")
                    ].count_documents({"_execucao_id": eid}),
                }
            )
            print(json.dumps(evidencias["etl"][-1], ensure_ascii=False), flush=True)
            if r["status"] == "sucesso":
                antes = mongo["bronze"][fonte.replace("-", "_")].count_documents({})
                repetida = execucao.executar(engine, mongo, config, fonte, eid)
                assert repetida["status"] == "sucesso"
                assert antes == mongo["bronze"][
                    fonte.replace("-", "_")
                ].count_documents({})
        with engine.connect() as c:
            evidencias["versao_banco"] = c.execute(
                text("select version_num from alembic_version")
            ).scalar_one()
            evidencias["gold_diferencas"] = gold.verificar(c)
            evidencias["silver"] = [
                dict(r)
                for r in c.execute(
                    text(
                        "select fonte_id,territorio_id,count(*) as registros,max(observado_em) as ultimo_dado,"
                        "max(emitido_em) as captura from silver.observacoes group by fonte_id,territorio_id order by 1,2"
                    )
                ).mappings()
            ]
            evidencias["apac"] = dict(
                c.execute(
                    text(
                        "select max(lida_em) as ultima_leitura,count(distinct estacao_id) filter "
                        "(where lida_em between now()-interval '2 hours' and now() and valor_mm is not null) as estacoes_recentes "
                        "from silver.apac_chuva_leituras"
                    )
                )
                .mappings()
                .one()
            )
        app = criar_app(config)
        app.state.mongo = mongo

        def sessao_local():
            with fabrica() as s:
                yield s

        app.dependency_overrides[obter_sessao] = sessao_local
        with fabrica() as db:
            if not db.execute(
                text(
                    "select exists(select 1 from app.usuarios where email='operacao-local@recife.pe.gov.br')"
                )
            ).scalar_one():
                conta = ServicoUsuarios(db).criar(
                    "Teste de operação local",
                    "operacao-local@recife.pe.gov.br",
                    ["administrador"],
                    autor=None,
                    senha_inicial="senha publica apenas do teste local",
                )
                conta.usuario.troca_senha_obrigatoria = False
                db.commit()
        respostas, codigos = {}, {}
        with TestClient(app) as cliente:
            login = cliente.post(
                "/api/v1/auth/entrar",
                json={
                    "email": "operacao-local@recife.pe.gov.br",
                    "senha": "senha publica apenas do teste local",
                },
            )
            print(json.dumps({"login_local_http": login.status_code}), flush=True)
            assert login.status_code == 200
            cliente.headers["X-CSRF-Token"] = cliente.cookies.get("cs_csrf")
            caminhos = (
                "/auth/eu",
                "/fontes",
                "/situacao/chuva",
                "/estagios?nivel=distrito",
                "/estagios/oficial",
                "/estagios/parametros",
                "/cenarios",
                "/cenarios/premissas-atuais",
                "/cenarios/estimativa?territorio_id=recife&horizonte_h=72",
                "/cenarios/impacto-previsto?horizonte_h=24",
                "/cenarios/impacto-previsto?horizonte_h=72",
                "/territorios/bairros.geojson",
                "/territorios/distritos.geojson",
            )
            for caminho in caminhos:
                r = cliente.get("/api/v1" + caminho)
                print(
                    json.dumps({"api_local": caminho, "http": r.status_code}),
                    flush=True,
                )
                codigos[caminho] = r.status_code
                if r.status_code == 200:
                    respostas[caminho] = r.json()
            r = cliente.post(
                "/api/v1/cenarios/simular",
                json={
                    "chuva_prevista_mm": 60,
                    "duracao_h": 24,
                    "chuva_acumulada_mm": None,
                    "mare_m": None,
                    "horizonte_h": 24,
                },
            )
            codigos["/cenarios/simular"] = r.status_code
            if r.status_code == 200:
                respostas["/cenarios/simular"] = (
                    r.json()
                )  # cenário manual explicitamente hipotético
        r = respostas.get("/cenarios/impacto-previsto?horizonte_h=72", {}).get(
            "dados", {}
        )
        distritos = [i for i in r.get("itens", []) if i["nivel"] == "distrito"]
        evidencias["distritos"] = [
            {
                "id": i["territorio_id"],
                "classe": i["classe_alagamento"],
                "avaliacao": i["avaliacao"],
            }
            for i in distritos
        ]
        evidencias["ml"] = {
            "artefato_compativel_carregado": armazenamento.carregar_em_cache()
            is not None,
            **r.get("ml_alagamento", {}),
        }
        if r:
            with fabrica() as db:
                evidencias["persistidos"] = persistir(db, r)
                db.commit()
            with fabrica() as db:
                evidencias["repeticao_persistencia"] = persistir(db, r)
                evidencias["gold_inferencias"] = db.execute(
                    text("select count(*) from gold.previsoes_impacto")
                ).scalar_one()
                db.commit()
        evidencias["http"] = codigos
        evidencias["capturado_em"] = datetime.now(UTC).isoformat()
        SAIDA.parent.mkdir(exist_ok=True)
        SAIDA.write_text(
            json.dumps(
                {"evidencias": evidencias, "respostas": respostas},
                ensure_ascii=False,
                indent=2,
                default=str,
            ),
            encoding="utf-8",
        )
        print(
            json.dumps(
                {
                    "http": codigos,
                    "distritos_avaliados": len(distritos),
                    "relatorio": str(SAIDA.relative_to(RAIZ)),
                },
                ensure_ascii=False,
            )
        )
        falhas = validar_evidencias(evidencias)
        print(json.dumps({"falhas_de_validacao": falhas}, ensure_ascii=False))
        return 1 if falhas else 0
    finally:
        engine.dispose()
        mongo.close()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as erro:  # noqa: BLE001 — não imprime URI nem conteúdo arbitrário
        import traceback

        print(
            json.dumps(
                {
                    "local_da_falha": [
                        {"arquivo": Path(f.filename).name, "linha": f.lineno}
                        for f in traceback.extract_tb(erro.__traceback__)
                    ]
                }
            ),
            file=sys.stderr,
        )
        print(f"Validação local interrompida ({type(erro).__name__}).", file=sys.stderr)
        raise SystemExit(1) from None
