import type { Esquemas } from "@/lib/api";
import { diaNoRecife, formatarHora, formatarMm, formatarNumero } from "@/lib/formatos";
import { infoEstagio } from "@/features/evento/estagios";
import { diaMes, listaEmFrase, nomeCurto, quandoAs } from "@/features/evento/textos";
import type { Acao } from "@/features/evento/tipos";
import { NIVEL_ALERTA, type ResumoSaude } from "@/features/saude/tipos";

/** O contrato do relatório executivo ganhou campos; os que o OpenAPI gerado ainda não traz ficam opcionais. */
export type Boletim = Esquemas["Boletim"] & {
  periodo?: { desde: string; ate: string } | null;
  acoes_concluidas?: Acao[] | null;
};
export type Distrito = Boletim["estagios"][number];

/** BOL-2026-1105-1700: ano, mês e dia, hora e minuto da emissão (hora do Recife). */
export function numeroBoletim(em: Date): string {
  const [a, m, d] = diaNoRecife(em).split("-");
  return `BOL-${a}-${m}${d}-${formatarHora(em).replace("h", "")}`;
}

export const ordemPorNome = (a: Distrito, b: Distrito) =>
  a.territorio_nome.localeCompare(b.territorio_nome, "pt-BR", { numeric: true });

/** Frase da situação: só a declarada pela equipe. A sugestão do sistema não entra no boletim. */
export function fraseSituacao(ds: Distrito[]): string {
  const declarados = ds.filter((d) => d.declarado);
  if (ds.length === 0) return "Sem informação da situação dos distritos.";
  if (declarados.length === 0) return "Nenhum distrito tem situação declarada pela equipe.";
  const grupos = new Map<string, string[]>();
  for (const d of [...declarados].sort(
    (a, b) => infoEstagio(b.declarado?.estagio).ordem - infoEstagio(a.declarado?.estagio).ordem,
  )) {
    const r = infoEstagio(d.declarado?.estagio).rotulo;
    grupos.set(r, [...(grupos.get(r) ?? []), nomeCurto(d.territorio_nome)]);
  }
  const partes = [...grupos.entries()].map(([r, n]) => `${listaEmFrase(n)} em ${r}`);
  const resto = ds.length - declarados.length;
  return `${partes.join("; ")}.${
    resto ? ` ${resto === 1 ? "Um distrito está" : `Os outros ${resto} estão`} sem declaração.` : ""
  }`;
}

export function fraseChuva(c: Boletim["chuva"]): string {
  const ult =
    c.chuva_24h_mm === null
      ? "Sem leitura da chuva das últimas 24 h"
      : `Nas últimas 24 h choveu até ${formatarMm(c.chuva_24h_mm)}${
          c.chuva_24h_territorio ? ` (${nomeCurto(c.chuva_24h_territorio)})` : ""
        }`;
  const prev =
    c.chuva_prev_72h_mm === null
      ? "a previsão para os próximos 3 dias está indisponível"
      : `a previsão para os próximos 3 dias é de até ${formatarMm(c.chuva_prev_72h_mm)}${
          c.chuva_prev_72h_territorio ? ` (${nomeCurto(c.chuva_prev_72h_territorio)})` : ""
        }`;
  return `${ult}; ${prev}.`;
}

export function fraseSaude(saude: ResumoSaude | undefined, saudeFalhou: boolean): string {
  const j = saude?.janela_leptospirose;
  const lepto = j?.ativa
    ? `janela de vigilância de leptospirose aberta até ${diaMes(j.fim)}`
    : saude
      ? "nenhuma janela de vigilância de leptospirose aberta"
      : saudeFalhou
        ? "dados de saúde ainda não disponíveis"
        : "";
  return lepto ? `${lepto[0].toUpperCase()}${lepto.slice(1)}.` : "";
}

/** Destaques em tópicos, só com o que existe nos dados. */
export function destaques(
  b: Boletim | undefined,
  saude: ResumoSaude | undefined,
  emAndamento: number,
): string[] {
  const s: string[] = [];
  if (b) {
    for (const d of b.estagios) {
      const sug = infoEstagio(d.sugerido?.estagio).ordem;
      const dec = d.declarado ? infoEstagio(d.declarado.estagio).ordem : 0;
      if (sug >= 1 && sug > dec)
        s.push(
          `${nomeCurto(d.territorio_nome)}: o sistema sugere ${
            infoEstagio(d.sugerido.estagio).rotulo
          }, acima do declarado.`,
        );
    }
    if (b.chuva.chuva_prev_24h_mm !== null)
      s.push(
        `Maior chuva prevista em 24 h: ${formatarMm(b.chuva.chuva_prev_24h_mm)}${
          b.chuva.chuva_prev_24h_territorio ? ` no ${nomeCurto(b.chuva.chuva_prev_24h_territorio)}` : ""
        }.`,
      );
    if (b.mare.maxima_m !== null)
      s.push(
        `Maré mais alta: ${formatarNumero(b.mare.maxima_m, 2)} m${
          b.mare.maxima_em ? `, ${quandoAs(b.mare.maxima_em)}` : ""
        }.`,
      );
  }
  for (const a of saude?.agravos ?? []) {
    if (a.nivel_alerta && a.nivel_alerta >= 2)
      s.push(`${a.nome}: ${NIVEL_ALERTA[a.nivel_alerta].rotulo.toLowerCase()} no InfoDengue.`);
    else if (a.variacao_4s_pct !== null && a.variacao_4s_pct >= 10)
      s.push(`${a.nome}: casos subiram ${formatarNumero(a.variacao_4s_pct)}% em 4 semanas.`);
  }
  if (emAndamento > 0)
    s.push(`${emAndamento} ${emAndamento === 1 ? "ação em andamento" : "ações em andamento"}.`);
  return s.slice(0, 6);
}
