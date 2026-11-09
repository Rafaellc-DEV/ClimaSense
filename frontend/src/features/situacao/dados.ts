import type { ItemEstagio } from "@/features/evento/tipos";
import { nomeCurto } from "@/features/evento/textos";
import type { FonteMeta } from "@/lib/frescor";

export const num = (v: unknown): number | null => (typeof v === "number" && Number.isFinite(v) ? v : null);

export interface PontoChuvaHora {
  t: string;
  valor: number | null;
  min: number | null;
  max: number | null;
}
export interface PontoMareHora {
  t: string;
  valor: number | null;
}
export interface CenarioHora {
  territorio_id: string;
  territorio_nome: string;
  previsao_emitida_em: string | null;
  mare_emitida_em: string | null;
  chuva: PontoChuvaHora[];
  mare: PontoMareHora[];
}

export type Insumo = "chuva_24h_mm" | "chuva_prev_24h_mm" | "chuva_prev_72h_mm" | "mare_max_m";

/** O distrito com o maior valor de um insumo (ou o único escolhido). Sem valor em nenhum, `null` (RN-01). */
export function maiorDe(itens: ItemEstagio[], insumo: Insumo): { item: ItemEstagio; valor: number } | null {
  let m: { item: ItemEstagio; valor: number } | null = null;
  for (const item of itens) {
    const v = num(item.sugerido?.insumos?.[insumo]);
    if (v !== null && (m === null || v > m.valor)) m = { item, valor: v };
  }
  return m;
}

export interface LinhaDistrito {
  id: string;
  nome: string;
  mm: number | null;
}

/** Chuva medida nas últimas 24 h por distrito, do maior ao menor; sem leitura vai ao fim (nunca zero). */
export function linhasMedidas(itens: ItemEstagio[]): LinhaDistrito[] {
  return itens
    .map((i) => ({
      id: i.territorio_id,
      nome: nomeCurto(i.territorio_nome),
      mm: num(i.sugerido?.insumos?.chuva_24h_mm),
    }))
    .sort((a, b) => (b.mm ?? -1) - (a.mm ?? -1) || a.nome.localeCompare(b.nome, "pt-BR", { numeric: true }));
}

/** Faixa de incerteza das próximas `horas` horas: soma dos mínimos e dos máximos horários. */
export function faixaDeIncerteza(
  c: CenarioHora | undefined,
  horas = 24,
): { min: number; max: number } | null {
  const pts = (c?.chuva ?? []).slice(0, horas).filter((p) => p.min !== null && p.max !== null);
  if (pts.length === 0) return null;
  return {
    min: pts.reduce((s, p) => s + (p.min as number), 0),
    max: pts.reduce((s, p) => s + (p.max as number), 0),
  };
}

export const achaFonte = (fontes: FonteMeta[], ...ids: string[]) => fontes.filter((f) => ids.includes(f.id));
