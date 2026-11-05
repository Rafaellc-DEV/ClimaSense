import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { App } from "@/app/App";
import { simularApi, usuarioTeste } from "@/features/evento/testes";
import { clienteConsultas } from "@/lib/api";
import { eventoAtual, montarLinha } from "./linhaTempo";

const acao = (id: string, descricao: string, em: string, extra = {}) => ({
  id,
  territorio_id: "recife",
  territorio_nome: "Recife inteiro",
  tipo: "outro",
  descricao,
  situacao: "concluida",
  inicio_em: em,
  criada_em: em,
  autor_nome: "Mari Lima",
  ...extra,
});

function base(permissoes = ["consultar", "editar"]) {
  return {
    "/auth/eu": usuarioTeste(permissoes),
    "/painel/resumo": { contadores: { avaliacoes: 0, comunicados: 0 }, fontes: [] },
    "/territorios": [],
    "/acoes": {
      itens: [
        acao("1", "Evento encerrado.", "2026-05-01T12:00:00Z", {
          licao_aprendida: "Avisar o DS VIII mais cedo.",
        }),
        acao("2", "Orientação às equipes do Ibura.", "2026-05-15T10:50:00Z", {
          territorio_id: "bairro-ibura",
          territorio_nome: "Ibura",
        }),
        acao("3", "Boletim emitido: BOL-2026-0515-1100", "2026-05-15T14:00:00Z"),
      ],
    },
    "/estagios/historico": [
      {
        id: "h1",
        lote_id: "l1",
        territorio_id: "ds-5",
        territorio_nome: "Distrito Sanitário V",
        estagio: "alerta",
        justificativa: "Chuva de 60 mm.",
        autor_nome: "Mari Siqueira",
        declarado_em: "2026-05-15T10:40:00Z",
      },
      {
        id: "h2",
        lote_id: "l1",
        territorio_id: "ds-6",
        territorio_nome: "Distrito Sanitário VI",
        estagio: "alerta",
        justificativa: "Chuva de 60 mm.",
        autor_nome: "Mari Siqueira",
        declarado_em: "2026-05-15T10:40:00Z",
      },
    ],
  };
}

afterEach(() => {
  vi.unstubAllGlobals();
  clienteConsultas.clear();
});

test("a linha do tempo mistura registros, declarações e boletins do evento atual", async () => {
  simularApi(base());
  window.history.pushState({}, "", "/app/registro");
  render(<App />);
  const linha = await screen.findByRole("list", { name: "Linha do tempo do evento" });
  const itens = within(linha).getAllByRole("listitem");
  expect(itens).toHaveLength(3);
  expect(itens[0]).toHaveTextContent("BoletimBOL-2026-0515-1100");
  expect(itens[1]).toHaveTextContent("Ibura: Orientação às equipes do Ibura.");
  expect(itens[2]).toHaveTextContent("DS V, DS VI em Alerta.");
  // o evento anterior fica guardado, com a lição
  expect(screen.getByText(/Eventos anteriores \(1\)/)).toBeInTheDocument();
  expect(screen.getByText("Lição: Avisar o DS VIII mais cedo.")).toBeInTheDocument();
  expect(screen.queryByText(/Planejada|Em andamento|Iniciar/)).not.toBeInTheDocument();
});

test("registrar manda o texto com hora automática; sem território vale o Recife inteiro", async () => {
  const pedidos = simularApi(base(), { "/acoes": { status: 201, corpo: {} } });
  window.history.pushState({}, "", "/app/registro");
  render(<App />);
  const u = userEvent.setup();
  await u.click(await screen.findByRole("button", { name: "Registrar" }));
  expect(await screen.findByText("Escreva o que aconteceu em uma frase.")).toBeInTheDocument();
  await u.type(screen.getByLabelText(/O que aconteceu\?/), "Árvore caída na Av. Recife.");
  await u.click(screen.getByRole("button", { name: "Registrar" }));
  await waitFor(() => expect(pedidos.some((p) => p.metodo === "POST")).toBe(true));
  const corpo = pedidos.find((p) => p.metodo === "POST")?.corpo as Record<string, unknown>;
  expect(corpo).toMatchObject({
    territorio_id: "recife",
    tipo: "outro",
    descricao: "Árvore caída na Av. Recife.",
    situacao: "concluida",
  });
  expect(typeof corpo.inicio_em).toBe("string");
});

test("encerrar o evento faz uma pergunta só e grava a lição", async () => {
  const pedidos = simularApi(base(), { "/acoes": { status: 201, corpo: {} } });
  window.history.pushState({}, "", "/app/registro");
  render(<App />);
  const u = userEvent.setup();
  await u.click(await screen.findByRole("button", { name: "Encerrar evento e registrar lição aprendida" }));
  const dialogo = await screen.findByRole("dialog", { name: "Encerrar o evento" });
  expect(within(dialogo).getAllByRole("textbox")).toHaveLength(1);
  await u.type(
    within(dialogo).getByLabelText("O que funcionou e o que mudar da próxima vez?"),
    "Avisar antes.",
  );
  await u.click(within(dialogo).getByRole("button", { name: "Encerrar evento" }));
  await waitFor(() =>
    expect(pedidos.find((p) => p.metodo === "POST")?.corpo).toMatchObject({
      descricao: "Evento encerrado.",
      licao_aprendida: "Avisar antes.",
    }),
  );
});

test("quem só consulta vê a linha do tempo, sem caixa de registro", async () => {
  simularApi(base(["consultar"]));
  window.history.pushState({}, "", "/app/registro");
  render(<App />);
  await screen.findByRole("list", { name: "Linha do tempo do evento" });
  expect(screen.queryByLabelText(/O que aconteceu\?/)).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: /Encerrar evento/ })).not.toBeInTheDocument();
});

test("sem nenhum encerramento, tudo é o evento atual", () => {
  const l = montarLinha(
    [],
    [{ estagio: "atencao", declarado_em: "2026-05-01T10:00:00Z", territorio_nome: "Distrito Sanitário I" }],
  );
  expect(eventoAtual(l).atual).toHaveLength(1);
  expect(eventoAtual(l).encerrados).toHaveLength(0);
});
