import { api, type Esquemas, ErroApi } from "@/lib/api";

type Execucao = Esquemas["Execucao"];
export const PRAZO_COLETA_MS = 30 * 60_000;

export async function apiComPrazo<T>(
  caminho: string,
  signal: AbortSignal,
  init: RequestInit = {},
): Promise<T> {
  const c = new AbortController();
  const cancelar = () => c.abort();
  signal.addEventListener("abort", cancelar, { once: true });
  if (signal.aborted) c.abort();
  const t = setTimeout(cancelar, 15_000);
  try {
    return await api<T>(caminho, { ...init, signal: c.signal });
  } finally {
    clearTimeout(t);
    signal.removeEventListener("abort", cancelar);
  }
}

/** Acompanhar não cancela a carga no servidor. Falhas de rede e execuções abandonadas têm limite explícito. */
export async function acompanhar(id: string, signal: AbortSignal): Promise<Execucao> {
  const fim = Date.now() + PRAZO_COLETA_MS;
  let falhas = 0;
  while (!signal.aborted && Date.now() < fim) {
    try {
      const e = await apiComPrazo<Execucao>(`/etl/execucoes/${id}`, signal);
      falhas = 0;
      if (e.status !== "em_andamento") return e;
    } catch (erro) {
      if (signal.aborted) throw erro;
      falhas++;
      if (falhas >= 3 || (erro instanceof ErroApi && [401, 403, 404].includes(erro.status)))
        throw new Error("Não foi possível acompanhar a coleta. Consulte o histórico antes de repetir.");
    }
    await new Promise<void>((resolve) => {
      const encerrar = () => {
        clearTimeout(t);
        signal.removeEventListener("abort", encerrar);
        resolve();
      };
      const t = setTimeout(encerrar, 3000);
      signal.addEventListener("abort", encerrar, { once: true });
    });
  }
  throw new Error(
    "Acompanhamento encerrado. A coleta pode continuar no servidor; consulte o histórico antes de repetir.",
  );
}
