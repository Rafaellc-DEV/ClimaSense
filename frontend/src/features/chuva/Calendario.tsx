import { useMemo } from "react";
import type { EChartsOption } from "echarts";
import { QuadroGrafico } from "@/charts/QuadroGrafico";
import { token, useTemaAtual } from "@/charts/tema";
import { Pilula } from "@/design-system/componentes/Pilula";
import type { Esquemas } from "@/lib/api";
import { formatarMm, nomeMes } from "@/lib/formatos";
import estilos from "./Chuva.module.css";

const RAMPA = ["--g-calor-1", "--g-calor-2", "--g-calor-3", "--g-calor-4", "--g-calor-5"];

/**
 * Calendário ano × mês em mapa de calor (RF-08.5). A rampa vem dos tokens `--g-calor-*` (amarelo → vermelho escuro);
 * mês sem dado completo fica hachurado e com a legenda “Sem dado completo”, nunca na cor do zero (RN-02).
 */
export function Calendario({ dados }: { dados: Esquemas["Sazonalidade"] }) {
  const modo = useTemaAtual();
  const { opcao, tabela, resumo, pico, max } = useMemo(() => {
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
    const papel = token("--cs-papel");
    const o: EChartsOption = {
      grid: { left: 8, right: 8, top: 8, bottom: 8, containLabel: true },
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
      xAxis: { type: "category", data: meses, splitArea: { show: false }, splitLine: { show: false } },
      yAxis: { type: "category", data: anos, inverse: true, splitLine: { show: false } },
      // a legenda é um bloco de HTML abaixo do gráfico (rampa + “Sem dado completo”); aqui só mapeia valor → cor
      visualMap: [
        {
          show: false,
          min: 0,
          max,
          inRange: { color: RAMPA.map(token) },
          seriesIndex: 0,
        },
        { show: false, seriesIndex: 1, min: -1, max: -1, inRange: { color: [token("--n-insuf-bg")] } },
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
          itemStyle: { borderColor: papel, borderWidth: 2, borderRadius: 4 },
          emphasis: { itemStyle: { borderColor: token("--cs-tinta"), borderWidth: 2 } },
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
            color: token("--n-insuf-bg"),
            borderColor: papel,
            borderWidth: 2,
            borderRadius: 4,
            decal: {
              symbol: "rect",
              dashArrayX: [1, 0],
              dashArrayY: [2, 4],
              rotation: Math.PI / 4,
              color: token("--g-eixo"),
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
      ? `${nomeMes(mesTopo + 1).replace(/^./, (x) => x.toUpperCase())} é, em média, o mês mais chuvoso.`
      : "Não há meses completos para comparar.";
    const p = maisChuvoso
      ? `${nomeMes(maisChuvoso.mes)} de ${maisChuvoso.ano}, ${formatarMm(maisChuvoso.valor, 0)}`
      : null;
    return { opcao: o, tabela: t, resumo: r, pico: p, max };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dados, modo]);
  return (
    <QuadroGrafico
      titulo="Em que meses choveu mais?"
      resumo={resumo}
      opcao={opcao}
      tabela={tabela}
      altura={Math.max(220, dados.anos.length * 44 + 40)}
      selos={
        pico && (
          <Pilula tom="marca" semMarca>
            Maior mês: {pico}
          </Pilula>
        )
      }
      legenda={
        <div className={estilos.legendaCalor} role="group" aria-label="Legenda de cores do calendário">
          <span className={estilos.legendaRotulo}>Chuva no mês</span>
          <span className={estilos.rampa}>
            <span>0 mm</span>
            <i aria-hidden="true" />
            <span>{formatarMm(max, 0)}</span>
          </span>
          <span className={estilos.legendaSem}>
            <i aria-hidden="true" /> Sem dado completo
          </span>
        </div>
      }
    />
  );
}
