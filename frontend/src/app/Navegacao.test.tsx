import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { App } from "@/app/App";
import { simularApi, usuarioTeste } from "@/features/evento/testes";
import { clienteConsultas } from "@/lib/api";

afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
  clienteConsultas.clear();
});

const MENU = ["Mapa", "Dashboards", "Situação do evento", "Saúde", "Ações", "Simulador"];
const ENDERECOS = ["/app", "/app/dashboards", "/app/situacao", "/app/saude", "/app/acoes", "/app/simulador"];

test("o menu tem as telas da equipe, nesta ordem, e Fontes e Administração no rodapé", async () => {
  simularApi({ "/auth/eu": usuarioTeste(["consultar", "editar", "administrar"]) });
  window.history.pushState({}, "", "/app/situacao");
  render(<App />);
  const menu = (await screen.findAllByRole("navigation", { name: "Menu principal" }))[0];
  const listas = within(menu).getAllByRole("list");
  const links = within(listas[0]).getAllByRole("link");
  expect(links.map((l) => l.textContent?.trim())).toEqual(MENU);
  expect(links.map((l) => l.getAttribute("href"))).toEqual(ENDERECOS);
  const rodape = within(listas[1])
    .getAllByRole("link")
    .map((l) => l.textContent?.trim());
  expect(rodape).toEqual(["Fontes", "Administração"]);
  for (const fora of [
    "Chuva",
    "Registro do evento",
    "Boletim",
    "Comunicados",
    "Situação",
    "Painel",
    "Territórios",
  ])
    expect(within(menu).queryByRole("link", { name: fora })).not.toBeInTheDocument();
});

test("o menu não consulta mais /painel/*", async () => {
  const pedidos = simularApi({ "/auth/eu": usuarioTeste() });
  window.history.pushState({}, "", "/app/acoes");
  render(<App />);
  await screen.findAllByRole("navigation", { name: "Menu principal" });
  expect(pedidos.some((p) => p.url.includes("/painel/"))).toBe(false);
});

test("Administração só aparece com permissão", async () => {
  simularApi({ "/auth/eu": usuarioTeste(["consultar"]) });
  window.history.pushState({}, "", "/app/acoes");
  render(<App />);
  const menu = (await screen.findAllByRole("navigation", { name: "Menu principal" }))[0];
  expect(within(menu).getByRole("link", { name: "Fontes" })).toBeInTheDocument();
  expect(within(menu).queryByRole("link", { name: "Administração" })).not.toBeInTheDocument();
});

test.each([
  ["/app/estagios", "Mapa"],
  ["/app/mapa", "Mapa"],
  ["/app/avaliacoes/123", "Mapa"],
  ["/app/cenarios", "Chuva"],
  ["/app/series", "Chuva"],
  ["/app/registro", "Ações"],
  ["/app/painel", "Situação do evento"],
  ["/app/boletim", "Ações"],
  ["/app/acoes/relatorio", "Ações"],
  ["/app/chuva", "Chuva"],
  ["/app/qualquer-coisa", "Mapa"],
])("o endereço antigo %s leva à tela %s, sem 404", async (de, titulo) => {
  simularApi({ "/auth/eu": usuarioTeste() });
  window.history.pushState({}, "", de);
  render(<App />);
  expect(await screen.findByRole("heading", { level: 1, name: titulo })).toBeInTheDocument();
  if (de === "/app/series") expect(window.location.search).toBe("?aba=historico");
  if (de === "/app/registro") expect(window.location.pathname).toBe("/app/acoes");
  if (de === "/app/boletim" || de === "/app/acoes/relatorio")
    expect(window.location.pathname).toBe("/app/acoes");
});

test("o menu recolhe e expande por um botão na borda; a escolha fica guardada", async () => {
  window.localStorage.removeItem("climasense.menu-recolhido");
  simularApi({ "/auth/eu": usuarioTeste() });
  window.history.pushState({}, "", "/app/acoes");
  render(<App />);
  const recolher = await screen.findByRole("button", { name: "Recolher menu" });
  expect(recolher).toHaveAttribute("aria-expanded", "true");
  await userEvent.click(recolher);
  const expandir = screen.getByRole("button", { name: "Expandir menu" });
  expect(expandir).toHaveAttribute("aria-expanded", "false");
  expect(window.localStorage.getItem("climasense.menu-recolhido")).toBe("1");
  // recolhido, cada item continua com nome acessível (e dica) para quem usa leitor de tela ou mouse
  const menu = screen.getAllByRole("navigation", { name: "Menu principal" })[0];
  expect(within(menu).getByRole("link", { name: "Mapa" })).toHaveAttribute("title", "Mapa");
  await userEvent.click(expandir);
  expect(screen.getByRole("button", { name: "Recolher menu" })).toBeInTheDocument();
  expect(window.localStorage.getItem("climasense.menu-recolhido")).toBe("0");
});
