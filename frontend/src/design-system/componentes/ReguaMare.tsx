import { useEffect, useState, type CSSProperties } from "react";
import { ESCALA_REGUA, NIVEIS, type ChaveNivel } from "../niveis";
import estilos from "./ReguaMare.module.css";

/** Altura da água (%) por quantidade de marcas: a água chega ao topo do segmento do nível vigente. */
const ALTURA = [4, 25, 50, 75, 100];

export interface ReguaMareProps {
  nivel: ChaveNivel;
  compacta?: boolean;
  /** Anima a subida da água uma vez ao montar (único movimento da landing — design §8.7). */
  animar?: boolean;
}

export function ReguaMare({ nivel, compacta, animar = true }: ReguaMareProps) {
  const n = NIVEIS[nivel];
  const [altura, setAltura] = useState(animar ? ALTURA[0] : ALTURA[n.marcas]);
  useEffect(() => {
    const quadro = requestAnimationFrame(() => setAltura(ALTURA[n.marcas]));
    return () => cancelAnimationFrame(quadro);
  }, [n.marcas]);

  const ativo = nivel === "sem" || nivel === "insuficiente" ? null : nivel;
  const descricao = nivel === "sem" ? "nenhum" : n.rotulo;
  const classes = [
    estilos.regua,
    compacta && estilos.compacta,
    nivel === "insuficiente" && estilos.insuficiente,
  ];

  return (
    <figure className={classes.filter(Boolean).join(" ")} data-nivel={nivel}>
      <div className={estilos.corpo} aria-hidden="true">
        {[4, 3, 2, 1].map((num) => (
          <div key={num} className={estilos.segmento} style={{ top: `${(4 - num) * 25}%` }}>
            <span className={estilos.numero}>{num}</span>
          </div>
        ))}
        {nivel !== "insuficiente" && (
          <div
            className={estilos.agua}
            data-testid="agua"
            style={{ "--altura-agua": `${altura}%`, "--cor-agua": n.cor } as CSSProperties}
          />
        )}
      </div>
      <ol className={estilos.legenda} aria-hidden="true">
        {[...ESCALA_REGUA].reverse().map((chave) => (
          <li key={chave} data-ativo={chave === ativo}>
            {NIVEIS[chave].rotulo}
          </li>
        ))}
      </ol>
      <figcaption className={estilos.titulo}>
        Nível do aviso mais alto em vigor: <strong>{descricao}</strong>
      </figcaption>
    </figure>
  );
}
