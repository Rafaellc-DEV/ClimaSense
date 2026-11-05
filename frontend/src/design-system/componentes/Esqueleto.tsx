import type { CSSProperties } from "react";
import estilos from "./Esqueleto.module.css";

export interface EsqueletoProps {
  /** Largura CSS ("60%", "8rem"). Padrão: toda a linha. */
  largura?: string;
  /** Altura CSS. Padrão: uma linha de texto. */
  altura?: string;
  forma?: "linha" | "bloco" | "circulo";
  className?: string;
}

/** Peça cinza que pulsa no lugar do conteúdo que ainda carrega. Decorativa: quem anuncia é `CarregandoLista`. */
export function Esqueleto({ largura, altura, forma = "linha", className }: EsqueletoProps) {
  return (
    <span
      aria-hidden="true"
      className={[estilos.esqueleto, estilos[forma], className].filter(Boolean).join(" ")}
      style={{ "--larg": largura, "--alt": altura } as CSSProperties}
    />
  );
}

/** Esqueleto de um cartão de indicador (rótulo, valor grande, rodapé). */
export function EsqueletoIndicador() {
  return (
    <div className={estilos.indicador} aria-hidden="true">
      <Esqueleto largura="45%" />
      <Esqueleto largura="60%" altura="2.4rem" forma="bloco" />
      <Esqueleto largura="35%" />
    </div>
  );
}

/** Esqueleto de linhas de tabela ou de ranking. Anuncia “Carregando…” uma vez, para leitores de tela. */
export function CarregandoLista({
  linhas = 4,
  texto = "Carregando…",
  altura = "4.5rem",
}: {
  linhas?: number;
  texto?: string;
  altura?: string;
}) {
  return (
    <div className={estilos.lista} role="status" aria-busy="true">
      <span className="so-leitor">{texto}</span>
      {Array.from({ length: linhas }, (_, i) => (
        <Esqueleto key={i} forma="bloco" altura={altura} />
      ))}
    </div>
  );
}
