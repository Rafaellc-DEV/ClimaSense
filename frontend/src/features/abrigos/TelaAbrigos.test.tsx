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

const totaisSit = {
  abrigos_abertos: 1,
  abrigos_cadastrados: 1,
  pessoas_abrigadas: 42,
  desabrigados: 50,
  parcial: false,
  abertos_sem_contagem: 0,
  atualizado_em: AGORA,
  atualizado_por_nome: "Mari Siqueira",
};

function base() {
  return {
    "/auth/eu": usuarioTeste(),
    "/territorios": [
      { id: "ds-1", tipo: "distrito", nome_exibicao: "Distrito Sanitário 1", pai_id: "recife" },
      { id: "bairro-afogados", tipo: "bairro", nome_exibicao: "Afogados", pai_id: "ds-1" },
    ],
    "/abrigos": abrigos,
    "/abrigos/situacao": {
      dados: {
        cidade: totaisSit,
        distritos: [],
        ocupacao_atualizada_em: AGORA,
      },
      meta: { fontes: [] },
    },
  };
}

afterEach(() => {
  vi.unstubAllGlobals();
  clienteConsultas.clear();
});

test("a lista tem hora e autor da última atualização, pessoas abrigadas e desabrigados", async () => {
  simularApi(base());
  window.history.pushState({}, "", "/app/situacao");
  render(<App />);
  expect(await screen.findByRole("rowheader", { name: /Escola Municipal Afogados/ })).toBeInTheDocument();
  expect(screen.getByText("de 80 vagas")).toBeInTheDocument();
  expect(screen.getAllByText("42").length).toBeGreaterThan(0);
  expect(screen.getAllByText("50").length).toBeGreaterThan(0);
  expect(screen.getByText("por Mari Siqueira")).toBeInTheDocument();
});

test("atualização rápida manda aberto ou fechado, pessoas abrigadas, desabrigados e a observação", async () => {
  const pedidos = simularApi(base(), { "/abrigos/ab-1": { ...abrigos.itens[0], aberto: false } });
  window.history.pushState({}, "", "/app/situacao");
  render(<App />);
  const u = userEvent.setup();
  await u.click(await screen.findByRole("button", { name: /Atualizar Escola Municipal Afogados/ }));
  const dialogo = await screen.findByRole("dialog", { name: /Atualizar Escola Municipal Afogados/ });
  const abrigadas = within(dialogo).getByLabelText(/Pessoas abrigadas/);
  await u.clear(abrigadas);
  await u.type(abrigadas, "55");
  await u.clear(within(dialogo).getByLabelText(/Desabrigados atendidos/));
  await u.click(within(dialogo).getByRole("radio", { name: "Fechado" }));
  await u.click(within(dialogo).getByRole("button", { name: "Salvar" }));
  await waitFor(() =>
    expect(pedidos.find((p) => p.metodo === "PATCH")).toMatchObject({
      url: expect.stringContaining("/abrigos/ab-1"),
      corpo: { aberto: false, pessoas_abrigadas: 55, desabrigados: null, observacao: null },
    }),
  );
});

test("cadastro pede nome e bairro antes de enviar", async () => {
  const pedidos = simularApi(base(), { "/abrigos": { status: 201, corpo: { id: "ab-2" } } });
  window.history.pushState({}, "", "/app/situacao");
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
  delete b["/abrigos/situacao"];
  simularApi(b);
  window.history.pushState({}, "", "/app/situacao");
  render(<App />);
  expect((await screen.findAllByText("Ainda não disponível.")).length).toBeGreaterThan(0);
  expect(screen.queryByText(/^\d+$/)).not.toBeInTheDocument();
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
  window.history.pushState({}, "", "/app/situacao");
  render(<App />);
  expect(await screen.findByText("Sem informação")).toBeInTheDocument();
  expect(screen.queryByText("Fechado")).not.toBeInTheDocument();
  expect(screen.getByText(/Nenhum está marcado como aberto/)).toBeInTheDocument();
  expect(screen.queryByText(/abertos primeiro/)).not.toBeInTheDocument();
});

test("“Só abertos” sem nenhum aberto explica o que fazer e leva de volta a todos os locais", async () => {
  simularApi({ ...base(), "/abrigos?aberto=true": { itens: [], totais: { abrigos_abertos: 0 } } });
  window.history.pushState({}, "", "/app/situacao");
  render(<App />);
  const u = userEvent.setup();
  await u.click(await screen.findByRole("radio", { name: "Só abertos" }));
  expect(await screen.findByText("Nenhum abrigo aberto registrado.")).toBeInTheDocument();
  expect(screen.getByText(/marcado como aberto/)).toBeInTheDocument();
  await u.click(screen.getByRole("button", { name: "Ver todos os locais" }));
  expect(await screen.findByRole("rowheader", { name: /Escola Municipal Afogados/ })).toBeInTheDocument();
});

test("Editar dados manda só capacidade, endereço e observação (PATCH), sem ocupação", async () => {
  const pedidos = simularApi(base(), { "/abrigos/ab-1": abrigos.itens[0] });
  window.history.pushState({}, "", "/app/situacao");
  render(<App />);
  const u = userEvent.setup();
  await u.click(await screen.findByRole("button", { name: /Editar dados de Escola Municipal Afogados/ }));
  const dialogo = await screen.findByRole("dialog", { name: /Editar dados de Escola Municipal Afogados/ });
  const cap = within(dialogo).getByLabelText("Capacidade em pessoas");
  await u.clear(cap);
  await u.type(cap, "120");
  await u.type(within(dialogo).getByLabelText("Observação"), "Confirmado por ligação em 04/11.");
  await u.click(within(dialogo).getByRole("button", { name: "Salvar" }));
  await waitFor(() => expect(pedidos.find((p) => p.metodo === "PATCH")).toBeTruthy());
  const corpo = pedidos.find((p) => p.metodo === "PATCH")?.corpo as Record<string, unknown>;
  expect(corpo).toEqual({
    capacidade: 120,
    endereco: "Rua Exemplo, 10",
    observacao: "Confirmado por ligação em 04/11.",
  });
});

test("sem capacidade: “sem dado” e “Informar” abre o mesmo diálogo; quem só consulta não vê", async () => {
  const sem = { ...abrigos, itens: [{ ...abrigos.itens[0], capacidade: null }] };
  simularApi({ ...base(), "/abrigos": sem });
  window.history.pushState({}, "", "/app/situacao");
  render(<App />);
  const u = userEvent.setup();
  await u.click(await screen.findByRole("button", { name: /Informar capacidade de Escola/ }));
  expect(await screen.findByRole("dialog", { name: /Editar dados de/ })).toBeInTheDocument();
});

test("o histórico mostra capacidade e endereço quando mudaram", async () => {
  simularApi({
    ...base(),
    "/abrigos/ab-1/historico": [
      {
        id: 1,
        em: AGORA,
        autor_nome: "Mari Siqueira",
        aberto: true,
        alteracoes: {
          capacidade: { de: null, para: 120 },
          endereco: { de: "Rua A", para: "Rua B, 20" },
        },
      },
    ],
  });
  window.history.pushState({}, "", "/app/situacao");
  render(<App />);
  const u = userEvent.setup();
  await u.click(await screen.findByRole("button", { name: /Histórico de Escola Municipal Afogados/ }));
  expect(await screen.findByText("Capacidade: de sem dado para 120 pessoas")).toBeInTheDocument();
  expect(screen.getByText("Endereço: de Rua A para Rua B, 20")).toBeInTheDocument();
});
