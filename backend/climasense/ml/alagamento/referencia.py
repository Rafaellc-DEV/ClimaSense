"""Aplica o `EstimadorReferencia` (regra da tela de cenários) aos dias do passado, para comparar com o modelo.

Para cada distrito e dia D do teste, a regra recebe: a chuva horária REAL de D como se fosse a previsão
(cenário otimista para a regra: previsão perfeita), a maré astronômica horária de D e todos os dias de
chuva anteriores a D como histórico. A prioridade vira um nível: sem indicação 0, atenção 1, alerta 2,
crítico 3; "dados insuficientes" fica nulo (não conta como aviso, RN-01).
"""

from __future__ import annotations

from datetime import datetime

import numpy as np
import pandas as pd

from climasense.dominio import cenario
from climasense.ml.alagamento.clima import prever_mare
from climasense.modelos.estimador import EstimadorReferencia

NIVEL = {"sem_indicacao": 0, "atencao": 1, "alerta": 2, "critico": 3, "dados_insuficientes": None}


def prioridades(
    horaria: pd.DataFrame, diaria: pd.DataFrame, harmonicos: dict, dias: pd.DatetimeIndex
) -> pd.DataFrame:
    """Prioridade da regra por (distrito_id, data)."""
    estimador = EstimadorReferencia()
    linhas = []
    for distrito, h in horaria.groupby("territorio_id"):
        h = h.set_index("hora")["mm"].sort_index()
        d = diaria[diaria["territorio_id"] == distrito].set_index("data")["mm"].sort_index()
        acumulado = d.to_numpy()
        datas_hist = d.index.to_numpy()
        for dia in dias:
            ini = pd.Timestamp(dia)
            fim = ini + pd.Timedelta(hours=24)
            chuva_d = h.loc[ini : fim - pd.Timedelta(hours=1)]
            horas = pd.date_range(ini, periods=24, freq="h")
            mare = prever_mare(harmonicos, horas)
            n_hist = int(np.searchsorted(datas_hist, np.datetime64(ini)))
            insumos = cenario.Insumos(
                chuva_prevista=[(t.to_pydatetime(), float(v)) for t, v in chuva_d.items()],
                mare_prevista=[(t.to_pydatetime(), float(v)) for t, v in zip(horas, mare, strict=True)],
                chuva_historica_diaria=acumulado[:n_hist].tolist(),
                ocorrencias_historicas=None,
            )
            emitida = datetime.combine(ini.date(), datetime.min.time())
            est = estimador.estimar(distrito, 24, insumos, emitida)
            linhas.append({"distrito_id": distrito, "data": ini, "nivel": NIVEL[est.prioridade]})
    return pd.DataFrame(linhas)


def nivel_por_linha(teste: pd.DataFrame, niveis: pd.DataFrame) -> pd.Series:
    m = teste[["distrito_id", "data"]].merge(niveis, on=["distrito_id", "data"], how="left")
    return pd.Series(m["nivel"].to_numpy(dtype=float), index=teste.index)
