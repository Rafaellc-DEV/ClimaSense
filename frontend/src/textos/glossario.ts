/**
 * Vocabulário fixo da interface (design §8.9, RNF-MAN-07). Use estes termos em toda tela; a revisão de
 * linguagem acontece aqui, não espalhada pelos componentes.
 */
export const GLOSSARIO = {
  aviso: "O que a população vê na página inicial. Só existe depois de revisado e publicado.",
  comunicado: "O texto que a equipe escreve, revisa e publica. Quando publicado, vira um aviso.",
  avaliacao: "O registro de por que um território precisa (ou não) de atenção, com evidências.",
  revisar: "Outra pessoa confere a versão e aprova ou devolve com o motivo.",
  publicar: "Torna o aviso visível para qualquer pessoa na página inicial, até o fim da validade.",
  encerrar: "Tira da página inicial e guarda no histórico.",
  dadosInsuficientes: "Falta informação para dizer algo com segurança. Nunca quer dizer risco baixo.",
  derivada: "Dado de modelo meteorológico (reanálise), não medido numa estação.",
  prevista: "Previsão emitida por um modelo, com horário de emissão.",
  observada: "Medida ou registrada por um órgão oficial.",
} as const;

export const ESTADOS: Record<string, string> = {
  rascunho: "Rascunho",
  em_revisao: "Em revisão",
  aprovado: "Aprovado",
  devolvido: "Devolvido",
  publicado: "Publicado",
  encerrado: "Encerrado",
};

/** Avaliação concorda no feminino. */
export const ESTADOS_AVALIACAO: Record<string, string> = {
  rascunho: "Rascunho",
  em_revisao: "Em revisão",
  aprovado: "Aprovada",
  devolvido: "Devolvida",
  encerrado: "Encerrada",
};

export const PRIORIDADES: Record<string, string> = {
  sem_indicacao: "Sem indicação",
  atencao: "Atenção",
  alerta: "Alerta",
  critico: "Situação crítica",
  dados_insuficientes: "Dados insuficientes",
};

export const TIPOS_FONTE: Record<string, string> = {
  observada: "Observada",
  prevista: "Prevista",
  derivada: "Derivada (modelo)",
};

export const PAPEIS: Record<string, string> = {
  analista: "Analista",
  revisor: "Revisor",
  coordenacao: "Coordenação",
  administrador: "Administrador",
};

export const PUBLICOS: Record<string, string> = {
  populacao: "População",
  equipes_saude: "Equipes de saúde",
};

export const ROMANOS = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII"];

/** "Distrito Sanitário IV (DS IV)" na primeira menção (design §8.9). */
export function distritoPorExtenso(id: string, comSigla = false): string {
  const n = Number(id.replace("ds-", ""));
  const r = ROMANOS[n] ?? id;
  return comSigla ? `Distrito Sanitário ${r} (DS ${r})` : `Distrito Sanitário ${r}`;
}
