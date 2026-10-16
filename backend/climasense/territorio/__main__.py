"""python -m climasense.territorio carregar [--baixar]  |  python -m climasense.territorio mapa [--local] [--saida arquivo.html]"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from climasense.config import obter_configuracao
from climasense.etl import execucao
from climasense.infra.mongo import conectar
from climasense.infra.postgres import engine_da_configuracao, fabrica_sessoes
from climasense.territorio import carga, mapa_portatil


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m climasense.territorio", description=__doc__)
    sub = p.add_subparsers(dest="comando", required=True)
    c = sub.add_parser(
        "carregar", help="Grava distritos e faixas hídricas no Atlas e sincroniza app.territorios"
    )
    c.add_argument("--baixar", action="store_true", help="Atualiza os arquivos oficiais antes da carga")
    m = sub.add_parser("mapa", help="Gera o HTML portátil do território")
    m.add_argument(
        "--local", action="store_true", help="Gera a partir dos arquivos oficiais locais, sem Atlas"
    )
    m.add_argument("--saida", default="mapa_distritos_sanitarios.html")
    args = p.parse_args(argv)
    config = obter_configuracao()
    try:
        if args.comando == "carregar":
            engine = engine_da_configuracao(config)
            execucao_id = execucao.iniciar(
                engine, "territorio-oficial"
            )  # aparece em Fontes de dados (RF-12.5)
            if args.baixar:
                carga.baixar_dados()
            geo = carga.geo_local()
            with conectar(config) as cliente:
                n = carga.salvar_atlas(cliente, geo, config.mongo_db_territorio)
                h = carga.salvar_hidrografia(
                    cliente,
                    carga.preparar_hidrografia(carga.carregar_hidrografia()),
                    config.mongo_db_territorio,
                )
            with fabrica_sessoes(engine)() as db:
                t = carga.sincronizar_territorios(db, geo)
            execucao.concluir(engine, execucao_id, lidos=n + h, gravados=n + h)
            print(
                f"{n} distritos e {h} faixas hídricas gravados em {config.mongo_db_territorio}. {t} territórios sincronizados."
            )
        else:
            if args.local:
                geo, fonte = (
                    carga.geo_local(),
                    "arquivos oficiais locais (sem consulta ao Atlas nesta geração)",
                )
            else:
                with conectar(config) as cliente:
                    geo = carga.ler_atlas(cliente, config.mongo_db_territorio)
                fonte = f"MongoDB Atlas · {config.mongo_db_territorio}.DistritosSanitarios"
            water = carga.carregar_hidrografia()
            Path(args.saida).write_text(mapa_portatil.gerar(geo, water, fonte), encoding="utf-8")
            print(f"Mapa gerado: {args.saida}. Origem: {fonte}.")
    except Exception as erro:  # noqa: BLE001
        if args.comando == "carregar" and "execucao_id" in locals():
            execucao.concluir(engine, execucao_id, erro=f"Carga territorial falhou ({type(erro).__name__}).")
        print(
            f"Não concluído ({type(erro).__name__}): confira o .env, a rede e os arquivos em data/territorio.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
