"""Qualidade da água de abastecimento por bairro e semana (SISAGUA, API de Dados Abertos do Ministério da Saúde).

`GET https://apidadosabertos.saude.gov.br/sisagua/vigilancia-parametros-basicos?codigo_ibge=261160&ano=<ano>
&limit=1000&offset=<n>` (JSON, chave `parametros`, sem autenticação). Cada linha é UM parâmetro de UMA amostra de
vigilância, com bairro (`area`), data da coleta, data do laudo e do registro e o resultado.

Rótulo obrigatório: "qualidade da água, coleta de rotina, não dirigida pelo evento". A amostragem é programada pela
Vigilância Ambiental; não segue a chuva. Semana sem amostra no bairro é "sem coleta", nunca "água boa" (RN-01).

O que se conta, sem percentual e sem classe de risco (RN-06):
- E. coli: análises com resultado válido (PRESENTE ou AUSENTE) e quantas deram PRESENTE;
- cloro residual livre: análises com resultado numérico e quantas ficaram fora da faixa de 0,2 a 5,0 mg/L (mínimo no
  sistema de distribuição e valor máximo permitido da Portaria GM/MS nº 888/2021; a faixa fica em `CLORO_MIN_MG_L` e
  `CLORO_MAX_MG_L`, para a Vigilância corrigir se discordar).
Os outros parâmetros (coliformes totais, turbidez, pH, cor, dióxido de cloro) não são usados e só aparecem no resumo.

Coletas de rotina e coletas dirigidas (surto, denúncia, desastre) ficam em grupos separados (`motivo_grupo`): somar as
dirigidas à rotina inflaria a proporção de positivos justamente depois de um evento.

**Minimização:** a API devolve também `descricao_do_local` (logradouro do ponto de coleta), `local`, número da amostra
e coordenadas. O conector agrega na leitura e só guarda semana, bairro, motivo, grandeza, classe e contagem. Ponto de
coleta não é dado pessoal, mas não precisa ir para o produto.

Atraso medido em 06/11/2026 (Recife, 2025–2026): mediana de 14 dias entre coleta e registro, 90% até 35 dias. Por isso
as `SEMANAS_INCOMPLETAS` semanas mais recentes (contadas a partir do último registro) saem marcadas como incompletas.
"""

from __future__ import annotations

import re
from collections import Counter
from datetime import date, timedelta

import pandas as pd
from sqlalchemy import text

from climasense.dominio import semana_epi
from climasense.etl import gold
from climasense.etl.conectores import comum
from climasense.etl.conectores.base import Conector, ExecucaoCtx, FonteInfo, FonteSemDados
from climasense.etl.conectores.samu import chave

URL = "https://apidadosabertos.saude.gov.br/sisagua/vigilancia-parametros-basicos"
IBGE_RECIFE_6 = 261160
PAGINA = 1000
MAX_PAGINAS = (
    100  # 100 mil linhas por ano: muito acima das ~6 mil reais; evita laço sem fim se a API ignorar offset
)
ANOS_RECENTES = 2  # ano corrente e o anterior (a série do Recife começa em 11/2025)
SEMANAS_INCOMPLETAS = 6
SEM_BAIRRO = "(em branco)"
CLORO_MIN_MG_L = 0.2
CLORO_MAX_MG_L = 5.0
ROTULO = "qualidade da água, coleta de rotina, não dirigida pelo evento"

ECOLI = "ecoli"
CLORO = "cloro"


def grandeza(parametro: str) -> str | None:
    p = chave(parametro)
    if p == "ESCHERICHIA COLI":
        return ECOLI
    if p.startswith("CLORO RESIDUAL LIVRE"):
        return CLORO
    return None


def classe(grandeza_: str, resultado) -> str | None:
    """'presente' | 'ausente' (E. coli); 'dentro' | 'fora' (cloro); None = resultado que não dá para contar."""
    if grandeza_ == ECOLI:
        r = chave(str(resultado or ""))
        return {"PRESENTE": "presente", "AUSENTE": "ausente"}.get(r)
    v = comum.numero(resultado)  # negativo e texto viram ausente
    if v is None:
        return None
    return "dentro" if CLORO_MIN_MG_L <= v <= CLORO_MAX_MG_L else "fora"


def motivo_grupo(motivo: str | None) -> str:
    return "rotina" if chave(motivo or "") == "ROTINA" else "dirigida"


def _dia(texto) -> date | None:
    t = str(texto or "").strip()
    return date.fromisoformat(t[:10]) if re.fullmatch(r"\d{4}-\d\d-\d\d.*", t) else None


def agregar(linhas: list[dict]) -> tuple[dict, list[dict]]:
    """(resumo, contagens por domingo × bairro × motivo × grandeza × classe) de uma resposta completa de um ano."""
    contagem: Counter = Counter()
    motivos: Counter = Counter()
    parametros: Counter = Counter()
    ultima_coleta = ultimo_registro = None
    for r in linhas:
        parametros[str(r.get("parametro") or "")] += 1
        registro = _dia(r.get("data_de_registro_no_sisagua"))
        if registro and (ultimo_registro is None or registro > ultimo_registro):
            ultimo_registro = registro
        coleta = _dia(r.get("data_da_coleta"))
        if coleta and (ultima_coleta is None or coleta > ultima_coleta):
            ultima_coleta = coleta
        g = grandeza(r.get("parametro") or "")
        if g is None:
            continue
        if coleta is None:
            motivos["data_da_coleta_invalida"] += 1
            continue
        c = classe(g, r.get("resultado"))
        if c is None:
            motivos["resultado_nao_contavel"] += 1
            continue
        inicio = semana_epi.inicio_semana(*semana_epi.semana_de(coleta))
        bairro = re.sub(r"\s+", " ", str(r.get("area") or "").strip().upper())[:120] or SEM_BAIRRO
        contagem[(inicio, bairro, motivo_grupo(r.get("motivo_da_coleta")), g, c)] += 1
    resumo = {
        "linhas": len(linhas),
        "ultima_coleta": ultima_coleta.isoformat() if ultima_coleta else None,
        "ultimo_registro": ultimo_registro.isoformat() if ultimo_registro else None,
        "parametros": [{"parametro": p, "n": n} for p, n in sorted(parametros.items())],
        "motivos": dict(motivos),
    }
    agregados = [
        {"inicio": i.isoformat(), "bairro_fonte": b, "motivo_grupo": m, "grandeza": g, "classe": c, "n": n}
        for (i, b, m, g, c), n in sorted(contagem.items())
    ]
    return resumo, agregados


class ConectorSisagua(Conector):
    id = "sisagua"
    fonte = FonteInfo(
        "Qualidade da água por bairro e semana (SISAGUA, vigilância)",
        "Ministério da Saúde — SISAGUA / API de Dados Abertos",
        "https://apidadosabertos.saude.gov.br/v1/",
        "observada",
        None,  # termo de uso não localizado na API
    )

    def __init__(self, http=None, **kw) -> None:
        super().__init__(**kw)
        self.http = http or comum.sessao_http()
        self.descartes: dict[str, int] = {}

    def anos(self, ctx: ExecucaoCtx) -> list[int]:
        return list(range(ctx.agora.year - ANOS_RECENTES + 1, ctx.agora.year + 1))

    def _baixar_ano(self, ano: int) -> list[dict]:
        linhas: list[dict] = []
        for pagina in range(MAX_PAGINAS):
            r = self.http.get(
                URL,
                params={"codigo_ibge": IBGE_RECIFE_6, "ano": ano, "limit": PAGINA, "offset": pagina * PAGINA},
                timeout=90,
            )
            r.raise_for_status()
            corpo = r.json()
            lote = corpo.get("parametros") if isinstance(corpo, dict) else None
            if lote is None:
                raise FonteSemDados(f"A API do SISAGUA respondeu sem a chave `parametros` para {ano}.")
            linhas.extend(lote)
            if len(lote) < PAGINA:
                break
        return linhas

    def extrair(self, ctx: ExecucaoCtx) -> list[dict]:
        registros: list[dict] = []
        for ano in self.anos(ctx):
            linhas = self._baixar_ano(ano)
            if not linhas:
                continue  # ano sem análise registrada: sem dado, não zero
            resumo, agregados = agregar(linhas)
            registros.append({"tipo": "arquivo", "ano": ano, "url": URL, **resumo})
            registros.extend({"tipo": "agregado", "ano": ano, **g} for g in agregados)
        if not registros:
            raise FonteSemDados(
                "A API do SISAGUA não devolveu nenhuma análise do Recife para os anos pedidos."
            )
        return registros

    def transformar(self, bruto: pd.DataFrame, ctx: ExecucaoCtx) -> pd.DataFrame:
        from climasense.ml.alagamento import ocorrencias as oc

        mapa = oc.mapa_bairros()
        self.descartes = {}
        arquivos = bruto[bruto["tipo"] == "arquivo"]
        for m in arquivos["motivos"].dropna():
            for k, v in (m or {}).items():
                self.descartes[k] = self.descartes.get(k, 0) + int(v)
        ultima_coleta = max(date.fromisoformat(d) for d in arquivos["ultima_coleta"].dropna())
        ultimo_registro = max(date.fromisoformat(d) for d in arquivos["ultimo_registro"].dropna())
        corte = semana_epi.inicio_semana(*semana_epi.semana_de(ultimo_registro)) - timedelta(
            weeks=SEMANAS_INCOMPLETAS - 1
        )
        soma: dict[tuple, Counter] = {}
        for r in bruto[bruto["tipo"] == "agregado"].to_dict("records"):
            c = soma.setdefault(
                (date.fromisoformat(r["inicio"]), r["bairro_fonte"], r["motivo_grupo"]), Counter()
            )
            c[f"{r['grandeza']}_{r['classe']}"] += int(r["n"])
        resolvido: dict[str, str | None] = {}
        linhas = []
        for (inicio, bairro, motivo), c in sorted(soma.items()):
            if bairro not in resolvido:
                alvo = None if bairro == SEM_BAIRRO else oc.resolver_bairro(bairro, mapa)
                resolvido[bairro] = alvo[0] if alvo else None
            ecoli_presente = c["ecoli_presente"]
            cloro_fora = c["cloro_fora"]
            linhas.append(
                {
                    "inicio": inicio,
                    "bairro_fonte": bairro,
                    "territorio_id": resolvido[bairro],
                    "motivo_grupo": motivo,
                    "analises_ecoli": ecoli_presente + c["ecoli_ausente"],
                    "ecoli_presente": ecoli_presente,
                    "analises_cloro": cloro_fora + c["cloro_dentro"],
                    "cloro_fora_padrao": cloro_fora,
                    "incompleta": inicio >= corte,
                    "ultima_coleta": ultima_coleta,
                    "ultimo_registro": ultimo_registro,
                }
            )
            if resolvido[bairro] is None and bairro != SEM_BAIRRO:
                self.descartes["bairro_fora_da_base_oficial"] = self.descartes.get(
                    "bairro_fora_da_base_oficial", 0
                ) + (ecoli_presente + c["ecoli_ausente"] + cloro_fora + c["cloro_dentro"])
        return pd.DataFrame(linhas)

    def gravar_silver(self, df: pd.DataFrame, ctx: ExecucaoCtx) -> int:
        with ctx.engine.begin() as c:
            c.execute(text("delete from silver.agua_vigilancia_semana"))
            c.execute(
                text(
                    "insert into silver.agua_vigilancia_semana (inicio, bairro_fonte, territorio_id, motivo_grupo, "
                    "analises_ecoli, ecoli_presente, analises_cloro, cloro_fora_padrao, incompleta, ultima_coleta, "
                    "ultimo_registro, coletado_em, execucao_id) values (:inicio, :bairro_fonte, :territorio_id, "
                    ":motivo_grupo, :analises_ecoli, :ecoli_presente, :analises_cloro, :cloro_fora_padrao, "
                    ":incompleta, :ultima_coleta, :ultimo_registro, :coletado_em, :ex)"
                ),
                [
                    {
                        **{k: comum.valor_sql(v) for k, v in r.items()},
                        "coletado_em": ctx.agora,
                        "ex": ctx.execucao_id,
                    }
                    for r in df.to_dict("records")
                ],
            )
        return len(df)

    def gerar_gold(self, ctx: ExecucaoCtx) -> None:
        with ctx.engine.begin() as c:
            gold.recalcular(c, gold.TABELAS_AGUA)
