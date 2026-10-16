import { useMemo } from "react";
import type { EChartsOption } from "echarts";
import { QuadroGrafico } from "@/charts/QuadroGrafico";
import type { Esquemas } from "@/lib/api";
import { formatarMm, nomeMes } from "@/lib/formatos";

const RAMPA = ["#e3eef7", "#b9d4ea", "#86b3d9", "#4f8cc2", "#1f6fb2", "#17558a", "#0e3a60"];

/** Calendário ano × mês em mapa de calor (RF-08.5): uma só matiz azul; mês sem dado completo fica vazio e hachurado. */
export function Calendario({
  dados,
  fontes,
}: {
  dados: Esquemas["Sazonalidade"];
  fontes: Esquemas["FonteMeta"][];
}) {
  const { opcao, tabela, resumo } = useMemo(() => {
    const anos = dados.anos.map(String);
    const meses = Array.from({ length: 12 }, (_, i) => nomeMes(i + 1, true));
    const porCelula = new Map(dados.celulas.map((c) => [`${c.ano}-${c.mes}`, c]));
    const comValor = dados.celulas.filter((c) => c.valor !== null);
    const max = Math.max(...comValor.map((c) => c.valor as number), 1);
    const maisChuvoso = comValor.reduce((a, b) => ((b.valor ?? 0) > (a.valor ?? 0) ? b : a), comValor[0]);
    const mediaPorMes = Array.from({ length: 12 }, (_, i) => {
      const v = comValor.filter((c) => c.mes === i + 1).map((c) => c.valor as number);
      return v.length ? v.reduce((s, x) => s + x, 0) / v.length : null;
    });
    const mesTopo = mediaPorMes.indexOf(Math.max(...mediaPorMes.map((v) => v ?? -1)));
    const o: EChartsOption = {
      grid: { left: 56, right: 16, top: 8, bottom: 72, containLabel: true },
      tooltip: {
        trigger: "item",
        formatter: (p) => {
          const [m, a] = (p as unknown as { data: [number, number, number] }).data;
          const c = porCelula.get(`${anos[a]}-${m + 1}`);
          return `${nomeMes(m + 1)} de ${anos[a]}<br><strong>${
            c?.valor === null || !c ? "sem dado completo" : formatarMm(c.valor)
          }</strong>`;
        },
      },
      xAxis: { type: "category", data: meses, splitArea: { show: false } },
      yAxis: { type: "category", data: anos, inverse: true },
      visualMap: [
        {
          min: 0,
          max,
          calculable: false,
          orient: "horizontal",
          left: "center",
          bottom: 0,
          itemHeight: 160,
          text: [formatarMm(max, 0), "0 mm"],
          inRange: { color: RAMPA },
          seriesIndex: 0,
        },
        { show: false, seriesIndex: 1, min: -1, max: -1, inRange: { color: ["#eef1f3"] } },
      ],
      series: [
        {
          type: "heatmap",
          data: dados.anos.flatMap((ano, a) =>
            Array.from({ length: 12 }, (_, m) => {
              const c = porCelula.get(`${ano}-${m + 1}`);
              return c && c.valor !== null ? [m, a, c.valor] : null;
            }).filter(Boolean),
          ) as [number, number, number][],
          itemStyle: { borderColor: "#ffffff", borderWidth: 2, borderRadius: 4 },
          emphasis: { itemStyle: { borderColor: "#0e2433", borderWidth: 2 } },
        },
        {
          // meses sem dado completo: hachura cinza, nunca a cor do zero (RN-02)
          type: "heatmap",
          data: dados.anos.flatMap((ano, a) =>
            Array.from({ length: 12 }, (_, m) => {
              const c = porCelula.get(`${ano}-${m + 1}`);
              return !c || c.valor === null ? [m, a, -1] : null;
            }).filter(Boolean),
          ) as [number, number, number][],
          itemStyle: {
            color: "#eef1f3",
            borderColor: "#ffffff",
            borderWidth: 2,
            decal: {
              symbol: "rect",
              dashArrayX: [1, 0],
              dashArrayY: [2, 4],
              rotation: Math.PI / 4,
              color: "#9aa8b2",
            },
          },
        },
      ],
    };
    const t = {
      colunas: ["Ano", ...meses],
      linhas: dados.anos.map((ano) => [
        String(ano),
        ...Array.from({ length: 12 }, (_, m) => porCelula.get(`${ano}-${m + 1}`)?.valor ?? null),
      ]),
    };
    const r = maisChuvoso
      ? `${nomeMes(mesTopo + 1).replace(/^./, (x) =>
          x.toUpperCase(),
        )} é, em média, o mês mais chuvoso. O mês com mais chuva do período foi ${nomeMes(
          maisChuvoso.mes,
        )} de ${maisChuvoso.ano}, com ${formatarMm(maisChuvoso.valor, 0)}.`
      : "Não há meses completos para comparar.";
    return { opcao: o, tabela: t, resumo: r };
  }, [dados]);
  return (
    <QuadroGrafico
      titulo="Chuva por mês e ano"
      resumo={resumo}
      opcao={opcao}
      tabela={tabela}
      fontes={fontes.map((f) => ({ nome: f.nome, atualizadoEm: f.atualizado_em }))}
      altura={Math.max(240, dados.anos.length * 40 + 110)}
    />
  );
}
