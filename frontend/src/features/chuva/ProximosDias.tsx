import { useId, useMemo, useState } from "react";
import type { EChartsOption } from "echarts";
import { QuadroGrafico } from "@/charts/QuadroGrafico";
import { estiloReferencia, token, useTemaAtual } from "@/charts/tema";
import campo from "@/design-system/componentes/Campo.module.css";
import { CarregandoLista } from "@/design-system/componentes/Esqueleto";
import { AtualizadoAs, EstadoDados, LegendaFonte, fontesDado } from "@/design-system/componentes/EstadoDados";
import { Pilula } from "@/design-system/componentes/Pilula";
import { consulta, type Esquemas } from "@/lib/api";
import { useConsulta, useConsultaViva } from "@/lib/consultas";
import { juntarFontes } from "@/lib/frescor";
import { formatarDataHora, formatarHora, formatarMm, formatarNumero, FUSO } from "@/lib/formatos";
import { infoEstagio } from "@/features/evento/estagios";
import { EstadoConsulta } from "@/features/evento/Evento";
import {
  atualizada,
  diaDaPrevisao,
  listaEmFrase,
  nomeCurto,
  quandoAs,
  useFontesResumo,
} from "@/features/evento/textos";
import { limiaresDe, listaDe, type ItemEstagio } from "@/features/evento/tipos";
import estilos from "./Chuva.module.css";

type Cenario = Esquemas["RespostaDados_Cenario_"];

const num = (v: unknown): number | null => (typeof v === "number" && Number.isFinite(v) ? v : null);

export interface Limites {
  lim24: number | null;
  lim72: number | null;
  mareAlta: number | null;
}

/** O distrito passa do limite de atenção: pela sugestão do sistema ou pela chuva prevista em 24 h ou 72 h. */
export function passaDoLimite(d: ItemEstagio, l: Limites): boolean {
  const p24 = num(d.sugerido?.insumos?.chuva_prev_24h_mm);
  const p72 = num(d.sugerido?.insumos?.chuva_prev_72h_mm);
  return (
    infoEstagio(d.sugerido?.estagio).ordem >= 1 ||
    (p24 !== null && l.lim24 !== null && p24 >= l.lim24) ||
    (p72 !== null && l.lim72 !== null && p72 >= l.lim72)
  );
}

/** A frase principal da aba, a partir dos distritos e dos limites. Sem previsão nunca vira “sem chuva” (RN-01). */
export function fraseProximosDias(
  itens: ItemEstagio[],
  l: Limites,
  agora = new Date(),
): { frase: string; apoio: string; acima: ItemEstagio[]; semPrevisao: boolean } {
  const comPrevisao = itens.filter((d) => num(d.sugerido?.insumos?.chuva_prev_72h_mm) !== null);
  if (comPrevisao.length === 0)
    return {
      frase: "Sem previsão de chuva agora.",
      apoio: "Isso não quer dizer que não vai chover. Confira a APAC enquanto a previsão não volta.",
      acima: [],
      semPrevisao: true,
    };
  const acima = itens
    .filter((d) => passaDoLimite(d, l))
    .sort(
      (a, b) =>
        (num(b.sugerido?.insumos?.chuva_prev_72h_mm) ?? 0) -
        (num(a.sugerido?.insumos?.chuva_prev_72h_mm) ?? 0),
    );
  if (acima.length === 0) {
    const maior = [...comPrevisao].sort(
      (a, b) =>
        (num(b.sugerido.insumos.chuva_prev_72h_mm) ?? 0) - (num(a.sugerido.insumos.chuva_prev_72h_mm) ?? 0),
    )[0];
    const limite =
      l.lim72 !== null
        ? ` O limite de atenção é ${formatarNumero(l.lim72)} mm em 3 dias${
            l.lim24 !== null ? ` ou ${formatarNumero(l.lim24)} mm em 24 h` : ""
          }.`
        : "";
    return {
      frase: "Nenhum distrito passa do limite nos próximos 3 dias.",
      apoio: `O máximo previsto é ${formatarMm(
        num(maior.sugerido.insumos.chuva_prev_72h_mm),
      )} em 3 dias, no ${nomeCurto(maior.territorio_nome)}.${limite}`,
      acima,
      semPrevisao: false,
    };
  }
  const dias = new Set(
    acima
      .map((d) => d.sugerido?.insumos?.pico_chuva_em)
      .filter((x): x is string => typeof x === "string")
      .map((x) => diaDaPrevisao(x, agora)),
  );
  const quando = dias.size === 1 ? [...dias][0] : "nos próximos 3 dias";
  const nomes = acima.map((d) => nomeCurto(d.territorio_nome));
  return {
    frase: `${listaEmFrase(nomes)} ${nomes.length === 1 ? "pode" : "podem"} passar do limite ${quando}.`,
    apoio:
      acima.length < itens.length
        ? `Os outros ${itens.length - acima.length} distritos ficam abaixo do limite de atenção.`
        : "Todos os distritos passam do limite de atenção.",
    acima,
    semPrevisao: false,
  };
}

const diaSemana = new Intl.DateTimeFormat("pt-BR", { weekday: "short", timeZone: FUSO });

function montarGrafico(d: Cenario["dados"], mareAlta: number | null) {
  const pontos = [...d.chuva.map((p) => p.t), ...d.mare.map((p) => p.t)].map((t) => new Date(t).getTime());
  const min = Math.min(...pontos);
  const max = Math.max(...pontos);
  const eixo = (gridIndex: number, mostrar: boolean) => ({
    type: "time" as const,
    gridIndex,
    min,
    max,
    axisLabel: mostrar
      ? {
          formatter: (v: number) => {
            const h = formatarHora(new Date(v), true);
            return h === "0h" ? diaSemana.format(new Date(v)).replace(".", "") : h;
          },
          hideOverlap: true,
        }
      : { show: false },
    splitLine: { show: false },
  });
  const opcao: EChartsOption = {
    legend: { top: 0, left: 0, data: ["Chuva prevista (mm por hora)", "Maré (m)"] },
    tooltip: {
      trigger: "axis",
      formatter: (ps: unknown) => {
        const lista = ps as { value: [number, number | null]; seriesName: string }[];
        if (!lista.length) return "";
        return `${formatarDataHora(new Date(lista[0].value[0]))}<br>${lista
          .map(
            (p) =>
              `${p.seriesName}: <strong>${
                p.value[1] === null
                  ? "sem dado"
                  : formatarNumero(p.value[1], p.seriesName.startsWith("Maré") ? 2 : 1)
              }</strong>`,
          )
          .join("<br>")}`;
      },
    },
    axisPointer: { link: [{ xAxisIndex: "all" }] },
    grid: [
      { left: 56, right: 16, top: 60, height: "40%" },
      { left: 56, right: 16, top: "68%", bottom: 32 },
    ],
    xAxis: [eixo(0, false), eixo(1, true)],
    yAxis: [
      { type: "value", gridIndex: 0, min: 0, name: "mm/h", nameGap: 8 },
      { type: "value", gridIndex: 1, scale: true, name: "m", nameGap: 8, splitNumber: 2 },
    ],
    series: [
      {
        name: "Chuva prevista (mm por hora)",
        type: "bar",
        xAxisIndex: 0,
        yAxisIndex: 0,
        barMaxWidth: 8,
        itemStyle: { color: token("--g-1"), borderRadius: [4, 4, 0, 0] },
        data: d.chuva.map((p) => [new Date(p.t).getTime(), p.valor]),
      },
      {
        name: "Maré (m)",
        type: "line",
        xAxisIndex: 1,
        yAxisIndex: 1,
        symbol: "none",
        lineStyle: { width: 2, color: token("--g-2") },
        itemStyle: { color: token("--g-2") },
        data: d.mare.map((p) => [new Date(p.t).getTime(), p.valor]),
        markLine:
          mareAlta !== null
            ? {
                silent: true,
                symbol: "none",
                lineStyle: { ...estiloReferencia().lineStyle, width: 1.5 },
                label: { formatter: "maré alta", color: token("--cs-tinta-2"), position: "insideEndTop" },
                data: [{ yAxis: mareAlta }],
              }
            : undefined,
      },
    ],
  };
  const mares = new Map(d.mare.map((p) => [p.t, p.valor]));
  const tabela = {
    colunas: ["Hora", "Chuva prevista (mm)", "Maré (m)"],
    linhas: d.chuva.map((p) => [formatarDataHora(p.t), p.valor, mares.get(p.t) ?? null]),
  };
  const total = d.chuva.reduce((s, p) => s + (p.valor ?? 0), 0);
  const e = d.estimativa;
  const resumo = d.chuva.length
    ? `${formatarMm(total)} previstos em 3 dias no ${nomeCurto(d.territorio_nome)}.${
        e.mare_maxima_m !== null && e.mare_maxima_em
          ? ` Maré mais alta: ${formatarNumero(e.mare_maxima_m, 2)} m, ${quandoAs(e.mare_maxima_em)}.`
          : ""
      }`
    : "Sem previsão de chuva carregada para este distrito.";
  return { opcao, tabela, resumo };
}

/** Aba “Próximos 3 dias”: uma frase, só os distritos acima do limite e o gráfico de chuva com maré. */
export function ProximosDias() {
  const modo = useTemaAtual();
  const r = useConsultaViva<unknown>(`/estagios${consulta({ nivel: "distrito" })}`);
  const p = useConsulta<unknown>("/estagios/parametros");
  const fontes = useFontesResumo();
  const lim = limiaresDe(p.data);
  const limites: Limites = {
    lim24: lim.chuva_prev_24h_atencao_mm ?? null,
    lim72: lim.chuva_prev_72h_atencao_mm ?? null,
    mareAlta: lim.mare_alta_m ?? null,
  };
  const itens = useMemo(
    () =>
      listaDe<ItemEstagio>(r.data).sort((a, b) =>
        a.territorio_nome.localeCompare(b.territorio_nome, "pt-BR", { numeric: true }),
      ),
    [r.data],
  );
  const leitura = fraseProximosDias(itens, limites);
  const maisChuvoso = [...itens].sort(
    (a, b) =>
      (num(b.sugerido?.insumos?.chuva_prev_72h_mm) ?? -1) -
      (num(a.sugerido?.insumos?.chuva_prev_72h_mm) ?? -1),
  )[0];
  const [escolha, setEscolha] = useState<string | null>(null);
  const distrito = escolha ?? maisChuvoso?.territorio_id ?? null;
  const cenario = useConsultaViva<Cenario>(
    distrito ? `/cenarios${consulta({ territorio_id: distrito, horizonte_h: 72 })}` : null,
    5 * 60_000,
    { staleTime: 5 * 60_000 },
  );
  const grafico = useMemo(
    () => (cenario.data ? montarGrafico(cenario.data.dados, limites.mareAlta) : null),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [cenario.data, limites.mareAlta, modo],
  );
  const idSelecao = useId();

  return (
    <div className={estilos.pagina}>
      <AtualizadoAs em={r.dataUpdatedAt} />
      {r.isPending && <CarregandoLista linhas={1} altura="7rem" texto="Carregando a previsão…" />}
      {r.isError && (
        <EstadoConsulta erro={r.error} oQue="a previsão por distrito" aoTentar={() => r.refetch()} />
      )}
      {r.isSuccess && (
        <section
          className={estilos.manchete}
          data-acima={leitura.acima.length > 0}
          data-semdado={leitura.semPrevisao}
          aria-labelledby="ch-frase"
        >
          <h2 id="ch-frase" className={estilos.fraseGrande}>
            {leitura.frase}
          </h2>
          <p className={estilos.apoio}>{leitura.apoio}</p>
          {leitura.acima.length > 0 && (
            <ul className={estilos.acima} aria-label="Distritos acima do limite">
              {leitura.acima.map((d) => {
                const ins = d.sugerido?.insumos ?? {};
                const pico = typeof ins.pico_chuva_em === "string" ? ins.pico_chuva_em : null;
                const mareNoPico = num(ins.mare_no_pico_m) ?? num(ins.mare_max_m);
                return (
                  <li key={d.territorio_id}>
                    <span className={estilos.acimaNome}>{nomeCurto(d.territorio_nome)}</span>
                    <span>
                      <span className={estilos.acimaMm}>{formatarMm(num(ins.chuva_prev_24h_mm))}</span> em 24
                      h
                    </span>
                    <span>{formatarMm(num(ins.chuva_prev_72h_mm))} em 3 dias</span>
                    {pico && <span>pico {quandoAs(pico)}</span>}
                    {/* maré alta sozinha não é notícia: o chip só aparece junto com chuva acima do limite */}
                    {limites.mareAlta !== null && mareNoPico !== null && mareNoPico >= limites.mareAlta && (
                      <Pilula tom="info" pequena>
                        Maré alta junto com a chuva
                      </Pilula>
                    )}
                  </li>
                );
              })}
            </ul>
          )}
        </section>
      )}

      {itens.length > 0 && !leitura.semPrevisao && (
        <div className={estilos.escolha}>
          <div className={campo.campo}>
            <label htmlFor={idSelecao} className={campo.rotulo}>
              Distrito do gráfico
            </label>
            <select
              id={idSelecao}
              className={campo.entrada}
              value={distrito ?? ""}
              onChange={(e) => setEscolha(e.target.value)}
            >
              {itens.map((d) => (
                <option key={d.territorio_id} value={d.territorio_id}>
                  {d.territorio_nome}
                </option>
              ))}
            </select>
          </div>
        </div>
      )}
      {distrito && cenario.isPending && (
        <CarregandoLista linhas={1} altura="20rem" texto="Carregando o gráfico de chuva e maré…" />
      )}
      {cenario.isError && (
        <EstadoConsulta
          erro={cenario.error}
          oQue="a previsão hora a hora"
          aoTentar={() => cenario.refetch()}
        />
      )}
      {cenario.data &&
        grafico &&
        (cenario.data.dados.chuva.length || cenario.data.dados.mare.length ? (
          <QuadroGrafico
            titulo="Chuva e maré, hora a hora"
            resumo={grafico.resumo}
            opcao={grafico.opcao}
            tabela={grafico.tabela}
            altura={340}
          />
        ) : (
          <EstadoDados tipo="insuficiente" titulo="Sem previsão hora a hora para este distrito." />
        ))}

      <p className={estilos.rodape}>
        Previsão de chuva e maré: Open-Meteo, {atualizada(fontes.hora("open-meteo-previsao"))}. A maré é a de
        frente ao Porto do Recife. É uma previsão, não um alerta oficial.
      </p>
      <LegendaFonte fontes={fontesDado(juntarFontes(r.data, cenario.data))} />
    </div>
  );
}
