/**
 * Opções ECharts do painel Dashboards (a biblioteca do projeto), em visual limpo: grade fraca, barras arredondadas,
 * gradientes suaves, rótulos de valor direto nas barras e cores dos tokens. Cada função devolve também a mesma
 * informação em tabela (RNF-ACE-09) e uma frase para o leitor de tela. Barra ausente = sem dado (RN-01), nunca
 * barra zero (RN-02). Nunca só cor: rótulo e legenda escritos.
 */
import type { EChartsOption } from "echarts";
import { token as tokenBruto } from "@/charts/tema";
import { ESTAGIOS } from "@/features/evento/estagios";
import type { CenarioHora } from "@/features/situacao/dados";
import type { ContagemEstagio } from "@/features/mapa/tipos";
import { siglaDistrito } from "@/lib/distritos";
import { formatarDataHora, formatarHora, formatarNumero } from "@/lib/formatos";
import type { ExposicaoDistrito, Janela, LinhaChuva, LinhaPrevista } from "./indicadores";

export interface TabelaGrafico {
  colunas: string[];
  linhas: (string | number | null)[][];
}
export interface GraficoPronto {
  opcao: EChartsOption;
  tabela: TabelaGrafico;
  resumo: string;
}

/** Cores de reserva: o token nunca volta vazio, para uma variável CSS ausente não derrubar o gráfico. */
const RESERVA: Record<string, string> = {
  "--cs-mare": "#0f4c75",
  "--cs-mangue": "#0b6f6c",
  "--cs-tinta": "#0e2433",
  "--cs-tinta-2": "#44596a",
  "--cs-papel": "#ffffff",
  "--n-info": "#1f6fb2",
  "--n-atencao": "#c98a00",
  "--n-alerta": "#d2581f",
  "--n-critico": "#a41f15",
  "--n-insuf-bg": "#eef1f3",
  "--g-1": "#1f6fb2",
  "--g-2": "#c4612b",
  "--g-3": "#0a8f63",
  "--g-ref": "#6b7a85",
  "--g-grade": "#d5e0e7",
  "--g-eixo": "#8fa3b1",
};
const token = (nome: string): string => tokenBruto(nome) || RESERVA[nome] || "#6b7a85";

const TAMANHO = 13;
const texto2 = () => token("--cs-tinta-2");
const eixoTexto = () => ({ fontSize: TAMANHO, color: texto2() });
const dica = { textStyle: { fontSize: 13 }, confine: true };
const idNumero = (id: string) => Number(id.replace(/\D/g, "")) || 0;
const grade = () => ({ lineStyle: { color: token("--g-grade"), type: "dashed" as const } });

/** "#1f6fb2" + 0,3 vira "rgba(31,111,178,0.3)"; cor que não seja hexadecimal passa como veio. */
export function comAlfa(cor: string | undefined, a: number): string {
  if (typeof cor !== "string") return `rgba(107,122,133,${a})`;
  const m = /^#([0-9a-f]{6})$/i.exec(cor.trim());
  if (!m) return cor;
  const n = parseInt(m[1], 16);
  return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`;
}
const degrade = (cor: string, topo = 1, base = 0.45) => ({
  type: "linear" as const,
  x: 0,
  y: 0,
  x2: 0,
  y2: 1,
  colorStops: [
    { offset: 0, color: comAlfa(cor, topo) },
    { offset: 1, color: comAlfa(cor, base) },
  ],
});

/**
 * Chuva medida e prevista por distrito contra os limiares dos estágios. O maior valor ganha cor forte e rótulo direto;
 * as linhas tracejadas dizem quanto falta para Atenção e Alerta. Previsão tracejada = experimental (RN-11).
 */
export function graficoChuvaDistritos(
  medida: LinhaChuva[],
  prevista: LinhaPrevista[],
  limiares: Record<string, number>,
  janela: Janela,
  destaque: string | null,
): GraficoPronto {
  const ids = [...new Set([...medida.map((m) => m.id), ...prevista.map((p) => p.id)])].sort(
    (a, b) => idNumero(a) - idNumero(b),
  );
  const sigla = (id: string) =>
    siglaDistrito(medida.find((m) => m.id === id)?.nome ?? prevista.find((p) => p.id === id)?.nome ?? id);
  const mm = (id: string) => medida.find((m) => m.id === id)?.mm ?? null;
  const pv = (id: string) => prevista.find((p) => p.id === id)?.prevMm ?? null;
  const maiorDe = (f: (id: string) => number | null) =>
    ids.reduce<string | null>((m, id) => ((f(id) ?? -1) > (m ? (f(m) ?? -1) : -1) ? id : m), null);
  const maxMed = maiorDe(mm);
  const cor = token("--cs-mangue");
  const forte = token("--cs-mare");
  const apagar = (id: string) => (destaque && id !== destaque ? 0.3 : 1);
  const rotulo = (valor: number | null) => ({
    show: true,
    position: "top" as const,
    fontWeight: 700,
    color: token("--cs-tinta"),
    fontSize: 12,
    formatter: `${formatarNumero(valor, valor !== null && valor < 10 ? 1 : 0)}`,
  });
  const sufixo = janela === 24 ? "prev_24h" : "prev_72h";
  const marcasBase = (
    [
      ["atencao", "Atenção", "--n-atencao"],
      ["alerta", "Alerta", "--n-alerta"],
    ] as const
  )
    .filter(([k]) => Number.isFinite(limiares[`chuva_${sufixo}_${k}_mm`]))
    .map(([k, nome, t]) => ({
      valor: limiares[`chuva_${sufixo}_${k}_mm`],
      nome: `${nome} ${formatarNumero(limiares[`chuva_${sufixo}_${k}_mm`])} mm`,
      cor: token(t),
    }));
  const maiorValor = Math.max(
    0,
    ...ids.flatMap((id) => [mm(id), pv(id)]).filter((v): v is number => v !== null),
  );
  const atencaoMm = limiares[`chuva_${sufixo}_atencao_mm`];
  // escala curta quando a chuva é baixa: até o maior valor x 1,3 ou o limiar de Atenção, o que for maior
  const teto = Math.max(
    5,
    Math.ceil(Math.max(maiorValor * 1.3, Number.isFinite(atencaoMm) ? atencaoMm : 0) / 5) * 5,
  );
  const marcas = marcasBase.map((m) => (m.valor > teto ? { ...m, nome: `${m.nome} (acima da escala)` } : m));
  const opcao: EChartsOption = {
    grid: { left: 8, right: 12, top: 34, bottom: 4, containLabel: true },
    legend: {
      top: 0,
      right: 0,
      itemWidth: 14,
      itemHeight: 8,
      textStyle: { fontSize: TAMANHO, color: texto2() },
      data: [`Medida (${janela} h)`, `Prevista (${janela} h)`, ...marcas.map((m) => m.nome)],
    },
    tooltip: { trigger: "axis", axisPointer: { type: "shadow" }, ...dica },
    xAxis: {
      type: "category",
      data: ids.map((id) => (mm(id) === null ? `${sigla(id)}\nsem leitura` : sigla(id))),
      axisLabel: { ...eixoTexto(), interval: 0, lineHeight: 16 },
      axisLine: { show: false },
    },
    yAxis: {
      type: "value",
      axisLabel: eixoTexto(),
      splitLine: grade(),
      splitNumber: 3,
      max: teto,
    },
    series: [
      {
        name: `Medida (${janela} h)`,
        type: "bar",
        barMaxWidth: 26,
        itemStyle: { color: degrade(forte, 1, 0.8), borderRadius: [8, 8, 0, 0] },
        data: ids.map((id) => ({
          value: mm(id),
          itemStyle: { opacity: apagar(id) },
          label: mm(id) === null ? { show: false } : rotulo(mm(id)),
        })),
      },
      {
        name: `Prevista (${janela} h)`,
        type: "bar",
        barMaxWidth: 26,
        itemStyle: {
          color: comAlfa(cor, 0.22),
          borderColor: cor,
          borderWidth: 1.5,
          borderType: "dashed",
          borderRadius: [8, 8, 0, 0],
        },
        data: ids.map((id) => ({
          value: pv(id),
          itemStyle: { opacity: apagar(id) },
          label: pv(id) === null ? { show: false } : rotulo(pv(id)),
        })),
      },
      // linhas dos limiares: uma série de linha tracejada por estágio (sem markLine, que quebra com valor ausente)
      ...marcas.map((m) => ({
        name: m.nome,
        type: "line" as const,
        silent: true,
        symbol: "none",
        z: 1,
        itemStyle: { color: m.cor },
        lineStyle: { color: m.cor, type: "dashed" as const, width: 1.5 },
        data: ids.map(() => m.valor),
      })),
    ],
  };
  const maior = maxMed ? medida.find((m) => m.id === maxMed) : undefined;
  return {
    opcao,
    tabela: {
      colunas: ["Distrito", `Medida em ${janela} h (mm)`, `Prevista em ${janela} h (mm)`],
      linhas: ids.map((id) => [sigla(id), mm(id), pv(id)]),
    },
    resumo: `Chuva medida e prevista em ${janela} h por distrito, com os limiares dos estágios. ${maior ? `Maior medida: ${maior.nome}, ${formatarNumero(maior.mm, 1)} mm.` : "Nenhum distrito com leitura medida."}`,
  };
}

export const COR_ESTAGIO: Record<string, string> = {
  critico: "--n-critico",
  alerta: "--n-alerta",
  atencao: "--n-atencao",
  observacao: "--n-info",
  sem_dados: "--n-insuf-bg",
};

/** Donut de territórios por estágio em vigor, com o total no centro. "Sem dados" é cinza hachurado, nunca "observação". */
export function graficoDonut(
  contagem: ContagemEstagio[],
  unidade: string,
): GraficoPronto & { total: number } {
  const fatias = contagem.map((c) => ({ ...c, n: c.declarados + c.sugeridos })).filter((c) => c.n > 0);
  const total = fatias.reduce((s, c) => s + c.n, 0);
  const opcao: EChartsOption = {
    tooltip: {
      trigger: "item",
      ...dica,
      formatter: (p: unknown) => {
        const x = p as { name: string; value: number };
        return `${x.name}: <b>${x.value}</b> ${unidade}`;
      },
    },
    series: [
      {
        type: "pie",
        radius: ["60%", "92%"],
        center: ["50%", "50%"],
        avoidLabelOverlap: false,
        label: { show: false },
        labelLine: { show: false },
        itemStyle: { borderColor: token("--cs-papel"), borderWidth: 3, borderRadius: 8 },
        data: fatias.map((c) => ({
          name: ESTAGIOS[c.estagio].rotulo,
          value: c.n,
          itemStyle:
            c.estagio === "sem_dados"
              ? {
                  color: token("--n-insuf-bg"),
                  decal: {
                    symbol: "rect",
                    dashArrayX: [1, 0],
                    dashArrayY: [2, 4],
                    rotation: Math.PI / 4,
                    color: token("--g-eixo"),
                  },
                }
              : { color: token(COR_ESTAGIO[c.estagio]) },
        })),
      },
    ],
    graphic: [
      {
        type: "text",
        left: "center",
        top: "middle",
        style: {
          text: `{n|${total}}\n{u|${unidade}}`,
          rich: {
            n: { fontSize: 34, fontWeight: 800, lineHeight: 36, align: "center", fill: token("--cs-tinta") },
            u: { fontSize: 13, lineHeight: 18, align: "center", fill: texto2() },
          },
        },
      },
    ],
  };
  return {
    opcao,
    total,
    tabela: {
      colunas: ["Estágio", "Declarados pela equipe", "Sugeridos pelo sistema"],
      linhas: fatias.map((c) => [ESTAGIOS[c.estagio].rotulo, c.declarados, c.sugeridos]),
    },
    resumo: `${total} ${unidade} por estágio: ${fatias.map((c) => `${c.n} em ${ESTAGIOS[c.estagio].rotulo}`).join(", ")}.`,
  };
}

/**
 * Chuva por hora (barras tracejadas: é previsão) e maré (linha com área em degradê), com o marcador "agora", o pico da
 * maré e a linha do limiar de maré alta dos parâmetros.
 */
export function graficoMareChuva(c: CenarioHora, agora: number, limiarMare: number | null): GraficoPronto {
  const t = (iso: string) => new Date(iso).getTime();
  const tudo = [...c.chuva.map((p) => t(p.t)), ...c.mare.map((p) => t(p.t))];
  const min = Math.min(...tudo);
  const max = Math.max(...tudo);
  const corChuva = token("--g-1");
  const corMare = token("--g-2");
  const opcao: EChartsOption = {
    grid: { left: 4, right: 4, top: 34, bottom: 4, containLabel: true },
    legend: {
      top: 0,
      right: 0,
      itemWidth: 14,
      itemHeight: 8,
      textStyle: { fontSize: TAMANHO, color: texto2() },
      data: ["Chuva (mm/h)", "Maré (m)"],
    },
    tooltip: {
      trigger: "axis",
      ...dica,
      formatter: (ps: unknown) => {
        const l = ps as { axisValue: number; seriesName: string; value: (number | null)[] }[];
        if (!l.length) return "";
        const linhas = l.map((p) => {
          const v = p.value[1];
          return `${p.seriesName}: <b>${v === null || v === undefined ? "sem dado" : formatarNumero(v, p.seriesName.startsWith("Maré") ? 2 : 1)}</b>`;
        });
        return `${formatarDataHora(new Date(l[0].axisValue))}<br>${linhas.join("<br>")}`;
      },
    },
    xAxis: {
      type: "time",
      min,
      max,
      splitLine: { show: false },
      axisLabel: {
        ...eixoTexto(),
        hideOverlap: true,
        formatter: (v: number) => formatarHora(new Date(v), true),
      },
    },
    yAxis: [
      {
        type: "value",
        min: 0,
        splitNumber: 3,
        axisLabel: { ...eixoTexto(), hideOverlap: true },
        splitLine: grade(),
      },
      {
        type: "value",
        scale: true,
        splitNumber: 3,
        axisLabel: { ...eixoTexto(), hideOverlap: true },
        splitLine: { show: false },
      },
    ],
    series: [
      {
        name: "Chuva (mm/h)",
        type: "bar",
        barMaxWidth: 9,
        itemStyle: {
          color: comAlfa(corChuva, 0.3),
          borderColor: corChuva,
          borderWidth: 1,
          borderType: "dashed",
          borderRadius: [3, 3, 0, 0],
        },
        data: c.chuva.map((p) => [t(p.t), p.valor]),
        markLine:
          agora >= min && agora <= max
            ? {
                silent: true,
                symbol: "none",
                lineStyle: { type: "dashed", color: texto2(), width: 1.2 },
                label: { formatter: "agora", position: "insideEndTop", fontSize: 12 },
                data: [{ xAxis: agora }],
              }
            : undefined,
      },
      {
        name: "Maré (m)",
        type: "line",
        yAxisIndex: 1,
        smooth: true,
        symbol: "none",
        lineStyle: { width: 3, color: corMare },
        itemStyle: { color: corMare },
        areaStyle: { color: degrade(corMare, 0.35, 0.02) },
        data: c.mare.map((p) => [t(p.t), p.valor]),
        markPoint: c.mare.some((p) => p.valor !== null)
          ? {
              symbol: "pin",
              symbolSize: 38,
              itemStyle: { color: corMare },
              label: {
                fontSize: 11,
                color: "#fff",
                formatter: (p: unknown) => formatarNumero((p as { value?: number }).value ?? null, 1),
              },
              data: [{ type: "max", name: "Pico da maré" }],
            }
          : undefined,
        markLine:
          limiarMare !== null && Number.isFinite(limiarMare)
            ? {
                silent: true,
                symbol: "none",
                lineStyle: { type: "dashed", color: corMare, width: 1.2 },
                label: {
                  formatter: `maré alta ${formatarNumero(limiarMare, 1)} m`,
                  position: "insideStartTop",
                  fontSize: 11,
                  color: corMare,
                },
                data: [{ yAxis: limiarMare }],
              }
            : undefined,
      },
    ],
  };
  const mares = new Map(c.mare.map((p) => [p.t, p.valor]));
  const total = c.chuva.reduce((s, p) => s + (p.valor ?? 0), 0);
  return {
    opcao,
    tabela: {
      colunas: ["Hora", "Chuva prevista (mm/h)", "Maré prevista (m)"],
      linhas: c.chuva.map((p) => [formatarDataHora(p.t), p.valor, mares.get(p.t) ?? null]),
    },
    resumo: `Recife: ${formatarNumero(total, 1)} mm previstos no período, hora a hora, com a maré prevista.`,
  };
}

/** Idosos e crianças que moram nos bairros em atenção ou mais, por distrito. Moradores, não atingidos. */
export function graficoPessoas(exposicao: ExposicaoDistrito[]): GraficoPronto & { vazio: boolean } {
  const linhas = exposicao
    .filter((e) => e.bairrosAtencao > 0)
    .sort((a, b) => b.idososAtencao + b.criancasAtencao - (a.idososAtencao + a.criancasAtencao));
  const rotulo = (cor: string) => ({
    show: true,
    position: "inside" as const,
    fontSize: 12,
    fontWeight: 700,
    color: cor,
    formatter: (p: unknown) =>
      (p as { value: number }).value > 0 ? formatarNumero((p as { value: number }).value) : "",
  });
  const idosos = token("--g-1");
  const criancas = token("--g-3");
  const opcao: EChartsOption = {
    grid: { left: 4, right: 12, top: 34, bottom: 4, containLabel: true },
    legend: {
      top: 0,
      right: 0,
      itemWidth: 14,
      itemHeight: 8,
      textStyle: { fontSize: TAMANHO, color: texto2() },
      data: ["Idosos (60+)", "Crianças (0 a 14)"],
    },
    tooltip: { trigger: "axis", axisPointer: { type: "shadow" }, ...dica },
    xAxis: { type: "value", axisLabel: eixoTexto(), splitLine: grade(), splitNumber: 3 },
    yAxis: {
      type: "category",
      inverse: true,
      data: linhas.map((e) => siglaDistrito(e.nome) + (e.parcial ? "*" : "")),
      axisLabel: { ...eixoTexto(), fontWeight: 700 },
      axisLine: { show: false },
      axisTick: { show: false },
    },
    series: [
      {
        name: "Idosos (60+)",
        type: "bar",
        stack: "p",
        barMaxWidth: 24,
        itemStyle: { color: degrade(idosos, 1, 0.75) },
        label: rotulo("#fff"),
        data: linhas.map((e) => e.idososAtencao),
      },
      {
        name: "Crianças (0 a 14)",
        type: "bar",
        stack: "p",
        barMaxWidth: 24,
        itemStyle: { color: degrade(criancas, 1, 0.75), borderRadius: [0, 8, 8, 0] },
        label: rotulo("#fff"),
        data: linhas.map((e) => e.criancasAtencao),
      },
    ],
  };
  return {
    opcao,
    vazio: linhas.length === 0,
    tabela: {
      colunas: ["Distrito", "Bairros em Atenção ou mais", "Idosos (60+)", "Crianças (0 a 14)"],
      linhas: linhas.map((e) => [
        siglaDistrito(e.nome),
        e.bairrosAtencao,
        e.idososAtencao,
        e.criancasAtencao,
      ]),
    },
    resumo:
      "Moradores idosos e crianças (Censo 2022) dos bairros com estágio sugerido Atenção ou mais, por distrito. Não é o número de atingidos. Asterisco: alguma contagem omitida, o total é um mínimo.",
  };
}

/** Mini série de barras (sem eixos) da chuva medida por hora; hora sem leitura fica vazia. */
export function graficoMini(pontos: { t: number; mm: number | null }[]): EChartsOption {
  return {
    grid: { left: 0, right: 0, top: 2, bottom: 0 },
    tooltip: {
      trigger: "axis",
      ...dica,
      formatter: (ps: unknown) => {
        const p = (ps as { value: [number, number | null] }[])[0];
        return `${formatarHora(new Date(p.value[0]))}: <b>${p.value[1] === null ? "sem leitura" : `${formatarNumero(p.value[1], 1)} mm`}</b>`;
      },
    },
    xAxis: { type: "time", show: false },
    yAxis: { type: "value", show: false, min: 0 },
    series: [
      {
        type: "bar",
        barMaxWidth: 6,
        itemStyle: { color: degrade(token("--g-1"), 1, 0.5), borderRadius: [3, 3, 0, 0] },
        data: pontos.map((p) => [p.t, p.mm]),
      },
    ],
  };
}

/**
 * Casos de dengue por semana epidemiológica (últimas 8 com dado): linha com pontos. A semana incompleta (atraso de
 * notificação) vai tracejada, esmaecida e com o rótulo "incompleta": não vale como queda (RF-39).
 */
export function graficoDengue(
  itens: {
    ano: number;
    semana: number;
    casos: number | null;
    incompleta: boolean;
    nivel_alerta: number | null;
  }[],
): GraficoPronto | null {
  const ultimas = itens.slice(-8);
  if (ultimas.filter((i) => i.casos !== null).length < 2) return null;
  const cor = token("--g-3");
  const rotulo = {
    show: true,
    position: "top" as const,
    fontSize: 12,
    fontWeight: 700,
    color: token("--cs-tinta"),
  };
  // série cheia: só semanas completas; série tracejada: do último ponto completo até as incompletas
  const ultimaCompleta = ultimas.map((i) => !i.incompleta && i.casos !== null).lastIndexOf(true);
  const cheia = ultimas.map((i) => (i.incompleta || i.casos === null ? null : i.casos));
  const ultimoIdx = ultimas.length - 1;
  const tracejada = ultimas.map((i, idx) =>
    (i.incompleta && i.casos !== null) || idx === ultimaCompleta
      ? {
          value: i.casos,
          label: i.incompleta
            ? {
                ...rotulo,
                formatter: idx === ultimoIdx ? `${i.casos} (incompleta)` : `${i.casos}`,
                color: texto2(),
                fontWeight: 400,
              }
            : { show: false },
          itemStyle: i.incompleta ? { color: token("--cs-papel"), borderColor: cor, borderWidth: 2 } : {},
        }
      : null,
  );
  const opcao: EChartsOption = {
    grid: { left: 4, right: 24, top: 28, bottom: 4, containLabel: true },
    tooltip: { trigger: "axis", ...dica },
    xAxis: {
      type: "category",
      data: ultimas.map((i) => `S${i.semana}`),
      axisLabel: { ...eixoTexto(), interval: 0 },
      axisLine: { lineStyle: { color: token("--g-grade") } },
      axisTick: { show: false },
    },
    yAxis: { type: "value", axisLabel: eixoTexto(), splitLine: grade(), splitNumber: 3 },
    series: [
      {
        name: "Casos",
        type: "line",
        symbol: "circle",
        symbolSize: 9,
        lineStyle: { width: 3, color: cor },
        itemStyle: { color: cor, borderColor: cor, borderWidth: 2 },
        areaStyle: { color: degrade(cor, 0.22, 0.02) },
        label: rotulo,
        data: cheia,
      },
      {
        name: "Semana incompleta",
        type: "line",
        symbol: "circle",
        symbolSize: 9,
        lineStyle: { width: 3, color: cor, type: "dashed", opacity: 0.45 },
        itemStyle: { color: cor, borderColor: cor, borderWidth: 2, opacity: 0.6 },
        data: tracejada,
      },
    ],
  };
  const fim = ultimas[ultimas.length - 1];
  return {
    opcao,
    tabela: {
      colunas: ["Semana", "Casos", "Nível InfoDengue", "Semana completa"],
      linhas: ultimas.map((i) => [
        `SE ${i.semana}/${i.ano}`,
        i.casos,
        i.nivel_alerta,
        i.incompleta ? "não" : "sim",
      ]),
    },
    resumo: `Casos de dengue por semana epidemiológica, de SE ${ultimas[0].semana}/${ultimas[0].ano} a SE ${fim.semana}/${fim.ano}. Semana incompleta: tracejada e esmaecida, não vale como queda.`,
  };
}
