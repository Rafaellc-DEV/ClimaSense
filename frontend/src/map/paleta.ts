/**
 * Paleta categórica dos 8 distritos sanitários do Recife (RF-20: o mapa não pode ser de uma cor só).
 *
 * Base: Okabe-Ito (desenhada para daltonismo) com um índigo (Tol) no lugar do cinza, porque cinza é a cor de "sem
 * dado" (RN-01). A distância mínima entre qualquer par, em CIELAB, é de ao menos 16 para visão normal, protanopia,
 * deuteranopia e tritanopia (testado em `paleta.test.ts`). A cor nunca é a única pista: o rótulo "DS I" fica no mapa
 * e em cada chip da legenda. No mapa as cores entram com transparência sobre o mapa de fundo.
 */
export const CORES_DISTRITO: Record<string, string> = {
  "ds-1": "#0072B2", // azul
  "ds-2": "#E69F00", // laranja
  "ds-3": "#009E73", // verde
  "ds-4": "#CC79A7", // rosa
  "ds-5": "#56B4E9", // azul-claro
  "ds-6": "#D55E00", // vermelhão
  "ds-7": "#F0E442", // amarelo
  "ds-8": "#332288", // índigo
};

/** Ids dos distritos em ordem numérica. */
export const IDS_DISTRITO = Object.keys(CORES_DISTRITO);

/** Cor do distrito (`ds-N`); id desconhecido recebe cinza neutro (nunca uma cor de risco). */
export function corDoDistrito(id: string | null | undefined): string {
  return (id && CORES_DISTRITO[id]) || "#8fa3b1";
}

/** "ds-3" vira "D3" (rótulo apertado, nunca romano). */
export function siglaDoDistrito(id: string): string {
  return `D${Number(id.replace("ds-", ""))}`;
}

/** "ds-3" vira "Distrito 3". */
export function nomeDoDistrito(id: string): string {
  return `Distrito ${Number(id.replace("ds-", ""))}`;
}
