/**
 * Operações puras do mapa: porte 1:1 do `mapa_assets/model.js` da Aula 07 (Desktop/AVD), agora em TypeScript.
 * Escala de 5 classes de intervalos iguais sobre TODOS os distritos (busca e filtro não mudam a escala),
 * busca sem acento e células de CSV protegidas contra fórmulas.
 */

/** Cores das classes: rampa de calor (amarelo → vermelho escuro), começando em #FED976 para a classe mais baixa não sumir. */
export const colors = ["#fed976", "#fd9a3c", "#f0592a", "#c81e1e", "#7f0a1a"];

export interface Classe {
  low: number;
  high: number;
  color: string;
}

export interface Escala {
  min: number;
  max: number;
  bins: Classe[];
}

export const normalize = (value: unknown): string =>
  String(value)
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .trim();

export function makeScale(values: (number | null | undefined)[]): Escala {
  const numbers = values.filter((v): v is number => Number.isFinite(v));
  if (!numbers.length) return { min: 0, max: 0, bins: [] };
  const min = Math.min(...numbers),
    max = Math.max(...numbers);
  const count = min === max ? 1 : colors.length;
  return {
    min,
    max,
    bins: Array.from({ length: count }, (_, i) => ({
      low: min + ((max - min) * i) / count,
      high: min + ((max - min) * (i + 1)) / count,
      color: colors[i],
    })),
  };
}

export function classIndex(value: number | null | undefined, scale: Escala): number {
  if (!Number.isFinite(value) || !scale.bins.length) return -1;
  if (scale.min === scale.max) return 0;
  // Os mesmos limites exatos mostrados na legenda, sem divisão de ponto flutuante perto das bordas.
  const index = scale.bins.findIndex((bin, i) => (value as number) < bin.high || i === scale.bins.length - 1);
  return Math.max(0, index);
}

export function matches(properties: { nome_distrito: string; bairros: string[] }, query: string): boolean {
  const needle = normalize(query);
  return [properties.nome_distrito, ...properties.bairros].some((value) => normalize(value).includes(needle));
}

export function csvCell(value: unknown): string {
  let text = String(value);
  if (/^[=+@\-\t\r]/.test(text)) text = "'" + text;
  return '"' + text.replace(/"/g, '""') + '"';
}
