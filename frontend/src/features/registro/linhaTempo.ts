/**
 * Linha do tempo do evento: junta os registros da equipe (/acoes), as declarações de situação (/estagios/historico)
 * e os boletins emitidos. Enquanto o backend não tem “evento” nem “boletim emitido” próprios, os dois viram registros
 * de /acoes com um texto fixo no começo (ver PREFIXO_BOLETIM e ENCERRAMENTO).
 */
import { diaNoRecife, formatarHora } from "@/lib/formatos";
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
  /** Quando a pessoa registrou, se for bem depois do fato (`em`). */
  registradoEm?: string | null;
}

/** Dia e hora digitados (fuso do Recife, UTC-3, sem horário de verão) viram ISO. Vazio ou inválido: null. */
export function isoDeDiaHora(dia: string, hora: string): string | null {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(dia) || !/^\d{2}:\d{2}$/.test(hora)) return null;
  const d = new Date(`${dia}T${hora}:00-03:00`);
  return Number.isNaN(d.getTime()) ? null : d.toISOString();
}

/** Valores iniciais dos campos Dia e Hora: agora, no fuso do Recife. */
export function agoraNoRecife(agora: Date = new Date()): { dia: string; hora: string } {
  return { dia: diaNoRecife(agora), hora: formatarHora(agora).replace("h", ":") };
}

const MARGEM_REGISTRO_MS = 10 * 60 * 1000;

const momento = (a: Acao) => a.inicio_em ?? a.criada_em ?? a.atualizada_em ?? "";

function deAcao(a: Acao): Entrada {
  const d = a.descricao ?? "";
  const tipo: TipoEntrada = d.startsWith(PREFIXO_BOLETIM)
    ? "boletim"
    : d.startsWith(ENCERRAMENTO)
      ? "encerramento"
      : "registro";
  const fato = momento(a);
  const feito = a.criada_em ?? null;
  const tardio = !!feito && !!a.inicio_em && Date.parse(feito) - Date.parse(fato) > MARGEM_REGISTRO_MS;
  const geral = !a.territorio_id || a.territorio_id === "recife";
  return {
    id: `acao-${a.id}`,
    em: fato,
    tipo,
    registradoEm: tardio ? feito : null,
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
