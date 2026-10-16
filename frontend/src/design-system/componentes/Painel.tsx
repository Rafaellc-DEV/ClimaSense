import type { ReactNode } from "react";
import { EstadoDados } from "./EstadoDados";
import estilos from "./Painel.module.css";

/** Bloco da área da equipe: borda de 1 px, sem sombra (design §8.6). O título é obrigatório e vira o nome da região. */
export function Painel({
  titulo,
  id,
  children,
  acoes,
  largo,
  className,
}: {
  titulo: string;
  id: string;
  children: ReactNode;
  acoes?: ReactNode;
  largo?: boolean;
  className?: string;
}) {
  return (
    <section
      className={[estilos.painel, largo && estilos.largo, className].filter(Boolean).join(" ")}
      aria-labelledby={id}
    >
      <div className={estilos.topo}>
        <h2 id={id}>{titulo}</h2>
        {acoes}
      </div>
      {children}
    </section>
  );
}

export function Carregando({ texto = "Carregando…" }: { texto?: string }) {
  return (
    <p className={estilos.carregando} role="status">
      <span className={estilos.barra} aria-hidden="true" />
      {texto}
    </p>
  );
}

/** Falha ao carregar: diz o que aconteceu e o que fazer, sem pedir desculpas (design §8.9). */
export function FalhaCarga({ erro, aoTentar }: { erro: Error | null; aoTentar?: () => void }) {
  return (
    <EstadoDados tipo="falha" titulo="Não foi possível carregar.">
      {erro?.message ?? "Tente de novo em alguns minutos."}{" "}
      {aoTentar && (
        <button type="button" className={estilos.tentar} onClick={aoTentar}>
          Tentar de novo
        </button>
      )}
    </EstadoDados>
  );
}
