import { useId, useMemo, useState } from "react";
import type { EChartsOption } from "echarts";
import { CircleCheck, Droplets } from "lucide-react";
import { QuadroGrafico } from "@/charts/QuadroGrafico";
import { token, useTemaAtual } from "@/charts/tema";
import { CabecalhoTela } from "@/design-system/componentes/CabecalhoTela";
import campo from "@/design-system/componentes/Campo.module.css";
import { CarregandoLista } from "@/design-system/componentes/Esqueleto";
import { EstadoDados } from "@/design-system/componentes/EstadoDados";
import { Dica } from "@/design-system/componentes/Dica";
import { Painel } from "@/design-system/componentes/Painel";
import { Pilula } from "@/design-system/componentes/Pilula";
import { Segmentado } from "@/design-system/componentes/Segmentado";
import { consulta, ErroApi } from "@/lib/api";
import { useConsulta } from "@/lib/consultas";
import { diaNoRecife, formatarNumero, somarDias } from "@/lib/formatos";
import { useTerritorios } from "@/app/FiltroFrase";
import { distritoPorExtenso } from "@/textos/glossario";
import { EstadoConsulta } from "@/features/evento/Evento";
import { atualizada, diaMes, nomeCurto, useFontesResumo } from "@/features/evento/textos";
import {
  dadosDe,
  NIVEL_ALERTA,
  NOME_AGRAVO,
  type Agravo,
  type CasosBairros,
  type ResumoAgravo,
  type ResumoSaude,
  type SerieSemanal,
} from "./tipos";
import { bairrosDoDistrito } from "./bairros";
import { PopoverBairros } from "./PopoverBairros";
import estilos from "./Saude.module.css";

export const NOTA_TECNICA =
  "https://www.gov.br/saude/pt-br/centrais-de-conteudo/publicacoes/notas-tecnicas/2022/nota-tecnica-138-2022-estrategias-para-enfrentamento-da-leptospirose-durante-inundacoes.pdf";

/** Checklist curto da Nota Técnica MS 138/2022 para os 30 dias depois do alagamento. */
export const CHECKLIST_LEPTO = [
  "Busca ativa: procure casos com febre e contato com água de enchente nos últimos 30 dias.",
  "Oriente quem teve contato com a água a procurar a unidade de saúde se tiver febre, dor no corpo ou dor de cabeça.",
  "Notifique todo caso suspeito e anote a exposição à enchente na ficha.",
];

/**
 * Saúde depois da chuva: janela de vigilância de leptospirose, dengue, chikungunya e leptospirose por semana ao lado
 * da chuva, e o retrato por bairro do ano escolhido. Prevenção, não diagnóstico.
 */
export function TelaSaude() {
  const resumo = useConsulta<unknown>("/saude/resumo");
  const fontes = useFontesResumo();
  const r = dadosDe<ResumoSaude>(resumo.data);
  const janela = r?.janela_leptospirose;
  // sem as rotas de saúde no servidor, um aviso só: os blocos abaixo diriam o mesmo três vezes
  const indisponivel = resumo.error instanceof ErroApi && resumo.error.status === 404;

  return (
    <>
      <CabecalhoTela
        titulo="Saúde depois da chuva"
        proposito="Dengue, chikungunya e leptospirose no Recife, ao lado da chuva, para agir antes dos casos."
      />
      <div className={estilos.pagina}>
        {janela?.ativa && <AvisoJanela janela={janela} />}

        <section aria-labelledby="sa-kpis">
          <h2 id="sa-kpis" className="so-leitor">
            Casos na última semana
          </h2>
          {resumo.isPending && <CarregandoLista linhas={1} altura="9rem" texto="Carregando os casos…" />}
          {resumo.isError && (
            <EstadoConsulta erro={resumo.error} oQue="os dados de saúde" aoTentar={() => resumo.refetch()} />
          )}
          {r && (
            <div className={estilos.kpis}>
              {(["dengue", "chikungunya", "leptospirose"] as Agravo[]).map((a) => (
                <CartaoAgravo key={a} agravo={a} item={r.agravos.find((x) => x.agravo === a)} />
              ))}
            </div>
          )}
          {r?.agravos.some((a) => a.incompleta) && (
            <p className={estilos.nota}>
              Os últimos dias ainda estão chegando; o número da semana pode subir.
            </p>
          )}
        </section>

        {!indisponivel && <GraficoSemanal />}
        {!indisponivel && <RankingBairros />}

        <p className={estilos.limites}>
          Limites: leptospirose só tem dado do Recife inteiro, sem bairro. Dengue e chikungunya por bairro
          saem uma vez por ano.
        </p>
        <p className={estilos.rodape}>
          {fraseFontes(r?.agravos ?? [], (id) => fontes.lista.find((f) => f.id === id))} Chuva: ERA5,{" "}
          {atualizada(fontes.hora("open-meteo-historico"))}.
        </p>
      </div>
    </>
  );
}

function fraseFontes(
  agravos: ResumoAgravo[],
  achar: (id: string) => { nome: string; ultima_atualizacao: string | null } | undefined,
) {
  if (!agravos.length) return "Casos: InfoDengue (dengue e chikungunya) e SINAN/DATASUS (leptospirose).";
  const ids = [...new Set(agravos.map((a) => a.fonte_id))];
  return `Casos: ${ids
    .map((id) => {
      const f = achar(id);
      const lepto = agravos.some((a) => a.fonte_id === id && a.agravo === "leptospirose");
      const nome = f?.nome ?? (lepto ? "SINAN/DATASUS, leptospirose" : "InfoDengue");
      return `${nome}, ${atualizada(f?.ultima_atualizacao)}`;
    })
    .join("; ")}.`;
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
          Janela de vigilância de leptospirose até {diaMes(janela.fim)}: 30 dias após o alagamento de{" "}
          {diaMes(janela.inicio)}
        </h2>
        {(janela.motivo || onde) && (
          <p className={estilos.apoio}>
            {janela.motivo}
            {onde && ` Onde: ${onde}.`}
          </p>
        )}
        <ul className={estilos.checklist}>
          {CHECKLIST_LEPTO.map((c) => (
            <li key={c}>
              <CircleCheck aria-hidden="true" size={20} />
              {c}
            </li>
          ))}
        </ul>
        <p className={estilos.apoio}>
          Fonte:{" "}
          <a href={NOTA_TECNICA} target="_blank" rel="noopener noreferrer">
            Nota Técnica 138/2022 do Ministério da Saúde<span className="so-leitor"> (abre em nova aba)</span>
          </a>
          . É um lembrete pelo tempo de incubação, não uma chance de adoecer.
        </p>
      </div>
    </section>
  );
}

/* ------------------------------------------------------------------ KPIs */
const PALAVRA_NIVEL: Record<number, string> = {
  1: "situação normal",
  2: "atenção",
  3: "transmissão sustentada",
  4: "muitos casos",
};
const EXPLICA_NIVEL =
  "Nível de alerta do InfoDengue, de 1 a 4: 1 verde, situação normal; 2 amarelo, atenção; 3 laranja, transmissão sustentada; 4 vermelho, muitos casos. Combina casos, temperatura e chuva.";

/** Uma frase simples: o que o número significa e se subiu ou desceu. Sem dado, nunca zero (RN-01). */
export function fraseAgravo(item: ResumoAgravo | undefined): string {
  if (!item || item.casos === null) return "Sem dado desta semana.";
  const semana = item.ultima_semana ? ` na semana de ${diaMes(item.ultima_semana.inicio)}` : "";
  const v = item.variacao_4s_pct;
  const comparacao =
    v === null || v === undefined
      ? ""
      : v >= 10
        ? `, ${formatarNumero(v)}% a mais que nas 4 semanas anteriores`
        : v <= -10
          ? `, ${formatarNumero(Math.abs(v))}% a menos que nas 4 semanas anteriores`
          : ", quase o mesmo das 4 semanas anteriores";
  const nivel = item.nivel_alerta
    ? ` Nível de alerta ${item.nivel_alerta} de 4: ${PALAVRA_NIVEL[item.nivel_alerta]}.`
    : "";
  return `${formatarNumero(item.casos)} ${
    item.casos === 1 ? "caso" : "casos"
  }${semana}${comparacao}.${nivel}`;
}

function CartaoAgravo({ agravo, item }: { agravo: Agravo; item: ResumoAgravo | undefined }) {
  const id = useId();
  const nivel = item?.nivel_alerta ? NIVEL_ALERTA[item.nivel_alerta] : null;
  const casos = item?.casos ?? null;
  return (
    <div role="group" aria-labelledby={id} className={estilos.cartao} data-tom={nivel?.tom}>
      <div className={estilos.cartaoTopo}>
        <p id={id} className={estilos.cartaoRotulo}>
          {item?.nome ?? NOME_AGRAVO[agravo]}
        </p>
        {nivel && (
          <span className={estilos.nivel}>
            <Pilula tom={nivel.tom} pequena>
              {nivel.rotulo}
            </Pilula>
            <Dica texto={EXPLICA_NIVEL} rotulo="O que significa o nível" alinhar="fim" lado="abaixo" />
          </span>
        )}
      </div>
      {casos === null ? (
        <p className={estilos.semDado}>Sem dado</p>
      ) : (
        <p className={estilos.numero}>
          <span className="numeros">{formatarNumero(casos)}</span>
          <span className={estilos.unidade}>{casos === 1 ? "caso" : "casos"}</span>
        </p>
      )}
      <p className={estilos.frase}>{fraseAgravo(item)}</p>
      {item?.incompleta && (
        <p className={estilos.incompleta}>
          Semana incompleta
          {item.casos_estimados !== null &&
            `: estimativa corrigida de ${formatarNumero(item.casos_estimados)}`}
          .
        </p>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ gráfico semanal */
export function montarSemanal(s: SerieSemanal, nome: string) {
  const rotulo = (d: string) => diaMes(d);
  const datas = s.itens.map((i) => i.inicio);
  const chuva = new Map(s.chuva.map((c) => [c.inicio, c.chuva_mm]));
  const completa = s.itens.map((i) => (i.incompleta ? null : i.casos));
  // a linha tracejada sai da última semana completa e cobre as incompletas
  const primeiraIncompleta = s.itens.findIndex((i) => i.incompleta);
  const incompleta = s.itens.map((i, k) =>
    i.incompleta || (primeiraIncompleta > 0 && k === primeiraIncompleta - 1) ? i.casos : null,
  );
  const opcao: EChartsOption = {
    legend: { top: 0, left: 0, data: [`${nome} (casos)`, "Semana incompleta", "Chuva na semana (mm)"] },
    tooltip: {
      trigger: "axis",
      formatter: (ps: unknown) => {
        const l = ps as { dataIndex: number }[];
        if (!l.length) return "";
        const it = s.itens[l[0].dataIndex];
        const c = chuva.get(it.inicio);
        return `Semana de ${rotulo(it.inicio)}${
          it.incompleta ? " (incompleta)" : ""
        }<br>Casos: <strong>${formatarNumero(it.casos)}</strong>${
          it.casos_estimados !== null ? `<br>Estimativa: ${formatarNumero(it.casos_estimados)}` : ""
        }<br>Chuva: <strong>${
          c === null || c === undefined ? "sem dado" : `${formatarNumero(c, 0)} mm`
        }</strong>`;
      },
    },
    axisPointer: { link: [{ xAxisIndex: "all" }] },
    grid: [
      { left: 56, right: 16, top: 60, height: "46%" },
      { left: 56, right: 16, top: "72%", bottom: 32 },
    ],
    xAxis: [
      { type: "category", gridIndex: 0, data: datas.map(rotulo), axisLabel: { show: false } },
      {
        type: "category",
        gridIndex: 1,
        data: datas.map(rotulo),
        axisLabel: { interval: Math.max(0, Math.ceil(datas.length / 8) - 1), hideOverlap: true },
      },
    ],
    yAxis: [
      { type: "value", gridIndex: 0, min: 0, name: "casos", nameGap: 8 },
      { type: "value", gridIndex: 1, min: 0, name: "mm", nameGap: 8, splitNumber: 2 },
    ],
    series: [
      {
        name: `${nome} (casos)`,
        type: "line",
        xAxisIndex: 0,
        yAxisIndex: 0,
        symbol: "circle",
        symbolSize: 6,
        connectNulls: false,
        lineStyle: { width: 2, color: token("--g-2") },
        itemStyle: { color: token("--g-2") },
        data: completa,
      },
      {
        name: "Semana incompleta",
        type: "line",
        xAxisIndex: 0,
        yAxisIndex: 0,
        symbol: "emptyCircle",
        symbolSize: 8,
        connectNulls: false,
        lineStyle: { width: 2, type: "dashed", color: token("--g-2") },
        itemStyle: { color: token("--g-2") },
        data: incompleta,
      },
      {
        name: "Chuva na semana (mm)",
        type: "bar",
        xAxisIndex: 1,
        yAxisIndex: 1,
        barWidth: "60%",
        itemStyle: { color: token("--g-1"), borderRadius: [4, 4, 0, 0] },
        data: datas.map((d) => chuva.get(d) ?? null),
      },
    ],
  };
  const tabela = {
    colunas: ["Semana", "Casos", "Estimativa", "Incompleta", "Chuva (mm)"],
    linhas: s.itens.map((i) => [
      rotulo(i.inicio),
      i.casos,
      i.casos_estimados,
      i.incompleta ? "sim" : "não",
      chuva.get(i.inicio) ?? null,
    ]),
  };
  const ultimas = s.itens.filter((i) => !i.incompleta && i.casos !== null);
  const pico = ultimas.reduce<(typeof ultimas)[number] | null>(
    (m, i) => (m === null || (i.casos ?? 0) > (m.casos ?? 0) ? i : m),
    null,
  );
  const resumo = pico
    ? `O maior número de casos de ${nome.toLowerCase()} no período foi na semana de ${rotulo(
        pico.inicio,
      )}: ${formatarNumero(pico.casos)}. As semanas tracejadas ainda estão incompletas.`
    : `Ainda não há semana completa de ${nome.toLowerCase()} no período.`;
  return { opcao, tabela, resumo };
}

function GraficoSemanal() {
  const modo = useTemaAtual();
  const [agravo, setAgravo] = useState<Agravo>("dengue");
  const desde = somarDias(diaNoRecife(), -364);
  const r = useConsulta<unknown>(`/saude/semanal${consulta({ agravo, desde })}`);
  const s = dadosDe<SerieSemanal>(r.data);
  const g = useMemo(
    () => (s && s.itens.length ? montarSemanal(s, NOME_AGRAVO[agravo]) : null),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [r.data, agravo, modo],
  );
  return (
    <section className={estilos.bloco} aria-labelledby="sa-semanal">
      <div className={estilos.topoBloco}>
        <h2 id="sa-semanal" className={estilos.tituloBloco}>
          Casos por semana e chuva: depois de chuva forte os casos sobem?
        </h2>
        <Segmentado
          rotulo="Agravo do gráfico"
          rotuloOculto
          opcoes={(["dengue", "chikungunya", "leptospirose"] as Agravo[]).map((a) => ({
            valor: a,
            rotulo: NOME_AGRAVO[a],
          }))}
          valor={agravo}
          aoMudar={setAgravo}
        />
      </div>
      <p className={estilos.legenda}>
        Em cima, os casos de cada semana. Embaixo, a chuva da mesma semana. Linha tracejada: semana ainda
        incompleta.
      </p>
      {r.isPending && <CarregandoLista linhas={1} altura="20rem" texto="Carregando a série semanal…" />}
      {r.isError && <EstadoConsulta erro={r.error} oQue="a série semanal" aoTentar={() => r.refetch()} />}
      {r.isSuccess && !g && <EstadoDados tipo="insuficiente" titulo="Sem semanas com dado neste período." />}
      {g && (
        <QuadroGrafico
          titulo={`${NOME_AGRAVO[agravo]} nos últimos 12 meses`}
          resumo={g.resumo}
          opcao={g.opcao}
          tabela={g.tabela}
          altura={360}
        />
      )}
    </section>
  );
}

/* ------------------------------------------------------------------ ranking por bairro ou distrito */
export function agruparPorDistrito(itens: CasosBairros["itens"]) {
  const m = new Map<string, number | null>();
  for (const i of itens) {
    const k = i.distrito_id ?? "sem-distrito";
    const atual = m.get(k);
    m.set(k, i.casos === null ? (atual ?? null) : (atual ?? 0) + i.casos);
  }
  return [...m.entries()].map(([id, casos]) => ({
    id,
    nome: id === "sem-distrito" ? "Sem distrito" : nomeCurto(distritoPorExtenso(id)),
    casos,
  }));
}

function RankingBairros() {
  const [agravo, setAgravo] = useState<Exclude<Agravo, "leptospirose">>("dengue");
  const [ano, setAno] = useState<number | null>(null);
  const [nivel, setNivel] = useState<"distrito" | "bairro">("distrito");
  const r = useConsulta<unknown>(`/saude/bairros${consulta({ agravo, ano: ano ?? undefined })}`);
  const territorios = useTerritorios();
  const d = dadosDe<CasosBairros>(r.data);
  const linhas = useMemo(() => {
    if (!d) return [];
    const base =
      nivel === "distrito"
        ? agruparPorDistrito(d.itens)
        : d.itens.map((i) => ({ id: i.bairro_id, nome: i.bairro_nome, casos: i.casos }));
    // quem não tem registro vai ao fim, escrito "sem registro" (nunca zero)
    return base
      .sort((a, b) => (b.casos ?? -1) - (a.casos ?? -1) || a.nome.localeCompare(b.nome, "pt-BR"))
      .slice(0, 10);
  }, [d, nivel]);
  const maximo = Math.max(1, ...linhas.map((l) => l.casos ?? 0));
  const anos = d?.anos_disponiveis ?? [];
  const comCasos = d?.itens.filter((i) => i.casos !== null) ?? [];
  const total = comCasos.reduce((s, i) => s + (i.casos ?? 0), 0);
  const nomeAgravo = NOME_AGRAVO[agravo].toLowerCase();
  const anoTexto = d?.ano ?? ano;

  return (
    <Painel
      id="sa-ranking"
      titulo={`Onde houve mais casos em ${anoTexto ?? "um ano"}`}
      acoes={
        <div className={estilos.filtros}>
          <Segmentado
            rotulo="Agravo do ranking"
            rotuloOculto
            opcoes={[
              { valor: "dengue" as const, rotulo: "Dengue" },
              { valor: "chikungunya" as const, rotulo: "Chikungunya" },
            ]}
            valor={agravo}
            aoMudar={setAgravo}
          />
          <Segmentado
            rotulo="Agrupar por"
            rotuloOculto
            opcoes={[
              { valor: "distrito" as const, rotulo: "Distrito" },
              { valor: "bairro" as const, rotulo: "Bairro" },
            ]}
            valor={nivel}
            aoMudar={setNivel}
          />
          {anos.length > 0 && (
            <div className={[campo.campo, estilos.ano].join(" ")}>
              <label htmlFor="sa-ano" className={estilos.anoRotulo}>
                Ano
              </label>
              <select
                id="sa-ano"
                className={campo.entrada}
                value={ano ?? d?.ano ?? ""}
                onChange={(e) => setAno(Number(e.target.value))}
              >
                {anos.map((a) => (
                  <option key={a} value={a}>
                    {a}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>
      }
    >
      {r.isPending && <CarregandoLista linhas={4} altura="1.5rem" texto="Carregando o ranking…" />}
      {r.isError && <EstadoConsulta erro={r.error} oQue="os casos por bairro" aoTentar={() => r.refetch()} />}
      {r.isSuccess && linhas.length === 0 && (
        <EstadoDados tipo="insuficiente" titulo="Sem casos por bairro neste ano." />
      )}
      {linhas.length > 0 && (
        <>
          <p className={estilos.totalAno}>
            {comCasos.length > 0 ? (
              <>
                Total em {anoTexto}: <b>{formatarNumero(total)}</b> casos de {nomeAgravo} nos bairros com
                registro.
              </>
            ) : (
              `Nenhum bairro com registro de ${nomeAgravo} em ${anoTexto}.`
            )}{" "}
            {nivel === "distrito" && "Toque no (i) para ver os bairros de cada distrito."}
          </p>
          <ol className={estilos.barras} aria-label={`Casos de ${nomeAgravo} por ${nivel}`}>
            {linhas.map((l) => (
              <li key={l.id}>
                <span className={estilos.nomeBarra}>
                  {l.nome}
                  {nivel === "distrito" && l.id !== "sem-distrito" && (
                    <PopoverBairros
                      distrito={l.nome}
                      bairros={bairrosDoDistrito(l.id, territorios.data ?? [], d?.itens ?? [])}
                      oQue={`Casos de ${nomeAgravo} em ${anoTexto}`}
                    />
                  )}
                </span>
                {l.casos === null ? (
                  <>
                    <span aria-hidden="true" />
                    <span className={estilos.semRegistro}>sem registro</span>
                  </>
                ) : (
                  <>
                    <span
                      className={estilos.barra}
                      style={{ width: `${Math.max(2, (l.casos / maximo) * 100)}%` }}
                      aria-hidden="true"
                    />
                    <span className={estilos.valorBarra}>
                      {formatarNumero(l.casos)}
                      <span className="so-leitor"> casos</span>
                    </span>
                  </>
                )}
              </li>
            ))}
          </ol>
        </>
      )}
    </Painel>
  );
}
