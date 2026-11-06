/**
 * Fontes e frescor de cada resposta da API (`meta.fontes`, RF-19). Quando a resposta ainda não traz `meta.fontes`,
 * as funções devolvem lista vazia e a tela mantém o comportamento anterior.
 */
export interface FonteMeta {
  id: string;
  nome: string;
  atualizado_em?: string | null;
  limite_frescor_h?: number | null;
  desatualizado?: boolean | null;
}

/** Lê `meta.fontes` do envelope `{ dados, meta }`. Sem isso, lista vazia. */
export function fontesDe(resposta: unknown): FonteMeta[] {
  if (!resposta || typeof resposta !== "object" || !("meta" in resposta)) return [];
  const meta = (resposta as { meta?: { fontes?: unknown } }).meta;
  const f = meta?.fontes;
  if (!Array.isArray(f)) return [];
  return f.filter((x): x is FonteMeta => !!x && typeof x === "object" && "nome" in x);
}

/** Reúne as fontes de várias respostas, sem repetir o mesmo id. */
export function juntarFontes(...respostas: unknown[]): FonteMeta[] {
  const mapa = new Map<string, FonteMeta>();
  for (const r of respostas) for (const f of fontesDe(r)) if (!mapa.has(f.id)) mapa.set(f.id, f);
  return [...mapa.values()];
}

/** Valor mínimo a partir do qual a API informa a contagem; abaixo disso vem `null` com `suprimido` (RNF-03). */
export const SUPRESSAO_PADRAO = 5;

export function supressaoMinima(resposta: unknown): number {
  if (!resposta || typeof resposta !== "object" || !("meta" in resposta)) return SUPRESSAO_PADRAO;
  const v = (resposta as { meta?: { supressao_minima?: unknown } }).meta?.supressao_minima;
  return typeof v === "number" && v > 0 ? v : SUPRESSAO_PADRAO;
}

/** “há 5 min”, “há 3 h”, “há 2 dias”. */
export function haQuanto(iso: string | Date, agora: Date = new Date()): string {
  const min = Math.floor((agora.getTime() - new Date(iso).getTime()) / 60_000);
  if (min < 1) return "agora há pouco";
  if (min < 60) return `há ${min} min`;
  const h = Math.floor(min / 60);
  if (h < 48) return `há ${h} h`;
  return `há ${Math.floor(h / 24)} dias`;
}
