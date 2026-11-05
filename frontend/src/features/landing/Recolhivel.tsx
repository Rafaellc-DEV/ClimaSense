import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { ChevronDown } from "lucide-react";
import { useRevelar } from "./efeitos";
import estilos from "./Recolhivel.module.css";

/**
 * Seção recolhida por padrão (“Como funciona”, “Quem somos…”): o título é um botão com aria-expanded. Um link para
 * `#id` (do rodapé, por exemplo) abre a seção. O conteúdo só é montado quando aberto: nada é buscado à toa.
 */
export function Recolhivel({ id, titulo, children }: { id: string; titulo: string; children: ReactNode }) {
  const [aberto, setAberto] = useState(false);
  const corpo = useId();
  const secao = useRef<HTMLElement>(null);
  useRevelar(secao);

  useEffect(() => {
    const abrirSeForOAlvo = () => {
      if (location.hash === `#${id}`) setAberto(true);
    };
    const aoClicar = (e: MouseEvent) => {
      const link = (e.target as Element | null)?.closest?.(`a[href$="#${id}"]`);
      if (link) setAberto(true);
    };
    abrirSeForOAlvo();
    window.addEventListener("hashchange", abrirSeForOAlvo);
    document.addEventListener("click", aoClicar);
    return () => {
      window.removeEventListener("hashchange", abrirSeForOAlvo);
      document.removeEventListener("click", aoClicar);
    };
  }, [id]);

  return (
    <section ref={secao} id={id} className={estilos.secao} aria-labelledby={`${id}-h`}>
      <h2 id={`${id}-h`} className={estilos.h2}>
        <button
          type="button"
          className={estilos.botao}
          aria-expanded={aberto}
          aria-controls={corpo}
          onClick={() => setAberto((a) => !a)}
        >
          <span>{titulo}</span>
          <ChevronDown aria-hidden="true" size={24} className={estilos.seta} />
        </button>
      </h2>
      {aberto && (
        <div id={corpo} className={estilos.corpo}>
          {children}
        </div>
      )}
    </section>
  );
}
