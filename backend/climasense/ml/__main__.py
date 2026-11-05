"""CLI dos estudos de ML: `python -m climasense.ml alagamento`. Lê o banco só para leitura."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def comando_alagamento(args: argparse.Namespace) -> int:
    """Risco de alagamento (F6): treina, valida no tempo, salva o modelo (joblib) e grava o relatório."""
    from climasense.ml.alagamento import estudo, relatorio

    e = estudo.executar(usar_banco=not args.sem_banco, diagnosticos=not args.sem_diagnosticos)
    r = e.resultado
    print(
        f"[alagamento] {len(e.rotulos)} bairro-dias com atendimento real ({e.rotulos['data'].min().date()} "
        f"a {e.rotulos['data'].max().date()})"
    )
    print(
        f"[alagamento] escolhida: {r.escolhida.conjunto} {r.escolhida.parametros} "
        f"AUC-PR(validação)={r.escolhida.auc_pr_oof:.4f}"
    )
    for nome, m in r.teste.items():
        print(
            f"[alagamento] teste {nome}: recall={m['recall']} precisão={m['precisao']} auc_pr={m['auc_pr']}"
        )
    print(f"[alagamento] publicável: {r.publicavel} {r.motivo or ''}")
    print(f"[alagamento] modelo salvo em {estudo.salvar(e, args.modelo)}")
    print(f"[alagamento] relatório em {relatorio.gravar(e, args.saida)}")
    return 0


def construir_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m climasense.ml", description=__doc__)
    sub = p.add_subparsers(dest="comando", required=True)
    a = sub.add_parser(
        "alagamento", help="risco de alagamento por bairro (F6): treino, validação e relatório"
    )
    a.add_argument("--saida", type=Path, default=None, help="pasta do relatório (padrão: docs/ml)")
    a.add_argument("--modelo", type=Path, default=None, help="arquivo do modelo (padrão: tmp/modelos/)")
    a.add_argument("--sem-banco", action="store_true", help="chuva só da API de arquivo da Open-Meteo")
    a.add_argument("--sem-diagnosticos", action="store_true", help="pula as divisões e rótulos alternativos")
    a.set_defaults(func=comando_alagamento)
    return p


def main(argv: list[str] | None = None) -> int:
    args = construir_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
