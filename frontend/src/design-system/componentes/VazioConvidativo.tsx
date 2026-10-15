import type { ReactNode } from "react";
import estilos from "./VazioConvidativo.module.css";

/** Estado vazio: convida a agir em vez de só dizer que não há nada (design §8.9). */
export function VazioConvidativo({
  titulo,
  texto,
  acao,
}: {
  titulo: string;
  texto?: ReactNode;
  acao?: ReactNode;
}) {
  return (
    <div className={estilos.vazio}>
      <h3 className={estilos.titulo}>{titulo}</h3>
      {texto && <p className={estilos.texto}>{texto}</p>}
      {acao}
    </div>
  );
}
