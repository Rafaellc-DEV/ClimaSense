/** Formatos pt-BR no fuso do Recife (RN-16). A API envia UTC; a conversão acontece aqui. */
export const FUSO = "America/Recife";

const partesDataHora = new Intl.DateTimeFormat("pt-BR", {
  timeZone: FUSO,
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
});

function partes(iso: string | Date) {
  const mapa: Record<string, string> = {};
  for (const p of partesDataHora.formatToParts(new Date(iso))) mapa[p.type] = p.value;
  return mapa;
}

/** "15/10/2026, 23h30" */
export function formatarDataHora(iso: string | Date): string {
  const p = partes(iso);
  return `${p.day}/${p.month}/${p.year}, ${p.hour}h${p.minute}`;
}

/** "15/10/2026" */
export function formatarData(iso: string | Date): string {
  const p = partes(iso);
  return `${p.day}/${p.month}/${p.year}`;
}

/** "18h04" */
export function formatarHora(iso: string | Date): string {
  const p = partes(iso);
  return `${p.hour}h${p.minute}`;
}

/** Números com vírgula decimal. `null` nunca vira 0 (RN-02). */
export function formatarNumero(valor: number | null | undefined, casas = 0): string {
  if (valor === null || valor === undefined || Number.isNaN(valor)) return "sem dado";
  return new Intl.NumberFormat("pt-BR", {
    minimumFractionDigits: casas,
    maximumFractionDigits: casas,
  }).format(valor);
}
