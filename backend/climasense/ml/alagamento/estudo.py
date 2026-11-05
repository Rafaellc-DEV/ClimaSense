"""Orquestra o estudo: rótulos reais → atributos → validação temporal → artefato (joblib) → relatório.

Nada aqui escreve no banco: a chuva é lida da silver em modo somente leitura (ou da API de arquivo).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import pandas as pd

from climasense.ml.alagamento import armazenamento, base, clima, modelo, ocorrencias, referencia

log = logging.getLogger("climasense.ml.alagamento")
INICIO = date(2014, 1, 1)
ANO_TESTE_ROBUSTEZ = 2022  # segunda divisão, só para ver se a conclusão muda com um teste mais longo


@dataclass
class Estudo:
    rotulos: pd.DataFrame
    base: pd.DataFrame
    harmonicos: dict
    resultado: modelo.Resultado
    artefato: modelo.Artefato
    origem_chuva: str
    janela_dias: int
    diagnosticos: dict[str, modelo.Resultado] = field(default_factory=dict)


def _engine_ou_nada():
    try:
        from climasense.infra.postgres import engine_da_configuracao

        engine = engine_da_configuracao()
        with engine.connect():
            pass
        return engine
    except Exception as erro:  # noqa: BLE001 — sem banco, a chuva vem só da API de arquivo
        log.warning("Banco indisponível (%s): chuva só da API de arquivo", type(erro).__name__)
        return None


def executar(
    engine=None,
    usar_banco: bool = True,
    grade: dict | None = None,
    janela_dias: int = base.JANELA_ROTULO_DIAS,
    diagnosticos: bool = True,
) -> Estudo:
    rotulos = ocorrencias.ocorrencias_alagamento(criterio="evento")
    if rotulos.empty:
        raise RuntimeError("Nenhuma ocorrência de alagamento encontrada na fonte.")
    fim = date(int(rotulos["data"].dt.year.max()), 12, 31)
    bairros = {t: ds for t, ds in ocorrencias.mapa_bairros().values()}

    engine = engine if engine is not None else (_engine_ou_nada() if usar_banco else None)
    horaria = clima.chuva_horaria(INICIO - pd.Timedelta(days=7), fim, engine=engine)
    diaria = clima.chuva_diaria(horaria)
    harmonicos = clima.ajustar_mare(clima.serie_mare_real(fim=date.today()))
    mare = clima.mare_max_diaria(harmonicos, pd.date_range(INICIO, fim, freq="D"))

    def tabela_para(r: pd.DataFrame, janela: int) -> pd.DataFrame:
        return base.montar_base(r, diaria, mare, bairros, INICIO, fim, janela)

    tabela = tabela_para(rotulos, janela_dias)
    dias_ref = pd.date_range(date(ANO_TESTE_ROBUSTEZ, 1, 1), fim, freq="D")
    niveis = referencia.prioridades(horaria, diaria, harmonicos, dias_ref)

    def rodar(t: pd.DataFrame, ano_teste: int, janela: int) -> modelo.Resultado:
        _, teste = modelo.dividir(t, ano_teste)
        ref = referencia.nivel_por_linha(teste, niveis)
        return modelo.treinar(t, ref, grade, ano_teste=ano_teste, janela_dias=janela)

    resultado = rodar(tabela, modelo.ANO_TESTE, janela_dias)
    extras: dict[str, modelo.Resultado] = {}
    if diagnosticos:
        extras[f"teste desde {ANO_TESTE_ROBUSTEZ}"] = rodar(tabela, ANO_TESTE_ROBUSTEZ, janela_dias)
        extras["rótulo sem janela (só o dia do atendimento)"] = rodar(
            tabela_para(rotulos, 0), modelo.ANO_TESTE, 0
        )
        amplo = ocorrencias.ocorrencias_alagamento(criterio="amplo")
        extras["rótulo amplo (inclui monitoramento de rotina)"] = rodar(
            tabela_para(amplo, janela_dias), modelo.ANO_TESTE, janela_dias
        )
    artefato = modelo.montar_artefato(resultado, tabela, harmonicos, ocorrencias.URL_CONJUNTO, "evento")
    artefato.validacao["janela_rotulo_dias"] = janela_dias
    origem = (
        "silver.observacoes (open-meteo-historico, somente leitura) + API de arquivo Open-Meteo para os anos "
        "que o banco não tem"
        if engine is not None
        else "API de arquivo Open-Meteo (ERA5)"
    )
    return Estudo(rotulos, tabela, harmonicos, resultado, artefato, origem, janela_dias, extras)


def salvar(estudo: Estudo, caminho_modelo: Path | None = None) -> Path:
    return armazenamento.salvar(estudo.artefato, caminho_modelo)
