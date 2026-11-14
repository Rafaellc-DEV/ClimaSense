"""Dias locais nas próximas 72 h: sinalização interna por limiares existentes, sem I/O."""

from datetime import datetime, time, timedelta
from math import fsum, isfinite

from climasense.dominio import estagio, simulador
from climasense.etl.conectores.comum import FUSO_RECIFE


def inicio_janela(agora: datetime) -> datetime:
    hora = agora.replace(minute=0, second=0, microsecond=0)
    return hora if hora == agora else hora + timedelta(hours=1)


def resumir(previsoes: dict, distritos: dict, agora: datetime, parametros: estagio.Parametros) -> list[dict]:
    inicio = inicio_janela(agora)
    fim = inicio + timedelta(hours=72)
    dia = inicio.astimezone(FUSO_RECIFE).date()
    dias = []
    while datetime.combine(dia, time(), FUSO_RECIFE) < fim:
        a = max(inicio, datetime.combine(dia, time(), FUSO_RECIFE))
        b = min(fim, datetime.combine(dia + timedelta(days=1), time(), FUSO_RECIFE))
        horas = int((b - a).total_seconds() / 3600)
        itens = []
        for ds, nome in distritos.items():
            emissoes = previsoes.get(ds, {})
            emitida = max(emissoes) if emissoes else None
            velha = emitida is not None and not timedelta(0) <= agora - emitida <= timedelta(hours=6)
            serie = emissoes.get(emitida, [])
            por_hora = {}
            duplicadas = set()
            for t, v in serie:
                if t in por_hora:
                    duplicadas.add(t)
                por_hora[t] = v
            validos = []
            for h in range(horas):
                t = a + timedelta(hours=h)
                v = por_hora.get(t)
                if t not in duplicadas and v is not None and isfinite(v) and v >= 0:
                    validos.append(float(v))
            completa = len(validos) == horas
            soma = fsum(validos) if validos else None
            # Uma soma parcial só prova ultrapassagem; nunca prova ausência de atenção.
            pode_classificar = soma is not None and (completa or soma >= parametros.chuva_prev_24h_atencao_mm)
            classe = (
                estagio.nivel_por_limiar(
                    soma,
                    parametros.chuva_prev_24h_atencao_mm,
                    parametros.chuva_prev_24h_alerta_mm,
                    parametros.chuva_prev_24h_critico_mm,
                )
                if pode_classificar and emitida is not None and not velha
                else "sem_dados"
            )
            itens.append(
                {
                    "territorio_id": ds,
                    "nome": nome,
                    "chuva_prevista_mm": soma if completa else None,
                    "chuva_disponivel_mm": soma,
                    "horas_validas": len(validos),
                    "horas_esperadas": horas,
                    "cobertura_completa": completa,
                    "desatualizada": velha,
                    "referencia_em": emitida,
                    "sinalizacao": classe,
                    "chuva_intensa": None if classe == "sem_dados" else classe != "observacao",
                }
            )
        dias.append(
            {
                "data": dia,
                "inicio": a,
                "fim": b,
                "periodo_parcial": horas != 24,
                "horas_periodo": horas,
                "distritos": itens,
                "distritos_em_atencao": [i["territorio_id"] for i in itens if i["chuva_intensa"] is True],
                "criterios": {
                    "atencao_mm": parametros.chuva_prev_24h_atencao_mm,
                    "alerta_mm": parametros.chuva_prev_24h_alerta_mm,
                    "critico_mm": parametros.chuva_prev_24h_critico_mm,
                },
            }
        )
        dia += timedelta(days=1)
    return dias


def premissas_do_dia(dia: dict, distrito: dict, mare_no_pico: float | None) -> simulador.Premissas | None:
    """Classificação territorial só com chuva completa e recente; maré ausente reduz confiança."""
    mm = distrito["chuva_prevista_mm"]
    if mm is None or distrito["desatualizada"] or distrito["referencia_em"] is None:
        return None
    horas = dia["horas_periodo"]
    # Não extrapola períodos parciais para 24 h nem usa observação atual como solo futuro.
    return simulador.Premissas(mm, horas, None, mare_no_pico, horas, (mm, mm))
