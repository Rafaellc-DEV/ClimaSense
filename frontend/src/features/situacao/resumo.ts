/** Contas da tela Situação: situação em vigor, contagens, maiores valores e bairros que passam do distrito. */
import { infoEstagio } from "@/features/evento/estagios";
import type { ItemEstagio } from "@/features/evento/tipos";
import { nomeCurto } from "@/features/evento/textos";
import { pedeDecisao } from "./Declarar";

/** Situação em vigor: a declarada; sem declaração, a sugerida. */
export const estagioEmVigor = (i: ItemEstagio) => i.declarado?.estagio ?? i.sugerido?.estagio;

export const ordemEmVigor = (i: ItemEstagio) => infoEstagio(estagioEmVigor(i)).ordem;

export type ContagemSituacao = Record<"observacao" | "atencao" | "alerta" | "critico" | "sem_dados", number>;

/** Quantos distritos há em cada situação em vigor. */
export function contarSituacoes(itens: ItemEstagio[]): ContagemSituacao {
  const c: ContagemSituacao = { observacao: 0, atencao: 0, alerta: 0, critico: 0, sem_dados: 0 };
  for (const i of itens) {
    const o = ordemEmVigor(i);
    if (o === 0) c.observacao++;
    else if (o === 1) c.atencao++;
    else if (o === 2) c.alerta++;
    else if (o >= 3) c.critico++;
    else c.sem_dados++;
  }
  return c;
}

export type CampoInsumo = "chuva_24h_mm" | "chuva_prev_24h_mm" | "chuva_prev_72h_mm" | "mare_max_m";

export function insumo(i: ItemEstagio, campo: CampoInsumo): number | null {
  const v = i.sugerido?.insumos?.[campo];
  return typeof v === "number" ? v : null;
}

/** O maior valor entre os distritos e de qual distrito vem. `null` quando nenhum tem o dado. */
export function maiorValor(
  itens: ItemEstagio[],
  campo: CampoInsumo,
): { valor: number; nome: string; empatados: boolean } | null {
  let melhor: { valor: number; nome: string; empatados: boolean } | null = null;
  for (const i of itens) {
    const v = insumo(i, campo);
    if (v === null) continue;
    if (melhor === null || v > melhor.valor)
      melhor = { valor: v, nome: nomeCurto(i.territorio_nome), empatados: false };
    else if (v === melhor.valor) melhor.empatados = true;
  }
  return melhor;
}

/** Hora mais recente de um insumo de data (`previsao_emitida_em`, `mare_emitida_em`) entre os distritos. */
export function horaDoInsumo(itens: ItemEstagio[], campo: string): string | null {
  const horas = itens
    .map((i) => i.sugerido?.insumos?.[campo])
    .filter((x): x is string => typeof x === "string")
    .sort();
  return horas.pop() ?? null;
}

/** Quem pede decisão sobe; depois a situação em vigor mais grave; depois o nome. */
export function ordenarDistritos(itens: ItemEstagio[]): ItemEstagio[] {
  return [...itens].sort(
    (a, b) =>
      Number(pedeDecisao(b)) - Number(pedeDecisao(a)) ||
      Math.max(ordemEmVigor(b), infoEstagio(b.sugerido?.estagio).ordem) -
        Math.max(ordemEmVigor(a), infoEstagio(a.sugerido?.estagio).ordem) ||
      a.territorio_nome.localeCompare(b.territorio_nome, "pt-BR", { numeric: true }),
  );
}

/** Um bairro “passa do distrito” quando a situação sugerida dele é mais grave que a sugerida do distrito. */
export function passaDoDistrito(bairro: ItemEstagio, distrito: ItemEstagio): boolean {
  return infoEstagio(bairro.sugerido?.estagio).ordem > infoEstagio(distrito.sugerido?.estagio).ordem;
}

const porNome = (a: ItemEstagio, b: ItemEstagio) =>
  a.territorio_nome.localeCompare(b.territorio_nome, "pt-BR");

/** Separa os bairros de um distrito em os que pedem atenção (passam do distrito ou pedem decisão) e os demais. */
export function separarBairros(distrito: ItemEstagio, bairros: ItemEstagio[]) {
  const doDistrito = bairros.filter((b) => b.distrito_id === distrito.territorio_id);
  const destaque = doDistrito
    .filter((b) => passaDoDistrito(b, distrito) || pedeDecisao(b))
    .sort(
      (a, b) =>
        infoEstagio(b.sugerido?.estagio).ordem - infoEstagio(a.sugerido?.estagio).ordem || porNome(a, b),
    );
  const outros = doDistrito.filter((b) => !destaque.includes(b)).sort(porNome);
  return { total: doDistrito.length, destaque, outros };
}
