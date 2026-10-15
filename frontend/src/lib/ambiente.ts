/** A vitrine só existe em desenvolvimento (ou com VITE_VITRINE=1, para testes e capturas de tela). */
export const VITRINE_ATIVA = import.meta.env.DEV || import.meta.env.VITE_VITRINE === "1";
