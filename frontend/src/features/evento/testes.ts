/**
 * Apoio dos testes das telas do evento de chuva: um `fetch` falso por caminho (o mais longo que casa vence; sem
 * caminho, 404 como o backend ainda sem o endpoint) e itens de exemplo no formato do contrato (specs §4).
 * Só é importado por arquivos *.test.tsx.
 */
import type { ItemEstagio } from "./tipos";

export interface Pedido {
  url: string;
  metodo: string;
  corpo: unknown;
}

type Resposta = unknown | { status: number; corpo?: unknown };
const ehStatus = (r: unknown): r is { status: number; corpo?: unknown } =>
  typeof r === "object" &&
  r !== null &&
  "status" in r &&
  typeof (r as { status: unknown }).status === "number";

export const AGORA = new Date().toISOString();

export function usuarioTeste(permissoes: string[] = ["consultar", "editar"], papeis = ["analista"]) {
  return {
    id: "00000000-0000-0000-0000-000000000001",
    nome: "Mari Siqueira",
    email: "m@x.br",
    papeis,
    permissoes,
    troca_senha_obrigatoria: false,
    expira_em: new Date(Date.now() + 3_600_000).toISOString(),
    ambiente: "producao",
    inatividade_min: 60,
  };
}

/** Troca o `fetch` global. Devolve a lista de pedidos feitos (para conferir POST/PATCH). */
export function simularApi(mapa: Record<string, Resposta>, metodos: Record<string, Resposta> = {}) {
  const pedidos: Pedido[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init?: RequestInit) => {
      const metodo = (init?.method ?? "GET").toUpperCase();
      const corpo = init?.body ? JSON.parse(String(init.body)) : undefined;
      pedidos.push({ url, metodo, corpo });
      const fonte = metodo === "GET" ? mapa : metodos;
      const chave = Object.keys(fonte)
        .sort((a, b) => b.length - a.length)
        .find((k) => url.includes(k));
      const r = chave === undefined ? { status: 404, corpo: { detail: "Não encontrado." } } : fonte[chave];
      const status = ehStatus(r) ? r.status : 200;
      const conteudo = ehStatus(r) ? (r.corpo ?? {}) : r;
      return new Response(status === 204 ? null : JSON.stringify(conteudo), { status });
    }),
  );
  return pedidos;
}

export function itemEstagio(
  p: Partial<ItemEstagio> & { territorio_id: string; territorio_nome: string },
): ItemEstagio {
  return {
    nivel: "distrito",
    distrito_id: null,
    sugerido: {
      estagio: "observacao",
      motivos: [],
      insumos: { chuva_24h_mm: 4, chuva_prev_24h_mm: 10, chuva_prev_72h_mm: 22, mare_max_m: 2.1 },
      calculado_em: AGORA,
    },
    declarado: null,
    ...p,
  };
}
