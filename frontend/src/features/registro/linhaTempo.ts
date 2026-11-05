/**
 * Linha do tempo do evento: junta os registros da equipe (/acoes), as declarações de situação (/estagios/historico)
 * e os boletins emitidos. Enquanto o backend não tem “evento” nem “boletim emitido” próprios, os dois viram registros
 * de /acoes com um texto fixo no começo (ver PREFIXO_BOLETIM e ENCERRAMENTO).
 */
import { infoEstagio } from "@/features/evento/estagios";
import { nomeCurto } from "@/features/evento/textos";
import type { Acao } from "@/features/evento/tipos";

export const PREFIXO_BOLETIM = "Boletim emitido:";
export const ENCERRAMENTO = "Evento encerrado.";

export interface Declaracao {
  id?: string;
  lote_id?: string | null;
  territorio_id?: string;
  territorio_nome?: string;
  estagio: string;
  justificativa?: string | null;
  autor_nome?: string | null;
  declarado_em: string;
}

export type TipoEntrada = "registro" | "situacao" | "boletim" | "encerramento";

export interface Entrada {
  id: string;
  em: string;
  tipo: TipoEntrada;
  texto: string;
  autor?: string | null;
  territorio?: string | null;
  estagio?: string;
  licao?: string | null;
}

const momento = (a: Acao) => a.inicio_em ?? a.criada_em ?? a.atualizada_em ?? "";

function deAcao(a: Acao): Entrada {
  const d = a.descricao ?? "";
  const tipo: TipoEntrada = d.startsWith(PREFIXO_BOLETIM)
    ? "boletim"
    : d.startsWith(ENCERRAMENTO)
      ? "encerramento"
      : "registro";
  const geral = !a.territorio_id || a.territorio_id === "recife";
  return {
    id: `acao-${a.id}`,
    em: momento(a),
    tipo,
    texto: tipo === "boletim" ? d.slice(PREFIXO_BOLETIM.length).trim() : d,
    autor: a.autor_nome,
    territorio: geral ? null : a.territorio_nome ?? a.territorio_id,
    licao: a.licao_aprendida,
  };
}

/** Declarações feitas juntas (mesmo lote) viram uma linha só, com os territórios em lista. */
function deDeclaracoes(lista: Declaracao[]): Entrada[] {
  const lotes = new Map<string, Declaracao[]>();
  for (const d of lista) {
    const k = d.lote_id ?? d.id ?? `${d.declarado_em}-${d.territorio_id}`;
    lotes.set(k, [...(lotes.get(k) ?? []), d]);
  }
  return [...lotes.entries()].map(([k, ds]) => {
    const d = ds[0];
    const nomes = ds.map((x) => nomeCurto(x.territorio_nome ?? x.territorio_id ?? "território"));
    const onde = nomes.length > 3 ? `${nomes.length} territórios` : nomes.join(", ");
    const retirada = d.estagio === "encerrado";
    return {
      id: `sit-${k}`,
      em: d.declarado_em,
      tipo: "situacao" as const,
      texto: retirada
        ? `${onde}: declaração retirada.${d.justificativa ? ` “${d.justificativa}”` : ""}`
        : `${onde} em ${infoEstagio(d.estagio).rotulo}.${d.justificativa ? ` “${d.justificativa}”` : ""}`,
      autor: d.autor_nome,
      estagio: d.estagio,
    };
  });
}

/** Tudo em ordem do mais recente para o mais antigo. */
export function montarLinha(acoes: Acao[], declaracoes: Declaracao[]): Entrada[] {
  return [...acoes.map(deAcao), ...deDeclaracoes(declaracoes)]
    .filter((e) => e.em)
    .sort((a, b) => b.em.localeCompare(a.em));
}

/** Separa o evento atual (depois do último encerramento) dos encerramentos anteriores. */
export function eventoAtual(linha: Entrada[]): { atual: Entrada[]; encerrados: Entrada[] } {
  const i = linha.findIndex((e) => e.tipo === "encerramento");
  return {
    atual: i < 0 ? linha : linha.slice(0, i),
    encerrados: linha.filter((e) => e.tipo === "encerramento"),
  };
}
