/**
 * Tipos do evento de chuva (specs/foco-chuvas.md §4): situações, ações e boletim.
 *
 * O backend destes endpoints está sendo escrito em paralelo, então os tipos ficam aqui (e não em `api-tipos.ts`, que é
 * gerado do OpenAPI). Quando o contrato entrar no OpenAPI, troque por `Esquemas[...]` e rode `npm run gerar-tipos`.
 * Todo campo que o contrato não garante é opcional: a tela mostra “Sem dado” em vez de inventar.
 */

/** `encerrado` só aparece no histórico: é a linha que tirou a declaração do território. */
export type Estagio = "sem_dados" | "observacao" | "atencao" | "alerta" | "critico" | "encerrado";

export interface FonteEvento {
  id?: string;
  nome: string;
  atualizado_em?: string | null;
}

export interface InsumosEstagio {
  chuva_24h_mm?: number | null;
  chuva_prev_24h_mm?: number | null;
  chuva_prev_72h_mm?: number | null;
  mare_max_m?: number | null;
  /** Classe do modelo de alagamento (F6) ou objeto com `classe`; sempre experimental. */
  risco_ml?: string | { classe?: string | null; fatores?: string[] } | null;
  ocorrencias_historicas?: number | null;
  [outro: string]: unknown;
}

export interface EstagioSugerido {
  estagio: Estagio;
  motivos: string[];
  insumos: InsumosEstagio;
  calculado_em: string | null;
  fontes?: FonteEvento[];
  /** Insumos que faltaram para sugerir (o motivo de `sem_dados`). */
  faltando?: string[];
}

export interface EstagioDeclarado {
  estagio: Estagio;
  justificativa: string;
  autor_nome: string;
  declarado_em: string;
  /** true quando a declaração vem do distrito ou do Recife, não do próprio território. */
  herdado?: boolean;
  territorio_origem_nome?: string;
}

export interface ItemEstagio {
  territorio_id: string;
  territorio_nome: string;
  nivel: "distrito" | "bairro";
  distrito_id: string | null;
  /** Bairro: id do distrito de onde vêm a chuva e a maré (RN-07). */
  herda_chuva_de?: string | null;
  sugerido: EstagioSugerido;
  declarado: EstagioDeclarado | null;
  /** Alertas de órgãos oficiais, quando o conector existir. */
  alertas_oficiais?: {
    origem: string;
    nivel: string;
    emitido_em: string;
    url?: string | null;
    evento?: string | null;
    expira_em?: string | null;
    /** Área exata do aviso na fonte (ex.: município, mesorregião). */
    area?: string | null;
  }[];
}

export interface MensagemWhatsApp {
  texto: string;
  wa_me_url: string;
  /** Só no navegador: de que territórios e situação é a mensagem, para registrar o uso na auditoria. */
  uso?: { territorio_ids: string[]; estagio?: string };
}

export type SituacaoAcao = "planejada" | "em_andamento" | "concluida" | "cancelada";

export interface Acao {
  id: string | number;
  territorio_id: string;
  territorio_nome?: string | null;
  /** "municipio", "distrito" ou "bairro". */
  territorio_nivel?: "municipio" | "distrito" | "bairro" | null;
  distrito_id?: string | null;
  distrito_nome?: string | null;
  tipo: string;
  descricao: string;
  responsavel?: string | null;
  situacao: SituacaoAcao;
  inicio_em?: string | null;
  fim_em?: string | null;
  criada_em?: string | null;
  atualizada_em?: string | null;
  autor_nome?: string | null;
  atualizado_por_nome?: string | null;
  /** Obsoleto (PRD §5): a tela não usa. */
  licao_aprendida?: string | null;
}

/** Um passo do histórico de uma ação (`GET /acoes/{id}`). */
export interface EventoAcao {
  id: number | string;
  em: string;
  autor_nome: string;
  situacao: SituacaoAcao;
  texto: string;
}

type Objeto = Record<string, unknown>;
const ehObjeto = (x: unknown): x is Objeto => typeof x === "object" && x !== null && !Array.isArray(x);

/** Tira o envelope `RespostaDados` ({ dados, meta }) quando houver. */
export function desembrulhar<T>(r: unknown): T | undefined {
  if (ehObjeto(r) && "dados" in r && "meta" in r) return r.dados as T;
  return r as T | undefined;
}

/** Fontes do envelope (`meta.fontes`), quando a resposta vier nele. */
export function fontesDoEnvelope(r: unknown): FonteEvento[] {
  if (ehObjeto(r) && ehObjeto(r.meta) && Array.isArray(r.meta.fontes)) return r.meta.fontes as FonteEvento[];
  return [];
}

/** Lista de itens de uma resposta: aceita lista pura, `{ itens }` ou o envelope em volta de qualquer um deles. */
export function listaDe<T>(r: unknown): T[] {
  const d = desembrulhar<unknown>(r);
  if (Array.isArray(d)) return d as T[];
  if (ehObjeto(d) && Array.isArray(d.itens)) return d.itens as T[];
  return [];
}

/** Limiares de `/estagios/parametros`: só os valores numéricos, achatados por nome. */
export function limiaresDe(r: unknown): Record<string, number> {
  let d = desembrulhar<unknown>(r);
  if (ehObjeto(d) && ehObjeto(d.limiares)) d = d.limiares;
  const saida: Record<string, number> = {};
  if (ehObjeto(d)) for (const [k, v] of Object.entries(d)) if (typeof v === "number") saida[k] = v;
  return saida;
}

/** Quem e quando os parâmetros mudaram pela última vez, se o backend contar. */
export function autoriaParametros(r: unknown): { autor?: string; em?: string } {
  const d = desembrulhar<unknown>(r);
  if (!ehObjeto(d)) return {};
  const autor = d.atualizado_por_nome ?? d.autor_nome ?? d.atualizado_por;
  const em = d.atualizado_em;
  return {
    autor: typeof autor === "string" ? autor : undefined,
    em: typeof em === "string" ? em : undefined,
  };
}

/** Classe do risco de alagamento (F6) nos insumos, se o modelo estiver publicado. */
export function riscoMl(i: InsumosEstagio | undefined): { classe: string; fatores: string[] } | null {
  const r = i?.risco_ml;
  if (!r) return null;
  if (typeof r === "string") return { classe: r, fatores: [] };
  if (ehObjeto(r) && typeof r.classe === "string") return { classe: r.classe, fatores: r.fatores ?? [] };
  return null;
}

/** Link de WhatsApp seguro: só `https://wa.me/`; senão, monta a partir do texto. */
export function linkWhatsApp(m: MensagemWhatsApp): string {
  return /^https:\/\/wa\.me\//.test(m.wa_me_url)
    ? m.wa_me_url
    : `https://wa.me/?text=${encodeURIComponent(m.texto)}`;
}
