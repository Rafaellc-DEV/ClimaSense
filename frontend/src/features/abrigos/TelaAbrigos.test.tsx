import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { App } from "@/app/App";
import { AGORA, simularApi, usuarioTeste } from "@/features/evento/testes";
import { clienteConsultas } from "@/lib/api";

const abrigos = {
  itens: [
    {
      id: "ab-1",
      nome: "Escola Municipal Afogados",
      bairro_id: "bairro-afogados",
      bairro_nome: "Afogados",
      endereco: "Rua Exemplo, 10",
      capacidade: 80,
      aberto: true,
      pessoas_abrigadas: 42,
      desabrigados: 50,
      observacao: null,
      atualizado_em: AGORA,
      atualizado_por_nome: "Mari Siqueira",
    },
  ],
  totais: { abrigos_abertos: 1, pessoas_abrigadas: 42, desabrigados: 50, atualizado_em: AGORA },
};

function base() {
  return {
    "/auth/eu": usuarioTeste(),
    "/painel/resumo": { contadores: { avaliacoes: 0, comunicados: 0 }, fontes: [] },
    "/territorios": [
      { id: "ds-1", tipo: "distrito", nome_exibicao: "Distrito Sanitário 1", pai_id: "recife" },
      { id: "bairro-afogados", tipo: "bairro", nome_exibicao: "Afogados", pai_id: "ds-1" },
    ],
    "/abrigos": abrigos,
  };
}

afterEach(() => {
  vi.unstubAllGlobals();
  clienteConsultas.clear();
});

test("totais no topo e a lista com hora e autor da última atualização", async () => {
  simularApi(base());
  window.history.pushState({}, "", "/app/abrigos");
  render(<App />);
  const totais = await screen.findByRole("region", { name: "Totais" });
  expect(
    within(await within(totais).findByRole("group", { name: "Abrigos abertos" })).getByText("1"),
  ).toBeInTheDocument();
  // ocupação e desabrigados saíram: sem fonte pública e sem contagem pela equipe
  expect(within(totais).queryByRole("group", { name: "Desabrigados" })).not.toBeInTheDocument();
  expect(within(totais).queryByRole("group", { name: "Pessoas abrigadas" })).not.toBeInTheDocument();
  expect(await screen.findByRole("rowheader", { name: /Escola Municipal Afogados/ })).toBeInTheDocument();
  expect(screen.getByText("80 pessoas")).toBeInTheDocument();
  expect(screen.getByText("por Mari Siqueira")).toBeInTheDocument();
});

test("atualização rápida manda só aberto ou fechado e a observação", async () => {
  const pedidos = simularApi(base(), { "/abrigos/ab-1": { ...abrigos.itens[0], aberto: false } });
  window.history.pushState({}, "", "/app/abrigos");
  render(<App />);
  const u = userEvent.setup();
  await u.click(await screen.findByRole("button", { name: /Atualizar Escola Municipal Afogados/ }));
  const dialogo = await screen.findByRole("dialog", { name: /Atualizar Escola Municipal Afogados/ });
  expect(within(dialogo).queryByLabelText("Desabrigados atendidos")).not.toBeInTheDocument();
  await u.click(within(dialogo).getByRole("radio", { name: "Fechado" }));
  await u.click(within(dialogo).getByRole("button", { name: "Salvar" }));
  await waitFor(() =>
    expect(pedidos.find((p) => p.metodo === "PATCH")).toMatchObject({
      url: expect.stringContaining("/abrigos/ab-1"),
      corpo: { aberto: false, observacao: null },
    }),
  );
});

test("cadastro pede nome e bairro antes de enviar", async () => {
  const pedidos = simularApi(base(), { "/abrigos": { status: 201, corpo: { id: "ab-2" } } });
  window.history.pushState({}, "", "/app/abrigos");
  render(<App />);
  const u = userEvent.setup();
  await u.click(await screen.findByRole("button", { name: "Cadastrar abrigo" }));
  const dialogo = await screen.findByRole("dialog", { name: "Cadastrar abrigo" });
  await u.click(within(dialogo).getByRole("button", { name: "Cadastrar abrigo" }));
  expect(await within(dialogo).findByText("Escreva o nome do abrigo.")).toBeInTheDocument();
  expect(within(dialogo).getByText("Escolha o bairro.")).toBeInTheDocument();
  expect(pedidos.some((p) => p.metodo === "POST")).toBe(false);

  await u.type(within(dialogo).getByLabelText("Nome do abrigo"), "Igreja do Bongi");
  await waitFor(() => expect(within(dialogo).getByLabelText("Bairro")).toBeEnabled());
  await u.selectOptions(within(dialogo).getByLabelText("Bairro"), "bairro-afogados");
  await u.type(within(dialogo).getByLabelText("Capacidade em pessoas (opcional)"), "120");
  await u.click(within(dialogo).getByRole("button", { name: "Cadastrar abrigo" }));
  await waitFor(() =>
    expect(pedidos.find((p) => p.metodo === "POST")?.corpo).toMatchObject({
      nome: "Igreja do Bongi",
      bairro_id: "bairro-afogados",
      aberto: true,
      capacidade: 120,
    }),
  );
});

test("sem o endpoint de abrigos (404), nada de zero: a tela diz que ainda não está disponível", async () => {
  const b = base() as Record<string, unknown>;
  delete b["/abrigos"];
  simularApi(b);
  window.history.pushState({}, "", "/app/abrigos");
  render(<App />);
  expect(await screen.findByText("Ainda não disponível.")).toBeInTheDocument();
  expect(screen.queryByRole("group", { name: "Abrigos abertos" })).not.toBeInTheDocument();
});

test("local que ninguém informou é “Sem informação”, não “Fechado” (RN-01); e a contagem diz que nenhum está aberto", async () => {
  const carregado = {
    ...abrigos.itens[0],
    id: "ab-2",
    nome: "Escola Carregada dos Dados Abertos",
    aberto: false,
    status_fonte: null,
    status_informado_em: null,
    atualizado_por_nome: null,
  };
  simularApi({
    ...base(),
    "/abrigos": {
      itens: [carregado],
      totais: { abrigos_abertos: 0, pessoas_abrigadas: null, desabrigados: null },
    },
  });
  window.history.pushState({}, "", "/app/abrigos");
  render(<App />);
  expect(await screen.findByText("Sem informação")).toBeInTheDocument();
  expect(screen.queryByText("Fechado")).not.toBeInTheDocument();
  expect(screen.getByText(/Nenhum está marcado como aberto/)).toBeInTheDocument();
  expect(screen.queryByText(/abertos primeiro/)).not.toBeInTheDocument();
});

test("“Só abertos” sem nenhum aberto explica o que fazer e leva de volta a todos os locais", async () => {
  simularApi({ ...base(), "/abrigos?aberto=true": { itens: [], totais: { abrigos_abertos: 0 } } });
  window.history.pushState({}, "", "/app/abrigos");
  render(<App />);
  const u = userEvent.setup();
  await u.click(await screen.findByRole("radio", { name: "Só abertos" }));
  expect(await screen.findByText("Nenhum abrigo aberto registrado.")).toBeInTheDocument();
  expect(screen.getByText(/marcado como aberto/)).toBeInTheDocument();
  await u.click(screen.getByRole("button", { name: "Ver todos os locais" }));
  expect(await screen.findByRole("rowheader", { name: /Escola Municipal Afogados/ })).toBeInTheDocument();
});
