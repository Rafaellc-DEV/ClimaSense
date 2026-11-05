import type { ReactNode } from "react";
import { Dica } from "./Dica";
import { EstadoDados } from "./EstadoDados";
import estilos from "./Painel.module.css";

/**
 * Cartão de seção da gestão: fundo branco, raio de 14 px e sombra suave em camadas. O título é obrigatório e vira o
 * nome da região; `dica` guarda a explicação atrás de um (i), em vez de um parágrafo solto.
 */
export function Painel({
  titulo,
  id,
  children,
  acoes,
  dica,
  largo,
  className,
}: {
  titulo: string;
  id: string;
  children: ReactNode;
  acoes?: ReactNode;
  /** Para que serve este bloco ou como ler os dados, atrás do (i) ao lado do título. */
  dica?: ReactNode;
  largo?: boolean;
  className?: string;
}) {
  return (
    <section
      className={[estilos.painel, largo && estilos.largo, className].filter(Boolean).join(" ")}
      aria-labelledby={id}
    >
      <div className={estilos.topo}>
        <h2>
          <span id={id}>{titulo}</span>
          {dica && <Dica texto={dica} rotulo={`Sobre ${titulo}`} lado="abaixo" />}
        </h2>
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
