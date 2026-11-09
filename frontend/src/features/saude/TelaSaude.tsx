import { useMemo } from "react";
import ReactECharts from "echarts-for-react";
import type { EChartsOption } from "echarts";
import { CircleCheck, Droplets } from "lucide-react";
import { token, temaClimaSense, useTemaAtual } from "@/charts/tema";
import { CabecalhoTela } from "@/design-system/componentes/CabecalhoTela";
import { CarregandoLista } from "@/design-system/componentes/Esqueleto";
import { fontesDado, LegendaFonte } from "@/design-system/componentes/EstadoDados";
import { ValorSuprimido } from "@/design-system/componentes/ValorSuprimido";
import { EstadoConsulta } from "@/features/evento/Evento";
import { diaMes, nomeCurto, quandoAs } from "@/features/evento/textos";
import { consulta, ErroApi } from "@/lib/api";
import { INTERVALO, useConsultaViva, ultimaAtualizacao } from "@/lib/consultas";
import { diaNoRecife, formatarNumero, somarDias } from "@/lib/formatos";
import { fontesDe, supressaoMinima, type FonteMeta } from "@/lib/frescor";
import { dadosDe, type Agravo, type ResumoAgravo, type ResumoSaude, type SerieSemanal } from "./tipos";
import estilos from "./Saude.module.css";

export const NOTA_TECNICA =
  "https://www.gov.br/saude/pt-br/centrais-de-conteudo/publicacoes/notas-tecnicas/2022/nota-tecnica-138-2022-estrategias-para-enfrentamento-da-leptospirose-durante-inundacoes.pdf";

/** Os agravos que a equipe acompanha. Zika ainda não tem fonte no sistema. */
const ARBOVIROSES = [
  { id: "dengue", nome: "Dengue" },
  { id: "chikungunya", nome: "Chikungunya" },
  { id: "zika", nome: "Zika" },
] as const;

/** Mais velho que isto, o dado semanal já não ajuda a decidir (a semana começou há mais de 14 dias). */
export const LIMITE_DIAS = 14;
const SEMANAS_NO_GRAFICO = 8;

type Tendencia = "subindo" | "estável" | "caindo";

/** Início (AAAA-MM-DD) da semana mais recente com dado: o campo novo do backend ou, na falta dele, `ultima_semana`. */
export function inicioDaSemana(item: ResumoAgravo | undefined): string | null {
  if (!item) return null;
  const c = item.ultima_semana_com_dado;
  if (typeof c === "string" && c) return c.slice(0, 10);
  if (c && typeof c === "object" && c.inicio) return c.inicio;
  return item.ultima_semana?.inicio ?? null;
}

const diasEntre = (inicio: string, agora: Date) =>
  Math.floor((agora.getTime() - new Date(`${inicio}T12:00:00Z`).getTime()) / 86_400_000);

/**
 * Só indicador recente ajuda a decidir. Vale o `utilizavel` do backend; sem ele, é utilizável se a semana não é mais
 * velha que 14 dias. Sem número nem contagem omitida, não há o que mostrar (RN-01).
 */
export function utilizavel(item: ResumoAgravo | undefined, agora = new Date()): boolean {
  if (!item) return false;
  if (item.casos === null && !item.suprimido) return false;
  if (typeof item.utilizavel === "boolean") return item.utilizavel;
  const inicio = inicioDaSemana(item);
  return inicio !== null && diasEntre(inicio, agora) <= LIMITE_DIAS;
}

/**
 * Subindo, estável ou caindo: a média das 3 últimas semanas contra a das 3 anteriores. Usa a estimativa corrigida pelo
 * atraso de notificação quando existe (o número notificado das últimas semanas ainda vai subir). Sem percentual (RN-06).
 */
export function tendenciaDe(s: SerieSemanal | undefined): Tendencia | null {
  const v = (s?.itens ?? [])
    .map((i) => i.casos_estimados ?? (i.incompleta ? null : i.casos))
    .filter((x): x is number => x !== null);
  if (v.length < 6) return null;
  const media = (l: number[]) => l.reduce((a, b) => a + b, 0) / l.length;
  const agora = media(v.slice(-3));
  const antes = media(v.slice(-6, -3));
  const dif = agora - antes;
  if (Math.abs(dif) < Math.max(2, antes * 0.15)) return "estável";
  return dif > 0 ? "subindo" : "caindo";
}

/** Checklist curto da Nota Técnica MS 138/2022: uma frase, não uma lista. */
export const FRASE_LEPTO =
  "Busque casos com febre e contato com água de enchente nos últimos 30 dias e notifique os suspeitos.";

/**
 * Saúde depois da chuva (RF-16): só o que ajuda a decidir. Dengue, chikungunya e zika com a semana mais recente,
 * tendência em palavras e as últimas 8 semanas. O que está velho ou sem fonte fica recolhido num item só.
 * Prevenção, não diagnóstico. Sem probabilidade (RN-06); contagem pequena fica omitida (RNF-03).
 */
export function TelaSaude() {
  const resumo = useConsultaViva<unknown>("/saude/resumo", INTERVALO.saude);
  const r = dadosDe<ResumoSaude>(resumo.data);
  const fontes = fontesDe(resumo.data);
  const indisponivel = resumo.error instanceof ErroApi && resumo.error.status === 404;
  const janela = r?.janela_leptospirose;
  const agora = new Date();

  const linhas = ARBOVIROSES.map((a) => ({ ...a, item: r?.agravos.find((x) => x.agravo === a.id) }));
  const uteis = linhas.filter((l) => utilizavel(l.item, agora));
  const velhos = r
    ? [
        ...linhas.filter((l) => !utilizavel(l.item, agora)),
        ...(r.agravos.some((x) => x.agravo === "leptospirose" && utilizavel(x, agora))
          ? []
          : [
              {
                id: "leptospirose",
                nome: "Leptospirose",
                item: r.agravos.find((x) => x.agravo === "leptospirose"),
              },
            ]),
      ]
    : [];

  return (
    <>
      <CabecalhoTela titulo="Saúde depois da chuva" atualizadoEm={ultimaAtualizacao(resumo)} />
      <div className={estilos.pagina}>
        {janela?.ativa && <AvisoJanela janela={janela} />}

        {resumo.isPending && <CarregandoLista linhas={2} altura="7rem" texto="Carregando os casos…" />}
        {resumo.isError && (
          <EstadoConsulta erro={resumo.error} oQue="os dados de saúde" aoTentar={() => resumo.refetch()} />
        )}
        {r && !indisponivel && (
          <>
            {uteis.length > 0 ? (
              <div className={estilos.kpis}>
                {uteis.map((l) => (
                  <CartaoArbovirose
                    key={l.id}
                    agravo={l.id as Agravo}
                    nome={l.nome}
                    item={l.item!}
                    fontes={fontes}
                    minimo={supressaoMinima(resumo.data)}
                  />
                ))}
              </div>
            ) : (
              <p className={estilos.vazio}>
                <b>Dados insuficientes:</b> nenhuma arbovirose tem dado recente. Veja abaixo o que falta.
              </p>
            )}
            {velhos.length > 0 && <Desatualizados itens={velhos} fontes={fontes} agora={agora} />}
          </>
        )}
      </div>
    </>
  );
}

/* ------------------------------------------------------------------ janela de leptospirose */
function AvisoJanela({ janela }: { janela: NonNullable<ResumoSaude["janela_leptospirose"]> }) {
  const onde = janela.territorios.map((t) => nomeCurto(t.nome)).join(", ");
  return (
    <section className={estilos.janela} aria-labelledby="sa-janela">
      <div className={estilos.janelaIcone} aria-hidden="true">
        <Droplets />
      </div>
      <div className={estilos.janelaCorpo}>
        <h2 id="sa-janela" className={estilos.janelaTitulo}>
          Leptospirose: vigilância até {diaMes(janela.fim)}
        </h2>
        <p className={estilos.apoio}>
          <CircleCheck aria-hidden="true" size={16} /> Alagamento declarado em {diaMes(janela.inicio)}
          {onde && ` (${onde})`}. {FRASE_LEPTO}
        </p>
        <p className={estilos.fonteLinha}>
          Fonte:{" "}
          <a href={NOTA_TECNICA} target="_blank" rel="noopener noreferrer">
            Nota Técnica 138/2022 do Ministério da Saúde<span className="so-leitor"> (abre em nova aba)</span>
          </a>
          .
        </p>
      </div>
    </section>
  );
}

/* ------------------------------------------------------------------ cartão de arbovirose */
function CartaoArbovirose({
  agravo,
  nome,
  item,
  fontes,
  minimo,
}: {
  agravo: Agravo;
  nome: string;
  item: ResumoAgravo;
  fontes: FonteMeta[];
  minimo: number;
}) {
  const desde = somarDias(diaNoRecife(), -7 * (SEMANAS_NO_GRAFICO + 1));
  const serie = useConsultaViva<unknown>(`/saude/semanal${consulta({ agravo, desde })}`, INTERVALO.saude);
  const s = dadosDe<SerieSemanal>(serie.data);
  const ultimas = useMemo(() => (s?.itens ?? []).slice(-SEMANAS_NO_GRAFICO), [s]);
  const tendencia = tendenciaDe(s);
  const inicio = inicioDaSemana(item);
  const dele = fontes.filter((f) => f.id === item.fonte_id);
  const casos = item.casos;
  return (
    <section className={estilos.cartao} aria-label={nome}>
      <h2 className={estilos.cartaoRotulo}>{nome}</h2>
      <p className={estilos.numero}>
        {casos === null ? (
          <span className="numeros">
            <ValorSuprimido minimo={minimo} />
          </span>
        ) : (
          <span className="numeros">{formatarNumero(casos)}</span>
        )}
        <span className={estilos.unidade}>
          {casos === 1 ? "caso" : "casos"}
          {inicio ? ` na semana de ${diaMes(inicio)}` : ""}
        </span>
      </p>
      <p className={estilos.tendencia}>
        {tendencia ? (
          <>
            Tendência: <b data-tendencia={tendencia}>{tendencia}</b>
          </>
        ) : serie.isPending ? null : (
          "Tendência indisponível."
        )}
      </p>
      {item.incompleta && (
        <p className={estilos.fonteLinha}>
          Semana incompleta: o número ainda vai subir. Pontilhado: estimativa corrigida.
        </p>
      )}
      {serie.isPending ? (
        <p className={estilos.carregando}>Carregando o gráfico…</p>
      ) : ultimas.length > 1 ? (
        <MiniGrafico nome={nome} itens={ultimas} />
      ) : (
        <p className={estilos.fonteLinha}>Sem série semanal para o gráfico.</p>
      )}
      <LegendaFonte fontes={fontesDado(dele)} />
    </section>
  );
}

/** Últimas semanas em linha pequena; as semanas incompletas ficam tracejadas. */
export function opcaoMini(itens: SerieSemanal["itens"], nome: string): EChartsOption {
  const rotulo = (d: string) => diaMes(d);
  const datas = itens.map((i) => rotulo(i.inicio));
  const primeira = itens.findIndex((i) => i.incompleta);
  const completa = itens.map((i) => (i.incompleta ? null : i.casos));
  const incompleta = itens.map((i, k) =>
    i.incompleta || (primeira > 0 && k === primeira - 1) ? i.casos : null,
  );
  const cor = token("--g-2");
  return {
    animation: false,
    grid: { left: 20, right: 20, top: 8, bottom: 22, containLabel: false },
    tooltip: {
      trigger: "axis",
      formatter: (ps: unknown) => {
        const l = ps as { dataIndex: number }[];
        const it = itens[l[0]?.dataIndex ?? 0];
        return it
          ? `${nome}, semana de ${rotulo(it.inicio)}${it.incompleta ? " (incompleta)" : ""}<br><strong>${
              it.casos === null ? "valor omitido" : formatarNumero(it.casos)
            }</strong> casos`
          : "";
      },
    },
    xAxis: {
      type: "category",
      data: datas,
      boundaryGap: false,
      axisLabel: { interval: datas.length - 2 < 1 ? 0 : datas.length - 2, fontSize: 12, hideOverlap: true },
    },
    yAxis: { type: "value", min: 0, show: false },
    series: [
      {
        type: "line",
        symbol: "none",
        lineStyle: { width: 1.5, type: "dotted", color: token("--g-ref") },
        data: itens.map((i) => (i.incompleta ? i.casos_estimados : null)),
      },
      {
        type: "line",
        symbol: "circle",
        symbolSize: 5,
        lineStyle: { width: 2, color: cor },
        itemStyle: { color: cor },
        data: completa,
      },
      {
        type: "line",
        symbol: "emptyCircle",
        symbolSize: 6,
        lineStyle: { width: 2, type: "dashed", color: cor },
        itemStyle: { color: cor },
        data: incompleta,
      },
    ],
  };
}

function MiniGrafico({ nome, itens }: { nome: string; itens: SerieSemanal["itens"] }) {
  const modo = useTemaAtual();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const tema = useMemo(() => temaClimaSense(), [modo]);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const opcao = useMemo(() => opcaoMini(itens, nome), [itens, nome, modo]);
  const validos = itens.filter((i) => i.casos !== null);
  const resumo = validos.length
    ? `Casos de ${nome.toLowerCase()} nas últimas ${itens.length} semanas, de ${diaMes(itens[0].inicio)} a ${diaMes(
        itens[itens.length - 1].inicio,
      )}: ${validos.map((i) => formatarNumero(i.casos)).join(", ")}. A linha tracejada é a semana ainda incompleta.`
    : `Sem casos de ${nome.toLowerCase()} com valor nas últimas semanas.`;
  return (
    <div className={estilos.mini} role="img" aria-label={resumo}>
      <ReactECharts
        option={opcao}
        theme={tema}
        style={{ height: 84, width: "100%" }}
        notMerge
        opts={{ renderer: "svg" }}
      />
    </div>
  );
}

/* ------------------------------------------------------------------ o que está velho ou sem fonte */
function Desatualizados({
  itens,
  fontes,
  agora,
}: {
  itens: { id: string; nome: string; item: ResumoAgravo | undefined }[];
  fontes: FonteMeta[];
  agora: Date;
}) {
  return (
    <details className={estilos.velhos}>
      <summary>Dados que não estão atualizados ({itens.length})</summary>
      <ul>
        {itens.map(({ id, nome, item }) => {
          const inicio = inicioDaSemana(item);
          const fonte = item ? fontes.find((f) => f.id === item.fonte_id) : undefined;
          return (
            <li key={id}>
              <b>{nome}:</b>{" "}
              {item && inicio ? (
                <>
                  último dado da semana de {diaMes(inicio)} (há {diasEntre(inicio, agora)} dias).
                  {fonte && (
                    <>
                      {" "}
                      Fonte: {fonte.nome}
                      {fonte.atualizado_em ? `, carregada ${quandoAs(fonte.atualizado_em)}` : ""}.
                    </>
                  )}
                </>
              ) : (
                <>Dados insuficientes: falta a fonte de casos de {nome.toLowerCase()}.</>
              )}
            </li>
          );
        })}
      </ul>
    </details>
  );
}
