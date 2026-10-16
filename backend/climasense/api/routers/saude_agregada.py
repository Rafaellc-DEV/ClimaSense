"""Saúde agregada (T6.5, RF-15): vacinação por distrito e mês. Só agregados; contagens pequenas suprimidas (RN-13)
e o rótulo de amostra quando a extração é parcial (RN-10)."""

from __future__ import annotations

from datetime import date, datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from climasense.api.autorizacao import Contexto, exige, relogio
from climasense.api.envelope import Amostra, Meta, RecorteMeta, RespostaDados
from climasense.dominio.papeis import Permissao
from climasense.dominio.recorte import granularidade
from climasense.infra.postgres import obter_sessao
from climasense.servicos import fontes as servico_fontes
from climasense.servicos.territorio import no_maximo_distrito

router = APIRouter(prefix="/saude", tags=["Saúde agregada"])
consultar = exige(Permissao.CONSULTAR)


class CelulaVacinacao(BaseModel):
    territorio_id: str
    mes: date
    doses: int | None
    suprimido: bool


@router.get(
    "/vacinacao",
    response_model=RespostaDados[list[CelulaVacinacao]],
    summary="Doses aplicadas por distrito e mês (agregado, com amostra)",
)
def vacinacao(
    territorio_id: str = "recife",
    inicio: date | None = None,
    fim: date | None = None,
    _: Contexto = Depends(consultar),
    db: Session = Depends(obter_sessao),
    agora: datetime = Depends(relogio),
) -> RespostaDados[list[CelulaVacinacao]]:
    t = no_maximo_distrito(db, territorio_id)
    filtro_ds = None if t.usado == "recife" else int(t.usado.removeprefix("ds-"))
    linhas = (
        db.execute(
            text(
                "select distrito_codigo, mes, doses, suprimido, amostra_n, total_fonte from gold.vacinacao_distrito_mes "
                "where (cast(:d as smallint) is null or distrito_codigo = :d) "
                "and (cast(:i as date) is null or mes >= date_trunc('month', cast(:i as date))) "
                "and (cast(:f as date) is null or mes <= :f) order by mes, distrito_codigo"
            ),
            {"d": filtro_ds, "i": inicio, "f": fim},
        )
        .mappings()
        .all()
    )
    n = sum(r["amostra_n"] for r in linhas)
    total = max((r["total_fonte"] or 0 for r in linhas), default=0) or None
    avisos = list(t.avisos)
    if linhas and (total is None or n < total):
        avisos.append(f"Amostra de {n} registros, não representa o total.")
    if any(r["suprimido"] for r in linhas):
        avisos.append(
            "Meses com menos de 5 doses no distrito aparecem como suprimidos, para proteger a privacidade."
        )
    return RespostaDados(
        dados=[
            CelulaVacinacao(
                territorio_id=f"ds-{r['distrito_codigo']}",
                mes=r["mes"],
                doses=r["doses"],
                suprimido=r["suprimido"],
            )
            for r in linhas
        ],
        meta=Meta(
            fontes=[servico_fontes.meta(db, "vacinacao", agora)],
            recorte=RecorteMeta(
                territorio_id=t.usado, inicio=inicio, fim=fim, granularidade=granularidade(t.usado)
            ),
            amostra=Amostra(n=n, total_fonte=total) if linhas else None,
            avisos=avisos,
            dados_insuficientes=not linhas,
        ),
    )
