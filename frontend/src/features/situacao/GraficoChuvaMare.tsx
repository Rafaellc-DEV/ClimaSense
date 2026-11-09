import { useMemo } from "react";
import type { EChartsOption } from "echarts";
import { QuadroGrafico } from "@/charts/QuadroGrafico";
import { token, useTemaAtual } from "@/charts/tema";
import { CarregandoLista } from "@/design-system/componentes/Esqueleto";
import { fontesDado } from "@/design-system/componentes/EstadoDados";
import { EstadoConsulta } from "@/features/evento/Evento";
import { nomeDistrito } from "@/lib/distritos";
import { formatarDataHora, formatarHora, formatarNumero } from "@/lib/formatos";
import type { FonteMeta } from "@/lib/frescor";
import type { UseQueryResult } from "@tanstack/react-query";
import type { ErroApi } from "@/lib/api";
import { achaFonte, type CenarioHora } from "./dados";
import estilos from "./Situacao.module.css";

/** Previsão de chuva por hora (barras tracejadas, com a faixa de incerteza) e a maré prevista, com o marcador "agora". */
export function montarGrafico(c: CenarioHora, agora = Date.now()) {
  const tempo = (t: string) => new Date(t).getTime();
  const chuva = c.chuva.map((p) => [tempo(p.t), p.valor, p.min, p.max] as const);
  const cor = token("--g-1");
  const corMare = token("--g-2");
  const todos = [...c.chuva.map((p) => tempo(p.t)), ...c.mare.map((p) => tempo(p.t))];
  const min = Math.min(...todos);
  const max = Math.max(...todos);
  const opcao: EChartsOption = {
    legend: {
      top: 0,
      left: 0,
      data: ["Chuva prevista (mm/h)", "Faixa de incerteza", "Maré prevista (m)"],
    },
    tooltip: {
      trigger: "axis",
      formatter: (ps: unknown) => {
        const l = ps as { axisValue: number; seriesName: string; value: (number | null)[] }[];
        if (!l.length) return "";
        const t = l[0].axisValue;
        const linhas = l
          .filter((p) => p.seriesName === "Chuva prevista (mm/h)" || p.seriesName.startsWith("Maré"))
          .map((p) => {
            const v = p.value[1];
            return `${p.seriesName}: <strong>${v === null || v === undefined ? "sem dado" : formatarNumero(v, p.seriesName.startsWith("Maré") ? 2 : 1)}</strong>`;
          });
        return `${formatarDataHora(new Date(t))}<br>${linhas.join("<br>")}`;
      },
    },
    grid: { left: 48, right: 48, top: 84, bottom: 32 },
    xAxis: {
      type: "time",
      min,
      max,
      splitLine: { show: false },
      axisLabel: { formatter: (v: number) => formatarHora(new Date(v), true), hideOverlap: true },
    },
    yAxis: [
      { type: "value", min: 0, name: "mm/h", nameGap: 8 },
      { type: "value", scale: true, name: "m", nameGap: 8, splitLine: { show: false } },
    ],
    series: [
      {
        name: "base",
        type: "line",
        stack: "faixa",
        symbol: "none",
        silent: true,
        lineStyle: { opacity: 0 },
        tooltip: { show: false },
        data: chuva.map((p) => [p[0], p[2]]),
      },
      {
        name: "Faixa de incerteza",
        type: "line",
        stack: "faixa",
        symbol: "none",
        silent: true,
        lineStyle: { opacity: 0 },
        areaStyle: { color: cor, opacity: 0.18 },
        data: chuva.map((p) => [p[0], p[2] !== null && p[3] !== null ? p[3] - p[2] : null]),
      },
      {
        name: "Chuva prevista (mm/h)",
        type: "bar",
        barMaxWidth: 10,
        itemStyle: {
          color: cor,
          opacity: 0.35,
          borderColor: cor,
          borderWidth: 1.5,
          borderType: "dashed",
          borderRadius: [3, 3, 0, 0],
        },
        data: chuva.map((p) => [p[0], p[1]]),
        markLine:
          agora >= min && agora <= max
            ? {
                silent: true,
                symbol: "none",
                lineStyle: { type: "dashed", color: token("--cs-tinta-2"), width: 1.5 },
                label: { formatter: "agora", position: "insideEndTop" },
                data: [{ xAxis: agora }],
              }
            : undefined,
      },
      {
        name: "Maré prevista (m)",
        type: "line",
        yAxisIndex: 1,
        symbol: "none",
        lineStyle: { width: 2, color: corMare },
        itemStyle: { color: corMare },
        data: c.mare.map((p) => [tempo(p.t), p.valor]),
      },
    ],
  };
  const mares = new Map(c.mare.map((p) => [p.t, p.valor]));
  const tabela = {
    colunas: ["Hora", "Chuva prevista (mm/h)", "Mínimo", "Máximo", "Maré prevista (m)"],
    linhas: c.chuva.map((p) => [formatarDataHora(p.t), p.valor, p.min, p.max, mares.get(p.t) ?? null]),
  };
  const total = c.chuva.reduce((s, p) => s + (p.valor ?? 0), 0);
  const resumo = `${nomeDistrito(c.territorio_nome)}: ${formatarNumero(total, 1)} mm previstos no período, hora a hora, com a maré prevista.`;
  return { opcao, tabela, resumo };
}

export function GraficoChuvaMare({
  cenario,
  fontes,
}: {
  cenario: UseQueryResult<{ dados: CenarioHora }, ErroApi>;
  fontes: FonteMeta[];
}) {
  const modo = useTemaAtual();
  const c = cenario.data?.dados;
  const g = useMemo(
    () => (c && (c.chuva.length || c.mare.length) ? montarGrafico(c) : null),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [c, modo],
  );
  return (
    <section className={estilos.bloco} aria-labelledby="se-grafico">
      <h2 id="se-grafico" className={estilos.pergunta}>
        Chuva e maré
      </h2>
      {cenario.isPending ? (
        <div className={estilos.esqueleto}>
          <p className={estilos.carregando}>Carregando…</p>
          <CarregandoLista linhas={1} altura="14rem" texto="Carregando o gráfico de chuva e maré…" />
        </div>
      ) : cenario.isError ? (
        <EstadoConsulta
          erro={cenario.error}
          oQue="a previsão hora a hora"
          aoTentar={() => cenario.refetch()}
        />
      ) : !g ? (
        <p className={estilos.insuficiente}>
          <b>Dados insuficientes:</b> falta a previsão de chuva e maré (Open-Meteo).
        </p>
      ) : (
        <>
          <QuadroGrafico
            titulo="Previsão hora a hora"
            resumo={g.resumo}
            opcao={g.opcao}
            tabela={g.tabela}
            altura={300}
            fontes={fontesDado(achaFonte(fontes, "open-meteo-previsao", "open-meteo-mare"))}
          />
          <p className={estilos.insuficiente}>
            <b>Dados insuficientes:</b> falta a chuva medida hora a hora (série horária dos pluviômetros,
            APAC).
          </p>
        </>
      )}
    </section>
  );
}
