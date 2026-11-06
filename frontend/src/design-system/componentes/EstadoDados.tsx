import type { ReactNode } from "react";
import { CircleOff, Clock, TriangleAlert } from "lucide-react";
import { haQuanto, type FonteMeta } from "@/lib/frescor";
import { formatarDataHora, formatarHoraMinuto } from "@/lib/formatos";
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
  acao,
}: {
  tipo: TipoEstadoDados;
  titulo?: string;
  /** Uma frase: o que aconteceu e o que fazer. */
  children?: ReactNode;
  /** Botão de saída, ex.: “Tentar de novo”. */
  acao?: ReactNode;
}) {
  const p = PADRAO[tipo];
  return (
    <div className={`${estilos.estado} ${estilos[tipo]}`} role="status" data-estado={tipo}>
      {p.icone}
      <div>
        <p className={estilos.titulo}>{titulo ?? p.titulo}</p>
        {children && <p className={estilos.texto}>{children}</p>}
      </div>
      {acao && <div className={estilos.acao}>{acao}</div>}
    </div>
  );
}

export interface FonteDado {
  nome: string;
  atualizadoEm?: string | null;
  tipo?: "observada" | "prevista" | "derivada";
  /**
   * Vem de `meta.fontes`: `true` = vencida, `false` = em dia, `null` = sem como saber. `undefined` = a resposta não
   * trouxe `meta.fontes` (comportamento anterior, só nome e hora).
   */
  desatualizado?: boolean | null;
}

/** Converte `meta.fontes` da API para o que os componentes mostram. */
export function fontesDado(fontes: FonteMeta[]): FonteDado[] {
  return fontes.map((f) => ({
    nome: f.nome,
    atualizadoEm: f.atualizado_em ?? null,
    desatualizado: f.desatualizado ?? null,
  }));
}

/** Selo “Desatualizado”: texto e ícone, nunca só cor (RF-19). */
export function SeloDesatualizado() {
  return (
    <span className={estilos.seloVencido} data-selo="desatualizado">
      <Clock aria-hidden="true" size={14} />
      Desatualizado
    </span>
  );
}

/** Uma fonte em uma frase: “APAC, atualizado há 3 h”, com selo se vencida, ou “Dados insuficientes: falta …”. */
export function TextoFonte({ f }: { f: FonteDado }) {
  if (f.desatualizado === undefined) {
    return <>{f.atualizadoEm ? `${f.nome}, atualizada em ${formatarDataHora(f.atualizadoEm)}` : f.nome}</>;
  }
  if (!f.atualizadoEm) {
    return (
      <>
        <b>Dados insuficientes:</b> falta a fonte {f.nome}
      </>
    );
  }
  return (
    <>
      {f.nome}, atualizado {haQuanto(f.atualizadoEm)} ({formatarHoraMinuto(f.atualizadoEm)})
      {f.desatualizado === true && (
        <>
          {" "}
          <SeloDesatualizado />
        </>
      )}
    </>
  );
}

/**
 * “Fonte: … atualizado há …” — todo valor exibido se relaciona a uma fonte e a um horário (CA-02, RF-19).
 * Sem fontes, não desenha nada.
 */
export function LegendaFonte({ fontes, children }: { fontes: FonteDado[]; children?: ReactNode }) {
  if (fontes.length === 0 && !children) return null;
  return (
    <p className={estilos.legendaFonte}>
      {fontes.length > 0 && fontes.every((f) => f.desatualizado === undefined) && (
        <span>
          Fonte:{" "}
          {fontes
            .map((f) =>
              f.atualizadoEm ? `${f.nome}, atualizada em ${formatarDataHora(f.atualizadoEm)}` : f.nome,
            )
            .join("; ")}
          .
        </span>
      )}
      {fontes.length > 0 && fontes.some((f) => f.desatualizado !== undefined) && (
        <span>
          Fonte:{" "}
          {fontes.map((f, i) => (
            <span key={`${f.nome}-${i}`}>
              {i > 0 && "; "}
              <TextoFonte f={f} />
            </span>
          ))}
          .
        </span>
      )}
      {children}
    </p>
  );
}

/** “Atualizado às 14:32” discreto: a tela se renova sozinha (RF-10). Sem leitura ainda, não aparece. */
export function AtualizadoAs({ em }: { em: number | null | undefined }) {
  if (!em) return null;
  return (
    <p className={estilos.atualizadoAs} data-atualizado-as="true">
      Atualizado às {formatarHoraMinuto(em)}
    </p>
  );
}
