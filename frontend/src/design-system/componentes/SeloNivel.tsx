import type { CSSProperties } from "react";
import { NIVEIS, type ChaveNivel } from "../niveis";
import estilos from "./SeloNivel.module.css";

export interface SeloNivelProps {
  nivel: ChaveNivel;
  /** Substitui o nome do nível, ex.: "Faltam 4 dias" num selo de dados insuficientes. */
  rotulo?: string;
  grande?: boolean;
}

/** Régua compacta + nome do nível. A cor nunca carrega o significado sozinha (RN-17). */
export function SeloNivel({ nivel, rotulo, grande }: SeloNivelProps) {
  const n = NIVEIS[nivel];
  const classes = [
    estilos.selo,
    grande && estilos.grande,
    nivel === "critico" && estilos.critico,
    nivel === "insuficiente" && estilos.insuficiente,
  ];
  return (
    <span
      className={classes.filter(Boolean).join(" ")}
      style={{ "--cor": n.cor, "--fundo": n.fundo, "--texto": n.texto } as CSSProperties}
      data-nivel={nivel}
    >
      <span className={estilos.mini} aria-hidden="true">
        {[4, 3, 2, 1].map((m) => (
          <i key={m} data-cheio={m <= n.marcas} />
        ))}
      </span>
      {rotulo ?? n.rotulo}
    </span>
  );
}
