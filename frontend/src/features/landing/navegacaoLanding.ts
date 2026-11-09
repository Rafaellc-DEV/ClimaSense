import { useEffect } from "react";

const ABAS = new Set(["#comunicados", "#avisos", "#mapa"]);

/** Elemento até onde a tela rola para um hash da landing (ou null se não houver). */
function alvoDoHash(hash: string): HTMLElement | null {
  return document.getElementById(ABAS.has(hash) ? "avisos-e-mapa" : hash.slice(1));
}

function rolarAte(hash: string) {
  const reduzir = matchMedia("(prefers-reduced-motion: reduce)").matches;
  alvoDoHash(hash)?.scrollIntoView?.({ block: "start", behavior: reduzir ? "auto" : "smooth" });
}

/** Quem chega à página inicial vindo de outra (`/#mapa`) ou já com hash: leva a tela até a seção. */
export function useRolarAoChegar(naHome: boolean) {
  useEffect(() => {
    if (!naHome || !location.hash) return;
    const hash = location.hash;
    // espera a aba ou o recolhível abrir e a página montar
    const t = window.setTimeout(() => requestAnimationFrame(() => rolarAte(hash)), 250);
    return () => window.clearTimeout(t);
  }, [naHome]);
}
