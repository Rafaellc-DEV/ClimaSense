import type { ButtonHTMLAttributes, ReactNode } from "react";
import estilos from "./Botao.module.css";

export type VarianteBotao = "principal" | "secundario" | "discreto" | "perigo";

export interface BotaoProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variante?: VarianteBotao;
  grande?: boolean;
  larguraTotal?: boolean;
  /** Ícone decorativo; o texto do botão continua obrigatório (RNF-ACE-05). */
  icone?: ReactNode;
  children: ReactNode;
}

export function classesBotao(variante: VarianteBotao = "principal", grande = false, larguraTotal = false) {
  return [estilos.botao, estilos[variante], grande && estilos.grande, larguraTotal && estilos.larguraTotal]
    .filter(Boolean)
    .join(" ");
}

export function Botao({
  variante = "principal",
  grande,
  larguraTotal,
  icone,
  children,
  type = "button",
  className,
  ...resto
}: BotaoProps) {
  return (
    <button
      type={type}
      className={[classesBotao(variante, grande, larguraTotal), className].filter(Boolean).join(" ")}
      {...resto}
    >
      {icone && <span aria-hidden="true">{icone}</span>}
      {children}
    </button>
  );
}
