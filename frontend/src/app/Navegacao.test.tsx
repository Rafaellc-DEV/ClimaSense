import { render, screen, within } from "@testing-library/react";
import { App } from "@/app/App";
import { simularApi, usuarioTeste } from "@/features/evento/testes";
import { clienteConsultas } from "@/lib/api";

afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
  clienteConsultas.clear();
});

const MENU = ["Mapa", "Situação do evento", "Saúde", "Ações", "Simulador"];
const ENDERECOS = ["/app", "/app/situacao", "/app/saude", "/app/acoes", "/app/simulador"];

test("o menu tem as cinco telas do PRD, nesta ordem, e Fontes e Administração no rodapé", async () => {
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
  ["/app/boletim", "Relatório executivo — Secretaria de Saúde"],
  ["/app/acoes/relatorio", "Relatório executivo — Secretaria de Saúde"],
  ["/app/chuva", "Chuva"],
  ["/app/qualquer-coisa", "Mapa"],
])("o endereço antigo %s leva à tela %s, sem 404", async (de, titulo) => {
  simularApi({ "/auth/eu": usuarioTeste() });
  window.history.pushState({}, "", de);
  render(<App />);
  expect(await screen.findByRole("heading", { level: 1, name: titulo })).toBeInTheDocument();
  if (de === "/app/series") expect(window.location.search).toBe("?aba=historico");
  if (de === "/app/registro") expect(window.location.pathname).toBe("/app/acoes");
  if (de === "/app/boletim") expect(window.location.pathname).toBe("/app/acoes/relatorio");
});
