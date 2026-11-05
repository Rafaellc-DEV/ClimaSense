import type { ReactNode } from "react";
import rios from "@/assets/tracos/rios.svg?raw";
import estilos from "./FaixaMare.module.css";

export interface FaixaMareProps {
  /** Nome da faixa; vira o <h2> e o nome da região. */
  titulo: string;
  id: string;
  /** À direita do título: um (i), um selo. */
  ladoTitulo?: ReactNode;
  /** Cartão branco à direita (a régua de nível, por exemplo). Em telas estreitas desce para baixo do texto. */
  lateral?: ReactNode;
  children: ReactNode;
  className?: string;
}

/**
 * Faixa de azul profundo com a malha de pontos e o traço dos rios, a mesma linguagem do herói da landing.
 * Guarda a resposta principal de uma tela (“Situação agora”). Texto branco; os tokens `--sup-*` não invertem
 * no tema escuro. Dentro dela use `Botao variante="claro"` e `Pilula sobreMare`.
 */
export function FaixaMare({ titulo, id, ladoTitulo, lateral, children, className }: FaixaMareProps) {
  return (
    <section className={[estilos.faixa, className].filter(Boolean).join(" ")} aria-labelledby={id}>
      <div className={estilos.malha} aria-hidden="true" />
      <div className={estilos.rios} aria-hidden="true" dangerouslySetInnerHTML={{ __html: rios }} />
      <div className={estilos.interno}>
        <div className={estilos.texto}>
          <h2 className={estilos.titulo}>
            <span id={id}>{titulo}</span>
            {ladoTitulo}
          </h2>
          {children}
        </div>
        {lateral && <div className={estilos.lateral}>{lateral}</div>}
      </div>
    </section>
  );
}
