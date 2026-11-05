/**
 * Fontes que saíram do produto (specs/foco-chuvas.md §2): a vacinação não foi pedida pelo cliente. Enquanto o
 * backend ainda listar a fonte, o front não a mostra em lugar nenhum.
 */
const FORA_DO_PRODUTO = new Set(["vacinacao"]);

export function noProduto<T extends { id?: string | null; fonte_id?: string | null }>(f: T) {
  return !FORA_DO_PRODUTO.has(f.id ?? f.fonte_id ?? "");
}
