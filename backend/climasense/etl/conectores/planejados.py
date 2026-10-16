"""Fontes especificadas e ainda não integradas (aparecem como “Planejada”). Cada uma tem dicionário de dados
em docs/dicionario-dados/. Para integrar: implemente extrair/transformar/gravar_silver e marque
`implementada = true` em app.fontes."""

from __future__ import annotations

from climasense.etl.conectores.base import Conector, ConectorPlanejado, FonteInfo


class _Planejado(Conector):
    motivo = "Conector planejado: acesso e formato ainda não verificados."

    def extrair(self, ctx):
        raise ConectorPlanejado(self.motivo)

    def transformar(self, bruto, ctx):
        raise ConectorPlanejado(self.motivo)

    def gravar_silver(self, df, ctx):
        raise ConectorPlanejado(self.motivo)


class ConectorAnaTelemetria(_Planejado):
    id = "ana-telemetria"
    fonte = FonteInfo(
        "Chuva e nível de rios (estações telemétricas)",
        "ANA — HidroWebService",
        "https://www.gov.br/ana/pt-br",
        "observada",
    )
    motivo = "Conector planejado: exige cadastro na ANA (ANA_USUARIO e ANA_SENHA no .env)."


class ConectorApacChuva(_Planejado):
    id = "apac-chuva"
    fonte = FonteInfo(
        "Chuva acumulada em 24 h", "APAC", "https://www.apac.pe.gov.br/monitoramento", "observada"
    )


class ConectorInmet(_Planejado):
    id = "inmet"
    fonte = FonteInfo("Estação automática Recife (A301)", "INMET", "https://portal.inmet.gov.br", "observada")


class ConectorCemaden(_Planejado):
    id = "cemaden"
    fonte = FonteInfo("Pluviômetros automáticos", "Cemaden", "https://www.gov.br/cemaden", "observada")


class ConectorRecifeAlagamento(_Planejado):
    id = "recife-alagamento"
    fonte = FonteInfo(
        "Ocorrências de alagamento (Defesa Civil)",
        "Prefeitura do Recife (Dados Abertos)",
        "https://dados.recife.pe.gov.br/dataset?tags=alagamento",
        "observada",
    )
    motivo = "Conector planejado: o conjunto exato e o formato dos registros ainda precisam ser confirmados no catálogo."


class ConectorMareMarinha(_Planejado):
    id = "mare-marinha"
    fonte = FonteInfo(
        "Tábua de maré oficial do Porto do Recife",
        "Marinha do Brasil — CHM",
        "https://www.marinha.mil.br/chm/tabuas-de-mare",
        "prevista",
    )
