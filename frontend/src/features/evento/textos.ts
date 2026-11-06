/** Textos curtos comuns às telas da equipe: nomes de distrito, listas em frase, horas e fontes. */
import type { Esquemas } from "@/lib/api";
import { useConsultaViva } from "@/lib/consultas";
import { formatarData, quandoRelativo } from "@/lib/formatos";

/** “Distrito Sanitário V” → “DS V”. Bairro e outros nomes ficam como estão. */
export function nomeCurto(nome: string): string {
  return nome.replace(/^Distrito Sanit[aá]rio\s+/i, "DS ");
}

/** “DS I”, “DS I e DS II”, “DS I, DS II e DS III”. */
export function listaEmFrase(nomes: string[]): string {
  if (nomes.length <= 1) return nomes[0] ?? "";
  return `${nomes.slice(0, -1).join(", ")} e ${nomes[nomes.length - 1]}`;
}

/** “hoje às 14h”, “ontem às 23h33”, “03/11/2026 às 9h”. */
export function quandoAs(iso: string | Date, agora = new Date()): string {
  return quandoRelativo(iso, agora).replace(", ", " às ");
}

const DIAS = ["domingo", "segunda", "terça", "quarta", "quinta", "sexta", "sábado"];

/** “hoje”, “amanhã” ou o dia da semana (“na quinta”), para a frase da previsão. */
export function diaDaPrevisao(iso: string, agora = new Date()): string {
  const q = quandoRelativo(iso, agora);
  if (q.startsWith("hoje")) return "hoje";
  if (q.startsWith("amanhã")) return "amanhã";
  const d = new Date(new Date(iso).toLocaleString("en-US", { timeZone: "America/Recife" }));
  const dia = DIAS[d.getDay()];
  return dia === "sábado" || dia === "domingo" ? `no ${dia}` : `na ${dia}`;
}

/** “DD/MM” de uma data ISO ou “AAAA-MM-DD”. */
export function diaMes(iso: string): string {
  const s = /^\d{4}-\d{2}-\d{2}$/.test(iso) ? `${iso}T12:00:00Z` : iso;
  return formatarData(s).slice(0, 5);
}

/** Uma fonte de `GET /fontes`: nome, situação e hora da última carga (o `/painel/resumo` foi aposentado). */
export type FonteResumo = Pick<Esquemas["Fonte"], "id" | "nome" | "status" | "ultima_atualizacao">;

/** Fontes do painel (nome, situação e hora da última carga), para o rodapé de cada tela. */
export function useFontesResumo() {
  const r = useConsultaViva<FonteResumo[]>("/fontes");
  const lista = Array.isArray(r.data) ? r.data : [];
  return {
    consulta: r,
    lista,
    hora: (id: string): string | null => lista.find((f) => f.id === id)?.ultima_atualizacao ?? null,
  };
}

/** “atualizada ontem às 23h33” ou “sem hora de atualização”. */
export function atualizada(iso: string | null | undefined, genero: "a" | "o" = "a"): string {
  return iso ? `atualizad${genero} ${quandoAs(iso)}` : "sem hora de atualização";
}
