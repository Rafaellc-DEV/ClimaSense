import { useId } from "react";
import estilos from "./Segmentado.module.css";

export interface OpcaoSegmentada<V extends string | number> {
  valor: V;
  rotulo: string;
}

export interface SegmentadoProps<V extends string | number> {
  /** Nome do grupo para leitores de tela: “Horizonte”. */
  rotulo: string;
  opcoes: OpcaoSegmentada<V>[];
  valor: V;
  aoMudar: (v: V) => void;
  /** Esconde o rótulo na tela (continua para leitores de tela). */
  rotuloOculto?: boolean;
}

/**
 * Escolha de uma opção entre poucas, em pílulas encaixadas (24 h · 48 h · 72 h). Rádios nativos: as setas trocam
 * a opção, Tab entra e sai do grupo. A opção escolhida tem fundo cheio e peso maior, não só cor.
 */
export function Segmentado<V extends string | number>({
  rotulo,
  opcoes,
  valor,
  aoMudar,
  rotuloOculto,
}: SegmentadoProps<V>) {
  const nome = useId();
  return (
    <fieldset className={estilos.grupo}>
      <legend className={rotuloOculto ? "so-leitor" : estilos.legenda}>{rotulo}</legend>
      <div className={estilos.trilho}>
        {opcoes.map((o) => (
          <label key={String(o.valor)} data-marcado={o.valor === valor}>
            <input type="radio" name={nome} checked={o.valor === valor} onChange={() => aoMudar(o.valor)} />
            <span>{o.rotulo}</span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}
