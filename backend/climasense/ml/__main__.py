"""CLI dos estudos de ML: `python -m climasense.ml alagamento`. Lê o banco só para leitura."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def comando_alagamento(args: argparse.Namespace) -> int:
    """Risco de alagamento (F6): treina, valida no tempo, salva o modelo (joblib) e grava o relatório."""
    from climasense.ml.alagamento import estudo, relatorio

    try:
        e = estudo.executar(usar_banco=not args.sem_banco, diagnosticos=not args.sem_diagnosticos)
    except Exception as erro:  # noqa: BLE001 — sem mensagens de drivers/URLs ou artefatos de resultado parcial
        status = getattr(getattr(erro, "response", None), "status_code", None)
        detalhe = f"; HTTP {status}" if status is not None else ""
        print(
            f"[alagamento] Estudo interrompido ({type(erro).__name__}{detalhe}). Nenhum modelo ou relatório novo foi salvo.",
            file=sys.stderr,
        )
        return 1
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
    print(f"[alagamento] publicável: {e.artefato.publicavel} {e.artefato.motivo or ''}")
    print(f"[alagamento] modelo salvo em {estudo.salvar(e, args.modelo)}")
    print(f"[alagamento] relatório em {relatorio.gravar(e, args.saida)}")
    return 0


def comando_prever(args: argparse.Namespace) -> int:
    import json
    from datetime import UTC, datetime

    from climasense.infra.postgres import engine_da_configuracao, fabrica_sessoes
    from climasense.ml.alagamento.prever import executar

    with fabrica_sessoes(engine_da_configuracao())() as db:
        resultado = executar(db, datetime.now(UTC), args.horizonte, args.persistir)
    print(json.dumps(resultado, ensure_ascii=False, default=str))
    return 0


def comando_previa_local(args: argparse.Namespace) -> int:
    """Treina UMA configuração fixa, salva artefato NÃO PUBLICÁVEL, sem tocar em relatórios oficiais."""
    from climasense.config import obter_configuracao
    from climasense.ml.alagamento import estudo
    from climasense.ml.alagamento.base import ATRIBUTOS

    if obter_configuracao().ambiente != "desenvolvimento":
        print("[prévia] disponível somente em AMBIENTE=desenvolvimento.", file=sys.stderr)
        return 2
    grade = {"max_depth": [4], "min_samples_leaf": [20], "class_weight": ["balanced"]}
    try:
        e = estudo.executar(
            usar_banco=not args.sem_banco,
            grade=grade,
            conjuntos={"completo": list(ATRIBUTOS)},
            diagnosticos=False,
        )
        caminho = estudo.salvar(e, args.modelo)
    except Exception as erro:  # noqa: BLE001 — não exibir credenciais nem URLs
        print(f"[prévia] falhou: {type(erro).__name__}", file=sys.stderr)
        return 1
    print("[prévia] modelo fixo salvo SOMENTE para pesquisa em", caminho)
    print("[prévia] AUC-PR teste:", e.resultado.teste["modelo"]["auc_pr"])
    print("[prévia] publicável:", e.artefato.publicavel)
    print("[prévia] motivo:", e.artefato.motivo)
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
    d = sub.add_parser(
        "alagamento-previa-local",
        help="treino FIXO rápido, SOMENTE demonstração de pesquisa local não validada",
    )
    d.add_argument("--modelo", type=Path, default=None)
    d.add_argument("--sem-banco", action="store_true")
    d.set_defaults(func=comando_previa_local)
    i = sub.add_parser("prever-impacto", help="analisar a previsão armazenada; nunca treina")
    i.add_argument("--horizonte", type=int, choices=range(1, 73), default=24)
    i.add_argument(
        "--persistir", action="store_true", help="inserir histórico após migração 0025; padrão: só leitura"
    )
    i.set_defaults(func=comando_prever)
    return p


def main(argv: list[str] | None = None) -> int:
    args = construir_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
