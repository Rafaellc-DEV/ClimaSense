import { useEffect, type RefObject } from "react";

/**
 * Holofote da malha do herói: os pontos perto do cursor acendem. Só com mouse (pointer: fine) e sem movimento
 * reduzido; escreve a posição em --hx/--hy uma vez por quadro, sem ler layout durante o render.
 */
export function useHolofote(ref: RefObject<HTMLElement>) {
  useEffect(() => {
    const el = ref.current;
    if (!el || !window.matchMedia?.("(pointer: fine) and (prefers-reduced-motion: no-preference)").matches)
      return;
    let quadro = 0;
    let x = 0;
    let y = 0;
    const pintar = () => {
      quadro = 0;
      const r = el.getBoundingClientRect();
      el.style.setProperty("--hx", `${x - r.left}px`);
      el.style.setProperty("--hy", `${y - r.top}px`);
    };
    const mover = (e: PointerEvent) => {
      x = e.clientX;
      y = e.clientY;
      if (!quadro) quadro = requestAnimationFrame(pintar);
    };
    const entrar = () => (el.dataset.holofote = "on");
    const sair = () => (el.dataset.holofote = "off");
    el.addEventListener("pointermove", mover, { passive: true });
    el.addEventListener("pointerenter", entrar, { passive: true });
    el.addEventListener("pointerleave", sair, { passive: true });
    return () => {
      cancelAnimationFrame(quadro);
      el.removeEventListener("pointermove", mover);
      el.removeEventListener("pointerenter", entrar);
      el.removeEventListener("pointerleave", sair);
    };
  }, [ref]);
}
