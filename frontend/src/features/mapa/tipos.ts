/**
 * Tipos e regras da tela Mapa (RF-01, RF-05, RF-06, RF-07, RF-22).
 *
 * O contrato do estágio oficial (COP) e da prioridade está sendo criado no backend em paralelo, então os tipos ficam
 * aqui. Todo campo que o contrato não garante é opcional: a tela mostra "sem dado" em vez de inventar.
 */
import { ESTAGIOS, infoEstagio } from "@/features/evento/estagios";
import type { Estagio, ItemEstagio } from "@/features/evento/tipos";
import { estaVencida, fontesDe } from "@/lib/frescor";

/** Estágio da cidade informado pelo COP. `estagio: null` (ou resposta nula) = ninguém informou (RN-01). */
export interface EstagioOficial {
  estagio: "observacao" | "atencao" | "alerta" | "critico" | null;
  informado_em?: string | null;
  registrado_em?: string | null;
  autor_nome?: string | null;
  observacao?: string | null;
  fonte?: string | { nome?: string } | null;
}

export interface ItemPrioridadeTerritorio {
  territorio_id: string;
  nome: string;
  nivel?: string | null;
  posicao: number;
  ocorrencias_alagamento?: number | null;
  ocorrencias_deslizamento?: number | null;
  criterio?: string | null;
  /** Só nos distritos: contagens agregadas do Censo 2022 (nunca zero no lugar de ausente, RN-01). */
  idosos_60_mais?: number | null;
  criancas_0_14?: number | null;
  /** Data da ocorrência mais recente, se a API informar (não inventamos). */
  ultima_ocorrencia?: string | null;
}

/** Período das ocorrências contadas, como a fonte informa. Campo ausente = `null` (nunca inventado). */
export interface PeriodoOcorrencias {
  inicio: string | null;
  fim: string | null;
  ultima: string | null;
  fonte: string;
}

const MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];

function ano(v: unknown): string | null {
  const t = v == null ? "" : String(v).slice(0, 4);
  return /^\d{4}$/.test(t) ? t : null;
}

function mesAno(v: unknown): string | null {
  if (typeof v !== "string") return null;
  const m = /^(\d{4})-(\d{2})/.exec(v);
  return m && Number(m[2]) >= 1 && Number(m[2]) <= 12 ? `${MESES[Number(m[2]) - 1]}/${m[1]}` : null;
}

/** Lê o período em `dados` (`desde`, `periodo_inicio`, `periodo_fim`, `ultima_ocorrencia`) e a fonte em `meta.fontes`. */
export function periodoOcorrencias(resposta: unknown): PeriodoOcorrencias {
  const r = (resposta ?? {}) as { dados?: Record<string, unknown>; meta?: { fontes?: { nome?: string }[] } };
  const d = r.dados ?? {};
  return {
    inicio: ano(d.periodo_inicio ?? d.desde),
    fim: ano(d.periodo_fim),
    ultima: mesAno(d.ultima_ocorrencia),
    fonte: r.meta?.fontes?.[0]?.nome ?? "Defesa Civil",
  };
}

/** "2014–2024 · Defesa Civil · última: mar/2024"; sem período: "período não informado pela fonte". */
export function textoPeriodo(p: PeriodoOcorrencias, ultimaDoItem?: string | null): string {
  const periodo = p.inicio
    ? p.fim
      ? `${p.inicio}–${p.fim}`
      : `desde ${p.inicio}`
    : "período não informado pela fonte";
  const ultima = mesAno(ultimaDoItem) ?? p.ultima;
  return `${periodo} · ${p.fonte}${ultima ? ` · última: ${ultima}` : ""}`;
}

export interface PropsTerritorio {
  id: string;
  nome: string;
  distrito_id?: string | null;
}
export type ColecaoTerritorios = GeoJSON.FeatureCollection<GeoJSON.Geometry, PropsTerritorio>;

export function nomeDaFonte(f: EstagioOficial["fonte"]): string {
  if (!f) return "COP (Centro de Operações do Recife)";
  return typeof f === "string" ? f : (f.nome ?? "COP (Centro de Operações do Recife)");
}

export type OrigemEstagio = "declarado" | "sugerido" | "sem_dados";

export interface EmVigor {
  estagio: Estagio;
  /** 0 a 3 (observação a crítico); `null` = sem dado. */
  ordem: number | null;
  origem: OrigemEstagio;
}

/** Insumos da sugestão por fonte de `GET /estagios` (backend `servicos/estagios.py`). */
const INSUMOS_DA_FONTE: Record<string, string[]> = {
  "open-meteo-previsao": [
    "chuva_prev_24h_mm",
    "chuva_prev_72h_mm",
    "horas_previstas_72h",
    "pico_chuva_em",
    "previsao_emitida_em",
  ],
  "open-meteo-mare": ["mare_max_m", "mare_max_em", "mare_no_pico_m", "mare_emitida_em"],
  "recife-alagamento": ["ocorrencias_historicas"],
};

/**
 * Itens de `GET /estagios` sem o que vem de fonte vencida (ADR 0019). Cada insumo some só se a fonte dele venceu
 * (a chuva medida segue as fontes listadas em `chuva_24h_fontes`); a sugestão do sistema some se qualquer fonte dela
 * venceu, porque foi calculada com o dado velho. A declaração da equipe fica: é registro humano, não fonte.
 */
export function semSugestaoVencida(itens: ItemEstagio[], resposta: unknown): ItemEstagio[] {
  const vencidas = new Set(
    fontesDe(resposta)
      .filter(estaVencida)
      .map((f) => f.id),
  );
  if (vencidas.size === 0) return itens;
  return itens.map((i) => {
    const insumos = { ...i.sugerido.insumos };
    for (const [fonte, campos] of Object.entries(INSUMOS_DA_FONTE))
      if (vencidas.has(fonte)) for (const c of campos) delete insumos[c];
    const daChuva = (insumos.chuva_24h_fontes as string[] | undefined) ?? ["apac-chuva"];
    if (daChuva.some((f) => vencidas.has(f))) {
      delete insumos.chuva_24h_mm;
      delete insumos.chuva_24h_fontes;
    }
    return {
      ...i,
      alertas_oficiais: vencidas.has("alertas-oficiais") ? [] : i.alertas_oficiais,
      sugerido: { ...i.sugerido, estagio: "sem_dados", motivos: [], insumos, calculado_em: null },
    };
  });
}

/** Estágio em vigor do território: o declarado; sem declaração, o sugerido; sem nenhum, "sem dados" (nunca "observação"). */
export function emVigor(i: ItemEstagio | undefined): EmVigor {
  if (!i) return { estagio: "sem_dados", ordem: null, origem: "sem_dados" };
  const dec = i.declarado ? infoEstagio(i.declarado.estagio) : null;
  if (i.declarado && dec && dec.ordem >= 0)
    return { estagio: i.declarado.estagio, ordem: dec.ordem, origem: "declarado" };
  const sug = infoEstagio(i.sugerido?.estagio);
  if (sug.ordem >= 0) return { estagio: i.sugerido.estagio, ordem: sug.ordem, origem: "sugerido" };
  return { estagio: "sem_dados", ordem: null, origem: "sem_dados" };
}

export interface ContagemEstagio {
  estagio: Estagio;
  rotulo: string;
  declarados: number;
  sugeridos: number;
}

const ORDEM_EXIBICAO: Estagio[] = ["critico", "alerta", "atencao", "observacao", "sem_dados"];

/** Quantos bairros em cada estágio, separando declarado e sugerido. Mais grave primeiro. */
export function contarPorEstagio(itens: ItemEstagio[]): ContagemEstagio[] {
  return ORDEM_EXIBICAO.map((e) => {
    const v = itens.map(emVigor).filter((x) => x.estagio === e);
    return {
      estagio: e,
      rotulo: ESTAGIOS[e].rotulo,
      declarados: v.filter((x) => x.origem === "declarado").length,
      sugeridos: v.filter((x) => x.origem !== "declarado").length,
    };
  });
}

const FRASE_ESTAGIO: Record<Estagio, string> = {
  critico: "em estágio crítico",
  alerta: "em alerta",
  atencao: "em atenção",
  observacao: "em observação",
  sem_dados: "com dados insuficientes",
  encerrado: "encerrados",
};

/** Contagem em linguagem de bate-olho: "94 bairros em observação", "1 bairro em alerta" (o número vem à parte). */
export function frasePorEstagio(estagio: Estagio, n: number): string {
  return `${n === 1 ? "bairro" : "bairros"} ${FRASE_ESTAGIO[estagio]}`;
}

/** Id do bairro nas feições e nos itens da API: `bairro-…`. Distritos: `ds-N`. */
export const ehBairro = (id: string) => id.startsWith("bairro-");

/** Nome sem acento e em minúsculas, para a busca de bairro. */
export const semAcento = (t: string) => t.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().trim();

/** Bairros mais graves primeiro; dentro do mesmo estágio, ordem alfabética (RF-22: o mais crítico sobe). */
export function ordenarPorGravidade(itens: ItemEstagio[], posicao: Map<string, number>): ItemEstagio[] {
  return [...itens].sort((a, b) => {
    const oa = emVigor(a).ordem ?? -1;
    const ob = emVigor(b).ordem ?? -1;
    if (oa !== ob) return ob - oa;
    const pa = posicao.get(a.territorio_id) ?? Number.MAX_SAFE_INTEGER;
    const pb = posicao.get(b.territorio_id) ?? Number.MAX_SAFE_INTEGER;
    if (pa !== pb) return pa - pb;
    return a.territorio_nome.localeCompare(b.territorio_nome, "pt-BR");
  });
}
