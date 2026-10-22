import { useEffect } from "react";

/** Duração da rolagem conforme a distância: trechos curtos não se arrastam, os longos não teleportam. */
const duracaoPara = (distancia: number) => Math.min(1400, Math.max(600, 400 + Math.abs(distancia) * 0.4));

/** Começa devagar, acelera no meio e freia ao chegar. */
const suavizar = (t: number) => (t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2);

const semMovimento = () => matchMedia("(prefers-reduced-motion: reduce)").matches;

let rolagemAtual = 0;

/** Leva a página até o elemento, descontando o scroll-margin-top (o topo fixo não cobre o título da seção). */
function rolarAte(alvo: HTMLElement, aoChegar: () => void) {
  cancelAnimationFrame(rolagemAtual);
  const margem = parseFloat(getComputedStyle(alvo).scrollMarginTop) || 0;
  const inicio = window.scrollY;
  const destino = Math.max(0, inicio + alvo.getBoundingClientRect().top - margem);
  const distancia = destino - inicio;
  if (semMovimento() || Math.abs(distancia) < 2) {
    window.scrollTo(0, destino);
    aoChegar();
    return;
  }

  // a pessoa rolou por conta própria no meio do caminho: a animação para e não disputa com ela
  let interrompida = false;
  const interromper = () => {
    interrompida = true;
  };
  const eventos = ["wheel", "touchstart", "keydown"] as const;
  eventos.forEach((e) => window.addEventListener(e, interromper, { once: true, passive: true }));
  const limpar = () => eventos.forEach((e) => window.removeEventListener(e, interromper));

  const duracao = duracaoPara(distancia);
  const t0 = performance.now();
  const passo = (agora: number) => {
    if (interrompida) return limpar();
    const t = Math.min(1, (agora - t0) / duracao);
    window.scrollTo(0, inicio + distancia * suavizar(t));
    if (t < 1) rolagemAtual = requestAnimationFrame(passo);
    else {
      limpar();
      aoChegar();
    }
  };
  rolagemAtual = requestAnimationFrame(passo);
}

/** Leva o foco para a seção sem rolar de novo: quem usa teclado ou leitor de tela continua dali. */
function focar(alvo: HTMLElement) {
  if (!alvo.hasAttribute("tabindex") && !alvo.matches("a, button, input, select, textarea")) {
    alvo.setAttribute("tabindex", "-1");
  }
  alvo.focus({ preventScroll: true });
}

/** Links internos (#secao, ou /#secao estando na página inicial) descem até a seção devagar, em vez de saltar.
   Ao abrir a página inicial já com um #secao (vindo de outra página), ela começa no topo e desce até lá. */
export function useRolagemSuave(inicio: boolean) {
  useEffect(() => {
    const aoClicar = (e: MouseEvent) => {
      if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      const link = (e.target as Element | null)?.closest?.("a[href*='#']");
      if (!(link instanceof HTMLAnchorElement)) return;
      const url = new URL(link.href);
      if (url.origin !== location.origin || url.pathname !== location.pathname || !url.hash) return;
      const alvo = document.getElementById(decodeURIComponent(url.hash.slice(1)));
      if (!alvo) return;
      e.preventDefault();
      if (location.hash !== url.hash) history.pushState(history.state, "", url.hash);
      rolarAte(alvo, () => focar(alvo));
    };
    document.addEventListener("click", aoClicar);
    return () => {
      document.removeEventListener("click", aoClicar);
      cancelAnimationFrame(rolagemAtual);
    };
  }, []);

  useEffect(() => {
    if (!inicio || !location.hash) return;
    const alvo = document.getElementById(decodeURIComponent(location.hash.slice(1)));
    if (!alvo) return;
    window.scrollTo(0, 0);
    // um instante para a página se mostrar antes de descer: a pessoa vê de onde saiu e para onde vai
    const espera = window.setTimeout(() => rolarAte(alvo, () => focar(alvo)), 350);
    return () => window.clearTimeout(espera);
  }, [inicio]);
}
