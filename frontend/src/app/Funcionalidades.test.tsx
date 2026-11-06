import { render, screen, within } from "@testing-library/react";
import { App } from "@/app/App";
import { simularApi, usuarioTeste } from "@/features/evento/testes";
import { clienteConsultas } from "@/lib/api";
import { enderecoInicial, funcionalidadeLigada } from "@/lib/funcionalidades";

afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
  clienteConsultas.clear();
});

test("todas as chaves vêm desligadas por padrão", () => {
  for (const f of [
    "landingPublica",
    "comunicados",
    "avaliacoes",
    "mapaPortatil",
    "estatisticasSeries",
  ] as const)
    expect(funcionalidadeLigada(f)).toBe(false);
  expect(enderecoInicial()).toBe("/entrar");
});

describe("chaves desligadas", () => {
  test("sem sessão, / abre o login e não há link para a landing", async () => {
    simularApi({ "/auth/eu": { status: 401 } });
    window.history.pushState({}, "", "/");
    render(<App />);
    expect(await screen.findByRole("heading", { level: 1, name: "Acesso da equipe" })).toBeInTheDocument();
    expect(window.location.pathname).toBe("/entrar");
    expect(screen.queryByText("Voltar à página inicial")).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /página inicial/ })).not.toBeInTheDocument();
  });

  test("com sessão, / leva à área da equipe", async () => {
    simularApi({ "/auth/eu": usuarioTeste() });
    window.history.pushState({}, "", "/");
    render(<App />);
    expect(await screen.findByRole("heading", { level: 1, name: "Mapa" })).toBeInTheDocument();
    expect(window.location.pathname).toBe("/app");
  });

  test("o endereço de um aviso público e o de comunicados não existem: redirecionam", async () => {
    simularApi({ "/auth/eu": usuarioTeste() });
    window.history.pushState({}, "", "/app/comunicados/novo");
    render(<App />);
    expect(await screen.findByRole("heading", { level: 1, name: "Mapa" })).toBeInTheDocument();
    expect(window.location.pathname).toBe("/app");
    const menu = (await screen.findAllByRole("navigation", { name: "Menu principal" }))[0];
    expect(within(menu).queryByRole("link", { name: /Comunicados/ })).not.toBeInTheDocument();
  });

  test("/avisos/x vai ao login", async () => {
    simularApi({ "/auth/eu": { status: 401 } });
    window.history.pushState({}, "", "/avisos/x");
    render(<App />);
    expect(await screen.findByRole("heading", { level: 1, name: "Acesso da equipe" })).toBeInTheDocument();
  });
});

describe("chaves ligadas", () => {
  test("a landing volta em / e os comunicados continuam fora do menu (PRD §5)", async () => {
    vi.stubEnv("VITE_FUNC_LANDING_PUBLICA", "1");
    vi.stubEnv("VITE_FUNC_COMUNICADOS", "1");
    expect(enderecoInicial()).toBe("/");
    simularApi({ "/auth/eu": usuarioTeste(), "/comunicados": { itens: [] } });
    window.history.pushState({}, "", "/app/saude");
    render(<App />);
    const menu = (await screen.findAllByRole("navigation", { name: "Menu principal" }))[0];
    expect(within(menu).queryByRole("link", { name: /Comunicados/ })).not.toBeInTheDocument();
  });
});
