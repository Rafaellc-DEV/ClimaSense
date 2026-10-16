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

/** "18h04"; hora cheia vira "18h". */
export function formatarHora(iso: string | Date, compacta = false): string {
  const p = partes(iso);
  return compacta && p.minute === "00" ? `${Number(p.hour)}h` : `${p.hour}h${p.minute}`;
}

/** "AAAA-MM-DD" do dia no Recife. */
export function diaNoRecife(momento: Date = new Date()): string {
  const p = partes(momento);
  return `${p.year}-${p.month}-${p.day}`;
}

const MESES = [
  "janeiro",
  "fevereiro",
  "março",
  "abril",
  "maio",
  "junho",
  "julho",
  "agosto",
  "setembro",
  "outubro",
  "novembro",
  "dezembro",
];
const MESES_CURTOS = [
  "jan.",
  "fev.",
  "mar.",
  "abr.",
  "maio",
  "jun.",
  "jul.",
  "ago.",
  "set.",
  "out.",
  "nov.",
  "dez.",
];

export function nomeMes(mes: number, curto = false): string {
  return (curto ? MESES_CURTOS : MESES)[mes - 1];
}

/** Data de calendário ("2026-07-01", sem fuso) por extenso: "1º de julho de 2026". */
export function dataPorExtenso(dia: string, comAno = true): string {
  const [a, m, d] = dia.split("-").map(Number);
  const diaTexto = d === 1 ? "1º" : String(d);
  return `${diaTexto} de ${MESES[m - 1]}${comAno ? ` de ${a}` : ""}`;
}

/** "01/07/2026" a partir de "2026-07-01" (sem passar por fuso). */
export function dataCurta(dia: string): string {
  const [a, m, d] = dia.split("-");
  return `${d}/${m}/${a}`;
}

/** "hoje, 18h04", "amanhã, 18h", "ontem, 9h30" ou "16/10/2026, 18h". */
export function quandoRelativo(iso: string | Date, agora: Date = new Date()): string {
  const dia = diaNoRecife(new Date(iso));
  const hoje = diaNoRecife(agora);
  const amanha = diaNoRecife(new Date(agora.getTime() + 86_400_000));
  const ontem = diaNoRecife(new Date(agora.getTime() - 86_400_000));
  const hora = formatarHora(iso, true);
  if (dia === hoje) return `hoje, ${hora}`;
  if (dia === amanha) return `amanhã, ${hora}`;
  if (dia === ontem) return `ontem, ${hora}`;
  return `${formatarData(iso)}, ${hora}`;
}

/** Números com vírgula decimal. `null` nunca vira 0 (RN-02). */
export function formatarNumero(valor: number | null | undefined, casas = 0): string {
  if (valor === null || valor === undefined || Number.isNaN(valor)) return "sem dado";
  return new Intl.NumberFormat("pt-BR", {
    minimumFractionDigits: casas,
    maximumFractionDigits: casas,
  }).format(valor);
}

export function formatarMm(valor: number | null | undefined, casas = 1): string {
  return valor === null || valor === undefined ? "sem dado" : `${formatarNumero(valor, casas)} mm`;
}

/** Soma dias a uma data de calendário "AAAA-MM-DD". */
export function somarDias(dia: string, n: number): string {
  const d = new Date(`${dia}T12:00:00Z`);
  d.setUTCDate(d.getUTCDate() + n);
  return d.toISOString().slice(0, 10);
}
