import { useEffect, useState } from "react";
import type { Esquemas } from "@/lib/api";
import { useConsulta } from "@/lib/consultas";

export type EstadoPublico = Esquemas["EstadoPublico"];
export type AvisoPublico = Esquemas["AvisoPublico"];

export type Situacao =
  | { tipo: "carregando"; tentandoDeNovo: boolean }
  | { tipo: "erro" }
  | { tipo: "ok"; estado: EstadoPublico };

/** A primeira consulta fica pelo menos este tempo em "verificando": uma resposta instantânea faz o texto piscar e
   uma falha rápida parece que nem tentou. Nos testes não há espera. */
const ESPERA_MINIMA_MS = import.meta.env.MODE === "test" ? 0 : 1500;

/** Estado público dos avisos. Uma falha vira “não foi possível verificar”, nunca “sem aviso” (RN-01). */
export function useEstado(): Situacao {
  const r = useConsulta<EstadoPublico>("/publico/estado", { refetchInterval: 120_000, retry: 1 });
  const [esperou, setEsperou] = useState(ESPERA_MINIMA_MS === 0);
  useEffect(() => {
    if (esperou) return;
    const t = setTimeout(() => setEsperou(true), ESPERA_MINIMA_MS);
    return () => clearTimeout(t);
  }, [esperou]);
  if (r.isPending || !esperou) return { tipo: "carregando", tentandoDeNovo: r.failureCount > 0 };
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
