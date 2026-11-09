/**
 * Regras do Mapa por distrito (RF-01, RF-22): ordem das chips, bairros de cada distrito e a classe de prioridade
 * usada na coloração. Tudo derivado do GeoJSON e das listas já carregadas; nada aqui chama a API.
 */
import { IDS_DISTRITO } from "@/map/paleta";
import type { ColecaoFeicoes } from "@/map/MapaBairros";
import type { ItemPrioridadeTerritorio } from "./tipos";

export type Colorir = "distrito" | "estagio" | "prioridade";

export const OPCOES_COLORIR: { valor: Colorir; rotulo: string }[] = [
  { valor: "distrito", rotulo: "Distritos" },
  { valor: "estagio", rotulo: "Estágio" },
  { valor: "prioridade", rotulo: "Prioridade" },
];

/** Distritos do mais ao menos prioritário (RF-22); sem a lista de prioridade, em ordem numérica. */
export function distritosPorPrioridade(lista: ItemPrioridadeTerritorio[]): string[] {
  const posicao = new Map(
    lista.filter((p) => p.nivel === "distrito").map((p) => [p.territorio_id, p.posicao]),
  );
  return [...IDS_DISTRITO].sort((a, b) => {
    const pa = posicao.get(a) ?? Number.MAX_SAFE_INTEGER;
    const pb = posicao.get(b) ?? Number.MAX_SAFE_INTEGER;
    return pa === pb ? a.localeCompare(b) : pa - pb;
  });
}

/** Bairros (id e nome) do distrito, em ordem alfabética, direto do GeoJSON. */
export function bairrosDoDistrito(
  territorios: ColecaoFeicoes | undefined,
  distritoId: string,
): { id: string; nome: string }[] {
  return (territorios?.features ?? [])
    .filter((f) => f.properties.distrito_id === distritoId)
    .map((f) => ({ id: f.properties.id, nome: f.properties.nome }))
    .sort((a, b) => a.nome.localeCompare(b.nome, "pt-BR"));
}

export const CLASSES_PRIORIDADE = 5;

/** Classe 0..4 da posição (4 = mais prioritário) em faixas de igual tamanho; `null` = sem posição (sem dado). */
export function classePrioridade(posicao: number | undefined, total: number): number | null {
  if (posicao === undefined || total <= 0) return null;
  const faixa = Math.min(CLASSES_PRIORIDADE - 1, Math.floor(((posicao - 1) * CLASSES_PRIORIDADE) / total));
  return CLASSES_PRIORIDADE - 1 - faixa;
}

/** Rótulos das faixas da legenda, da mais prioritária (classe 4) para a menos: "1º a 18º", "19º a 37º"… */
export function rotulosPrioridade(total: number): string[] {
  const nomes: string[] = [];
  for (let q = 0; q < CLASSES_PRIORIDADE; q++) {
    const de = Math.ceil((q * total) / CLASSES_PRIORIDADE) + 1;
    const ate = Math.ceil(((q + 1) * total) / CLASSES_PRIORIDADE);
    nomes.push(de >= ate ? `${de}º` : `${de}º a ${ate}º`);
  }
  return nomes;
}
