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
