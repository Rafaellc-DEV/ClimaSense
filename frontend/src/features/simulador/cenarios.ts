import { formatarNumero } from "@/lib/formatos";

export interface CenarioPronto {
  chave: "moderada" | "forte" | "extrema";
  rotulo: string;
  chuva_prevista_mm: number;
  chuva_acumulada_mm: number;
  mare_m: number;
  duracao_h: number;
}

const arredondar = (v: number, passo = 1) => Math.round(v / passo) * passo;

/**
 * Cenários prontos a partir dos gatilhos REAIS de `/estagios/parametros`: moderada logo abaixo do gatilho de atenção,
 * forte entre atenção e alerta, extrema no gatilho crítico (ou bem acima do alerta, se não houver). Sem os gatilhos
 * de chuva, não há cenário pronto: nada é inventado.
 */
export function cenariosProntos(lim: Record<string, number>): CenarioPronto[] {
  const a24 = lim.chuva_prev_24h_atencao_mm;
  const b24 = lim.chuva_prev_24h_alerta_mm;
  if (a24 === undefined || b24 === undefined) return [];
  const c24 = lim.chuva_prev_24h_critico_mm ?? b24 * 1.6;
  const a72 = lim.chuva_prev_72h_atencao_mm ?? a24 * 2.4;
  const b72 = lim.chuva_prev_72h_alerta_mm ?? b24 * 2;
  const c72 = lim.chuva_prev_72h_critico_mm ?? b72 * 1.5;
  const mare = lim.mare_alta_m ?? 0.6;
  return [
    {
      chave: "moderada",
      rotulo: "Chuva moderada",
      chuva_prevista_mm: arredondar(a24 * 0.8),
      chuva_acumulada_mm: arredondar(a72 * 0.8),
      mare_m: arredondar(mare * 0.8, 0.1),
      duracao_h: 6,
    },
    {
      chave: "forte",
      rotulo: "Chuva forte",
      chuva_prevista_mm: arredondar((a24 + b24) / 2),
      chuva_acumulada_mm: arredondar((a72 + b72) / 2),
      mare_m: arredondar(mare, 0.1),
      duracao_h: 12,
    },
    {
      chave: "extrema",
      rotulo: "Chuva extrema",
      chuva_prevista_mm: arredondar(c24),
      chuva_acumulada_mm: arredondar(c72),
      mare_m: arredondar(mare * 1.5, 0.1),
      duracao_h: 24,
    },
  ];
}

/** "Forte · 45 mm em 24 h": o nome curto e o valor que o botão aplica. */
export function textoCenario(c: CenarioPronto): string {
  return `${c.rotulo.replace("Chuva ", "").replace(/^./, (x) => x.toUpperCase())} · ${formatarNumero(c.chuva_prevista_mm)} mm em 24 h`;
}
