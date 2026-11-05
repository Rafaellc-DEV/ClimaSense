import { useSyncExternalStore } from "react";
import type { MarkAreaComponentOption } from "echarts";

/**
 * Tema ECharts derivado dos tokens (design §8.4). As cores são lidas das variáveis CSS em tempo de execução,
 * então o modo escuro funciona sem um segundo tema. Ordem categórica fixa e validada — nunca ciclar cores.
 */
const PADRAO: Record<string, string> = {
  "--g-1": "#1f6fb2",
  "--g-2": "#c4612b",
  "--g-3": "#0a8f63",
  "--g-4": "#7a52c7",
  "--g-5": "#5d7f1f",
  "--g-6": "#b8478f",
  "--g-ref": "#6b7a85",
  "--g-grade": "#d5e0e7",
  "--g-eixo": "#8fa3b1",
  "--cs-tinta": "#0e2433",
  "--cs-tinta-2": "#44596a",
  "--cs-papel": "#ffffff",
  "--cs-linha": "#d5e0e7",
  "--n-insuf-bg": "#eef1f3",
  "--n-sem": "#0b6f6c",
  "--n-atencao": "#c98a00",
  "--n-alerta": "#d2581f",
  "--n-critico": "#a41f15",
  "--g-calor-1": "#fed976",
  "--g-calor-2": "#fd9a3c",
  "--g-calor-3": "#f0592a",
  "--g-calor-4": "#c81e1e",
  "--g-calor-5": "#7f0a1a",
};

export function token(nome: string): string {
  if (typeof window === "undefined") return PADRAO[nome];
  const v = getComputedStyle(document.documentElement).getPropertyValue(nome).trim();
  return v || PADRAO[nome];
}

function assinar(aviso: () => void) {
  const obs = new MutationObserver(aviso);
  obs.observe(document.documentElement, { attributes: true, attributeFilter: ["data-tema"] });
  return () => obs.disconnect();
}

/** Tema atual ("claro" ou "escuro"). Faz o componente redesenhar quando a pessoa troca, para os tokens valerem. */
export function useTemaAtual(): string {
  return useSyncExternalStore(
    assinar,
    () => document.documentElement.dataset.tema ?? "claro",
    () => "claro",
  );
}

export const SERIES = ["--g-1", "--g-2", "--g-3", "--g-4", "--g-5", "--g-6"];

export function coresSeries(): string[] {
  return SERIES.map(token);
}

export function temaClimaSense() {
  const tinta = token("--cs-tinta");
  const tinta2 = token("--cs-tinta-2");
  const eixo = {
    axisLine: { lineStyle: { color: token("--g-eixo") } },
    axisTick: { show: false },
    axisLabel: { color: tinta2, fontSize: 15, fontFamily: "inherit" },
    splitLine: { lineStyle: { color: token("--g-grade") } },
    nameTextStyle: { color: tinta2, fontSize: 15 },
  };
  return {
    color: coresSeries(),
    backgroundColor: "transparent",
    textStyle: {
      fontFamily: "Atkinson Hyperlegible Next Variable, Atkinson Hyperlegible, system-ui, sans-serif",
      color: tinta,
      fontSize: 16,
    },
    grid: { left: 56, right: 24, top: 32, bottom: 48, containLabel: true },
    legend: { textStyle: { color: tinta, fontSize: 16 }, itemWidth: 24, itemHeight: 3, icon: "rect" },
    tooltip: {
      trigger: "axis",
      backgroundColor: token("--cs-papel"),
      borderColor: token("--cs-linha"),
      textStyle: { color: tinta, fontSize: 16 },
      axisPointer: { type: "line", lineStyle: { color: token("--g-eixo"), width: 1 } },
    },
    categoryAxis: eixo,
    valueAxis: eixo,
    timeAxis: eixo,
    line: { symbol: "none", lineStyle: { width: 2.5 }, connectNulls: false },
    bar: { itemStyle: { borderRadius: [4, 4, 0, 0] }, barMaxWidth: 28 },
  };
}

/** Série de referência histórica: sempre cinza tracejado, nunca uma cor de série. */
export function estiloReferencia() {
  return {
    color: token("--g-ref"),
    lineStyle: { type: "dashed" as const, width: 2, color: token("--g-ref") },
  };
}

/** Faixa hachurada para intervalos sem dado (RN-01/RN-02). */
export function areaSemDado(inicio: string | number, fim: string | number): MarkAreaComponentOption {
  return {
    silent: true,
    itemStyle: {
      color: token("--n-insuf-bg"),
      decal: {
        symbol: "rect",
        dashArrayX: [1, 0],
        dashArrayY: [2, 4],
        rotation: Math.PI / 4,
        color: token("--g-eixo"),
      },
    },
    label: {
      show: true,
      position: "top" as const,
      formatter: "sem dados",
      color: token("--cs-tinta-2"),
      fontSize: 14,
    },
    data: [[{ xAxis: inicio }, { xAxis: fim }]] as MarkAreaComponentOption["data"],
  };
}
