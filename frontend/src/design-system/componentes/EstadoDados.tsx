import type { ReactNode } from "react";
import { CircleOff, Clock, TriangleAlert } from "lucide-react";
import { formatarDataHora } from "@/lib/formatos";
import estilos from "./EstadoDados.module.css";

export type TipoEstadoDados = "insuficiente" | "desatualizado" | "falha";

const PADRAO: Record<TipoEstadoDados, { titulo: string; icone: ReactNode }> = {
  insuficiente: { titulo: "Dados insuficientes", icone: <CircleOff aria-hidden="true" /> },
  desatualizado: { titulo: "Dados desatualizados", icone: <Clock aria-hidden="true" /> },
  falha: { titulo: "A fonte não respondeu", icone: <TriangleAlert aria-hidden="true" /> },
};

/**
 * Estado explícito dos dados (RN-01). É o único componente para esses casos:
 * a falta de informação nunca vira zero, "baixo" ou "normal".
 */
export function EstadoDados({
  tipo,
  titulo,
  children,
}: {
  tipo: TipoEstadoDados;
  titulo?: string;
  children?: ReactNode;
}) {
  const p = PADRAO[tipo];
  return (
    <div className={`${estilos.estado} ${estilos[tipo]}`} role="status" data-estado={tipo}>
      {p.icone}
      <div>
        <p className={estilos.titulo}>{titulo ?? p.titulo}</p>
        {children && <p className={estilos.texto}>{children}</p>}
      </div>
    </div>
  );
}

export interface FonteDado {
  nome: string;
  atualizadoEm?: string | null;
  tipo?: "observada" | "prevista" | "derivada";
}

/** "Fonte: … Atualizada em …" — todo valor exibido se relaciona a uma fonte e a um horário (CA-02). */
export function LegendaFonte({ fontes, children }: { fontes: FonteDado[]; children?: ReactNode }) {
  return (
    <p className={estilos.legendaFonte}>
      <span>
        Fonte:{" "}
        {fontes
          .map((f) =>
            f.atualizadoEm ? `${f.nome}, atualizada em ${formatarDataHora(f.atualizadoEm)}` : f.nome,
          )
          .join("; ")}
        .
      </span>
      {children}
    </p>
  );
}
