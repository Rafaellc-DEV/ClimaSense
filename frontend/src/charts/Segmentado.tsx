import { useId } from "react";
import estilos from "./Segmentado.module.css";

export interface OpcaoSegmentada {
  valor: string;
  rotulo: string;
  desabilitada?: boolean;
}

export interface SegmentadoProps {
  /** Nome do grupo, lido por leitores de tela. */
  rotulo: string;
  /** Mostra o nome do grupo ao lado, em Outfit fina. */
  rotuloVisivel?: boolean;
  opcoes: OpcaoSegmentada[];
  valor: string;
  aoMudar: (valor: string) => void;
  /** Rola na horizontal dentro do próprio grupo quando falta espaço (celular). */
  rolavel?: boolean;
}

/**
 * Escolha única em pílulas (um grupo de rádios nativos: setas, Tab e leitor de tela funcionam sem ARIA extra).
 * Mesma linguagem da landing: trilho claro, item ativo em azul maré.
 */
export function Segmentado({ rotulo, rotuloVisivel, opcoes, valor, aoMudar, rolavel }: SegmentadoProps) {
  const nome = useId();
  return (
    <div className={estilos.grupo} data-rolavel={rolavel}>
      <span id={`${nome}-rotulo`} className={rotuloVisivel ? estilos.legenda : "so-leitor"}>
        {rotulo}
      </span>
      <div className={estilos.trilho} role="radiogroup" aria-labelledby={`${nome}-rotulo`}>
        {opcoes.map((o) => (
          <label key={o.valor} className={estilos.opcao} data-marcado={valor === o.valor}>
            <input
              type="radio"
              name={nome}
              value={o.valor}
              checked={valor === o.valor}
              disabled={o.desabilitada}
              onChange={() => aoMudar(o.valor)}
            />
            <span>{o.rotulo}</span>
          </label>
        ))}
      </div>
    </div>
  );
}
