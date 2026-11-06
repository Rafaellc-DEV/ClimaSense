import { useEffect, useId, useRef, useState } from "react";
import { Info, X } from "lucide-react";
import { ValorSuprimido } from "@/design-system/componentes/ValorSuprimido";
import { formatarNumero } from "@/lib/formatos";
import type { BairroDoDistrito } from "./bairros";
import estilos from "./PopoverBairros.module.css";

/**
 * Ícone (i) ao lado do distrito: abre por clique, toque ou teclado e lista todos os bairros dele, com os casos.
 * Fecha com Esc, com o botão Fechar, ao clicar fora ou ao sair com o Tab. Bairro sem registro diz “sem registro”.
 */
export function PopoverBairros({
  distrito,
  bairros,
  oQue,
  minimo = 5,
}: {
  distrito: string;
  bairros: BairroDoDistrito[];
  /** “casos de dengue em 2025” */
  oQue: string;
  /** `meta.supressao_minima`. */
  minimo?: number;
}) {
  const [aberto, setAberto] = useState(false);
  const raiz = useRef<HTMLSpanElement>(null);
  const botao = useRef<HTMLButtonElement>(null);
  const id = useId();

  useEffect(() => {
    if (!aberto) return;
    const fora = (e: PointerEvent) => {
      if (raiz.current && !raiz.current.contains(e.target as Node)) setAberto(false);
    };
    document.addEventListener("pointerdown", fora);
    return () => document.removeEventListener("pointerdown", fora);
  }, [aberto]);

  const comRegistro = bairros.filter((b) => b.casos !== null || b.suprimido).length;
  return (
    <span
      ref={raiz}
      className={estilos.raiz}
      onKeyDown={(e) => {
        if (e.key === "Escape" && aberto) {
          e.stopPropagation();
          setAberto(false);
          botao.current?.focus();
        }
      }}
      onBlur={(e) => {
        if (!raiz.current?.contains(e.relatedTarget as Node | null)) setAberto(false);
      }}
    >
      <button
        ref={botao}
        type="button"
        className={estilos.botao}
        aria-label={`Bairros de ${distrito}`}
        aria-expanded={aberto}
        aria-controls={id}
        onClick={() => setAberto((a) => !a)}
      >
        <Info aria-hidden="true" size={16} />
      </button>
      <span
        id={id}
        role="group"
        aria-label={`Bairros de ${distrito}`}
        tabIndex={-1}
        className={estilos.painel}
        hidden={!aberto}
      >
        <span className={estilos.topo}>
          <b>Bairros de {distrito}</b>
          <button
            type="button"
            className={estilos.fechar}
            aria-label="Fechar"
            onClick={() => setAberto(false)}
          >
            <X aria-hidden="true" size={18} />
          </button>
        </span>
        <span className={estilos.apoio}>
          {bairros.length === 0
            ? "Sem bairros na lista."
            : `${oQue}. ${comRegistro} de ${bairros.length} com registro.`}
        </span>
        {bairros.length > 0 && (
          <ul className={estilos.lista} tabIndex={0} aria-label={`Lista de bairros de ${distrito}`}>
            {bairros.map((b) => (
              <li key={b.id}>
                <span>{b.nome}</span>
                {b.suprimido && b.casos === null ? (
                  <ValorSuprimido minimo={minimo} />
                ) : b.casos === null ? (
                  <span className={estilos.semRegistro}>sem registro</span>
                ) : (
                  <b>{formatarNumero(b.casos)}</b>
                )}
              </li>
            ))}
          </ul>
        )}
      </span>
    </span>
  );
}
