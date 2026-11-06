/**
 * Camadas do mapa (RF-02, RF-03, RF-04, RF-26) e resumo de vulnerabilidade do bairro (RF-07, RF-25).
 *
 * Regras que valem aqui: sem dado nunca vira zero (RN-01); contagem pequena vem suprimida da API e aparece como
 * "< 5" (RNF-03); só contagens de residentes, nunca percentual (RN-06); nada que identifique pessoa (RN-13).
 */
import { formatarNumero } from "@/lib/formatos";

export type IdCamada = "base" | "populacao" | "areas" | "equipamentos" | "abrigos";

export const CAMINHO_CAMADA = {
  equipamentos: "/territorios/camadas/equipamentos-saude",
  populacao: "/territorios/camadas/vulneraveis",
  areas: "/territorios/camadas/areas-risco",
} as const;

/** Fonte de cada camada, usada quando a resposta não traz `meta.fontes`. */
export const FONTE_PADRAO: Record<Exclude<IdCamada, "base">, string> = {
  equipamentos: "CNES (Ministério da Saúde)",
  populacao: "IBGE, Censo 2022",
  areas: "Defesa Civil do Recife",
  abrigos: "Cadastro de abrigos (equipe e COP)",
};

export const ROTULO_CAMADA: Record<Exclude<IdCamada, "base">, string> = {
  equipamentos: "Equipamentos de saúde",
  populacao: "População vulnerável",
  areas: "Áreas de risco",
  abrigos: "Abrigos",
};

// ---------- população vulnerável
export type Indicador = "idosos_60_mais" | "idosos_70_mais" | "criancas_0_4" | "criancas_0_14";

export const INDICADORES: { valor: Indicador; rotulo: string }[] = [
  { valor: "idosos_60_mais", rotulo: "Idosos 60+" },
  { valor: "idosos_70_mais", rotulo: "Idosos 70+" },
  { valor: "criancas_0_4", rotulo: "Crianças 0–4" },
  { valor: "criancas_0_14", rotulo: "Crianças 0–14" },
];

export const AVISO_DEFICIENCIA = "Dados insuficientes: não há dado público por bairro";

export interface ItemVulneravel {
  bairro_id: string;
  nome?: string;
  distrito_id?: string | null;
  criancas_0_4?: number | null;
  criancas_0_14?: number | null;
  idosos_60_mais?: number | null;
  idosos_70_mais?: number | null;
  total?: number | null;
  suprimido?: Partial<Record<string, boolean>> | null;
  deficiencia?: null;
}

export interface ValorPopulacao {
  valor: number | null;
  suprimido: boolean;
}

export function valorDe(
  item:
    | (Partial<Record<Indicador, number | null>> & { suprimido?: Partial<Record<string, boolean>> | null })
    | undefined,
  ind: Indicador,
): ValorPopulacao {
  if (!item) return { valor: null, suprimido: false };
  const v = item[ind];
  return {
    valor: typeof v === "number" && Number.isFinite(v) ? v : null,
    suprimido: item.suprimido?.[ind] === true,
  };
}

/** "< 5" quando suprimido, o número quando há, "Dados insuficientes" quando não há (nunca 0). */
export function textoPessoas(v: ValorPopulacao): string {
  if (v.suprimido) return "< 5";
  if (v.valor === null) return "Dados insuficientes";
  return formatarNumero(v.valor);
}

/**
 * Cortes por quantis dos valores conhecidos: devolve até `n - 1` limites superiores crescentes, sem repetir.
 * A faixa i vai até o corte i (inclusive); a última não tem limite.
 */
export function cortes(valores: number[], n = 5): number[] {
  const v = valores.filter((x) => Number.isFinite(x)).sort((a, b) => a - b);
  if (v.length === 0) return [];
  const saida: number[] = [];
  for (let i = 1; i < n; i++) {
    const c = v[Math.min(v.length - 1, Math.floor((i * v.length) / n))];
    if (saida.length === 0 || c > saida[saida.length - 1]) saida.push(c);
  }
  // o último corte igual ao máximo criaria uma faixa vazia
  while (saida.length && saida[saida.length - 1] >= v[v.length - 1]) saida.pop();
  return saida;
}

/** Índice da faixa (0 a cortes.length) de um valor. */
export function faixaDe(valor: number, c: number[]): number {
  const i = c.findIndex((limite) => valor < limite);
  return i === -1 ? c.length : i;
}

/** Rótulos das faixas: "Até 1.200", "1.200 a 3.400", "3.400 ou mais". */
export function rotulosFaixas(c: number[], minimo: number): string[] {
  if (c.length === 0) return [`${formatarNumero(minimo)} ou mais`];
  const f = (n: number) => formatarNumero(n);
  return [
    `Menos de ${f(c[0])}`,
    ...c.slice(1).map((limite, i) => `${f(c[i])} a ${f(limite - 1)}`),
    `${f(c[c.length - 1])} ou mais`,
  ];
}

// ---------- equipamentos de saúde
export interface PropsEquipamento {
  cnes?: string | number | null;
  nome?: string | null;
  tipo?: string | null;
  esfera?: string | null;
  bairro_id?: string | null;
  distrito_id?: string | null;
}

export interface TipoEquip {
  chave: "hospital" | "urgencia" | "basica" | "ambulatorio" | "outro";
  rotulo: string;
  glifo: string;
}

const semAcento = (t: string) => t.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

/** Agrupa os tipos do CNES em poucas famílias, cada uma com ícone próprio (letra e forma, não só cor). */
export function tipoEquipamento(tipo: string | null | undefined): TipoEquip {
  const t = semAcento(tipo ?? "");
  if (t.includes("hospital")) return { chave: "hospital", rotulo: "Hospital", glifo: "H" };
  if (/\bupa\b|pronto|urgencia|emergencia/.test(t))
    return { chave: "urgencia", rotulo: "Urgência e emergência", glifo: "U" };
  if (/basica|posto|\bubs\b|saude da familia|centro de saude/.test(t))
    return { chave: "basica", rotulo: "Unidade básica", glifo: "+" };
  if (/policlinica|clinica|ambulatorio|especializ|diagnose|laborat/.test(t))
    return { chave: "ambulatorio", rotulo: "Ambulatório e clínica", glifo: "A" };
  return { chave: "outro", rotulo: "Outro serviço de saúde", glifo: "S" };
}

export const TIPOS_EQUIP: TipoEquip[] = [
  tipoEquipamento("hospital"),
  tipoEquipamento("upa"),
  tipoEquipamento("unidade básica"),
  tipoEquipamento("clínica"),
  tipoEquipamento(""),
];

// ---------- áreas de risco
export interface PropsAreaRisco {
  id?: string | number | null;
  tipo?: string | null;
  grau?: string | null;
  regional?: string | null;
  bairro_id?: string | null;
}

export interface CoberturaRisco {
  regionais_com_dado?: string[] | null;
  bairros_com_dado?: number | null;
  total_bairros?: number | null;
  parcial?: boolean | null;
  texto?: string | null;
}

/** Texto permanente da cobertura. Parcial nunca é omitido: bairro sem polígono não é bairro sem risco (RN-01). */
export function textoCobertura(c: CoberturaRisco | null | undefined): string | null {
  if (!c || c.parcial !== true) return null;
  const regionais = (c.regionais_com_dado ?? []).filter(Boolean);
  if (regionais.length) return `Cobertura parcial: só ${listaPt(regionais)}`;
  return c.texto ? `Cobertura parcial: ${c.texto}` : "Cobertura parcial";
}

export function listaPt(itens: string[]): string {
  if (itens.length <= 1) return itens[0] ?? "";
  return `${itens.slice(0, -1).join(", ")} e ${itens[itens.length - 1]}`;
}

export function rotuloTipoRisco(tipo: string | null | undefined): string {
  const t = (tipo ?? "").trim();
  if (!t) return "Tipo não informado";
  return t.charAt(0).toUpperCase() + t.slice(1).replace(/_/g, " ");
}

// ---------- resposta das camadas
export type Envelope = { dados?: unknown; meta?: Record<string, unknown> } & Record<string, unknown>;

const obj = (x: unknown): Record<string, unknown> | null =>
  x && typeof x === "object" && !Array.isArray(x) ? (x as Record<string, unknown>) : null;

/** `meta` da resposta, venha a camada como GeoJSON (meta no topo) ou como `{ dados, meta }`. */
export function metaDe(r: unknown): Record<string, unknown> {
  return obj(obj(r)?.meta) ?? {};
}

/** A resposta diz que não tem dado? Devolve a(s) fonte(s) que faltam ou `""` quando a API não disse qual. */
export function faltaDe(r: unknown): string | null {
  const o = obj(r);
  if (!o) return null;
  const meta = metaDe(r);
  const dados = obj(o.dados);
  const marcado = [o, meta, dados].some(
    (x) => x?.dados_insuficientes === true || x?.dados_insuficientes === "true",
  );
  if (!marcado) return null;
  for (const x of [o, meta, dados]) {
    for (const campo of ["fonte_faltante", "fontes_faltantes", "faltando", "fonte"]) {
      const v = x?.[campo];
      if (Array.isArray(v) && v.length) return v.map(String).join(", ");
      if (typeof v === "string" && v) return v;
    }
  }
  return "";
}

/** Features de uma resposta GeoJSON (direto ou dentro de `dados`). */
export function featuresDe<P>(r: unknown): GeoJSON.Feature<GeoJSON.Geometry, P>[] {
  const o = obj(r);
  const colecao = o?.type === "FeatureCollection" ? o : obj(o?.dados);
  const f = colecao?.features;
  return Array.isArray(f) ? (f as GeoJSON.Feature<GeoJSON.Geometry, P>[]) : [];
}

export function itensVulneraveis(r: unknown): ItemVulneravel[] {
  const d = obj(obj(r)?.dados);
  const i = d?.itens;
  return Array.isArray(i) ? (i as ItemVulneravel[]) : [];
}

// ---------- resumo do bairro
export interface ResumoVulnerabilidade {
  idosos_60_mais?: number | null;
  criancas_0_14?: number | null;
  suprimido?: Partial<Record<string, boolean>> | null;
  deficiencia?: null;
  equipamentos?: { cnes?: string | number | null; nome?: string | null; tipo?: string | null }[] | null;
  equipamentos_em_area_de_risco?: (string | number)[] | number | null;
  abrigos?: number | { nome?: string }[] | null;
  areas_risco?: number | null;
  cobertura_risco_parcial?: boolean | null;
}

/** Quantos equipamentos estão em área de risco, ou quais (por CNES). */
export function cnesEmRisco(r: ResumoVulnerabilidade | undefined): Set<string> {
  const v = r?.equipamentos_em_area_de_risco;
  return new Set(Array.isArray(v) ? v.map(String) : []);
}

// ---------- simulador: população exposta (RF-25)
export interface ImpactoPessoas {
  idosos_60_mais?: number | null;
  criancas_0_14?: number | null;
  equipamentos_saude?: number | null;
  deficiencia?: null;
  total_pessoas?: number | null;
  criterio?: string | null;
}

export function impactoDe(v: unknown): ImpactoPessoas | null {
  const o = obj(v);
  return o ? (o as ImpactoPessoas) : null;
}

/** Soma de residentes em bairros em alerta ou acima (`resumo.pessoas_vulneraveis_em_alerta`). */
export interface PessoasEmAlerta {
  bairros_em_alerta?: number | null;
  idosos_60_mais?: number | null;
  criancas_0_14?: number | null;
  /** `true` = algum bairro em alerta ficou sem número (sem dado ou suprimido): a soma é um mínimo. */
  parcial?: boolean | null;
  criterio?: string | null;
}

export function somaExposta(resumo: unknown): PessoasEmAlerta | null {
  const o = obj(obj(resumo)?.pessoas_vulneraveis_em_alerta);
  return o ? (o as PessoasEmAlerta) : null;
}
