/**
 * Indicadores de decisão (docs/propostas/dashboards-indicadores.md, I-01 a I-12). Funções puras: recebem as respostas
 * da API já lidas e devolvem o que a tela mostra. Sem dado, devolvem `null` ou lista vazia, nunca zero (RN-01, RN-02).
 * Risco só como classe (RN-06). Reaproveitadas no Dashboards e no topo do Mapa.
 */
import { infoEstagio } from "@/features/evento/estagios";
import { desembrulhar, type Estagio, type ItemEstagio } from "@/features/evento/tipos";
import type { ResumoAgravo, JanelaLeptospirose } from "@/features/saude/tipos";
import { nomeDistrito } from "@/lib/distritos";
import { diaNoRecife, formatarNumero, nomeMes } from "@/lib/formatos";
import type { FonteMeta } from "@/lib/frescor";
import { emVigor, ordenarPorGravidade } from "@/features/mapa/tipos";

export type Janela = 24 | 72;
export const JANELAS: Janela[] = [24, 72];

const num = (v: unknown): number | null => (typeof v === "number" && Number.isFinite(v) ? v : null);
const SEQUENCIA = ["observacao", "atencao", "alerta", "critico"] as const;
const nomeCurto = (n: string) => nomeDistrito(n);
const rotuloEstagio = (e: string) => infoEstagio(e).rotulo;
const ORDEM = (e: string) => infoEstagio(e).ordem;

/* ---------- formas das respostas que as funções leem (campo ausente = sem dado) ---------- */

export interface ChuvaDistritoApi {
  territorio_id: string;
  territorio_nome: string;
  chuva_24h_mm: number | null;
  chuva_72h_mm: number | null;
  estacoes_total?: number | null;
  estacoes_com_leitura?: number | null;
  medicao_propria?: boolean;
  motivo?: string | null;
}
export interface SituacaoChuvaApi {
  distritos: ChuvaDistritoApi[];
  maior_24h: { territorio_id: string; territorio_nome: string; mm: number } | null;
  maior_72h: { territorio_id: string; territorio_nome: string; mm: number } | null;
  estacoes: { total: number | null; com_leitura: number | null; sem_leitura: number | null };
  /** Série medida hora a hora (últimas 72 h). Hora sem leitura simplesmente não aparece (lacuna, não zero). */
  observada?: {
    serie: { t: string; municipio_mm: number; distritos?: Record<string, number> }[];
  };
  previsao: {
    previsao_emitida_em: string | null;
    mare_emitida_em: string | null;
    chuva: { t: string; valor: number | null; min: number | null; max: number | null }[];
    mare: { t: string; valor: number | null }[];
  };
}
export interface ItemImpacto {
  territorio_id: string;
  nome: string;
  nivel: "bairro" | "distrito";
  distrito_id: string;
  estagio_sugerido: Estagio;
  /** Classe prevista por perigo (Experimental, RN-11): classe, nunca percentual (RN-06). */
  classe_alagamento?: Estagio;
  classe_deslizamento?: Estagio;
  impacto_pessoas: {
    idosos_60_mais: number | null;
    criancas_0_14: number | null;
    equipamentos_saude: number | null;
  } | null;
}
export interface ImpactoApi {
  itens: ItemImpacto[];
  resumo?: {
    pessoas_vulneraveis_em_alerta?: {
      bairros_em_alerta: number;
      idosos_60_mais: number | null;
      criancas_0_14: number | null;
      parcial: boolean;
    } | null;
  };
}
export interface AcoesApi {
  por_distrito: { distrito_id: string; distrito_nome: string; contagens: Record<string, number> }[];
}
export interface ReferenciaApi {
  meses: { mes: number; media_mm: number | null }[];
}

/* ---------- I-01 decisões pendentes ---------- */

export interface Pendencia {
  id: string;
  nome: string;
  nivel: "bairro" | "distrito";
  distritoId: string | null;
  sugerido: Estagio;
  declarado: Estagio | null;
  posicao: number | null;
}
export interface ResumoPendencias {
  itens: Pendencia[];
  total: number;
  distritos: number;
  /** Territórios sem sugestão e sem declaração: contados à parte, nunca somados a "observação" (RN-01). */
  semDados: number;
  avaliados: number;
}

/**
 * Pendente = o sistema sugere atenção, alerta ou crítico e a equipe não declarou, ou declarou abaixo do sugerido.
 * Mais vulnerável primeiro (RF-22): estágio sugerido e, no empate, posição na prioridade. O sistema só sugere (RN-05).
 */
export function decisoesPendentes(itens: ItemEstagio[], posicao: Map<string, number>): ResumoPendencias {
  const pendentes: Pendencia[] = [];
  let semDados = 0;
  for (const i of itens) {
    const sug = infoEstagio(i.sugerido?.estagio);
    const dec = i.declarado ? infoEstagio(i.declarado.estagio) : null;
    const temDeclarado = !!dec && dec.ordem >= 0;
    if (sug.ordem < 0 && !temDeclarado) semDados++;
    if (sug.ordem >= 1 && (!temDeclarado || dec!.ordem < sug.ordem))
      pendentes.push({
        id: i.territorio_id,
        nome: nomeCurto(i.territorio_nome),
        nivel: i.nivel,
        distritoId: i.distrito_id,
        sugerido: i.sugerido.estagio,
        declarado: temDeclarado ? i.declarado!.estagio : null,
        posicao: posicao.get(i.territorio_id) ?? null,
      });
  }
  pendentes.sort(
    (a, b) =>
      ORDEM(b.sugerido) - ORDEM(a.sugerido) ||
      (a.posicao ?? 9999) - (b.posicao ?? 9999) ||
      a.nome.localeCompare(b.nome, "pt-BR"),
  );
  return {
    itens: pendentes,
    total: pendentes.length,
    distritos: new Set(pendentes.map((p) => p.distritoId ?? p.id)).size,
    semDados,
    avaliados: itens.length,
  };
}

/* ---------- I-02 falta para o próximo estágio ---------- */

export type InsumoGatilho = "chuva_24h_mm" | "chuva_prev_24h_mm" | "chuva_prev_72h_mm";
const PREFIXO: Record<InsumoGatilho, string> = {
  chuva_24h_mm: "chuva_24h",
  chuva_prev_24h_mm: "chuva_prev_24h",
  chuva_prev_72h_mm: "chuva_prev_72h",
};
export const ROTULO_INSUMO: Record<InsumoGatilho, string> = {
  chuva_24h_mm: "chuva medida em 24 h",
  chuva_prev_24h_mm: "chuva prevista em 24 h",
  chuva_prev_72h_mm: "chuva prevista em 72 h",
};

export interface Gatilho {
  id: string;
  nome: string;
  insumo: InsumoGatilho;
  atual: number;
  limiar: number;
  falta: number;
  proximo: Estagio;
}
export interface ResumoGatilhos {
  /** Um por distrito: o insumo mais perto do limiar do próximo estágio. Mais perto primeiro. */
  itens: Gatilho[];
  semDados: number;
  noTopo: number;
}

/** Quanto falta de chuva para o distrito subir ao próximo estágio sugerido, pelos limiares de `/estagios/parametros`. */
export function gatilhos(
  distritos: ItemEstagio[],
  limiares: Record<string, number>,
  janela?: Janela,
): ResumoGatilhos {
  // 72 h: o acumulado previsto de 72 h é a referência; 24 h: a medida e a prevista de 24 h. Sem janela, todos.
  const insumos = (Object.keys(PREFIXO) as InsumoGatilho[]).filter(
    (i) => !janela || (janela === 72 ? i === "chuva_prev_72h_mm" : i !== "chuva_prev_72h_mm"),
  );
  const itens: Gatilho[] = [];
  let semDados = 0;
  let noTopo = 0;
  for (const d of distritos) {
    const ordem = ORDEM(d.sugerido?.estagio);
    if (ordem < 0) {
      semDados++;
      continue;
    }
    if (ordem >= 3) {
      noTopo++;
      continue;
    }
    const proximo = SEQUENCIA[ordem + 1];
    let melhor: Gatilho | null = null;
    for (const insumo of insumos) {
      const atual = num(d.sugerido?.insumos?.[insumo]);
      const limiar = num(limiares[`${PREFIXO[insumo]}_${proximo}_mm`]);
      if (atual === null || limiar === null) continue;
      const falta = Math.max(limiar - atual, 0);
      if (!melhor || falta < melhor.falta)
        melhor = {
          id: d.territorio_id,
          nome: nomeCurto(d.territorio_nome),
          insumo,
          atual,
          limiar,
          falta,
          proximo,
        };
    }
    if (melhor) itens.push(melhor);
    else semDados++;
  }
  itens.sort((a, b) => a.falta - b.falta || a.nome.localeCompare(b.nome, "pt-BR", { numeric: true }));
  return { itens, semDados, noTopo };
}

/* ---------- I-03 chuva medida ---------- */

export interface LinhaChuva {
  id: string;
  nome: string;
  mm: number | null;
  /** "3 de 3 estações" quando a API conta as estações. */
  estacoes: string | null;
  motivo: string | null;
}

/** Chuva medida por distrito na janela; sem leitura fica `null` e vai ao fim (zero medido continua zero, RN-02). */
export function chuvaMedida(s: SituacaoChuvaApi | undefined, janela: Janela): LinhaChuva[] {
  return (s?.distritos ?? [])
    .map((d) => ({
      id: d.territorio_id,
      nome: nomeCurto(d.territorio_nome),
      mm: num(janela === 24 ? d.chuva_24h_mm : d.chuva_72h_mm),
      estacoes:
        d.estacoes_total != null && d.estacoes_com_leitura != null
          ? `${d.estacoes_com_leitura} de ${d.estacoes_total} estações`
          : null,
      motivo: d.motivo ?? null,
    }))
    .sort((a, b) => (b.mm ?? -1) - (a.mm ?? -1) || a.nome.localeCompare(b.nome, "pt-BR", { numeric: true }));
}

export interface MaiorChuva {
  id: string;
  nome: string;
  mm: number;
  estacoes: string | null;
}

export function maiorChuva(s: SituacaoChuvaApi | undefined, janela: Janela): MaiorChuva | null {
  const m = janela === 24 ? s?.maior_24h : s?.maior_72h;
  if (!m || num(m.mm) === null) return null;
  const e = s?.estacoes;
  return {
    id: m.territorio_id,
    nome: nomeCurto(m.territorio_nome),
    mm: m.mm,
    estacoes:
      e && e.total != null && e.com_leitura != null ? `${e.com_leitura} de ${e.total} estações` : null,
  };
}

/* ---------- I-04 prevista x média do mês ---------- */

export interface LinhaPrevista {
  id: string;
  nome: string;
  prevMm: number | null;
  /** Média do período (janela) para o mês, a partir da média mensal da reanálise ERA5. */
  mediaMm: number | null;
  razao: number | null;
}

export function mediaDoMes(ref: unknown, mes: number): number | null {
  const r = desembrulhar<ReferenciaApi>(ref);
  return num(r?.meses?.find((m) => m.mes === mes)?.media_mm);
}

/** Mês e ano de hoje no Recife. */
export function mesEAno(agora: Date): { mes: number; ano: number } {
  const [ano, mes] = diaNoRecife(agora).split("-").map(Number);
  return { mes, ano };
}

export function previstaVsMedia(
  distritos: ItemEstagio[],
  mediaMensal: Map<string, number | null>,
  agora: Date,
  janela: Janela,
): LinhaPrevista[] {
  const { mes, ano } = mesEAno(agora);
  const dias = new Date(ano, mes, 0).getDate();
  return distritos.map((d) => {
    const prev = num(d.sugerido?.insumos?.[janela === 24 ? "chuva_prev_24h_mm" : "chuva_prev_72h_mm"]);
    const mensal = mediaMensal.get(d.territorio_id) ?? null;
    const media = mensal === null ? null : (mensal / dias) * (janela / 24);
    return {
      id: d.territorio_id,
      nome: nomeCurto(d.territorio_nome),
      prevMm: prev,
      mediaMm: media,
      razao: prev !== null && media !== null && media > 0 ? prev / media : null,
    };
  });
}

/* ---------- I-05 maré no pico da chuva ---------- */

export interface MareNoPico {
  id: string;
  nome: string;
  mareM: number;
  picoChuvaEm: string | null;
  /** Maré a partir do limiar `mare_alta_m` junto ao pico: o estágio sugerido sobe um nível. */
  alta: boolean;
}

export function mareNoPico(distritos: ItemEstagio[], limiares: Record<string, number>): MareNoPico | null {
  let m: MareNoPico | null = null;
  for (const d of distritos) {
    const v = num(d.sugerido?.insumos?.mare_no_pico_m);
    if (v === null || (m && v <= m.mareM)) continue;
    const pico = d.sugerido.insumos.pico_chuva_em;
    m = {
      id: d.territorio_id,
      nome: nomeCurto(d.territorio_nome),
      mareM: v,
      picoChuvaEm: typeof pico === "string" ? pico : null,
      alta: limiares.mare_alta_m !== undefined && v >= limiares.mare_alta_m,
    };
  }
  return m;
}

/* ---------- I-06 e I-07 quem está exposto ---------- */

export interface PessoasAlerta {
  bairros: number;
  idosos: number | null;
  criancas: number | null;
  parcial: boolean;
}

/** `false` quando nenhum item tem estágio sugerido: a previsão falta e "nenhum bairro em alerta" seria falso (RN-01). */
export function previsaoDisponivel(i: ImpactoApi | undefined): boolean {
  return !!i && Array.isArray(i.itens) && i.itens.some((x) => x.estagio_sugerido !== "sem_dados");
}

/**
 * Residentes (Censo 2022) em bairros com estágio sugerido alerta ou crítico. Contagem de moradores, não de atingidos.
 * Com `distritoId`, só os bairros do distrito. `null` = Dados insuficientes.
 */
export function pessoasEmAlerta(i: ImpactoApi | undefined, distritoId?: string | null): PessoasAlerta | null {
  if (!previsaoDisponivel(i)) return null;
  const r = i?.resumo?.pessoas_vulneraveis_em_alerta;
  if (!distritoId && r)
    return {
      bairros: r.bairros_em_alerta,
      idosos: r.idosos_60_mais,
      criancas: r.criancas_0_14,
      parcial: r.parcial,
    };
  const bairros = i!.itens.filter(
    (x) =>
      x.nivel === "bairro" && ORDEM(x.estagio_sugerido) >= 2 && (!distritoId || x.distrito_id === distritoId),
  );
  const soma = (campo: "idosos_60_mais" | "criancas_0_14") => {
    const v = bairros.map((b) => num(b.impacto_pessoas?.[campo]));
    if (bairros.length === 0) return 0;
    return v.some((x) => x === null) ? null : v.reduce<number>((s, x) => s + (x ?? 0), 0);
  };
  return {
    bairros: bairros.length,
    idosos: soma("idosos_60_mais"),
    criancas: soma("criancas_0_14"),
    parcial: bairros.some(
      (b) =>
        num(b.impacto_pessoas?.idosos_60_mais) === null || num(b.impacto_pessoas?.criancas_0_14) === null,
    ),
  };
}

export interface ExposicaoDistrito {
  id: string;
  nome: string;
  bairrosAlerta: number;
  idosos: number;
  criancas: number;
  /** Alguma contagem do distrito veio suprimida ou sem dado: o total é um mínimo. */
  parcial: boolean;
  unidadesAtencao: number;
  /** Moradores em bairros com estágio sugerido atenção ou mais (inclui os em alerta). */
  bairrosAtencao: number;
  idososAtencao: number;
  criancasAtencao: number;
}

/** Por distrito: idosos e crianças nos bairros em alerta ou mais; unidades de saúde nos bairros em atenção ou mais. */
export function exposicaoPorDistrito(i: ImpactoApi | undefined): ExposicaoDistrito[] {
  if (!previsaoDisponivel(i)) return [];
  const nomes = new Map(i!.itens.filter((x) => x.nivel === "distrito").map((x) => [x.territorio_id, x.nome]));
  const porId = new Map<string, ExposicaoDistrito>();
  for (const [id, nome] of nomes)
    porId.set(id, {
      id,
      nome: nomeCurto(nome),
      bairrosAlerta: 0,
      idosos: 0,
      criancas: 0,
      parcial: false,
      unidadesAtencao: 0,
      bairrosAtencao: 0,
      idososAtencao: 0,
      criancasAtencao: 0,
    });
  for (const b of i!.itens.filter((x) => x.nivel === "bairro")) {
    const d = porId.get(b.distrito_id);
    if (!d) continue;
    const o = ORDEM(b.estagio_sugerido);
    const p = b.impacto_pessoas;
    if (o >= 1) {
      const u = num(p?.equipamentos_saude);
      if (u === null) d.parcial = true;
      else d.unidadesAtencao += u;
      d.bairrosAtencao++;
      const idosos = num(p?.idosos_60_mais);
      const criancas = num(p?.criancas_0_14);
      if (idosos === null || criancas === null) d.parcial = true;
      d.idososAtencao += idosos ?? 0;
      d.criancasAtencao += criancas ?? 0;
    }
    if (o >= 2) {
      d.bairrosAlerta++;
      const idosos = num(p?.idosos_60_mais);
      const criancas = num(p?.criancas_0_14);
      if (idosos === null || criancas === null) d.parcial = true;
      d.idosos += idosos ?? 0;
      d.criancas += criancas ?? 0;
    }
  }
  return [...porId.values()].sort((a, b) => a.nome.localeCompare(b.nome, "pt-BR", { numeric: true }));
}

/* ---------- I-08 alertas oficiais vigentes ---------- */

export interface AlertaVigente {
  origem: string;
  nivel: string;
  evento: string | null;
  emitidoEm: string;
  expiraEm: string | null;
  url: string | null;
  area: string | null;
}

/** Alertas únicos (origem, emissão, nível) ainda dentro da validade. O mesmo alerta vem repetido em cada território. */
export function alertasVigentes(itens: ItemEstagio[], agora: Date): AlertaVigente[] {
  const vistos = new Map<string, AlertaVigente>();
  for (const i of itens)
    for (const a of i.alertas_oficiais ?? []) {
      if (a.expira_em && new Date(a.expira_em).getTime() < agora.getTime()) continue;
      const chave = `${a.origem}|${a.emitido_em}|${a.nivel}|${a.evento ?? ""}`;
      if (!vistos.has(chave))
        vistos.set(chave, {
          origem: a.origem,
          nivel: a.nivel,
          evento: a.evento ?? null,
          emitidoEm: a.emitido_em,
          expiraEm: a.expira_em ?? null,
          url: a.url ?? null,
          area: a.area ?? null,
        });
    }
  return [...vistos.values()].sort(
    (a, b) => (a.expiraEm ?? "9999").localeCompare(b.expiraEm ?? "9999") || a.origem.localeCompare(b.origem),
  );
}

/* ---------- I-10 saúde ---------- */

/** Abaixo disso a variação de 4 semanas conta como estável. Valor de leitura da tela, não da API. */
export const LIMIAR_TENDENCIA_PCT = 10;
export type Tendencia = "sobe" | "estavel" | "cai";

export interface LeituraAgravo {
  agravo: string;
  nome: string;
  nivel: number | null;
  tendencia: Tendencia | null;
  semTendencia: string | null;
}

/** Seta de tendência só com base suficiente: semana incompleta ou sem variação não vira queda (RF-39, RN-01). */
export function leituraAgravo(a: ResumoAgravo): LeituraAgravo {
  let tendencia: Tendencia | null = null;
  let semTendencia: string | null = null;
  if (a.incompleta) semTendencia = "semana ainda incompleta";
  else if (a.variacao_4s_pct === null || a.variacao_4s_pct === undefined)
    semTendencia = "sem base para comparar";
  else
    tendencia =
      a.variacao_4s_pct > LIMIAR_TENDENCIA_PCT
        ? "sobe"
        : a.variacao_4s_pct < -LIMIAR_TENDENCIA_PCT
          ? "cai"
          : "estavel";
  return { agravo: a.agravo, nome: a.nome, nivel: a.nivel_alerta ?? null, tendencia, semTendencia };
}

const diasEntre = (de: string, ate: string) =>
  Math.round(
    (Date.parse(`${ate.slice(0, 10)}T00:00:00Z`) - Date.parse(`${de.slice(0, 10)}T00:00:00Z`)) / 86_400_000,
  );

/** "Dia 9 de 30" da janela de vigilância de leptospirose; `null` sem janela ativa. */
export function janelaLeptospirose(
  j: JanelaLeptospirose | null | undefined,
  agora: Date,
): { dia: number; total: number } | null {
  if (!j || !j.ativa || !j.inicio || !j.fim) return null;
  const total = diasEntre(j.inicio, j.fim) + 1;
  const dia = diasEntre(j.inicio, diaNoRecife(agora)) + 1;
  return dia >= 1 && dia <= total ? { dia, total } : null;
}

/* ---------- I-11 ações nos territórios em alerta ---------- */

export interface LinhaAcoes {
  id: string;
  nome: string;
  estagio: Estagio;
  emAndamento: number;
  planejadas: number;
  /** Estágio em atenção ou mais e nenhuma ação em andamento. */
  semAcao: boolean;
}

export function acoesPorDistrito(distritos: ItemEstagio[], acoes: AcoesApi | undefined): LinhaAcoes[] {
  if (!acoes) return [];
  const linhas = distritos.map((d) => {
    const c = acoes.por_distrito.find((x) => x.distrito_id === d.territorio_id)?.contagens ?? {};
    const v = emVigor(d);
    return {
      id: d.territorio_id,
      nome: nomeCurto(d.territorio_nome),
      estagio: v.estagio,
      emAndamento: c.em_andamento ?? 0,
      planejadas: c.planejada ?? 0,
      semAcao: (v.ordem ?? -1) >= 1 && (c.em_andamento ?? 0) === 0,
    };
  });
  return linhas.sort(
    (a, b) =>
      Number(b.semAcao) - Number(a.semAcao) ||
      ORDEM(b.estagio) - ORDEM(a.estagio) ||
      a.nome.localeCompare(b.nome, "pt-BR", { numeric: true }),
  );
}

/* ---------- I-12 confiança dos dados ---------- */

export interface ConfiancaDados {
  fontes: FonteMeta[];
  vencidas: FonteMeta[];
  distritosSemMedicao: string[];
  estacoesSemLeitura: number | null;
}

export function confiancaDados(fontes: FonteMeta[], s: SituacaoChuvaApi | undefined): ConfiancaDados {
  return {
    fontes,
    vencidas: fontes.filter((f) => f.desatualizado === true),
    distritosSemMedicao: (s?.distritos ?? [])
      .filter((d) => d.chuva_24h_mm === null)
      .map((d) => nomeCurto(d.territorio_nome)),
    estacoesSemLeitura: s?.estacoes?.sem_leitura ?? null,
  };
}

/* ---------- insights em frase ---------- */

export interface Insight {
  id: string;
  gravidade: number;
  /** Frase completa (diálogo de detalhes). */
  texto: string;
  /** Versão de uma linha, para o chip no topo do painel. */
  curto: string;
  /** Usa previsão ou estágio sugerido: leva o selo Experimental (RN-11). */
  experimental?: boolean;
  fonte: string;
}

export interface EntradaInsights {
  pendencias: ResumoPendencias | null;
  gatilhos: ResumoGatilhos | null;
  razoes: LinhaPrevista[];
  acoes: LinhaAcoes[];
  alertas: AlertaVigente[];
  pessoas: PessoasAlerta | null;
  leptospirose: { dia: number; total: number } | null;
  chuva: SituacaoChuvaApi | undefined;
  fontes: FonteMeta[];
  janela: Janela;
  agora: Date;
  /** Formata uma data ISO como "hoje às 14h" (injetado para manter a função pura e testável). */
  quando: (iso: string) => string;
}

export const LIMITE_RAZAO = 1.5;
export const LIMITE_FALTA_MM = 10;

/** Nome de fonte para chip de uma linha: as conhecidas viram sigla; as outras, o começo do nome. */
function nomeCurtoFonte(f: FonteMeta): string {
  const conhecidas: Record<string, string> = {
    "apac-chuva": "APAC",
    "open-meteo-previsao": "previsão de chuva",
    "open-meteo-mare": "previsão de maré",
  };
  if (conhecidas[f.id]) return conhecidas[f.id];
  return f.nome.length > 32 ? `${f.nome.slice(0, 30).trimEnd()}…` : f.nome;
}

function lista(nomes: string[], max = 3): string {
  const m = nomes.slice(0, max);
  const resto = nomes.length - m.length;
  const base = m.length <= 1 ? (m[0] ?? "") : `${m.slice(0, -1).join(", ")} e ${m[m.length - 1]}`;
  return resto > 0 ? `${base} e mais ${resto}` : base;
}

/** Até 3 frases, a mais grave primeiro, geradas por regras fixas (sem modelo de linguagem). */
export function gerarInsights(e: EntradaInsights): Insight[] {
  const r: Insight[] = [];
  const add = (i: Insight) => r.push(i);
  const p = e.pendencias;
  const mm = (v: number) => formatarNumero(v, v < 10 ? 1 : 0);
  if (p && p.total > 0) {
    const n = p.total;
    const nome =
      p.itens[0].nivel === "bairro" ? (n === 1 ? "bairro" : "bairros") : n === 1 ? "distrito" : "distritos";
    add({
      id: "pendentes",
      gravidade: 90,
      texto: `${n} ${nome} com sugestão de estágio acima do declarado: ${lista(p.itens.map((x) => x.nome))}.`,
      curto: `${n} ${nome} com sugestão acima do declarado`,
      experimental: true,
      fonte: "Estágios sugeridos e declarados (ClimaSense)",
    });
  }
  const vencida = e.fontes.find((f) => f.desatualizado === true);
  if (vencida)
    add({
      id: "fonte-vencida",
      gravidade: 78,
      texto: `${vencida.nome} está desatualizada${vencida.atualizado_em ? ` (última atualização ${e.quando(vencida.atualizado_em)})` : ""}: confira antes de decidir.`,
      curto: `Fonte desatualizada: ${nomeCurtoFonte(vencida)}`,
      fonte: vencida.nome,
    });
  const a = e.alertas[0];
  if (a)
    add({
      id: "alerta-oficial",
      gravidade: 85,
      texto: `${a.origem}: ${a.evento ?? `alerta ${a.nivel}`}${a.expiraEm ? ` até ${e.quando(a.expiraEm)}` : ""}. Confira na fonte oficial.`,
      curto: `${a.origem}: ${a.evento ?? `alerta ${a.nivel}`}`,
      fonte: a.origem,
    });
  const semAcao = e.acoes.find((x) => x.semAcao && ORDEM(x.estagio) >= 2);
  if (semAcao)
    add({
      id: "sem-acao",
      gravidade: 80,
      texto: `${semAcao.nome} em ${rotuloEstagio(semAcao.estagio)} e nenhuma ação em andamento.`,
      curto: `${semAcao.nome} em ${rotuloEstagio(semAcao.estagio)}, sem ação em andamento`,
      fonte: "Ações da equipe",
    });
  const semMedicao = e.chuva?.distritos.filter((d) => d.chuva_24h_mm === null) ?? [];
  if (semMedicao.length > 0 && semMedicao.length < (e.chuva?.distritos.length ?? 0)) {
    const nomes = lista(semMedicao.map((d) => nomeCurto(d.territorio_nome)));
    add({
      id: "sem-medicao",
      gravidade: 75,
      texto: `Sem medição de chuva em ${nomes}: é falta de dado, não chuva zero.`,
      curto: `Sem medição de chuva: ${nomes}`,
      fonte: "Pluviômetros (APAC)",
    });
  }
  const alta = e.razoes
    .filter((x) => x.razao !== null && x.razao >= LIMITE_RAZAO)
    .sort((x, y) => (y.razao ?? 0) - (x.razao ?? 0))[0];
  if (alta)
    add({
      id: "prevista-acima-da-media",
      gravidade: 70,
      texto: `Chuva prevista para ${e.janela} h no ${alta.nome} (${mm(alta.prevMm!)} mm) é ${formatarNumero(alta.razao, 1)} vezes a média de ${nomeMes(mesEAno(e.agora).mes)} (reanálise ERA5, desde 2021).`,
      curto: `${alta.nome}: previsão ${formatarNumero(alta.razao, 1)} vezes a média de ${nomeMes(mesEAno(e.agora).mes)}`,
      experimental: true,
      fonte: "Open-Meteo e ERA5",
    });
  const perto = e.gatilhos?.itens[0];
  if (perto && perto.falta <= LIMITE_FALTA_MM)
    add({
      id: "perto-do-gatilho",
      gravidade: 65,
      texto: `${perto.nome} está a ${mm(perto.falta)} mm de ${ROTULO_INSUMO[perto.insumo]} do estágio ${rotuloEstagio(perto.proximo)}.`,
      curto: `${perto.nome} a ${mm(perto.falta)} mm do estágio ${rotuloEstagio(perto.proximo)}`,
      experimental: true,
      fonte: "Limiares dos estágios",
    });
  if (e.pessoas && e.pessoas.bairros > 0 && e.pessoas.idosos !== null && e.pessoas.criancas !== null)
    add({
      id: "pessoas",
      gravidade: 55,
      texto: `Bairros em alerta somam ${e.pessoas.parcial ? "pelo menos " : ""}${formatarNumero(e.pessoas.idosos)} idosos e ${formatarNumero(e.pessoas.criancas)} crianças que moram lá (Censo 2022).`,
      curto: `${formatarNumero(e.pessoas.idosos)} idosos e ${formatarNumero(e.pessoas.criancas)} crianças em bairros em alerta`,
      experimental: true,
      fonte: "IBGE, Censo 2022",
    });
  if (e.leptospirose)
    add({
      id: "leptospirose",
      gravidade: 50,
      texto: `Janela de leptospirose: dia ${e.leptospirose.dia} de ${e.leptospirose.total}, período de vigilância reforçada.`,
      curto: `Leptospirose: dia ${e.leptospirose.dia} de ${e.leptospirose.total} da janela`,
      fonte: "SINAN, nota técnica 138/2022",
    });
  if (p && p.total === 0 && e.gatilhos && e.gatilhos.itens.length > 0) {
    const g = e.gatilhos.itens[0];
    add({
      id: "nada",
      gravidade: 1,
      texto: `Nenhuma decisão pendente. O mais perto de mudar de estágio: ${g.nome}, a ${mm(g.falta)} mm de ${ROTULO_INSUMO[g.insumo]} para ${rotuloEstagio(g.proximo)}.`,
      curto: "Nenhuma decisão pendente",
      fonte: "Limiares dos estágios",
    });
  }
  return r.sort((x, y) => y.gravidade - x.gravidade).slice(0, 3);
}

/** Série medida hora a hora das últimas `horas` horas (maior pluviômetro). Hora sem leitura = `null`, nunca zero. */
export function serieHoraria(
  s: SituacaoChuvaApi | undefined,
  horas: number,
  agora: Date,
  distritoId?: string | null,
): { t: number; mm: number | null }[] | null {
  const serie = s?.observada?.serie;
  if (!serie || serie.length === 0) return null;
  const porHora = new Map(
    serie.map((h) => [Date.parse(h.t), distritoId ? num(h.distritos?.[distritoId]) : num(h.municipio_mm)]),
  );
  const fim = Math.floor(agora.getTime() / 3_600_000) * 3_600_000;
  const pontos = Array.from({ length: horas }, (_, i) => {
    const t = fim - (horas - 1 - i) * 3_600_000;
    return { t, mm: porHora.get(t) ?? null };
  });
  return pontos.filter((p) => p.mm !== null).length >= 2 ? pontos : null;
}

export interface LinhaRanking {
  id: string;
  nome: string;
  distrito: string | null;
  estagio: Estagio;
  origem: "declarado" | "sugerido" | "sem_dados";
  /** Idosos + crianças que moram no bairro; `null` = sem dado ou omitido (RN-13). */
  pessoas: number | null;
  pendente: boolean;
}

/** Os bairros em atenção ou mais, mais graves e mais prioritários primeiro (RF-22), com os moradores vulneráveis. */
export function rankingAgir(
  bairros: ItemEstagio[],
  posicao: Map<string, number>,
  impacto: ImpactoApi | undefined,
  pendentes: Set<string>,
  distritoId: string | null,
  limite = 5,
): LinhaRanking[] {
  const pessoas = new Map(
    (impacto?.itens ?? []).map((i) => {
      const p = i.impacto_pessoas;
      const a = num(p?.idosos_60_mais);
      const c = num(p?.criancas_0_14);
      return [i.territorio_id, a === null || c === null ? null : a + c] as const;
    }),
  );
  return ordenarPorGravidade(
    bairros.filter((b) => !distritoId || b.distrito_id === distritoId),
    posicao,
  )
    .filter((b) => (emVigor(b).ordem ?? -1) >= 1)
    .slice(0, limite)
    .map((b) => {
      const v = emVigor(b);
      return {
        id: b.territorio_id,
        nome: b.territorio_nome,
        distrito: b.distrito_id,
        estagio: v.estagio,
        origem: v.origem,
        pessoas: pessoas.get(b.territorio_id) ?? null,
        pendente: pendentes.has(b.territorio_id),
      };
    });
}

/**
 * Contexto fixo do histórico (estudo de 01/2022 a 06/2024, APAC x Defesa Civil). Não é previsão: descreve o passado,
 * com período e fonte. Percentual aqui é parcela dos registros, nunca chance (RN-06).
 */
export const CONTEXTO_HISTORICO = {
  periodo: "01/2022 a 06/2024",
  fonte: "APAC × Defesa Civil",
  definicao: "Dia pesado: 50 mm ou mais em 24 h, ou 100 mm ou mais em 72 h, no maior pluviômetro.",
  frases: [
    "Com 50 mm ou mais em 24 h, houve deslizamento no dia ou no seguinte em 33 de 40 dias.",
    "Em dias pesados, o Distrito 7 concentrou metade dos deslizamentos; os Distritos 7, 8 e 2 somaram 86%.",
    "Em dias pesados, os alagamentos se concentraram nos Distritos 4 e 5 (57% dos registros).",
    "Maio e junho concentram o maior número de ocorrências (2014 a 06/2024).",
    "A leptospirose sobe de 1 a 2 semanas depois da chuva extrema e o excesso dura cerca de 5 semanas.",
  ],
} as const;

/** O estágio mais alto que o sistema sugere hoje entre os territórios; `null` = nenhum com sugestão (RN-01). */
export function maiorSugerido(itens: ItemEstagio[]): Estagio | null {
  let melhor: Estagio | null = null;
  for (const i of itens) {
    const e = i.sugerido?.estagio;
    if (e && ORDEM(e) >= 0 && (melhor === null || ORDEM(e) > ORDEM(melhor))) melhor = e;
  }
  return melhor;
}

/** Leitura histórica fixa do gatilho (estudo 01/2022 a 06/2024, APAC x Defesa Civil). Contagem, não chance (RN-06). */
export const LEITURA_GATILHO = {
  curta: "Acima de 50 mm em 24 h (ou 100 mm em 72 h), os deslizamentos sobem de 2–3 para 9–29 por dia.",
  fonte: "APAC × Defesa Civil, 2022 a 06/2024",
} as const;

export interface BairroVulneravel {
  bairro_id: string;
  nome: string;
  distrito_id: string | null;
  idosos_60_mais: number | null;
  criancas_0_14: number | null;
  suprimido?: { idosos_60_mais?: boolean; criancas_0_14?: boolean } | null;
}

/**
 * Os bairros com mais idosos e crianças (Censo 2022) de um distrito. É referência de exposição, não previsão de impacto.
 * Contagem omitida ou sem dado não entra como zero: o bairro fica de fora (RN-01, RN-13).
 */
export function topVulneraveis(
  itens: BairroVulneravel[] | undefined,
  distritoId: string | null | undefined,
  n = 3,
): { id: string; nome: string; idosos: number; criancas: number; total: number }[] {
  if (!itens || !distritoId) return [];
  return itens
    .filter((b) => b.distrito_id === distritoId)
    .flatMap((b) => {
      const idosos = num(b.idosos_60_mais);
      const criancas = num(b.criancas_0_14);
      if (idosos === null || criancas === null || b.suprimido?.idosos_60_mais || b.suprimido?.criancas_0_14)
        return [];
      return [{ id: b.bairro_id, nome: b.nome, idosos, criancas, total: idosos + criancas }];
    })
    .sort((a, b) => b.total - a.total)
    .slice(0, n);
}

/**
 * Tendência dos casos por semana usando só semanas completas (a última costuma estar incompleta por atraso de
 * notificação): compara a última semana completa com a de 4 semanas antes. `null` sem 5 semanas completas (RN-01).
 */
export function tendenciaDaSerie(
  itens: { casos: number | null; incompleta: boolean }[] | undefined,
): Tendencia | null {
  const completas = (itens ?? []).filter((i) => !i.incompleta && i.casos !== null);
  if (completas.length < 5) return null;
  const ultima = completas[completas.length - 1].casos as number;
  const antes = completas[completas.length - 5].casos as number;
  if (antes <= 0) return null;
  const variacao = ((ultima - antes) / antes) * 100;
  return variacao > LIMIAR_TENDENCIA_PCT ? "sobe" : variacao < -LIMIAR_TENDENCIA_PCT ? "cai" : "estavel";
}

/** O próximo limiar de estágio acima do valor (Atenção, Alerta, Crítico); `atingido` quando já passou do Crítico. */
export function limiarSeguinte(
  valor: number,
  prefixo: string,
  limiares: Record<string, number>,
): { limiar: number; estagio: Estagio; atingido: boolean } | null {
  for (const n of ["atencao", "alerta", "critico"] as const) {
    const l = num(limiares[`${prefixo}_${n}_mm`]);
    if (l !== null && valor < l) return { limiar: l, estagio: n, atingido: false };
  }
  const critico = num(limiares[`${prefixo}_critico_mm`]);
  return critico === null ? null : { limiar: critico, estagio: "critico", atingido: true };
}
