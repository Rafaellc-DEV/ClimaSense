/** Dia e hora das ações (fuso do Recife, UTC-3, sem horário de verão). */
import { diaNoRecife, formatarHora } from "@/lib/formatos";

/** Dia e hora digitados viram ISO. Vazio ou inválido: null. */
export function isoDeDiaHora(dia: string, hora: string): string | null {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(dia) || !/^\d{2}:\d{2}$/.test(hora)) return null;
  const d = new Date(`${dia}T${hora}:00-03:00`);
  return Number.isNaN(d.getTime()) ? null : d.toISOString();
}

/** Valores iniciais dos campos Dia e Hora: agora, no fuso do Recife. */
export function agoraNoRecife(agora: Date = new Date()): { dia: string; hora: string } {
  return { dia: diaNoRecife(agora), hora: formatarHora(agora).replace("h", ":") };
}
