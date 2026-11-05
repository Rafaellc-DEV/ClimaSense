import type { ChaveNivel } from "@/design-system/niveis";
import type { Estagio, SituacaoAcao } from "./tipos";

/** Situações operacionais (F1). `sem_dados` usa o tom de “Dados insuficientes”, nunca o verde (RN-01). */
export const ESTAGIOS: Record<Estagio, { rotulo: string; nivel: ChaveNivel; ordem: number }> = {
  sem_dados: { rotulo: "Sem dados", nivel: "insuficiente", ordem: -1 },
  observacao: { rotulo: "Observação", nivel: "informativo", ordem: 0 },
  atencao: { rotulo: "Atenção", nivel: "atencao", ordem: 1 },
  alerta: { rotulo: "Alerta", nivel: "alerta", ordem: 2 },
  critico: { rotulo: "Crítico", nivel: "critico", ordem: 3 },
  encerrado: { rotulo: "Encerrado", nivel: "insuficiente", ordem: -2 },
};

/** Os que uma pessoa pode declarar. “Sem dados” é estado do sistema, não decisão. */
export const ESTAGIOS_DECLARAVEIS: Estagio[] = ["observacao", "atencao", "alerta", "critico"];

/** Situação desconhecido é tratado como falta de dado, nunca como calmaria. */
export function infoEstagio(e: string | null | undefined) {
  return ESTAGIOS[(e ?? "sem_dados") as Estagio] ?? ESTAGIOS.sem_dados;
}

export const SITUACOES: Record<SituacaoAcao, string> = {
  planejada: "Planejada",
  em_andamento: "Em andamento",
  concluida: "Concluída",
  cancelada: "Cancelada",
};

export const TIPOS_ACAO: Record<string, string> = {
  orientacao: "Orientação",
  visita: "Visita",
  distribuicao_insumos: "Distribuição de insumos",
  vigilancia_agravo: "Vigilância de agravo",
  articulacao: "Articulação",
  outro: "Outro",
};

/** Nomes dos limiares conhecidos; o resto aparece com o nome técnico legível. */
export const ROTULOS_LIMIARES: Record<string, string> = {
  chuva_prev_24h_atencao_mm: "Chuva prevista em 24 h para Atenção (mm)",
  chuva_prev_24h_alerta_mm: "Chuva prevista em 24 h para Alerta (mm)",
  chuva_prev_24h_critico_mm: "Chuva prevista em 24 h para Crítico (mm)",
  chuva_prev_72h_atencao_mm: "Chuva prevista em 72 h para Atenção (mm)",
  chuva_prev_72h_alerta_mm: "Chuva prevista em 72 h para Alerta (mm)",
  chuva_prev_72h_critico_mm: "Chuva prevista em 72 h para Crítico (mm)",
  chuva_24h_atencao_mm: "Chuva das últimas 24 h para Atenção (mm)",
  chuva_24h_alerta_mm: "Chuva das últimas 24 h para Alerta (mm)",
  chuva_24h_critico_mm: "Chuva das últimas 24 h para Crítico (mm)",
  mare_alta_m: "Maré alta a partir de (m acima do nível médio)",
  mare_janela_h: "Maré alta junto ao pico de chuva, janela de (h)",
  ocorrencias_bairro_minimo: "Ocorrências históricas para pesar no bairro (mínimo)",
};

export function rotuloLimiar(chave: string) {
  if (ROTULOS_LIMIARES[chave]) return ROTULOS_LIMIARES[chave];
  const t = chave
    .replace(/_/g, " ")
    .replace(/\bmm\b/, "(mm)")
    .replace(/\bm\b$/, "(m)");
  return t.charAt(0).toUpperCase() + t.slice(1);
}
