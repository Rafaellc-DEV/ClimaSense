/** Consultas da API com TanStack Query: cache, carregamento e erro com a mensagem da própria API. */
import { useQuery, type UseQueryOptions } from "@tanstack/react-query";
import { api, type ErroApi } from "./api";

export function useConsulta<T>(
  caminho: string | null,
  opcoes: Omit<UseQueryOptions<T, ErroApi>, "queryKey" | "queryFn"> = {},
) {
  return useQuery<T, ErroApi>({
    queryKey: [caminho],
    queryFn: () => api<T>(caminho as string),
    enabled: caminho !== null && (opcoes.enabled ?? true),
    ...opcoes,
  });
}

/** Intervalos de atualização automática (RF-10, RNF-05). */
export const INTERVALO = { vivo: 60_000, saude: 600_000 } as const;

/**
 * Consulta que se renova sozinha, sem recarregar a página. Pausa com a aba oculta e, ao voltar a ela, busca de novo
 * se o dado já passou do tempo.
 */
export function useConsultaViva<T>(
  caminho: string | null,
  intervalo: number = INTERVALO.vivo,
  opcoes: Omit<UseQueryOptions<T, ErroApi>, "queryKey" | "queryFn"> = {},
) {
  return useConsulta<T>(caminho, {
    refetchInterval: intervalo,
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: true,
    staleTime: Math.min(intervalo, 30_000),
    ...opcoes,
  });
}

/** Momento da última resposta bem-sucedida entre várias consultas (0 se nenhuma ainda). */
export function ultimaAtualizacao(...consultas: { dataUpdatedAt: number }[]): number {
  return Math.max(0, ...consultas.map((c) => c.dataUpdatedAt));
}
