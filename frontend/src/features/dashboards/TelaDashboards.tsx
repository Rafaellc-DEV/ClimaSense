import { useEffect, useId, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import type { EChartsOption } from "echarts";
import {
  ChevronRight,
  CircleOff,
  Crosshair,
  FlaskConical,
  Hospital,
  Info,
  MapPin,
  Share2,
  Baby,
  Users,
  Sparkles,
  TrendingDown,
  TrendingUp,
  Minus,
} from "lucide-react";
import { token } from "@/charts/tema";
import { useAviso } from "@/design-system/componentes/Aviso";
import { Dialogo } from "@/design-system/componentes/Dialogo";
import { EstadoDados } from "@/design-system/componentes/EstadoDados";
import { Pilula } from "@/design-system/componentes/Pilula";
import { Segmentado } from "@/design-system/componentes/Segmentado";
import { Tabela } from "@/design-system/componentes/Tabela";
import { ESTAGIOS, infoEstagio } from "@/features/evento/estagios";
import { nomeCurto, quandoAs } from "@/features/evento/textos";
import { desembrulhar } from "@/features/evento/tipos";
import { contarPorEstagio } from "@/features/mapa/tipos";
import { NIVEL_ALERTA, type SemanaCasos } from "@/features/saude/tipos";
import type { CenarioHora } from "@/features/situacao/dados";
import { consulta } from "@/lib/api";
import { INTERVALO, useConsultaViva } from "@/lib/consultas";
import { siglaDistrito } from "@/lib/distritos";
import { diaNoRecife, formatarHoraMinuto, formatarNumero, somarDias } from "@/lib/formatos";
import { fontesDe, haQuanto, semVencidas } from "@/lib/frescor";
import { CartaoPainel, GraficoPainel, SeloExp, Vazio } from "./CartaoPainel";
import {
  COR_ESTAGIO,
  graficoChuvaDistritos,
  graficoDengue,
  graficoDonut,
  graficoMareChuva,
  graficoPessoas,
} from "./graficos";
import {
  acoesPorDistrito,
  alertasVigentes,
  confiancaDados,
  CONTEXTO_HISTORICO,
  exposicaoPorDistrito,
  gerarInsights,
  JANELAS,
  janelaLeptospirose,
  leituraAgravo,
  mareNoPico,
  previstaVsMedia,
  rankingAgir,
  ROTULO_INSUMO,
  tendenciaDaSerie,
  topVulneraveis,
  type Janela,
} from "./indicadores";
import { KpisPainel, RodapeFonte } from "./Kpis";
import { useDadosDecisao } from "./usarDadosDecisao";
import estilos from "./Painel.module.css";

type Foco = "tudo" | "deslizamento" | "alagamento" | "saude";
const FOCOS: { valor: Foco; rotulo: string }[] = [
  { valor: "tudo", rotulo: "Tudo" },
  { valor: "deslizamento", rotulo: "Deslizamento" },
  { valor: "alagamento", rotulo: "Alagamento" },
  { valor: "saude", rotulo: "Saúde" },
];
const TODOS = ["pendentes", "gatilho", "chuva", "chuva-distrito", "expostos", "agir", "saude"];
/** O que cada foco destaca. O resto continua na tela, mais claro. "Situação agora" vale para todos. */
const RELEVANTES: Record<Foco, string[]> = {
  tudo: TODOS,
  deslizamento: ["pendentes", "gatilho", "chuva", "chuva-distrito", "expostos", "agir"],
  alagamento: ["pendentes", "gatilho", "chuva", "chuva-distrito", "expostos", "agir"],
  saude: ["saude", "agir", "expostos"],
};

const mm = (v: number) => formatarNumero(v, v < 10 && !Number.isInteger(v) ? 1 : 0);

/** "Bom dia", "Boa tarde" ou "Boa noite" pela hora do Recife. */
function saudacao(agora: Date): string {
  const h = Number(
    new Intl.DateTimeFormat("pt-BR", {
      timeZone: "America/Recife",
      hour: "numeric",
      hourCycle: "h23",
    }).format(agora),
  );
  return h < 12 ? "Bom dia" : h < 18 ? "Boa tarde" : "Boa noite";
}

/** Monta um gráfico sem derrubar a página se os dados vierem fora do esperado: `null` mostra o aviso no cartão. */
function tentar<T>(montar: () => T): T | null {
  try {
    return montar();
  } catch {
    return null;
  }
}
const SEM_GRAFICO = {
  opcao: null as unknown as EChartsOption,
  tabela: { colunas: [] as string[], linhas: [] as (string | number | null)[][] },
  resumo: "",
};

/**
 * Dashboards (aprovado pelo dono em 26/11/2026, P-61). Poucos números e gráficos; frases, histórico, alertas e a
 * confiança dos dados ficam em "Detalhes". Filtros no endereço (?territorio=&janela=&foco=) para mandar o link. Sem
 * dado, "Dados insuficientes" e a fonte que falta. A tela não muda estágio: quem declara é a equipe, no Mapa (RN-05).
 */
export function TelaDashboards() {
  const idTerr = useId();
  const idFoco = useId();
  const avisar = useAviso();
  const [params, setParams] = useSearchParams();
  const territorio = /^ds-\d$/.test(params.get("territorio") ?? "")
    ? (params.get("territorio") as string)
    : "recife";
  const janela: Janela = params.get("janela") === "72" ? 72 : 24;
  const foco: Foco = FOCOS.some((f) => f.valor === params.get("foco"))
    ? (params.get("foco") as Foco)
    : "tudo";
  const mudar = (chave: string, valor: string, padrao: string) =>
    setParams(
      (anterior) => {
        const novo = new URLSearchParams(anterior);
        if (valor === padrao) novo.delete(chave);
        else novo.set(chave, valor);
        return novo;
      },
      { replace: true },
    );
  const [detalhes, setDetalhes] = useState(false);
  const distritoId = territorio === "recife" ? null : territorio;
  const d = useDadosDecisao({ janela, distritoId });
  const agora = useMemo(() => new Date(), [d.momento]); // eslint-disable-line react-hooks/exhaustive-deps
  const esmaecer = useMemo(() => new Set(TODOS.filter((i) => !RELEVANTES[foco].includes(i))), [foco]);

  useEffect(() => {
    document.title = "Dashboards | ClimaSense";
  }, []);

  const compartilhar = async () => {
    try {
      await navigator.clipboard.writeText(window.location.href);
      avisar({ titulo: "Link copiado.", texto: "Quem abrir vê o mesmo território, período e foco." });
    } catch {
      avisar({ titulo: "Não foi possível copiar.", texto: "Copie o endereço na barra do navegador." });
    }
  };

  const quando = (iso: string) => quandoAs(iso, agora);
  const linhasPrevista = useMemo(
    () => previstaVsMedia(d.itensDistrito, d.mediaMensal, agora, janela),
    [d.itensDistrito, d.mediaMensal, agora, janela],
  );
  const mare = useMemo(() => mareNoPico(d.distritosEscopo, d.limiares), [d.distritosEscopo, d.limiares]);
  const acoes = useMemo(
    () => acoesPorDistrito(d.itensDistrito, d.dadosAcoes),
    [d.itensDistrito, d.dadosAcoes],
  );
  const alertas = useMemo(() => alertasVigentes(d.itensDistrito, agora), [d.itensDistrito, agora]);
  const lepto = janelaLeptospirose(d.dadosSaude?.janela_leptospirose, agora);
  const confianca = confiancaDados(d.fontes, d.chuva);
  const insights = gerarInsights({
    pendencias: d.pendencias,
    gatilhos: d.gatilhos,
    razoes: linhasPrevista.filter((l) => !distritoId || l.id === distritoId),
    acoes: acoes.filter((a) => !distritoId || a.id === distritoId),
    alertas,
    pessoas: d.pessoas,
    leptospirose: lepto,
    chuva: d.chuva,
    fontes: d.fontes,
    janela,
    agora,
    quando,
  });
  // dado de fonte vencida não aparece (ADR 0019): nem o número, nem aviso sobre ele
  const chipsFrases = insights.filter((i) => i.id !== "fonte-vencida").slice(0, 2);
  const fontesSaude = semVencidas(fontesDe(d.saude.data));

  // chuva por distrito
  const grafChuva =
    tentar(() => graficoChuvaDistritos(d.linhasChuva, linhasPrevista, d.limiares, janela, distritoId)) ??
    SEM_GRAFICO;
  const temChuva = d.linhasChuva.some((l) => l.mm !== null) || linhasPrevista.some((l) => l.prevMm !== null);
  const maiorMedida = d.linhasChuva.find((l) => l.mm !== null);

  // estágios
  const territoriosEstagio = useMemo(() => {
    const base = d.itensBairro.length > 0 ? d.itensBairro : d.itensDistrito;
    return distritoId
      ? base.filter((i) => (i.nivel === "bairro" ? i.distrito_id : i.territorio_id) === distritoId)
      : base;
  }, [d.itensBairro, d.itensDistrito, distritoId]);
  const unidade = d.itensBairro.length > 0 ? "bairros" : "distritos";
  const contagem = useMemo(() => contarPorEstagio(territoriosEstagio), [territoriosEstagio]);
  const donut = tentar(() => graficoDonut(contagem, unidade)) ?? {
    ...SEM_GRAFICO,
    total: contagem.reduce((n, c) => n + c.declarados + c.sugeridos, 0),
  };
  const declarados = contagem.reduce((n, c) => n + c.declarados, 0);

  // onde agir primeiro
  const pendentes = useMemo(() => new Set((d.pendencias?.itens ?? []).map((i) => i.id)), [d.pendencias]);
  const ranking = useMemo(
    () => rankingAgir(d.itensBairro, d.posicao, d.dadosImpacto, pendentes, distritoId),
    [d.itensBairro, d.posicao, d.dadosImpacto, pendentes, distritoId],
  );
  const maxPessoas = Math.max(...ranking.map((r) => r.pessoas ?? 0), 1);

  // quem está exposto (Detalhes)
  const exposicao = useMemo(
    () => exposicaoPorDistrito(d.dadosImpacto).filter((e) => !distritoId || e.id === distritoId),
    [d.dadosImpacto, distritoId],
  );
  // pessoas e unidades expostas: bairros com estágio sugerido Atenção ou mais
  const totalAtencao = exposicao.reduce((s, e) => s + e.bairrosAtencao, 0);
  const somaExp = exposicao.reduce(
    (s, e) => ({
      idosos: s.idosos + e.idososAtencao,
      criancas: s.criancas + e.criancasAtencao,
      unidades: s.unidades + e.unidadesAtencao,
      parcial: s.parcial || e.parcial,
    }),
    { idosos: 0, criancas: 0, unidades: 0, parcial: false },
  );
  const distritoRef = distritoId ?? d.gatilhos?.itens[0]?.id ?? null;
  const vulneraveisRef = topVulneraveis(d.bairrosVulneraveis, distritoRef);
  const nomeRef = nomeCurto(
    d.itensDistrito.find((i) => i.territorio_id === distritoRef)?.territorio_nome ?? "distrito",
  );

  const grafPessoas = tentar(() => graficoPessoas(exposicao)) ?? { ...SEM_GRAFICO, vazio: false };

  // maré e chuva previstas (Detalhes)
  const cenario: CenarioHora | null = useMemo(() => {
    const p = d.chuva?.previsao;
    if (!p || (p.chuva.length === 0 && p.mare.length === 0)) return null;
    const inicio = p.chuva[0] ? new Date(p.chuva[0].t).getTime() : Date.now();
    return {
      territorio_id: "recife",
      territorio_nome: "Recife",
      previsao_emitida_em: p.previsao_emitida_em,
      mare_emitida_em: p.mare_emitida_em,
      chuva: p.chuva.slice(0, janela),
      mare: p.mare.filter((m) => new Date(m.t).getTime() < inicio + janela * 3_600_000),
    };
  }, [d.chuva, janela]);
  const grafMare = cenario
    ? (tentar(() => graficoMareChuva(cenario, agora.getTime(), d.limiares.mare_alta_m ?? null)) ??
      SEM_GRAFICO)
    : null;

  // dengue nas últimas semanas
  const desde = somarDias(diaNoRecife(agora), -90);
  const semanal = useConsultaViva<unknown>(
    `/saude/semanal${consulta({ agravo: "dengue", desde })}`,
    INTERVALO.saude,
  );
  const semanas = desembrulhar<{ itens?: SemanaCasos[] }>(semanal.data)?.itens;
  const grafDengue = useMemo(() => tentar(() => graficoDengue(semanas ?? [])), [semanas]);
  const agravos = d.dadosSaude?.agravos ?? [];
  const leituras = agravos.map(leituraAgravo);
  const dengue = leituras.find((l) => l.agravo === "dengue");
  const dengueResumo = agravos.find((a) => a.agravo === "dengue");
  const ultimaSemana = (() => {
    const s = dengueResumo?.ultima_semana_com_dado ?? dengueResumo?.ultima_semana;
    return s && typeof s === "object" ? `SE ${s.semana}/${s.ano}` : null;
  })();
  // a semana incompleta fica fora da tendência; com a fonte parada (utilizável = falso) não há tendência atual
  const tendencia =
    dengueResumo?.utilizavel === false ? null : (tendenciaDaSerie(semanas) ?? dengue?.tendencia ?? null);
  const respostaSaude =
    tendencia === "sobe"
      ? { texto: "Subindo", tom: "alerta" as const }
      : tendencia === "cai"
        ? { texto: "Caindo", tom: "sucesso" as const }
        : tendencia === "estavel"
          ? { texto: "Estável", tom: "info" as const }
          : { texto: "Dados insuficientes", tom: "insuficiente" as const };
  const outros = leituras.filter((l) => l.agravo !== "dengue" && l.agravo !== "leptospirose");
  const nomeTerritorio =
    territorio === "recife"
      ? "Recife"
      : nomeCurto(d.itensDistrito.find((i) => i.territorio_id === territorio)?.territorio_nome ?? territorio);

  return (
    <div className={estilos.pagina}>
      <header className={estilos.cab}>
        <div className={estilos.titulo}>
          <h1>{saudacao(agora)}, equipe</h1>
          <p className={estilos.subtitulo}>
            {nomeTerritorio}
            {d.momento > 0 && ` · atualizado às ${formatarHoraMinuto(d.momento)}`} ·{" "}
            <span
              className={estilos.legendaExp}
              title="Experimental: usa previsão ou estágio sugerido, ainda sem validação."
            >
              <FlaskConical aria-hidden="true" size={13} /> experimental
            </span>
          </p>
        </div>
        <div className={estilos.acoes}>
          <label className={estilos.filtro} htmlFor={idTerr}>
            <MapPin aria-hidden="true" size={16} />
            <span className="so-leitor">Território</span>
            <select
              id={idTerr}
              value={territorio}
              onChange={(e) => mudar("territorio", e.target.value, "recife")}
            >
              <option value="recife">Recife</option>
              {d.itensDistrito.map((i) => (
                <option key={i.territorio_id} value={i.territorio_id}>
                  {nomeCurto(i.territorio_nome)}
                </option>
              ))}
            </select>
          </label>
          <Segmentado
            rotulo="Período"
            rotuloOculto
            opcoes={JANELAS.map((j) => ({ valor: j, rotulo: `${j} h` }))}
            valor={janela}
            aoMudar={(j) => mudar("janela", String(j), "24")}
          />
          <label className={estilos.filtro} htmlFor={idFoco}>
            <Crosshair aria-hidden="true" size={16} />
            <span className="so-leitor">Foco</span>
            <select id={idFoco} value={foco} onChange={(e) => mudar("foco", e.target.value, "tudo")}>
              {FOCOS.map((f) => (
                <option key={f.valor} value={f.valor}>
                  {f.rotulo}
                </option>
              ))}
            </select>
          </label>
          <button type="button" className={estilos.secundario} onClick={() => setDetalhes(true)}>
            <Info aria-hidden="true" size={18} /> Detalhes
          </button>
          <button type="button" className={estilos.primario} onClick={compartilhar}>
            <Share2 aria-hidden="true" size={18} /> Compartilhar
          </button>
        </div>
      </header>

      {(chipsFrases.length > 0 || !d.distritos.isPending) && (
        <ul className={estilos.chips} aria-label="Avisos e destaques">
          {chipsFrases.map((i) => (
            <li key={i.id} className={estilos.chip} title={i.texto}>
              <Sparkles aria-hidden="true" size={16} />
              {i.curto}
              {i.experimental && <SeloExp />}
            </li>
          ))}
          {!d.distritos.isPending && chipsFrases.length === 0 && (
            <li className={[estilos.chip, estilos.chipVazio].join(" ")}>
              <CircleOff aria-hidden="true" size={16} /> Sem destaques: dados insuficientes
            </li>
          )}
        </ul>
      )}

      <KpisPainel d={d} janela={janela} agora={agora} esmaecer={esmaecer} />

      <div className={[estilos.linha, estilos.linhaGrande].join(" ")}>
        <CartaoPainel
          id="db-chuva"
          titulo="Chuva por distrito"
          resposta={
            maiorMedida
              ? { texto: `Maior: ${maiorMedida.nome}, ${mm(maiorMedida.mm ?? 0)} mm`, tom: "info" }
              : null
          }
          experimental
          esmaecido={esmaecer.has("chuva-distrito")}
          carga={d.situacao}
          oQue="a chuva por distrito"
          insuficiente={temChuva ? null : "chuva medida (APAC) e prevista (Open-Meteo)"}
          tabela={grafChuva.tabela}
          alturaMin={280}
          rodape={
            <RodapeFonte
              ids={["apac-chuva", "open-meteo-previsao"]}
              padrao="APAC · Open-Meteo"
              consultadoEm={d.situacao.dataUpdatedAt}
              fontes={d.fontes}
            />
          }
        >
          <GraficoPainel opcao={grafChuva.opcao} rotulo="Chuva por distrito" resumo={grafChuva.resumo} />
        </CartaoPainel>

        <CartaoPainel
          id="db-expostos"
          titulo="Pessoas e unidades de saúde expostas"
          experimental
          esmaecido={esmaecer.has("expostos")}
          carga={d.impacto}
          oQue="as pessoas expostas"
          insuficiente={exposicao.length ? null : "previsão de chuva e maré (Open-Meteo)"}
          livre
          rodape={
            <>
              Moradores (Censo 2022) e unidades públicas ·{" "}
              <RodapeFonte
                ids={["ibge-censo-2022-bairro", "cnes-equipamentos"]}
                padrao="IBGE 2022"
                consultadoEm={d.impacto.dataUpdatedAt}
                fontes={d.fontes}
              />
            </>
          }
        >
          {totalAtencao > 0 ? (
            <div className={estilos.expostos}>
              <p className={estilos.expostosTopo}>
                {totalAtencao} {totalAtencao === 1 ? "bairro" : "bairros"} em Atenção ou mais
              </p>
              <ul className={estilos.tiles}>
                <li>
                  <Users aria-hidden="true" size={20} />
                  <b>{formatarNumero(somaExp.idosos)}</b>
                  <span>idosos (60+)</span>
                </li>
                <li>
                  <Baby aria-hidden="true" size={20} />
                  <b>{formatarNumero(somaExp.criancas)}</b>
                  <span>crianças (0 a 14)</span>
                </li>
                <li>
                  <Hospital aria-hidden="true" size={20} />
                  <b>{formatarNumero(somaExp.unidades)}</b>
                  <span>unidades de saúde</span>
                </li>
              </ul>
              {somaExp.parcial && (
                <p className={estilos.nota}>Contagem omitida em algum bairro: os totais são um mínimo.</p>
              )}
            </div>
          ) : (
            <div className={estilos.expostos}>
              <p className={estilos.expostosTopo}>Nenhum bairro em Atenção agora</p>
              {vulneraveisRef.length > 0 && (
                <>
                  <p className={estilos.nota}>
                    Referência, não previsão: mais moradores idosos e crianças no {nomeRef}, o distrito mais
                    perto do gatilho.
                  </p>
                  <ol className={estilos.topVuln}>
                    {vulneraveisRef.map((b) => (
                      <li key={b.id}>
                        <b>{b.nome}</b>
                        <span className={estilos.barraPessoas}>
                          <span>
                            <i style={{ width: `${(b.total / vulneraveisRef[0].total) * 100}%` }} />
                          </span>
                          <b>{formatarNumero(b.total)}</b>
                        </span>
                        <small>
                          {formatarNumero(b.idosos)} idosos · {formatarNumero(b.criancas)} crianças
                        </small>
                      </li>
                    ))}
                  </ol>
                </>
              )}
            </div>
          )}
        </CartaoPainel>
      </div>

      <div className={[estilos.linha, estilos.linhaGrande].join(" ")}>
        <CartaoPainel
          id="db-agir"
          titulo="Onde agir primeiro"
          experimental
          esmaecido={esmaecer.has("agir")}
          acao={
            <Link to="/app" className={estilos.verMapa}>
              Ver no Mapa <ChevronRight aria-hidden="true" size={16} />
            </Link>
          }
          carga={d.bairros.isPending ? d.bairros : undefined}
          oQue="os bairros"
          insuficiente={d.itensBairro.length === 0 && !d.bairros.isPending ? "estágios por bairro" : null}
          livre
          rodape={
            <>
              Moradores idosos e crianças (Censo 2022), não atingidos ·{" "}
              <RodapeFonte
                ids={["ibge-censo-2022-bairro"]}
                padrao="IBGE 2022"
                consultadoEm={d.impacto.dataUpdatedAt}
                fontes={d.fontes}
              />
            </>
          }
        >
          {ranking.length === 0 ? (
            <Vazio>
              Nenhum bairro em Atenção ou mais agora
              {d.pendencias && d.pendencias.semDados > 0 ? `; ${d.pendencias.semDados} sem dados` : ""}.
            </Vazio>
          ) : (
            <table className={estilos.tabelaAgir}>
              <caption className="so-leitor">Bairros em Atenção ou mais, os mais graves primeiro</caption>
              <thead>
                <tr>
                  <th scope="col">Bairro</th>
                  <th scope="col">Moradores vulneráveis</th>
                  <th scope="col">Estágio</th>
                  <th scope="col">
                    <span className="so-leitor">Ver no Mapa</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {ranking.map((r) => (
                  <tr key={r.id}>
                    <th scope="row">
                      <Link to={`/app?territorio=${encodeURIComponent(r.id)}`}>{r.nome}</Link>
                      <small>
                        {r.distrito ? siglaDistrito(r.distrito.replace("ds-", "Distrito ")) : ""}
                        {r.pendente ? " · sem declaração" : ""}
                      </small>
                    </th>
                    <td>
                      <span className={estilos.barraPessoas}>
                        <span>
                          {r.pessoas !== null && (
                            <i style={{ width: `${(r.pessoas / maxPessoas) * 100}%` }} />
                          )}
                        </span>
                        <b>{r.pessoas === null ? "sem dado" : formatarNumero(r.pessoas)}</b>
                      </span>
                    </td>
                    <td>
                      <Pilula nivel={infoEstagio(r.estagio).nivel} pequena>
                        {infoEstagio(r.estagio).rotulo}
                      </Pilula>
                    </td>
                    <td className={estilos.acaoLinha}>
                      <Link
                        to={`/app?territorio=${encodeURIComponent(r.id)}`}
                        aria-label={`Ver ${r.nome} no Mapa`}
                      >
                        <ChevronRight aria-hidden="true" size={20} />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CartaoPainel>

        <CartaoPainel
          id="db-saude"
          titulo="Dengue nas últimas semanas"
          resposta={respostaSaude}
          esmaecido={esmaecer.has("saude")}
          carga={d.saude}
          oQue="os agravos de saúde"
          insuficiente={agravos.length ? null : "situação semanal de dengue e chikungunya (InfoDengue)"}
          tabela={grafDengue?.tabela}
          alturaMin={220}
          rodape={
            <>
              {ultimaSemana ? `Último dado ${ultimaSemana} · ` : ""}
              <RodapeFonte
                ids={[...new Set(agravos.map((a) => a.fonte_id))]}
                padrao="InfoDengue"
                consultadoEm={d.saude.dataUpdatedAt}
                fontes={fontesSaude}
              />
            </>
          }
        >
          <div className={estilos.saudeCorpo}>
            <div className={estilos.saudeGrafico}>
              {grafDengue ? (
                <GraficoPainel
                  opcao={grafDengue.opcao}
                  rotulo="Casos de dengue por semana"
                  resumo={grafDengue.resumo}
                />
              ) : (
                <Vazio>Sem série semanal para o gráfico. Dados insuficientes.</Vazio>
              )}
            </div>
            <ul className={estilos.saudeChips}>
              {tendencia && (
                <li>
                  {tendencia === "sobe" ? (
                    <TrendingUp aria-hidden="true" size={16} />
                  ) : tendencia === "cai" ? (
                    <TrendingDown aria-hidden="true" size={16} />
                  ) : (
                    <Minus aria-hidden="true" size={16} />
                  )}
                  Dengue: {tendencia === "sobe" ? "sobe" : tendencia === "cai" ? "cai" : "estável"}
                </li>
              )}
              {outros.map((o) => {
                const n = o.nivel ? NIVEL_ALERTA[o.nivel] : null;
                return (
                  <li key={o.agravo}>
                    {o.nome}: {n ? n.rotulo : "dados insuficientes"}
                  </li>
                );
              })}
              <li>
                Leptospirose: {lepto ? `janela dia ${lepto.dia} de ${lepto.total}` : "sem janela aberta"}
              </li>
            </ul>
          </div>
        </CartaoPainel>
      </div>

      <Dialogo aberto={detalhes} aoMudar={setDetalhes} titulo="Detalhes do painel">
        <div className={estilos.detalhe}>
          <section>
            <h3>O que chama atenção</h3>
            {insights.length === 0 ? (
              <EstadoDados tipo="insuficiente">
                Falta: estágios, chuva ou previsão para gerar as frases.
              </EstadoDados>
            ) : (
              <ul>
                {insights.map((i) => (
                  <li key={i.id}>
                    {i.texto} {i.experimental && <SeloExp />}
                    <br />
                    <small>
                      Fonte: {i.fonte} · consultado às {formatarHoraMinuto(d.momento || Date.now())}
                    </small>
                  </li>
                ))}
              </ul>
            )}
          </section>
          <section>
            <h3>{unidade === "bairros" ? "Bairros por estágio" : "Distritos por estágio"}</h3>
            {donut.total === 0 ? (
              <EstadoDados tipo="insuficiente">Falta: estágios por bairro e distrito.</EstadoDados>
            ) : (
              <>
                <div className={estilos.graficoDetalhe}>
                  <GraficoPainel opcao={donut.opcao} rotulo="Estágios" resumo={donut.resumo} />
                </div>
                <ul className={estilos.legendaDetalhe}>
                  {contagem.map((c) => (
                    <li key={c.estagio}>
                      <i
                        className={c.estagio === "sem_dados" ? estilos.semDadoCor : undefined}
                        style={
                          c.estagio === "sem_dados"
                            ? undefined
                            : { background: token(COR_ESTAGIO[c.estagio]) }
                        }
                        aria-hidden="true"
                      />
                      {ESTAGIOS[c.estagio].rotulo} <b>{c.declarados + c.sugeridos}</b>
                    </li>
                  ))}
                </ul>
                <small>
                  {declarados} declarados pela equipe · {donut.total - declarados} sugeridos pelo sistema
                  (Experimental)
                </small>
              </>
            )}
          </section>
          <section>
            <h3>Quem está exposto?</h3>
            {exposicao.length === 0 ? (
              <EstadoDados tipo="insuficiente">Falta: previsão de chuva e maré (Open-Meteo).</EstadoDados>
            ) : grafPessoas.vazio ? (
              <p>Nenhum bairro em Atenção ou mais: ninguém para listar agora.</p>
            ) : (
              <>
                <div className={estilos.graficoDetalhe}>
                  <GraficoPainel
                    opcao={grafPessoas.opcao}
                    rotulo="Quem está exposto"
                    resumo={grafPessoas.resumo}
                  />
                </div>
                <small>
                  Moradores (Censo 2022) em bairros com estágio sugerido Atenção ou mais. Experimental.
                </small>
              </>
            )}
          </section>
          <section>
            <h3>Maré perto do pico da chuva</h3>
            {grafMare ? (
              <>
                <p>
                  {mare
                    ? `Maré prevista de ${formatarNumero(mare.mareM, 1)} m perto do pico de chuva. `
                    : "Sem a maré no pico da chuva. "}
                  É contexto: de 2022 a 06/2024, depois de descontar a chuva, a maré não mostrou efeito nos
                  alagamentos. <SeloExp />
                </p>
                <div className={estilos.graficoDetalhe}>
                  <GraficoPainel
                    opcao={grafMare.opcao}
                    rotulo="Maré e chuva previstas"
                    resumo={grafMare.resumo}
                  />
                </div>
                <small>
                  Fonte:{" "}
                  <RodapeFonte
                    ids={["open-meteo-previsao", "open-meteo-mare"]}
                    padrao="Open-Meteo"
                    consultadoEm={d.situacao.dataUpdatedAt}
                    fontes={d.fontes}
                  />
                </small>
              </>
            ) : (
              <EstadoDados tipo="insuficiente">Falta: previsão de chuva e maré (Open-Meteo).</EstadoDados>
            )}
          </section>
          <section>
            <h3>Alertas oficiais vigentes</h3>
            {alertas.length === 0 ? (
              <p>
                Nenhum alerta oficial vigente às {formatarHoraMinuto(d.distritos.dataUpdatedAt || Date.now())}{" "}
                (APAC, INMET, Cemaden, IDAP). Não quer dizer sem risco: confira nas fontes.
              </p>
            ) : (
              <ul>
                {alertas.map((a) => (
                  <li key={`${a.origem}${a.emitidoEm}${a.nivel}`}>
                    {a.origem}: {a.evento ?? `alerta ${a.nivel}`}, nível {a.nivel}, emitido{" "}
                    {quando(a.emitidoEm)}
                    {a.expiraEm ? `, vale até ${quando(a.expiraEm)}` : ""}
                  </li>
                ))}
              </ul>
            )}
          </section>
          <section>
            <h3>Rios e reservatórios</h3>
            <EstadoDados tipo="insuficiente" titulo="Ainda não disponível">
              O servidor ainda não oferece o nível do Capibaribe e dos reservatórios (RF-35). Nada é estimado
              aqui.
            </EstadoDados>
          </section>
          <section>
            <h3>Ações por distrito</h3>
            {acoes.length === 0 ? (
              <EstadoDados tipo="insuficiente">Falta: as ações registradas pela equipe.</EstadoDados>
            ) : (
              <Tabela
                legenda="Ações por distrito"
                legendaVisivel={false}
                densidade="compacta"
                colunas={[
                  { chave: "d", titulo: "Distrito", celula: (l) => l.nome },
                  { chave: "e", titulo: "Estágio", celula: (l) => ESTAGIOS[l.estagio].rotulo },
                  { chave: "a", titulo: "Em andamento", numerica: true, celula: (l) => l.emAndamento },
                  {
                    chave: "s",
                    titulo: "Atenção",
                    celula: (l) => (l.semAcao ? <b>Sem ação em andamento</b> : "—"),
                  },
                ]}
                linhas={acoes}
                chaveLinha={(l) => l.id}
              />
            )}
          </section>
          <section>
            <h3>Contexto do histórico ({CONTEXTO_HISTORICO.periodo})</h3>
            <p>{CONTEXTO_HISTORICO.definicao}</p>
            <ul>
              {CONTEXTO_HISTORICO.frases.map((f) => (
                <li key={f}>{f}</li>
              ))}
            </ul>
            <p>
              Fonte: {CONTEXTO_HISTORICO.fonte}, {CONTEXTO_HISTORICO.periodo}. É retrato do passado, não
              previsão. As ocorrências da Defesa Civil vão só até jun/2024.
            </p>
          </section>
          <section>
            <h3>Dá para confiar nos números de agora?</h3>
            {confianca.fontes.length === 0 ? (
              <EstadoDados tipo="insuficiente">Falta: a hora de atualização das fontes.</EstadoDados>
            ) : (
              <ul className={estilos.fontes}>
                {[...confianca.fontes, ...fontesSaude].map((f) => (
                  <li key={f.id}>
                    {f.nome}
                    {f.atualizado_em ? ` · ${haQuanto(f.atualizado_em)}` : " · sem hora"}
                  </li>
                ))}
              </ul>
            )}
            {(confianca.distritosSemMedicao.length > 0 || (confianca.estacoesSemLeitura ?? 0) > 0) && (
              <p>
                {confianca.estacoesSemLeitura
                  ? `${confianca.estacoesSemLeitura} estações de chuva sem leitura. `
                  : ""}
                {confianca.distritosSemMedicao.length > 0 &&
                  `Sem medição de chuva: ${confianca.distritosSemMedicao.join(", ")}.`}
              </p>
            )}
            {d.gatilhos?.itens[0] && (
              <p>
                Limiar mais próximo: {d.gatilhos.itens[0].nome}, {ROTULO_INSUMO[d.gatilhos.itens[0].insumo]},{" "}
                {mm(d.gatilhos.itens[0].atual)} de {mm(d.gatilhos.itens[0].limiar)} mm.
              </p>
            )}
          </section>
        </div>
      </Dialogo>
    </div>
  );
}
