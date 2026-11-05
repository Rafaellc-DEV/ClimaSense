import { useEffect, useState, type RefObject } from "react";

/** Efeitos da landing. O herói e a onda são parados; só a revelação ao rolar (abaixo do herói) se move, e nunca com
    movimento reduzido. Nenhum laço permanente; só `transform`/`opacity` se animam. */

const reduzido = () =>
  typeof matchMedia === "function" && matchMedia("(prefers-reduced-motion: reduce)").matches;

/**
 * Revelação ao rolar: o bloco abaixo da dobra entra com um fade curto (data-revelar). Se já está na tela, a
 * página não esconde nada; sem IntersectionObserver ou com movimento reduzido, nunca é escondido. Nunca use na busca,
 * no resultado nem no herói.
 */
export function useRevelar(ref: RefObject<HTMLElement>) {
  useEffect(() => {
    const el = ref.current;
    if (!el || typeof IntersectionObserver === "undefined" || reduzido()) return;
    if (el.getBoundingClientRect().top < window.innerHeight * 0.9) return;
    el.dataset.revelar = "oculto";
    const o = new IntersectionObserver(
      ([e]) => {
        if (!e.isIntersecting) return;
        el.dataset.revelar = "visivel";
        o.disconnect();
      },
      { rootMargin: "0px 0px -8% 0px" },
    );
    o.observe(el);
    return () => {
      o.disconnect();
      delete el.dataset.revelar;
    };
  }, [ref]);
}

/** Mesma consulta de mídia do CSS, para escolher o desenho da régua (medidor no desktop, faixa no celular). */
export function useMidia(consulta: string, padrao = false): boolean {
  const [ok, setOk] = useState(() =>
    typeof matchMedia === "function" ? matchMedia(consulta).matches : padrao,
  );
  useEffect(() => {
    if (typeof matchMedia !== "function") return;
    const m = matchMedia(consulta);
    const mudou = () => setOk(m.matches);
    mudou();
    m.addEventListener?.("change", mudou);
    return () => m.removeEventListener?.("change", mudou);
  }, [consulta]);
  return ok;
}
