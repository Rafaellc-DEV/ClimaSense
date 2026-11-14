"""Tabela de treino: uma linha por (bairro, dia), atributos conhecidos ATÉ aquele dia e o rótulo `alagou`.

Atributos (todos sem olhar o futuro):
- `chuva_1d`, `chuva_3d`, `chuva_7d`: chuva do dia e acumulados de 3 e 7 dias terminando no dia (mm, ERA5 do
  distrito ao qual o bairro pertence; o bairro herda a chuva do distrito, RN-07);
- `mare_max_m`: maior nível da maré astronômica no dia (m acima do nível médio);
- `mes`: mês do ano (sazonalidade da quadra chuvosa);
- `hist_dias_ano`: dias com atendimento de alagamento no bairro ANTES do dia, por ano de histórico
  (taxa, para não crescer só com o passar do tempo). Nunca inclui o próprio dia.

Rótulo `alagou` do dia D: houve atendimento de alagamento no bairro entre D e D + `JANELA_ROTULO_DIAS`
(a data da fonte é a da solicitação/vistoria, que chega depois do evento). Viés conhecido: um dia seco
logo antes de um atendimento também vira positivo; por isso o relatório também mede "dias com
ocorrência avisados".

Área e faixa hídrica não integram as seis features do modelo 0.2.0. A malha de bairros
está disponível para experimentos separados, sem alterar o contrato desta versão.
"""

from __future__ import annotations

from datetime import date
from math import isfinite

import pandas as pd

JANELA_ROTULO_DIAS = 3
VERSAO_ATRIBUTOS = "2-dias-reais-anteriores"
ATRIBUTOS = ["chuva_1d", "chuva_3d", "chuva_7d", "mare_max_m", "mes", "hist_dias_ano"]
NOMES = {
    "chuva_1d": "chuva do dia",
    "chuva_3d": "chuva acumulada em 3 dias",
    "chuva_7d": "chuva acumulada em 7 dias",
    "mare_max_m": "maré máxima do dia",
    "mes": "mês",
    "hist_dias_ano": "histórico de alagamento do bairro",
}


def taxa_historica(n: int, dia, inicio) -> float:
    """Mesma unidade no treino e na inferência: dias REAIS anteriores / anos decorridos."""
    anos = max((pd.Timestamp(dia) - pd.Timestamp(inicio)).days / 365.25, 1.0)
    return float(n) / anos


def atributos_diarios(
    chuva: dict[date, float], dia: date, mare: float, dias_atendimento: list[str], inicio: str
) -> dict[str, float] | None:
    """Contrato compartilhado: dia local completo e janelas terminando em D, nunca zero por falta."""
    dias = [pd.Timestamp(dia).date() - pd.Timedelta(days=k) for k in range(7)]
    valores = [chuva.get(d) for d in dias]
    if any(v is None or not isfinite(v) or v < 0 for v in valores) or not isfinite(mare):
        return None
    n = sum(inicio <= d < dia.isoformat() for d in set(dias_atendimento))
    return dict(
        zip(
            ATRIBUTOS,
            [
                valores[0],
                sum(valores[:3]),
                sum(valores),
                mare,
                float(dia.month),
                taxa_historica(n, dia, inicio),
            ],
            strict=True,
        )
    )


def acumulados(diaria: pd.DataFrame, inicio: pd.Timestamp, fim: pd.Timestamp) -> pd.DataFrame:
    """Por distrito e dia do calendário: chuva de 1, 3 e 7 dias. Faltou um dia na janela → nulo (RN-01)."""
    dias = pd.date_range(inicio - pd.Timedelta(days=6), fim, freq="D")
    partes = []
    for distrito, g in diaria.groupby("territorio_id"):
        s = g.set_index("data")["mm"].reindex(dias)
        partes.append(
            pd.DataFrame(
                {
                    "distrito_id": distrito,
                    "data": dias,
                    "chuva_1d": s.to_numpy(),
                    "chuva_3d": s.rolling(3, min_periods=3).sum().to_numpy(),
                    "chuva_7d": s.rolling(7, min_periods=7).sum().to_numpy(),
                }
            )
        )
    df = pd.concat(partes, ignore_index=True)
    return df[(df["data"] >= inicio) & (df["data"] <= fim)]


def historico(
    rotulos: pd.DataFrame, bairros: list[str], dias: pd.DatetimeIndex, inicio_historico: pd.Timestamp
) -> pd.DataFrame:
    """Taxa de dias com alagamento por ano, por bairro, usando só os dias ANTERIORES (shift de 1 dia)."""
    marcados = set(zip(rotulos["territorio_id"], rotulos["data"], strict=True))
    partes = []
    for b in bairros:
        alvo = pd.Series([(b, d) in marcados for d in dias], index=dias, dtype=float)
        anteriores = alvo.cumsum().shift(1, fill_value=0.0).to_numpy()
        taxas = [taxa_historica(int(n), d, inicio_historico) for n, d in zip(anteriores, dias, strict=True)]
        partes.append(pd.DataFrame({"territorio_id": b, "data": dias, "hist_dias_ano": taxas}))
    return pd.concat(partes, ignore_index=True)


def rotulo_com_janela(rotulos: pd.DataFrame, base: pd.DataFrame, janela_dias: int) -> pd.Series:
    """1 quando há atendimento no bairro em [D, D + janela_dias]."""
    marcados = rotulos[["territorio_id", "data"]].drop_duplicates()
    deslocados = pd.concat(
        [marcados.assign(data=marcados["data"] - pd.Timedelta(days=k)) for k in range(janela_dias + 1)]
    ).drop_duplicates()
    m = base[["territorio_id", "data"]].merge(
        deslocados.assign(_y=1), on=["territorio_id", "data"], how="left"
    )
    return pd.Series(m["_y"].fillna(0).astype(int).to_numpy(), index=base.index)


def montar_base(
    rotulos: pd.DataFrame,
    chuva_dia: pd.DataFrame,
    mare_max: pd.Series,
    bairros: dict[str, str],
    inicio: str | pd.Timestamp,
    fim: str | pd.Timestamp,
    janela_dias: int = JANELA_ROTULO_DIAS,
) -> pd.DataFrame:
    """`rotulos`: data, territorio_id (dias com atendimento). `chuva_dia`: territorio_id (distrito), data, mm.
    `mare_max`: série indexada pelo dia. `bairros`: territorio_id → distrito_id."""
    inicio, fim = pd.Timestamp(inicio).normalize(), pd.Timestamp(fim).normalize()
    dias = pd.date_range(inicio, fim, freq="D")
    rotulos = rotulos[(rotulos["data"] >= inicio) & (rotulos["data"] <= fim)]
    grade = pd.MultiIndex.from_product([sorted(bairros), dias], names=["territorio_id", "data"]).to_frame(
        index=False
    )
    grade["distrito_id"] = grade["territorio_id"].map(bairros)
    base = grade.merge(acumulados(chuva_dia, inicio, fim), on=["distrito_id", "data"], how="left")
    base["mare_max_m"] = base["data"].map(mare_max)
    base["mes"] = base["data"].dt.month
    base = base.merge(historico(rotulos, sorted(bairros), dias, inicio), on=["territorio_id", "data"])
    base["alagou"] = rotulo_com_janela(rotulos, base, janela_dias)
    base["registro"] = rotulo_com_janela(rotulos, base, 0)  # atendimento exatamente no dia (para métricas)
    base["ano"] = base["data"].dt.year
    base.attrs["janela_rotulo_dias"] = janela_dias
    return base
