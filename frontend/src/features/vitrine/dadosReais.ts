/**
 * Dados REAIS usados na vitrine: distritos sanitários do Recife, a partir de data/territorio/
 * (GeoJSON oficial + CSV de bairros com as 15 correções documentadas; área geodésica WGS84).
 * Fonte: Dados Abertos do Recife — https://dados.recife.pe.gov.br/dataset/distritos-sanitarios
 */
import distritos from "@/assets/tracos/distritos.json";

export const FONTE_DISTRITOS = {
  nome: "Dados Abertos do Recife, distritos sanitários (com correção dos DS VII e VIII)",
  atualizadoEm: "2026-03-02T14:38:37Z",
  tipo: "observada" as const,
};

export interface DistritoReal {
  codigo: number;
  nome: string;
  bairros: number;
  areaKm2: number;
}

const DADOS: Record<number, { bairros: number; areaKm2: number }> = {
  1: { bairros: 11, areaKm2: 15.25 },
  2: { bairros: 18, areaKm2: 14.805 },
  3: { bairros: 16, areaKm2: 18.124 },
  4: { bairros: 12, areaKm2: 42.073 },
  5: { bairros: 16, areaKm2: 29.898 },
  6: { bairros: 5, areaKm2: 24.91 },
  7: { bairros: 13, areaKm2: 60.749 },
  8: { bairros: 3, areaKm2: 17.257 },
};

export const DISTRITOS_REAIS: DistritoReal[] = distritos.distritos.map((d) => ({
  codigo: d.codigo,
  nome: d.nome,
  ...DADOS[d.codigo],
}));
