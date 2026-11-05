import { useMemo } from "react";
import { ErroApi } from "@/lib/api";
import { useConsulta } from "@/lib/consultas";
import type { AbrigoPublico, RespostaAbrigosPublicos } from "./abrigosPublicos";

export interface Abrigos {
  itens: AbrigoPublico[];
  carregando: boolean;
  /** 404: a lista ainda não existe. Tentar de novo só atrasaria a mensagem honesta. */
  indisponivel: boolean;
  erro: boolean;
  atualizadoEm?: string | null;
  aviso?: string | null;
  refazer: () => void;
}

/** Uma única consulta de abrigos para a página inteira (resultado da busca, aba Abrigos e mapa). */
export function useAbrigos(): Abrigos {
  const r = useConsulta<RespostaAbrigosPublicos>("/publico/abrigos", {
    staleTime: 60_000,
    retry: (n, e) => !(e instanceof ErroApi && e.status === 404) && n < 1,
  });
  const itens = useMemo(() => r.data?.itens ?? [], [r.data]);
  const indisponivel = r.isError && r.error instanceof ErroApi && r.error.status === 404;
  return {
    itens,
    carregando: r.isPending,
    indisponivel,
    erro: r.isError && !indisponivel,
    atualizadoEm: r.data?.atualizado_em,
    aviso: r.data?.aviso,
    refazer: () => void r.refetch(),
  };
}
