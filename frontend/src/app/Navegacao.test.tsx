import { render, screen, within } from "@testing-library/react";
import { App } from "@/app/App";
import { simularApi, usuarioTeste } from "@/features/evento/testes";
import { clienteConsultas } from "@/lib/api";

afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
  clienteConsultas.clear();
});

const MENU = [
  "Mapa",
  "Situação",
  "Chuva",
  "Registro do evento",
  "Abrigos",
  "Saúde depois da chuva",
  "Comunicados",
  "Boletim",
];

test("com comunicados ligado, o menu tem 8 itens, nesta ordem, e Fontes e Administração no rodapé", async () => {
  vi.stubEnv("VITE_FUNC_COMUNICADOS", "1");
  simularApi({
    "/auth/eu": usuarioTeste(["consultar", "editar", "administrar"]),
    "/painel/resumo": { contadores: { avaliacoes: 2, comunicados: 3 }, fontes: [] },
    "/abrigos": { itens: [], totais: { abrigos_abertos: 0, abrigos_cadastrados: 0 } },
  });
  window.history.pushState({}, "", "/app/abrigos");
  render(<App />);
  const menu = (await screen.findAllByRole("navigation", { name: "Menu principal" }))[0];
  const listas = within(menu).getAllByRole("list");
  const principais = within(listas[0])
    .getAllByRole("link")
    .map((l) => l.textContent?.replace(/\d+$/, "").trim());
  expect(principais).toEqual(MENU);
  const rodape = within(listas[1])
    .getAllByRole("link")
    .map((l) => l.textContent?.trim());
  expect(rodape).toEqual(["Fontes", "Administração"]);
  for (const fora of ["Painel", "Territórios", "Avaliações", "Cenários", "Séries", "Ações"])
    expect(within(menu).queryByRole("link", { name: fora })).not.toBeInTheDocument();
  expect(await within(menu).findByLabelText("3 aguardando a sua revisão")).toBeInTheDocument();
});

test("Administração só aparece com permissão", async () => {
  simularApi({
    "/auth/eu": usuarioTeste(["consultar"]),
    "/painel/resumo": { contadores: { avaliacoes: 0, comunicados: 0 }, fontes: [] },
  });
  window.history.pushState({}, "", "/app/boletim");
  render(<App />);
  const menu = (await screen.findAllByRole("navigation", { name: "Menu principal" }))[0];
  expect(within(menu).getByRole("link", { name: "Fontes" })).toBeInTheDocument();
  expect(within(menu).queryByRole("link", { name: "Administração" })).not.toBeInTheDocument();
});

test.each([
  ["/app/estagios", "Situação"],
  ["/app/mapa", "Mapa"],
  ["/app/avaliacoes/123", "Mapa"],
  ["/app/cenarios", "Chuva"],
  ["/app/series", "Chuva"],
  ["/app/acoes", "Registro do evento"],
  ["/app/qualquer-coisa", "Mapa"],
])("o endereço antigo %s leva à tela %s, sem 404", async (de, titulo) => {
  simularApi({
    "/auth/eu": usuarioTeste(),
    "/painel/resumo": { contadores: { avaliacoes: 0, comunicados: 0 }, fontes: [] },
  });
  window.history.pushState({}, "", de);
  render(<App />);
  expect(await screen.findByRole("heading", { level: 1, name: titulo })).toBeInTheDocument();
  if (de === "/app/series") expect(window.location.search).toBe("?aba=historico");
});
