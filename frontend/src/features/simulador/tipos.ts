/**
 * Tipos e regras do Simulador de cenário (RF-23 a RF-28, RN-06, RN-11, RNF-09).
 *
 * O contrato de `/cenarios` nasce no backend em paralelo: todo campo que ele não garante é opcional e o que não for
 * entendido vira "sem dado", nunca "baixo" nem "seguro" (RN-01). Classe é ordinal, nunca percentual (RN-06).
 */
import type { ChaveNivel } from "@/design-system/niveis";
import { formatarNumero } from "@/lib/formatos";

export const CAMPOS_NUMERICOS = ["chuva_prevista_mm", "duracao_h", "chuva_acumulada_mm", "mare_m"] as const;
export type CampoNumerico = (typeof CAMPOS_NUMERICOS)[number];

export const HORIZONTES = [6, 12, 24, 72] as const;
export const DURACOES = [1, 3, 6, 12, 24, 48, 72] as const;
export const HORIZONTE_PADRAO = 24;

/** O que a API aceita e devolve: cada campo pode ser nulo (sem dado). */
export interface Premissas {
  chuva_prevista_mm: number | null;
  duracao_h: number | null;
  chuva_acumulada_mm: number | null;
  mare_m: number | null;
  horizonte_h: number | null;
}

/** O formulário guarda texto: vazio = sem dado (nunca zero). */
export type Formulario = Record<CampoNumerico, string> & { horizonte_h: number };

export type ClasseArbovirose = "baixa" | "media" | "alta";

export interface PontoSemanalArbovirose {
  ano: number;
  semana: number;
  inicio: string;
  casos: number | null;
  suprimido: boolean;
  incompleta: boolean;
  nivel_alerta?: number | null;
}

export interface AgravoDistrito {
  agravo: string;
  nome: string;
  semana_recente: PontoSemanalArbovirose | null;
  ano_distrito: number | null;
  casos_ano_distrito: number | null;
  casos_ano_suprimido: boolean;
  classe_impacto: ClasseArbovirose | null;
  dados_insuficientes: boolean;
  motivo: string | null;
  fonte_semanal?: string | null;
  fonte_anual?: string | null;
}

/** Arboviroses de um distrito no cenário: contexto, nunca previsão causal. Nos bairros vem `null`. */
export interface ArbovirosesDistrito {
  agravos: AgravoDistrito[];
  classe_impacto: ClasseArbovirose | null;
  agravos_em_destaque: string[];
}

export interface OrdemDistrito {
  distrito_id: string;
  nome: string;
  estagio_sugerido?: string | null;
  classe_arboviroses: ClasseArbovirose | null;
  agravos_em_destaque: string[];
}

export interface ResumoArboviroses {
  experimental?: boolean;
  contexto?: boolean;
  aviso?: string | null;
  granularidade_semanal?: string | null;
  granularidade_anual?: string | null;
  fontes?: { id: string; nome: string; atualizado_em: string | null; status: string }[] | null;
}

export interface ItemSimulado {
  territorio_id: string;
  nome: string;
  nivel?: string | null;
  distrito_id?: string | null;
  classe_alagamento?: string | null;
  classe_deslizamento?: string | null;
  estagio_sugerido?: string | null;
  confianca?: string | null;
  motivos?: string[] | null;
  impacto_pessoas?: unknown;
  arboviroses?: ArbovirosesDistrito | null;
}

export interface ResultadoSimulacao {
  itens: ItemSimulado[];
  resumo?: {
    por_classe?: Record<string, number> | null;
    impacto_pessoas_aviso?: string | null;
    ordem_de_atencao_distritos?: OrdemDistrito[] | null;
    arboviroses?: ResumoArboviroses | null;
    pessoas_vulneraveis_em_alerta?: unknown;
  } | null;
  experimental?: boolean;
  calculado_em?: string | null;
  tempo_calculo_ms?: number | null;
}

export interface CenarioSalvo {
  id: string;
  nome: string;
  criado_em?: string | null;
  criado_por?: string | null;
  premissas?: Partial<Premissas> | null;
}

export type Visao = "alagamento" | "deslizamento" | "situacao";
export const VISOES: { valor: Visao; rotulo: string; campo: keyof ItemSimulado }[] = [
  { valor: "alagamento", rotulo: "Alagamento", campo: "classe_alagamento" },
  { valor: "deslizamento", rotulo: "Deslizamento", campo: "classe_deslizamento" },
  { valor: "situacao", rotulo: "Situação sugerida", campo: "estagio_sugerido" },
];

/** Classes em ordem crescente. Qualquer outra coisa (inclusive `sem_dados`) é falta de dado. */
export const CLASSES = ["observacao", "atencao", "alerta", "critico"] as const;
export const ROTULO_CLASSE = ["Observação", "Atenção", "Alerta", "Crítico"];
export const NIVEL_CLASSE: ChaveNivel[] = ["informativo", "atencao", "alerta", "critico"];

/** 0 a 3, ou `null` quando não há classe reconhecida. */
export function ordemDaClasse(classe: unknown): number | null {
  const i = CLASSES.indexOf(String(classe ?? "").toLowerCase() as (typeof CLASSES)[number]);
  return i >= 0 ? i : null;
}

export function classeDoItem(item: ItemSimulado | undefined, visao: Visao): number | null {
  if (!item) return null;
  const campo = VISOES.find((v) => v.valor === visao)!.campo;
  return ordemDaClasse(item[campo]);
}

export const ehNumero = (v: unknown): v is number => typeof v === "number" && Number.isFinite(v);

/** Valor do formulário a partir do que a API trouxe. Sem dado fica vazio. */
export function deAtuais(p: Partial<Premissas> | null | undefined): Formulario {
  const texto = (v: unknown) => (ehNumero(v) ? String(v).replace(".", ",") : "");
  const h = ehNumero(p?.horizonte_h) ? p.horizonte_h : HORIZONTE_PADRAO;
  const horizonte = HORIZONTES.reduce((a, b) => (Math.abs(b - h) < Math.abs(a - h) ? b : a));
  return {
    chuva_prevista_mm: texto(p?.chuva_prevista_mm),
    duracao_h: texto(p?.duracao_h),
    chuva_acumulada_mm: texto(p?.chuva_acumulada_mm),
    mare_m: texto(p?.mare_m),
    horizonte_h: horizonte,
  };
}

/** Lê um campo de texto: `null` = vazio, `"invalido"` = não é número válido. */
export function lerNumero(t: string): number | null | "invalido" {
  const s = t.trim().replace(",", ".");
  if (s === "") return null;
  const n = Number(s);
  return Number.isFinite(n) ? n : "invalido";
}

const MINIMO: Record<CampoNumerico, number | null> = {
  chuva_prevista_mm: 0,
  duracao_h: 0,
  chuva_acumulada_mm: 0,
  mare_m: null, // a maré pode ser negativa
};

export function erroDoCampo(campo: CampoNumerico, t: string): string | undefined {
  const n = lerNumero(t);
  if (n === "invalido") return "Digite só números, por exemplo 62 ou 2,4.";
  const min = MINIMO[campo];
  if (n !== null && min !== null && n < min) return "Use um valor igual ou maior que zero.";
  return undefined;
}

/** Premissas prontas para enviar, ou `null` se algum campo está inválido ou tudo está sem dado. */
export function paraPremissas(f: Formulario): Premissas | null {
  const saida: Partial<Premissas> = { horizonte_h: f.horizonte_h };
  for (const c of CAMPOS_NUMERICOS) {
    if (erroDoCampo(c, f[c])) return null;
    saida[c] = lerNumero(f[c]) as number | null;
  }
  return saida as Premissas;
}

export function temAlgumDado(p: Premissas): boolean {
  return CAMPOS_NUMERICOS.some((c) => p[c] !== null);
}

/** O cálculo exige a chuva prevista e a duração; acumulada e maré podem faltar (RN-01). */
export function podeSimular(p: Premissas): boolean {
  return p.chuva_prevista_mm !== null && p.duracao_h !== null;
}

const plural = (n: number, s: string, p: string) => `${formatarNumero(n)} ${n === 1 ? s : p}`;

/** Contagem de bairros por classe na visão escolhida. `sem` = sem dado. */
export function contar(itens: ItemSimulado[], visao: Visao) {
  const por = [0, 0, 0, 0];
  let sem = 0;
  for (const i of itens) {
    const o = classeDoItem(i, visao);
    if (o === null) sem += 1;
    else por[o] += 1;
  }
  return { por, sem };
}

/** "Com 80 mm em 24 h e maré de 2,4 m: 12 bairros em alerta ou acima, 30 em atenção." Sem dado nunca vira "tudo bem". */
export function fraseResumo(p: Premissas, itens: ItemSimulado[], visao: Visao): string {
  const { por, sem } = contar(itens, visao);
  const partes: string[] = [];
  if (p.chuva_prevista_mm !== null)
    partes.push(
      `${formatarNumero(p.chuva_prevista_mm, p.chuva_prevista_mm % 1 ? 1 : 0)} mm${
        p.duracao_h !== null ? ` em ${formatarNumero(p.duracao_h, p.duracao_h % 1 ? 1 : 0)} h` : ""
      }`,
    );
  if (p.mare_m !== null) partes.push(`maré de ${formatarNumero(p.mare_m, 1)} m`);
  const abertura = partes.length ? `Com ${partes.join(" e ")}: ` : "Neste cenário: ";
  const alertaOuMais = por[2] + por[3];
  const contagens: string[] = [];
  contagens.push(`${plural(alertaOuMais, "bairro", "bairros")} em alerta ou acima`);
  if (por[1] > 0) contagens.push(`${formatarNumero(por[1])} em atenção`);
  if (por[0] > 0) contagens.push(`${formatarNumero(por[0])} em observação`);
  if (sem > 0) contagens.push(`${formatarNumero(sem)} sem dados`);
  return `${abertura}${contagens.join(", ")}.`;
}

export function formatarSegundos(ms: number): string {
  if (ms < 100) return "menos de 0,1 s";
  return `${formatarNumero(ms / 1000, 1)} s`;
}
