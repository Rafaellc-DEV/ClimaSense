/**
 * Chaves de funcionalidade de build (ADR 0011, RNF-02). Todas DESLIGADAS por padrão: ligam só com `VITE_FUNC_*=1`
 * no build, por decisão do dono do produto registrada no PRD. Desligada, a rota não existe no roteador, o item some do
 * menu e nenhum link aponta para ela. O código fica no repositório.
 *
 * Lidas a cada chamada (e não uma vez na carga do módulo) para os testes poderem ligar e desligar com `vi.stubEnv`.
 */
const ligada = (valor: unknown) => valor === "1" || valor === "true";

export type Funcionalidade =
  | "landingPublica"
  | "comunicados"
  | "avaliacoes"
  | "mapaPortatil"
  | "estatisticasSeries";

export function funcionalidadeLigada(f: Funcionalidade): boolean {
  const e = import.meta.env;
  switch (f) {
    case "landingPublica":
      return ligada(e.VITE_FUNC_LANDING_PUBLICA);
    case "comunicados":
      return ligada(e.VITE_FUNC_COMUNICADOS);
    case "avaliacoes":
      return ligada(e.VITE_FUNC_AVALIACOES);
    case "mapaPortatil":
      return ligada(e.VITE_FUNC_MAPA_PORTATIL);
    case "estatisticasSeries":
      return ligada(e.VITE_FUNC_ESTATISTICAS_SERIES);
  }
}

/** Endereço da "casa" pública: a landing, se ligada; senão a tela de entrar (que leva à equipe se já houver sessão). */
export const enderecoInicial = () => (funcionalidadeLigada("landingPublica") ? "/" : "/entrar");
