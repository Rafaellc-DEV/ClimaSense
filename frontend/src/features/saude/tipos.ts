/**
 * Contrato das rotas /saude/* (em construção no backend). Os tipos ficam aqui até entrarem no OpenAPI; depois troque
 * por `Esquemas[...]` e rode `npm run gerar-tipos`. Campo ausente vira “sem dado”, nunca zero (RN-01).
 */
export type Agravo = "dengue" | "chikungunya" | "leptospirose";

export interface SemanaRef {
  ano: number;
  semana: number;
  /** Domingo que abre a semana epidemiológica, AAAA-MM-DD. */
  inicio: string;
}

export interface ResumoAgravo {
  agravo: Agravo;
  nome: string;
  fonte_id: string;
  ultima_semana: SemanaRef | null;
  /** `null` com `suprimido` = contagem pequena omitida (RNF-03). */
  casos: number | null;
  suprimido?: boolean;
  casos_estimados: number | null;
  variacao_4s_pct: number | null;
  /** Nível de alerta do InfoDengue, 1 a 4. */
  nivel_alerta: 1 | 2 | 3 | 4 | null;
  incompleta: boolean;
}

export interface JanelaLeptospirose {
  ativa: boolean;
  /** Dia do alagamento que abriu a janela. */
  inicio: string;
  fim: string;
  motivo: string | null;
  territorios: { id: string; nome: string }[];
}

export interface ResumoSaude {
  agravos: ResumoAgravo[];
  janela_leptospirose: JanelaLeptospirose | null;
  gerado_em: string;
}

export interface SemanaCasos extends SemanaRef {
  casos: number | null;
  casos_estimados: number | null;
  ic_inf: number | null;
  ic_sup: number | null;
  nivel_alerta: number | null;
  incompleta: boolean;
}

export interface SerieSemanal {
  itens: SemanaCasos[];
  chuva: { inicio: string; chuva_mm: number | null }[];
}

export interface CasosBairros {
  ano: number;
  itens: {
    bairro_id: string;
    bairro_nome: string;
    distrito_id: string | null;
    casos: number | null;
    /** Contagem abaixo do mínimo: `casos` vem `null` (RNF-03). */
    suprimido?: boolean;
  }[];
  anos_disponiveis: number[];
}

export const NOME_AGRAVO: Record<Agravo, string> = {
  dengue: "Dengue",
  chikungunya: "Chikungunya",
  leptospirose: "Leptospirose",
};

/** Nível do InfoDengue com a cor dita em palavras (a cor nunca fala sozinha). */
export const NIVEL_ALERTA: Record<
  number,
  { rotulo: string; tom: "sucesso" | "atencao" | "alerta" | "critico" }
> = {
  1: { rotulo: "Nível 1, verde", tom: "sucesso" },
  2: { rotulo: "Nível 2, amarelo", tom: "atencao" },
  3: { rotulo: "Nível 3, laranja", tom: "alerta" },
  4: { rotulo: "Nível 4, vermelho", tom: "critico" },
};

/** Aceita o envelope `{ dados, meta }` ou o corpo puro. */
export function dadosDe<T>(r: unknown): T | undefined {
  if (r && typeof r === "object" && "dados" in r) return (r as { dados: T }).dados;
  return r as T | undefined;
}
