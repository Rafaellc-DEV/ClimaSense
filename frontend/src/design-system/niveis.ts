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
  /** O que fazer, em uma linha — aparece sob o nível em vigor na régua. */
  acao?: string;
}

export const NIVEIS: Record<ChaveNivel, Nivel> = {
  sem: {
    chave: "sem",
    rotulo: "Nenhum aviso ativo",
    acao: "Sem aviso não é ausência de risco. Em chuva forte, evite áreas que costumam alagar.",
    marcas: 0,
    cor: "var(--n-sem)",
    fundo: "var(--n-sem-bg)",
    texto: "var(--n-texto)",
  },
  informativo: {
    chave: "informativo",
    rotulo: "Fique atento",
    acao: "Acompanhe a previsão; por enquanto, nada a fazer.",
    marcas: 1,
    cor: "var(--n-info)",
    fundo: "var(--n-info-bg)",
    texto: "var(--n-texto)",
  },
  atencao: {
    chave: "atencao",
    rotulo: "Atenção",
    acao: "Evite áreas que costumam alagar.",
    marcas: 2,
    cor: "var(--n-atencao)",
    fundo: "var(--n-atencao-bg)",
    texto: "var(--n-texto)",
  },
  alerta: {
    chave: "alerta",
    rotulo: "Alerta",
    acao: "Adie deslocamentos e afaste-se de canais e encostas.",
    marcas: 3,
    cor: "var(--n-alerta)",
    fundo: "var(--n-alerta-bg)",
    texto: "var(--n-texto)",
  },
  critico: {
    chave: "critico",
    rotulo: "Situação crítica",
    acao: "Procure um local seguro. Emergência: 199.",
    marcas: 4,
    cor: "var(--n-critico)",
    fundo: "var(--n-critico-bg)",
    texto: "var(--n-critico-texto)",
  },
  insuficiente: {
    chave: "insuficiente",
    rotulo: "Dados insuficientes",
    acao: "Não dá para afirmar o nível agora. Acompanhe a Defesa Civil (199).",
    marcas: 0,
    cor: "var(--n-insuf)",
    fundo: "var(--n-insuf-bg)",
    texto: "var(--n-texto)",
  },
};

/** Ordem dos segmentos da régua, de baixo para cima. */
export const ESCALA_REGUA: ChaveNivel[] = ["informativo", "atencao", "alerta", "critico"];
