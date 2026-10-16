import { useEffect, useMemo, useState } from "react";
import type { EChartsOption } from "echarts";
import { FlaskConical, Send } from "lucide-react";
import { useLocation, useNavigate } from "react-router-dom";
import { CabecalhoTela } from "@/app/AppShell";
import { QuadroGrafico } from "@/charts/QuadroGrafico";
import { token } from "@/charts/tema";
import { Botao } from "@/design-system/componentes/Botao";
import { EstadoDados, LegendaFonte } from "@/design-system/componentes/EstadoDados";
import { Carregando, FalhaCarga } from "@/design-system/componentes/Painel";
import { ReguaMare } from "@/design-system/componentes/ReguaMare";
import { SeloNivel } from "@/design-system/componentes/SeloNivel";
import type { ChaveNivel } from "@/design-system/niveis";
import { consulta, type Esquemas } from "@/lib/api";
import { useConsulta } from "@/lib/consultas";
import { formatarDataHora, formatarHora, formatarMm, formatarNumero, quandoRelativo } from "@/lib/formatos";
import { useRecorte } from "@/lib/recorte";
import { useSessao } from "@/lib/sessao";
import { PRIORIDADES } from "@/textos/glossario";
import estilos from "./TelaCenarios.module.css";

type Resposta = Esquemas["RespostaDados_Cenario_"];
const HORIZONTES = [24, 48, 72] as const;
const NIVEL: Record<string, ChaveNivel> = {
  sem_indicacao: "sem",
  atencao: "atencao",
  alerta: "alerta",
  critico: "critico",
  dados_insuficientes: "insuficiente",
};
const QUALIDADE: Record<string, string> = {
  completa: "Completa: todos os insumos chegaram.",
  parcial: "Parcial: falta algum insumo que melhoraria a estimativa.",
  insuficiente: "Insuficiente: faltam insumos obrigatórios.",
};

/** Cenários de alagamento (design §9.7, RF-09). Tudo EXPERIMENTAL; prioridade nunca é chance de alagar (RN-06). */
/** “hoje”, “amanhã” ou “18/10”: curto para caber embaixo da hora no eixo. */
function diaCurto(d: Date) {
  const hoje = new Date();
  hoje.setHours(0, 0, 0, 0);
  const dias = Math.round((new Date(d).setHours(0, 0, 0, 0) - hoje.getTime()) / 86_400_000);
  if (dias === 0) return "hoje";
  if (dias === 1) return "amanhã";
  return `${String(d.getDate()).padStart(2, "0")}/${String(d.getMonth() + 1).padStart(2, "0")}`;
}

export function TelaCenarios() {
  const { recorte } = useRecorte();
  const { pode } = useSessao();
  const navegar = useNavigate();
  const local = useLocation();
  const [horizonte, setHorizonte] = useState<(typeof HORIZONTES)[number]>(72);
  const r = useConsulta<Resposta>(
    `/cenarios${consulta({ territorio_id: recorte.territorio, horizonte_h: horizonte })}`,
    {
      staleTime: 5 * 60_000,
    },
  );
  useEffect(() => {
    document.title = "Cenários de alagamento | ClimaSense";
  }, []);

  const graficos = useMemo(() => {
    const d = r.data?.dados;
    if (!d) return null;
    const inicio = new Date(d.estimativa.emitida_em);
    inicio.setMinutes(0, 0, 0);
    const fim = new Date(inicio.getTime() + d.horizonte_h * 3_600_000);
    const passo = (d.horizonte_h <= 24 ? 3 : d.horizonte_h <= 48 ? 6 : 12) * 3_600_000;
    // os dois gráficos usam o MESMO domínio de tempo: os eixos ficam alinhados
    const eixoX = {
      type: "time" as const,
      min: inicio.getTime(),
      max: fim.getTime(),
      // o mesmo intervalo de marcação nos dois gráficos: os rótulos de hora caem nos mesmos lugares
      // (o ECharts só respeita o intervalo do eixo de tempo com mínimo e máximo iguais)
      minInterval: passo,
      maxInterval: passo,
      axisLabel: {
        formatter: (v: number) => `${formatarHora(new Date(v), true)}\n${diaCurto(new Date(v))}`,
        hideOverlap: true,
        lineHeight: 20,
      },
    };
    const grade = { left: 64, right: 24, top: 40, bottom: 56, containLabel: false };
    const tooltipHora = (unidade: (v: number | null) => string) => ({
      trigger: "axis" as const,
      formatter: (ps: unknown) => {
        const lista = ps as { value: [number, number | null]; seriesName: string }[];
        if (!lista.length) return "";
        const linhas = lista
          .filter((p) => !p.seriesName.startsWith("_"))
          .map((p) => `${p.seriesName}: <strong>${unidade(p.value[1])}</strong>`);
        return `${formatarDataHora(new Date(lista[0].value[0]))}<br>${linhas.join("<br>")}`;
      },
    });
    const temFaixa = d.chuva.some((p) => p.min !== null && p.max !== null);
    const chuva: EChartsOption = {
      grid: grade,
      legend: temFaixa ? { top: 0, left: 0, data: ["Chuva prevista", "Faixa entre previsões"] } : undefined,
      tooltip: tooltipHora((v) => formatarMm(v)),
      xAxis: eixoX,
      yAxis: { type: "value", name: "mm por hora", min: 0 },
      series: [
        ...(temFaixa
          ? [
              {
                name: "_base",
                type: "line" as const,
                stack: "faixa",
                symbol: "none",
                lineStyle: { opacity: 0 },
                data: d.chuva.map((p) => [new Date(p.t).getTime(), p.min]),
                silent: true,
              },
              {
                name: "Faixa entre previsões",
                type: "line" as const,
                stack: "faixa",
                symbol: "none",
                lineStyle: { opacity: 0 },
                areaStyle: { color: token("--g-1"), opacity: 0.18 },
                itemStyle: { color: token("--g-1") },
                data: d.chuva.map((p) => [
                  new Date(p.t).getTime(),
                  p.max !== null && p.min !== null ? p.max - p.min : null,
                ]),
              },
            ]
          : []),
        {
          name: "Chuva prevista",
          type: "bar",
          barMaxWidth: 8,
          itemStyle: { color: token("--g-1"), borderRadius: [3, 3, 0, 0] },
          data: d.chuva.map((p) => [new Date(p.t).getTime(), p.valor]),
          markArea: d.estimativa.janela_atencao
            ? {
                silent: true,
                itemStyle: { color: "rgba(201, 138, 0, 0.12)" },
                label: {
                  show: true,
                  position: "insideTop",
                  formatter: "janela de atenção",
                  color: token("--cs-tinta"),
                },
                data: [
                  [
                    { xAxis: new Date(d.estimativa.janela_atencao.inicio).getTime() },
                    { xAxis: new Date(d.estimativa.janela_atencao.fim).getTime() },
                  ],
                ],
              }
            : undefined,
        },
      ],
    };
    const mare: EChartsOption = {
      grid: grade,
      tooltip: tooltipHora((v) => (v === null ? "sem dado" : `${formatarNumero(v, 2)} m`)),
      xAxis: eixoX,
      yAxis: { type: "value", name: "metros (nível médio = 0)", scale: true },
      series: [
        {
          name: "Nível do mar previsto",
          type: "line",
          symbol: "none",
          lineStyle: { width: 2.5, color: token("--g-2") },
          itemStyle: { color: token("--g-2") },
          data: d.mare.map((p) => [new Date(p.t).getTime(), p.valor]),
          markLine: {
            silent: true,
            symbol: "none",
            lineStyle: { type: "dashed", color: token("--g-ref") },
            label: { formatter: "maré alta (0,6 m)", color: token("--cs-tinta-2") },
            data: [{ yAxis: 0.6 }],
          },
        },
      ],
    };
    const acumulado = d.chuva.reduce((s, p) => s + (p.valor ?? 0), 0);
    return {
      dominio: [eixoX.min, eixoX.max],
      chuva,
      mare,
      tabelaChuva: {
        colunas: ["Hora", "Chuva prevista (mm)", "Menor previsão (mm)", "Maior previsão (mm)"],
        linhas: d.chuva.map((p) => [formatarDataHora(p.t), p.valor, p.min, p.max]),
      },
      tabelaMare: {
        colunas: ["Hora", "Nível do mar (m)"],
        linhas: d.mare.map((p) => [formatarDataHora(p.t), p.valor]),
      },
      resumoChuva: d.chuva.length
        ? `Previsão de ${formatarMm(acumulado)} nas próximas ${d.horizonte_h} horas${
            d.estimativa.acumulado_previsto_mm !== null
              ? `, com ${formatarMm(d.estimativa.acumulado_previsto_mm)} nas 24 horas mais chuvosas`
              : ""
          }.`
        : "Não há previsão de chuva carregada para este horizonte.",
      resumoMare:
        d.estimativa.mare_maxima_m !== null && d.estimativa.mare_maxima_em
          ? `A maré mais alta prevista é de ${formatarNumero(
              d.estimativa.mare_maxima_m,
              2,
            )} m, ${quandoRelativo(d.estimativa.mare_maxima_em)}.`
          : d.mare.length
            ? "Nível do mar previsto em frente ao Porto do Recife."
            : "Não há previsão de maré carregada.",
    };
  }, [r.data]);

  function encaminhar() {
    const d = r.data?.dados;
    if (!d) return;
    const e = d.estimativa;
    navegar(`/app/avaliacoes/nova${local.search}`, {
      state: {
        territorio_id: d.territorio_id,
        prioridade: e.prioridade === "dados_insuficientes" ? "sem_indicacao" : e.prioridade,
        justificativa: [
          `Cenário experimental de ${d.horizonte_h} h emitido ${quandoRelativo(e.emitida_em)} (método ${
            e.metodo
          }, versão ${e.versao_metodo}).`,
          ...e.fatores.map((f) => `${f.nome}: ${f.descricao}`),
        ].join("\n"),
        limitacoes: e.limitacoes.join("\n"),
        evidencias: [
          {
            tipo: "cenario",
            descricao: `Cenário de ${d.horizonte_h} h para ${d.territorio_nome}: ${
              PRIORIDADES[e.prioridade]
            }`,
            fonte_id: "open-meteo-previsao",
            capturada_em: e.emitida_em,
            valor:
              e.acumulado_previsto_mm !== null ? formatarMm(e.acumulado_previsto_mm) + " em 24 h" : undefined,
            endereco: `/app/cenarios${local.search}`,
          },
          ...(e.mare_maxima_m !== null
            ? [
                {
                  tipo: "cenario",
                  descricao: "Maré máxima prevista no horizonte",
                  fonte_id: "open-meteo-mare",
                  capturada_em: d.mare_emitida_em ?? e.emitida_em,
                  valor: `${formatarNumero(e.mare_maxima_m, 2)} m`,
                },
              ]
            : []),
        ],
      },
    });
  }

  const d = r.data?.dados;
  const meta = r.data?.meta;
  const e = d?.estimativa;
  return (
    <>
      <p className={estilos.experimental} role="note">
        <FlaskConical aria-hidden="true" size={22} />
        <span>
          <strong>Experimental: não validado para uso operacional.</strong> A prioridade é uma indicação para
          a equipe avaliar, nunca a chance de alagar.
        </span>
      </p>
      <CabecalhoTela
        titulo="Cenários de alagamento"
        proposito="Chuva prevista e maré nas próximas horas, e o que a regra de referência indica para o território."
      />
      <fieldset className={estilos.horizonte}>
        <legend>Horizonte</legend>
        <div>
          {HORIZONTES.map((h) => (
            <label key={h} data-marcado={horizonte === h}>
              <input
                type="radio"
                name="horizonte"
                checked={horizonte === h}
                onChange={() => setHorizonte(h)}
              />
              {h} horas
            </label>
          ))}
        </div>
      </fieldset>
      {r.isPending && <Carregando texto="Montando o cenário com a previsão mais recente…" />}
      {r.isError && <FalhaCarga erro={r.error} aoTentar={() => r.refetch()} />}
      {d && e && meta && graficos && (
        <div className={estilos.area}>
          <div className={estilos.graficos} data-dominio={`${graficos.dominio[0]}/${graficos.dominio[1]}`}>
            <p className={estilos.separacao}>
              <strong>Observação:</strong> a reanálise de chuva medida chega com cerca de 7 dias de atraso,
              então o cenário usa só previsões. <strong>Previsão meteorológica:</strong> emitida{" "}
              {d.previsao_emitida_em ? quandoRelativo(d.previsao_emitida_em) : "sem emissão carregada"}.
            </p>
            {d.chuva.length ? (
              <QuadroGrafico
                titulo={`Chuva prevista: ${d.territorio_nome}`}
                resumo={graficos.resumoChuva}
                opcao={graficos.chuva}
                tabela={graficos.tabelaChuva}
                altura={280}
                fontes={meta.fontes
                  .filter((f) => f.id === "open-meteo-previsao")
                  .map((f) => ({ nome: `${f.nome} (prevista)`, atualizadoEm: f.atualizado_em }))}
              />
            ) : (
              <EstadoDados tipo="insuficiente" titulo="Sem previsão de chuva">
                A previsão de chuva ainda não foi carregada. Peça ao administrador para atualizar a fonte em
                Fontes de dados.
              </EstadoDados>
            )}
            {d.mare.length ? (
              <QuadroGrafico
                titulo="Maré prevista em frente ao Porto do Recife"
                resumo={graficos.resumoMare}
                opcao={graficos.mare}
                tabela={graficos.tabelaMare}
                altura={240}
                fontes={meta.fontes
                  .filter((f) => f.id === "open-meteo-mare")
                  .map((f) => ({ nome: `${f.nome} (prevista)`, atualizadoEm: f.atualizado_em }))}
              />
            ) : (
              <EstadoDados tipo="insuficiente" titulo="Sem previsão de maré">
                Sem a maré, o cenário não estima nada. Atualize a fonte de maré em Fontes de dados.
              </EstadoDados>
            )}
            {d.emissoes_na_faixa < 2 && (
              <p className={estilos.nota}>
                A faixa de incerteza compara emissões sucessivas da previsão para a mesma hora. Só há uma
                emissão carregada, então ela aparece depois da próxima atualização.
              </p>
            )}
          </div>

          <aside
            className={estilos.decisao}
            aria-labelledby="decisao-titulo"
            data-nivel={NIVEL[e.prioridade]}
          >
            <h2 id="decisao-titulo">Prioridade operacional indicada</h2>
            {e.prioridade === "dados_insuficientes" ? (
              <div className={estilos.insuficiente}>
                <ReguaMare nivel="insuficiente" compacta animar={false} />
                <EstadoDados tipo="insuficiente" titulo="Dados insuficientes para estimar">
                  {e.limitacoes[0]}
                </EstadoDados>
              </div>
            ) : (
              <>
                <SeloNivel nivel={NIVEL[e.prioridade]} rotulo={PRIORIDADES[e.prioridade]} grande />
                <p className={estilos.janela}>
                  {e.janela_atencao
                    ? `Janela de atenção: de ${quandoRelativo(e.janela_atencao.inicio)} a ${quandoRelativo(
                        e.janela_atencao.fim,
                      )}.`
                    : "Sem janela de atenção nas próximas horas."}
                </p>
              </>
            )}
            {e.fatores.length > 0 && (
              <>
                <h3>Por quê</h3>
                <ul className={estilos.fatores}>
                  {e.fatores.map((f) => (
                    <li key={f.nome}>
                      <strong>{f.nome}.</strong> {f.descricao}
                    </li>
                  ))}
                </ul>
              </>
            )}
            <h3>Qualidade dos dados</h3>
            <p>{QUALIDADE[e.qualidade]}</p>
            {e.prioridade !== "dados_insuficientes" && (
              <>
                <h3>Limitações</h3>
                <ul className={estilos.limitacoes}>
                  {e.limitacoes.map((l) => (
                    <li key={l}>{l}</li>
                  ))}
                </ul>
              </>
            )}
            <p className={estilos.metodo}>
              Método {e.metodo}, versão {e.versao_metodo}. Emitido {formatarDataHora(e.emitida_em)} e guardado
              para conferência futura (registro {d.registro_id}).
            </p>
            {pode("editar") && (
              <Botao onClick={encaminhar} icone={<Send />} larguraTotal>
                Encaminhar para avaliação
              </Botao>
            )}
            <LegendaFonte
              fontes={meta.fontes.map((f) => ({ nome: f.nome, atualizadoEm: f.atualizado_em }))}
            />
          </aside>
        </div>
      )}
    </>
  );
}
