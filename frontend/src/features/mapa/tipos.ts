/**
 * Tipos e regras da tela Mapa (RF-01, RF-05, RF-06, RF-07, RF-22).
 *
 * O contrato do estágio oficial (COP) e da prioridade está sendo criado no backend em paralelo, então os tipos ficam
 * aqui. Todo campo que o contrato não garante é opcional: a tela mostra "sem dado" em vez de inventar.
 */
import { ESTAGIOS, infoEstagio } from "@/features/evento/estagios";
import type { Estagio, ItemEstagio } from "@/features/evento/tipos";

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
