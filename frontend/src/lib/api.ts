/** Cliente HTTP da API /api/v1: cookies de sessão, cabeçalho CSRF e erros em problem+json (design §6). */
import { QueryClient } from "@tanstack/react-query";
import type { components } from "./api-tipos";

export type Esquemas = components["schemas"];

export class ErroApi extends Error {
  constructor(
    public status: number,
    mensagem: string,
    public titulo?: string,
  ) {
    super(mensagem);
  }
}

/** Mensagem da API quando não há `detail` (sem rede, resposta vazia). */
export const SEM_CONEXAO = "Não foi possível falar com o ClimaSense. Verifique a conexão e tente de novo.";

function csrf(): string {
  return (
    document.cookie
      .split("; ")
      .find((c) => c.startsWith("cs_csrf="))
      ?.slice(8) ?? ""
  );
}

/** Horário da última conversa autenticada com a API: a sessão expira 60 min depois (RF-02.5). */
let ultimaAtividade = Date.now();
const ouvintes401 = new Set<() => void>();

export function momentoUltimaAtividade() {
  return ultimaAtividade;
}

/** Avisa quando a API diz que a sessão acabou (401), para a interface levar ao login. */
export function aoSessaoTerminar(ouvinte: () => void) {
  ouvintes401.add(ouvinte);
  return () => {
    ouvintes401.delete(ouvinte);
  };
}

export async function api<T>(caminho: string, init: RequestInit = {}): Promise<T> {
  const metodo = (init.method ?? "GET").toUpperCase();
  const cabecalhos = new Headers(init.headers);
  if (init.body) cabecalhos.set("Content-Type", "application/json");
  if (metodo !== "GET") cabecalhos.set("X-CSRF-Token", decodeURIComponent(csrf()));
  let r: Response;
  try {
    r = await fetch(`/api/v1${caminho}`, { ...init, headers: cabecalhos, credentials: "same-origin" });
  } catch {
    throw new ErroApi(0, SEM_CONEXAO);
  }
  if (!caminho.startsWith("/publico")) ultimaAtividade = Date.now();
  if (r.status === 204 || r.status === 304) return undefined as T;
  const corpo = await r.json().catch(() => null);
  if (!r.ok) {
    if (r.status === 401 && !caminho.startsWith("/auth/eu") && !caminho.startsWith("/auth/entrar"))
      ouvintes401.forEach((o) => o());
    throw new ErroApi(
      r.status,
      corpo?.detail ?? corpo?.title ?? "Algo deu errado. Tente de novo.",
      corpo?.title,
    );
  }
  return corpo as T;
}

export function enviar<T>(caminho: string, corpo?: unknown, metodo = "POST"): Promise<T> {
  return api<T>(caminho, { method: metodo, body: corpo === undefined ? undefined : JSON.stringify(corpo) });
}

/** Monta a query string sem parâmetros vazios. */
export function consulta(parametros: Record<string, string | number | null | undefined>): string {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(parametros))
    if (v !== null && v !== undefined && v !== "") p.set(k, String(v));
  const s = p.toString();
  return s ? `?${s}` : "";
}

export const clienteConsultas = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60_000,
      refetchOnWindowFocus: false,
      // 401 e 403 não melhoram tentando de novo
      retry: (n, erro) => !(erro instanceof ErroApi && [401, 403, 404, 422].includes(erro.status)) && n < 1,
    },
  },
});
