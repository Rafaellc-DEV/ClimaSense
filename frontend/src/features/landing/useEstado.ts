import type { Esquemas } from "@/lib/api";
import { useConsulta } from "@/lib/consultas";

export type EstadoPublico = Esquemas["EstadoPublico"];
export type AvisoPublico = Esquemas["AvisoPublico"];

export type Situacao = { tipo: "carregando" } | { tipo: "erro" } | { tipo: "ok"; estado: EstadoPublico };

/** Estado público dos avisos. Uma falha vira “não foi possível verificar”, nunca “sem aviso” (RN-01). */
export function useEstado(): Situacao {
  const r = useConsulta<EstadoPublico>("/publico/estado", { refetchInterval: 120_000, retry: 1 });
  if (r.isPending) return { tipo: "carregando" };
  if (r.isError) return { tipo: "erro" };
  return { tipo: "ok", estado: r.data };
}

export function useAvisos(bairro?: string) {
  return useConsulta<AvisoPublico[]>(
    `/publico/avisos${bairro ? `?bairro=${encodeURIComponent(bairro)}` : ""}`,
    {
      refetchInterval: 120_000,
    },
  );
}
