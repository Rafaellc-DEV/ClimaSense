"""Inferência explícita (sem treinamento); persistência só mediante --persistir na CLI.

Reaproveita o serviço territorial e o artefato. Não contém fit nem busca de parâmetros.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, date, datetime

from sqlalchemy import text


def _json(valor) -> str:
    def temporal(v):
        if isinstance(v, datetime):
            v = v.replace(tzinfo=UTC) if v.tzinfo is None else v.astimezone(UTC)
            return v.isoformat()
        if isinstance(v, date):
            return v.isoformat()
        raise TypeError("Tipo de insumo não serializável.")

    return json.dumps(valor, ensure_ascii=False, sort_keys=True, default=temporal, allow_nan=False)


def registros(resultado: dict) -> list[dict]:
    """Somente previsão atual; modelo rejeitado nunca produz linha de ML."""
    if resultado.get("contexto") != "previsao_atual" or resultado.get("dia_selecionado") is not None:
        raise ValueError(
            "Persistência operacional aceita somente análise contínua da previsão atual, sem recorte diário."
        )
    saida = []
    for item in resultado["itens"]:
        if item["nivel"] != "bairro":
            continue
        a = item["avaliacao"]
        for tipo in ("alagamento", "deslizamento"):
            registro = {
                "territorio_id": item["territorio_id"],
                "distrito_id": item["distrito_id"],
                "tipo_impacto": tipo,
                "metodo": a["metodo"],
                "versao_modelo": a["versao"],
                "classe_resultado": item[f"classe_{tipo}"],
                "confianca_qualitativa": item["confianca"],
                "status_validacao": "regra_experimental",
                "data_previsao": resultado["calculado_em"],
                "emitido_em_fonte": a["emitido_em_fonte"],
                "inicio_validade": a["inicio_validade"],
                "fim_validade": a["fim_validade"],
                "horizonte_h": a["horizonte_h"],
                "fonte_meteorologica": a["fonte_meteorologica"],
                "fatores": item["motivos"],
                "insumos": {**a, "exposicao": item["impacto_pessoas"]},
                "motivo_indisponibilidade": (", ".join(a["faltando"]) or "; ".join(item["motivos"]))
                if item[f"classe_{tipo}"] == "sem_dados"
                else None,
            }
            saida.append(registro)
        # O ML avalia dias locais, não uma janela horária equivalente à das regras.
        # Não persistir como inferência horária sem validação operacional desse contrato.
    for r in saida:
        identidade = {k: v for k, v in r.items() if k != "data_previsao"}
        r["hash_entrada"] = hashlib.sha256(_json(identidade).encode()).hexdigest()
    return saida


def persistir(db, resultado: dict) -> int:
    """Inserção acumulativa e idempotente. Nenhum DELETE, UPDATE ou recálculo de gold."""
    novos = 0
    try:
        for r in registros(resultado):
            novos += db.execute(
                text(
                    "insert into silver.inferencias_impacto (territorio_id, distrito_id, tipo_impacto, metodo, "
                    "versao_modelo, classe_resultado, confianca_qualitativa, status_validacao, data_previsao, "
                    "emitido_em_fonte, inicio_validade, fim_validade, horizonte_h, fonte_meteorologica, fatores, "
                    "insumos, motivo_indisponibilidade, hash_entrada) values (:territorio_id, :distrito_id, "
                    ":tipo_impacto, :metodo, :versao_modelo, :classe_resultado, :confianca_qualitativa, "
                    ":status_validacao, :data_previsao, :emitido_em_fonte, :inicio_validade, :fim_validade, "
                    ":horizonte_h, :fonte_meteorologica, cast(:fatores as jsonb), cast(:insumos as jsonb), "
                    ":motivo_indisponibilidade, :hash_entrada) on conflict (hash_entrada) do nothing"
                ),
                {**r, "fatores": _json(r["fatores"]), "insumos": _json(r["insumos"])},
            ).rowcount
        db.commit()
    except Exception:
        db.rollback()
        raise
    return novos


def executar(db, agora, horizonte_h: int = 24, gravar: bool = False) -> dict:
    from climasense.servicos.impacto_territorial import analisar

    resultado = analisar(db, agora, horizonte_h)
    if gravar:
        resultado["registros_inseridos"] = persistir(db, resultado)
    return resultado
