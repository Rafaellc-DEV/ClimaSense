/** Níveis de aviso do ClimaSense (requirements §6.1, design §8.3). Cor nunca aparece sem o texto (RN-17). */
export type ChaveNivel = "sem" | "informativo" | "atencao" | "alerta" | "critico" | "insuficiente";

export interface Nivel {
  chave: ChaveNivel;
  rotulo: string;
  /** Marcas preenchidas na régua (0–4). "insuficiente" usa 0 com traço tracejado. */
  marcas: number;
  cor: string;
  fundo: string;
  texto: string;
}

export const NIVEIS: Record<ChaveNivel, Nivel> = {
  sem: {
    chave: "sem",
    rotulo: "Nenhum aviso ativo",
    marcas: 0,
    cor: "var(--n-sem)",
    fundo: "var(--n-sem-bg)",
    texto: "var(--n-texto)",
  },
  informativo: {
    chave: "informativo",
    rotulo: "Fique atento",
    marcas: 1,
    cor: "var(--n-info)",
    fundo: "var(--n-info-bg)",
    texto: "var(--n-texto)",
  },
  atencao: {
    chave: "atencao",
    rotulo: "Atenção",
    marcas: 2,
    cor: "var(--n-atencao)",
    fundo: "var(--n-atencao-bg)",
    texto: "var(--n-texto)",
  },
  alerta: {
    chave: "alerta",
    rotulo: "Alerta",
    marcas: 3,
    cor: "var(--n-alerta)",
    fundo: "var(--n-alerta-bg)",
    texto: "var(--n-texto)",
  },
  critico: {
    chave: "critico",
    rotulo: "Situação crítica",
    marcas: 4,
    cor: "var(--n-critico)",
    fundo: "var(--n-critico-bg)",
    texto: "var(--n-critico-texto)",
  },
  insuficiente: {
    chave: "insuficiente",
    rotulo: "Dados insuficientes",
    marcas: 0,
    cor: "var(--n-insuf)",
    fundo: "var(--n-insuf-bg)",
    texto: "var(--n-texto)",
  },
};

/** Ordem dos segmentos da régua, de baixo para cima. */
export const ESCALA_REGUA: ChaveNivel[] = ["informativo", "atencao", "alerta", "critico"];
