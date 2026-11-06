import type { CasosBairros } from "./tipos";

export interface TerritorioLista {
  id: string;
  tipo: string;
  nome_exibicao: string;
  pai_id?: string | null;
}

export interface BairroDoDistrito {
  id: string;
  nome: string;
  /** `null` = sem registro no ano. Nunca vira zero (RN-01). */
  casos: number | null;
}

/**
 * Todos os bairros de um distrito: os de /territorios (pai_id = distrito) e os que vieram em /saude/bairros.
 * Mais casos primeiro; bairro sem registro vai ao fim, em ordem alfabética.
 */
export function bairrosDoDistrito(
  distritoId: string,
  territorios: TerritorioLista[],
  itens: CasosBairros["itens"],
): BairroDoDistrito[] {
  const mapa = new Map<string, BairroDoDistrito>();
  for (const t of territorios) {
    if (t.tipo === "bairro" && t.pai_id === distritoId)
      mapa.set(t.id, { id: t.id, nome: t.nome_exibicao, casos: null });
  }
  for (const i of itens) {
    if (i.distrito_id === distritoId)
      mapa.set(i.bairro_id, { id: i.bairro_id, nome: i.bairro_nome, casos: i.casos });
  }
  return [...mapa.values()].sort((a, b) => {
    if (a.casos === null && b.casos === null) return a.nome.localeCompare(b.nome, "pt-BR");
    if (a.casos === null) return 1;
    if (b.casos === null) return -1;
    return b.casos - a.casos || a.nome.localeCompare(b.nome, "pt-BR");
  });
}
