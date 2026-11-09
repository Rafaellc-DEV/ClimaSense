"""ETL do ClimaSense (substitui o run_etl.py).

python -m climasense.etl listar
python -m climasense.etl run open-meteo-historico [--limite DIAS]
python -m climasense.etl run apac-chuva [--modo historico [--limite MESES]]
python -m climasense.etl verificar-gold
python -m climasense.etl atualizar [--forcar] [--sem-territorio]
python -m climasense.etl tempo-real          # APAC e alertas oficiais (a cada 10–15 min)
python -m climasense.etl semanal             # saúde: InfoDengue e SINAN leptospirose (uma vez por semana)
"""

from __future__ import annotations

import argparse
import sys

from climasense.config import obter_configuracao
from climasense.etl import execucao, gold, orquestrador
from climasense.etl.conectores import CONECTORES, IMPLEMENTADOS, MODOS
from climasense.infra.mongo import conectar
from climasense.infra.postgres import engine_do_dono


def main(argv: list[str] | None = None) -> int:
    for fluxo in (sys.stdout, sys.stderr):
        if hasattr(fluxo, "reconfigure"):
            fluxo.reconfigure(encoding="utf-8")  # acentos corretos no terminal do Windows
    p = argparse.ArgumentParser(
        prog="python -m climasense.etl",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = p.add_subparsers(dest="comando", required=True)
    sub.add_parser("listar", help="Lista as fontes e o estado de cada uma")
    r = sub.add_parser("run", help="Executa uma fonte")
    r.add_argument("fonte", choices=sorted(CONECTORES))
    r.add_argument(
        "--limite", type=int, help="Open-Meteo histórico: nº de dias. APAC histórico: nº de meses."
    )
    r.add_argument("--modo", help="apac-chuva: tempo-real | historico.")
    sub.add_parser("verificar-gold", help="Recalcula a gold a partir da silver e compara")
    a = sub.add_parser("atualizar", help="Roda o pipeline inteiro (todas as fontes reais) e confere a gold")
    a.add_argument(
        "--forcar", action="store_true", help="Refaz os conjuntos estáticos mesmo se carregados há pouco"
    )
    a.add_argument("--sem-territorio", action="store_true", help="Não recarrega a base territorial")
    sub.add_parser("tempo-real", help="Só as fontes rápidas: APAC e alertas oficiais")
    sub.add_parser("semanal", help="Só as séries de saúde: InfoDengue e SINAN leptospirose")
    args = p.parse_args(argv)
    config = obter_configuracao()
    if args.comando == "listar":
        for fid, classe in sorted(CONECTORES.items()):
            estado = "implementada" if fid in IMPLEMENTADOS else "planejada"
            print(f"{fid:24} {estado:13} {classe.fonte.tipo:9} {classe.fonte.nome}")
        return 0
    engine = engine_do_dono(config)  # o ETL escreve em silver/gold (ADR 0014)
    if args.comando == "verificar-gold":
        with engine.connect() as c:
            dif = gold.verificar(c)
        for tabela, n in dif.items():
            print(f"{tabela}: {'ok' if n == 0 else f'{n} linhas diferentes'}")
        return 0 if not any(dif.values()) else 1
    if args.comando == "atualizar":
        return _atualizar(engine, config, args)
    if args.comando in ("tempo-real", "semanal"):
        ordem = orquestrador.ORDEM_TEMPO_REAL if args.comando == "tempo-real" else orquestrador.ORDEM_SEMANAL
        with conectar(config) as mongo:
            passos = orquestrador.atualizar(engine, mongo, config, forcar=True, ordem=ordem)
        for ps in passos:
            print(f"{ps.nome:28} {ps.status:8} {ps.detalhe}")
        return 0 if all(ps.status != "falha" for ps in passos) else 1
    if args.modo and args.modo not in MODOS.get(args.fonte, ()):
        print(f"{args.fonte} não tem o modo “{args.modo}”.", file=sys.stderr)
        return 2
    execucao_id = execucao.iniciar(engine, args.fonte)
    with conectar(config) as mongo:
        r = execucao.executar(engine, mongo, config, args.fonte, execucao_id, args.limite, modo=args.modo)
    print(
        f"{args.fonte}: {r['status']} · lidos {r['lidos']} · gravados {r['gravados']} · descartados {r['descartados']}"
    )
    if r["erro"]:
        print(r["erro"], file=sys.stderr)
    return 0 if r["status"] == "sucesso" else 1


def _atualizar(engine, config, args) -> int:
    from climasense.infra.postgres import fabrica_sessoes
    from climasense.territorio import carga

    with conectar(config) as mongo:

        def territorio() -> tuple[int, int]:
            geo = carga.geo_local()
            n = carga.salvar_atlas(mongo, geo, config.mongo_db_territorio)
            h = carga.salvar_hidrografia(
                mongo, carga.preparar_hidrografia(carga.carregar_hidrografia()), config.mongo_db_territorio
            )
            geo_atlas = carga.ler_atlas(
                mongo, config.mongo_db_territorio
            )  # silver a partir da leitura do Atlas
            with fabrica_sessoes(engine)() as db:
                carga.sincronizar_territorios(db, geo_atlas)
            return n + h, n + h

        passos = orquestrador.atualizar(
            engine,
            mongo,
            config,
            forcar=args.forcar,
            carregar_territorio=None if args.sem_territorio else territorio,
        )
    for ps in passos:
        print(f"{ps.nome:28} {ps.status:8} {ps.detalhe}")
    return 0 if all(ps.status != "falha" for ps in passos) else 1


if __name__ == "__main__":
    raise SystemExit(main())
