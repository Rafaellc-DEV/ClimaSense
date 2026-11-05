/**
 * Abrigos para a população (landing, “Onde encontrar abrigo”). Contrato de `GET /api/v1/publico/abrigos`, escrito
 * pelo agente de ETL em paralelo; quando entrar no OpenAPI, troque por `Esquemas[...]`.
 *
 * Regra de ouro: “Aberto agora” só aparece quando `aberto === true` E há quem informou (COP ou equipe). Qualquer
 * outra coisa vira “abertura não confirmada”: um local cadastrado não é um abrigo aberto.
 */
import { quandoRelativo } from "@/lib/formatos";

export type TipoAbrigo = "abrigo_temporario" | "ponto_apoio" | "cras" | "outro";

export interface AbrigoPublico {
  id: string | number;
  nome: string;
  endereco?: string | null;
  bairro_nome?: string | null;
  distrito_nome?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  /** true só quando alguém informou que está aberto; null = não se sabe. */
  aberto?: boolean | null;
  /** Quem informou a abertura: o feed do COP ou a equipe. */
  aberto_fonte?: "cop" | "equipe" | null;
  /** Quando a abertura foi lida/informada. */
  aberto_lido_em?: string | null;
  capacidade?: number | null;
  tipo?: TipoAbrigo | string | null;
  atualizado_em?: string | null;
  origem?: string | null;
  fonte_url?: string | null;
}

export interface RespostaAbrigosPublicos {
  itens: AbrigoPublico[];
  atualizado_em?: string | null;
  aviso?: string | null;
}

/** Filtro de tipo da lista. O CRAS é assistência social, não abrigo: fica num filtro à parte. */
export type FiltroTipo = "abrigos" | "cras" | "todos";

export const ROTULO_TIPO: Record<string, string> = {
  abrigo_temporario: "Abrigo temporário",
  ponto_apoio: "Ponto de apoio",
  cras: "Assistência social (CRAS)",
  outro: "Local de apoio",
};

export function rotuloTipo(t: string | null | undefined) {
  return ROTULO_TIPO[t ?? "outro"] ?? ROTULO_TIPO.outro;
}

export const ehCras = (a: AbrigoPublico) => a.tipo === "cras";

/** Aberto confirmado: o único caso em que a página diz “Aberto agora”. */
export function abertoConfirmado(a: AbrigoPublico) {
  return a.aberto === true;
}

/** “informado pela Defesa Civil (COP do Recife), hoje, 14h10” ou “informado pela equipe, hoje, 14h10”. Sem hora, diz só quem informou. */
export function quemInformou(a: AbrigoPublico, agora?: Date): string {
  const quem =
    a.aberto_fonte === "cop"
      ? "informado pela Defesa Civil (COP do Recife)"
      : a.aberto_fonte === "equipe"
        ? "informado pela Vigilância em Saúde"
        : "segundo o cadastro";
  return a.aberto_lido_em ? `${quem}, ${quandoRelativo(a.aberto_lido_em, agora)}` : quem;
}

/** Sem acento e em minúsculas, para a busca achar “Varzea” em “Várzea”. */
export function normalizar(t: string) {
  return t.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().trim();
}

export function filtrar(itens: AbrigoPublico[], tipo: FiltroTipo, soAbertos: boolean) {
  return itens
    .filter((a) => (tipo === "todos" ? true : tipo === "cras" ? ehCras(a) : !ehCras(a)))
    .filter((a) => !soAbertos || abertoConfirmado(a))
    .sort(
      (a, b) =>
        Number(abertoConfirmado(b)) - Number(abertoConfirmado(a)) ||
        (a.bairro_nome ?? "").localeCompare(b.bairro_nome ?? "", "pt-BR") ||
        a.nome.localeCompare(b.nome, "pt-BR"),
    );
}

const coordenadaValida = (a: AbrigoPublico) =>
  typeof a.latitude === "number" &&
  typeof a.longitude === "number" &&
  Number.isFinite(a.latitude) &&
  Number.isFinite(a.longitude);

export function temCoordenada(
  a: AbrigoPublico,
): a is AbrigoPublico & { latitude: number; longitude: number } {
  return coordenadaValida(a);
}

/** Rota no Google Maps pela coordenada; sem coordenada, pelo endereço. Nada de link quebrado. */
export function linkComoChegar(a: AbrigoPublico): string | null {
  if (temCoordenada(a))
    return `https://www.google.com/maps/dir/?api=1&destination=${a.latitude},${a.longitude}`;
  if (a.endereco)
    return `https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(
      [a.endereco, a.bairro_nome, "Recife, PE"].filter(Boolean).join(", "),
    )}`;
  return null;
}

/** Mesmo lugar no OpenStreetMap, para quem não usa Google. */
export function linkOsm(a: AbrigoPublico): string | null {
  if (!temCoordenada(a)) return null;
  return `https://www.openstreetmap.org/?mlat=${a.latitude}&mlon=${a.longitude}#map=18/${a.latitude}/${a.longitude}`;
}

/** Só links https saem da página (o dado vem de fonte externa). */
export function linkSeguro(u: string | null | undefined): string | null {
  return u && /^https:\/\//.test(u) ? u : null;
}

/** Distância em linha reta (haversine), em km. */
export function distanciaKm(de: { lat: number; lon: number }, para: { lat: number; lon: number }) {
  const rad = (g: number) => (g * Math.PI) / 180;
  const dLat = rad(para.lat - de.lat);
  const dLon = rad(para.lon - de.lon);
  const h =
    Math.sin(dLat / 2) ** 2 + Math.cos(rad(de.lat)) * Math.cos(rad(para.lat)) * Math.sin(dLon / 2) ** 2;
  return 2 * 6371 * Math.asin(Math.sqrt(h));
}

/** “450 m” abaixo de 1 km; “1,2 km” acima. */
export function formatarDistancia(km: number) {
  return km < 1 ? `${Math.round(km * 100) * 10} m` : `${km.toFixed(1).replace(".", ",")} km`;
}

/** Local do resultado “perto de você”: com a distância real, em linha reta, desde a posição da pessoa. */
export interface LocalComDistancia {
  abrigo: AbrigoPublico;
  km: number;
}

/** Abrigos (sem CRAS) mais perto de um ponto, só os que têm coordenada. Nada de distância inventada. */
export function maisPertoDe(itens: AbrigoPublico[], ponto: { lat: number; lon: number }, max = 3) {
  return itens
    .filter((a) => !ehCras(a) && temCoordenada(a))
    .map((a) => ({ abrigo: a, km: distanciaKm(ponto, { lat: a.latitude!, lon: a.longitude! }) }))
    .sort((x, y) => x.km - y.km)
    .slice(0, max);
}

export type Proximidade = "bairro" | "distrito" | "outro";

/**
 * “Abrigos perto de <bairro>”: primeiro os do mesmo bairro, depois os do mesmo distrito sanitário, depois os demais.
 * Dentro de cada grupo, abertos confirmados primeiro e depois por distância ao centro dos abrigos do próprio bairro
 * (ou do distrito) quando houver coordenada. Sem coordenada de referência, não se ordena nem se mostra distância.
 */
export function pertoDoBairro(itens: AbrigoPublico[], bairro: string, distritoNome: string | null) {
  const b = normalizar(bairro);
  const d = distritoNome ? normalizar(distritoNome) : null;
  const grupo = (a: AbrigoPublico): Proximidade =>
    a.bairro_nome && normalizar(a.bairro_nome) === b
      ? "bairro"
      : d && a.distrito_nome && normalizar(a.distrito_nome) === d
        ? "distrito"
        : "outro";
  const base = itens.filter((a) => !ehCras(a)).map((a) => ({ abrigo: a, grupo: grupo(a) }));
  const centro = (g: Proximidade) => {
    const pts = base.filter((x) => x.grupo === g && temCoordenada(x.abrigo)).map((x) => x.abrigo);
    return pts.length
      ? {
          lat: pts.reduce((s, a) => s + a.latitude!, 0) / pts.length,
          lon: pts.reduce((s, a) => s + a.longitude!, 0) / pts.length,
        }
      : null;
  };
  const ref = centro("bairro") ?? centro("distrito");
  const ordem = { bairro: 0, distrito: 1, outro: 2 } as const;
  const dist = (a: AbrigoPublico) =>
    ref && temCoordenada(a) ? distanciaKm(ref, { lat: a.latitude, lon: a.longitude }) : Infinity;
  return base.sort(
    (x, y) =>
      ordem[x.grupo] - ordem[y.grupo] ||
      Number(abertoConfirmado(y.abrigo)) - Number(abertoConfirmado(x.abrigo)) ||
      dist(x.abrigo) - dist(y.abrigo) ||
      x.abrigo.nome.localeCompare(y.abrigo.nome, "pt-BR"),
  );
}
