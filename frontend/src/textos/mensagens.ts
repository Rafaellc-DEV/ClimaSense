/** Textos de retorno das ações: o mesmo verbo do botão (design §8.9: “Enviar para revisão” → “Enviado para revisão.”). */
export const RETORNO = {
  salvar: "Rascunho salvo.",
  enviar: "Enviado para revisão.",
  aprovar: "Versão aprovada.",
  devolver: "Devolvido com o motivo.",
  publicar: "Publicado na página inicial.",
  encerrar: "Encerrado.",
  atualizarFonte: "Atualização iniciada.",
} as const;

export const ROTULOS_ACAO: Record<string, string> = {
  enviar: "Enviar para revisão",
  aprovar: "Aprovar esta versão",
  devolver: "Devolver com justificativa",
  publicar: "Publicar",
  encerrar: "Encerrar",
};

export const SEM_PERMISSAO = "Você não tem permissão para esta ação. Fale com a coordenação.";
