import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { App } from "@/app/App";
import { AGORA, simularApi, usuarioTeste } from "@/features/evento/testes";
import { clienteConsultas } from "@/lib/api";

const acao = (id: string, extra = {}) => ({
  id,
  territorio_id: "ds-1",
  territorio_nome: "Distrito Sanitário I",
  distrito_id: "ds-1",
  tipo: "outro",
  descricao: `Ação ${id}`,
  responsavel: "Vigilância",
  situacao: "em_andamento",
  inicio_em: AGORA,
  criada_em: AGORA,
  autor_nome: "Mari Lima",
  ...extra,
});

function base() {
  return {
    "/auth/eu": usuarioTeste(),
    "/territorios/prioridade": {
      dados: {
        itens: [
          { territorio_id: "ds-7", nome: "Distrito Sanitário VII", nivel: "distrito", posicao: 1 },
          { territorio_id: "ds-1", nome: "Distrito Sanitário I", nivel: "distrito", posicao: 2 },
        ],
      },
      meta: { fontes: [] },
    },
    "/territorios": [
      { id: "ds-1", tipo: "distrito", nome_exibicao: "Distrito Sanitário I", pai_id: "recife" },
      { id: "ds-7", tipo: "distrito", nome_exibicao: "Distrito Sanitário VII", pai_id: "recife" },
    ],
    "/acoes": {
      itens: [
        acao("a1"),
        acao("a2", { territorio_id: "ds-7", territorio_nome: "Distrito Sanitário VII", distrito_id: "ds-7" }),
        acao("a3", { situacao: "concluida", fim_em: AGORA }),
      ],
      contagens: {},
      total: 3,
      por_distrito: [],
    },
  };
}

afterEach(() => {
  vi.unstubAllGlobals();
  clienteConsultas.clear();
});

test("lista em andamento com o distrito mais vulnerável primeiro; concluídas ficam recolhidas", async () => {
  simularApi(base());
  window.history.pushState({}, "", "/app/acoes");
  render(<App />);
  const lista = await screen.findByRole("region", { name: /Em andamento \(2\)/ });
  const nomes = within(lista)
    .getAllByText(/^DS (VII|I)$/)
    .map((e) => e.textContent);
  expect(nomes.slice(0, 2)).toEqual(["DS VII", "DS I"]);
  expect(within(lista).getByText(/Concluídas e canceladas \(1\)/)).toBeInTheDocument();
  expect(screen.getByText(/Fonte: registro da equipe/)).toBeInTheDocument();
  expect(screen.queryByText(/lição aprendida/i)).not.toBeInTheDocument();
  expect(screen.getByRole("link", { name: /Relatório executivo/ })).toHaveAttribute(
    "href",
    "/app/acoes/relatorio",
  );
});

test("mudança rápida de status manda PATCH com a situação", async () => {
  const pedidos = simularApi(base(), { "/acoes/a1": acao("a1") });
  window.history.pushState({}, "", "/app/acoes");
  render(<App />);
  const u = userEvent.setup();
  const sel = await screen.findAllByLabelText(/Mudar o status da ação em DS I$/);
  await u.selectOptions(sel[0], "concluida");
  await waitFor(() =>
    expect(pedidos.find((p) => p.metodo === "PATCH")?.corpo).toMatchObject({ situacao: "concluida" }),
  );
});

test("formulário pede distrito e descrição; envia distrito, responsável, status e horário", async () => {
  const pedidos = simularApi(base(), { "/acoes": { status: 201, corpo: acao("n1") } });
  window.history.pushState({}, "", "/app/acoes");
  render(<App />);
  const u = userEvent.setup();
  const form = await screen.findByRole("form", { name: "Registrar ação" });
  await u.click(within(form).getByRole("button", { name: "Registrar ação" }));
  expect(await within(form).findByText("Escolha o distrito.")).toBeInTheDocument();
  expect(within(form).getByText(/Escreva o que foi feito/)).toBeInTheDocument();
  await waitFor(() => expect(within(form).getByLabelText("Distrito")).toBeEnabled());
  await u.selectOptions(within(form).getByLabelText("Distrito"), "ds-7");
  await u.type(within(form).getByLabelText("O que foi feito"), "Visita ao abrigo");
  await u.type(within(form).getByLabelText(/Responsável/), "Assistência Social");
  await u.click(within(form).getByRole("button", { name: "Registrar ação" }));
  await waitFor(() =>
    expect(pedidos.find((p) => p.metodo === "POST")?.corpo).toMatchObject({
      territorio_id: "ds-7",
      descricao: "Visita ao abrigo",
      responsavel: "Assistência Social",
      situacao: "em_andamento",
    }),
  );
});

test("não existe mais Encerrar evento", async () => {
  simularApi(base());
  window.history.pushState({}, "", "/app/acoes");
  render(<App />);
  await screen.findByRole("form", { name: "Registrar ação" });
  expect(screen.queryByText(/Encerrar evento/i)).not.toBeInTheDocument();
});
