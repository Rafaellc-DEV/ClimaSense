/**
 * Nomes dos distritos sanitários para a tela: "Distrito 5", nunca "Distrito Sanitário V" nem "DS V".
 * A base territorial guarda o nome com algarismo romano; a conversão acontece só na hora de mostrar.
 */

const ROMANOS: Record<string, number> = { I: 1, II: 2, III: 3, IV: 4, V: 5, VI: 6, VII: 7, VIII: 8 };

// "Distrito Sanitário VII", "Distrito VII" ou "DS VII" (com ou sem acento), em qualquer ponto do texto.
const PADRAO = /\b(?:Distrito\s+Sanit[aá]rio|Distrito|DS)\s+(VIII|VII|VI|IV|V|III|II|I)\b/gi;

/** Troca, dentro de qualquer texto, o distrito em romano pelo número: "Distrito Sanitário IV" vira "Distrito 4". */
export function nomeDistrito(texto: string): string {
  return texto.replace(PADRAO, (_todo, romano: string) => `Distrito ${ROMANOS[romano.toUpperCase()]}`);
}

/** Forma compacta para espaços pequenos (rótulos no mapa): "D4". */
export function siglaDistrito(texto: string): string {
  return nomeDistrito(texto).replace(/\bDistrito\s+(\d)/g, "D$1");
}
