"""ETL do ClimaSense (substitui o run_etl.py).

python -m climasense.etl listar
python -m climasense.etl run vacinacao [--limite 1000]
python -m climasense.etl run open-meteo-historico [--limite DIAS]
python -m climasense.etl verificar-gold
"""

from __future__ import annotations

import argparse
import sys

from climasense.config import obter_configuracao
from climasense.etl import execucao, gold
from climasense.etl.conectores import CONECTORES, IMPLEMENTADOS
from climasense.infra.mongo import conectar
from climasense.infra.postgres import engine_da_configuracao


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="python -m climasense.etl",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = p.add_subparsers(dest="comando", required=True)
    sub.add_parser("listar", help="Lista as fontes e o estado de cada uma")
    r = sub.add_parser("run", help="Executa uma fonte")
    r.add_argument("fonte", choices=sorted(CONECTORES))
    r.add_argument("--limite", type=int, help="Vacinação: nº de registros. Open-Meteo histórico: nº de dias.")
    sub.add_parser("verificar-gold", help="Recalcula a gold a partir da silver e compara")
    args = p.parse_args(argv)
    config = obter_configuracao()
    if args.comando == "listar":
        for fid, classe in sorted(CONECTORES.items()):
            estado = "implementada" if fid in IMPLEMENTADOS else "planejada"
            print(f"{fid:24} {estado:13} {classe.fonte.tipo:9} {classe.fonte.nome}")
        return 0
    engine = engine_da_configuracao(config)
    if args.comando == "verificar-gold":
        with engine.connect() as c:
            dif = gold.verificar(c)
        for tabela, n in dif.items():
            print(f"{tabela}: {'ok' if n == 0 else f'{n} linhas diferentes'}")
        return 0 if not any(dif.values()) else 1
    execucao_id = execucao.iniciar(engine, args.fonte)
    with conectar(config) as mongo:
        r = execucao.executar(engine, mongo, config, args.fonte, execucao_id, args.limite)
    print(
        f"{args.fonte}: {r['status']} · lidos {r['lidos']} · gravados {r['gravados']} · descartados {r['descartados']}"
    )
    if r["erro"]:
        print(r["erro"], file=sys.stderr)
    return 0 if r["status"] == "sucesso" else 1


if __name__ == "__main__":
    raise SystemExit(main())
