import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { App } from "@/app/App";
import { AGORA, simularApi, usuarioTeste } from "@/features/evento/testes";
import { clienteConsultas } from "@/lib/api";
import { acompanhar } from "./acompanhar";

vi.mock("./acompanhar", async (importar) => ({
  ...(await importar<typeof import("./acompanhar")>()),
  acompanhar: vi.fn(),
}));

afterEach(() => {
  vi.unstubAllGlobals();
  clienteConsultas.clear();
  vi.clearAllMocks();
});

const fonte = (id: string, extra = {}) => ({
  id,
  nome: id,
  orgao: "Teste",
  tipo: "prevista",
  status: "desatualizada",
  ultima_atualizacao: AGORA,
  limite_desatualizacao_h: 6,
  ...extra,
});

test("trava o botão antes do POST e espera a primeira fonte antes de iniciar a próxima", async () => {
  const pedidos = simularApi(
    {
      "/auth/eu": usuarioTeste(["consultar", "executar_etl"], ["administrador"]),
      "/fontes": [
        fonte("open-meteo-previsao"),
        fonte("open-meteo-mare"),
        fonte("inmet", { status: "planejada" }),
      ],
    },
    { "/etl/execucoes": { id: "trabalho", status: "em_andamento" } },
  );
  let concluir!: (e: never) => void;
  vi.mocked(acompanhar).mockImplementationOnce(
    () =>
      new Promise((resolve) => {
        concluir = resolve;
      }),
  );
  vi.mocked(acompanhar).mockResolvedValueOnce({ status: "sucesso", gravados: 0 } as never);
  window.history.pushState({}, "", "/app/fontes");
  render(<App />);
  const botao = await screen.findByRole("button", { name: "Buscar dados mais recentes" });
  fireEvent.click(botao);
  fireEvent.click(botao);
  await waitFor(() => expect(acompanhar).toHaveBeenCalledTimes(1));
  expect(botao).toBeDisabled();
  expect(pedidos.filter((p) => p.metodo === "POST")).toHaveLength(1);
  concluir({ status: "sucesso", gravados: 0 } as never);
  await screen.findByText("Coletas concluídas.");
  expect(pedidos.filter((p) => p.metodo === "POST")).toHaveLength(2);
  expect(screen.getByText(/2 cargas sem novos registros/)).toBeInTheDocument();
  expect(screen.queryByText("Dados atualizados.")).not.toBeInTheDocument();
});

test("mostra só fontes atualizadas: atrasadas, com falha e nunca carregadas não aparecem", async () => {
  simularApi({
    "/auth/eu": usuarioTeste(),
    "/fontes": [
      fonte("open-meteo-previsao", {
        nome: "Previsão em dia",
        status: "atualizada",
        ultima_atualizacao: AGORA,
      }),
      fonte("infodengue", { nome: "Fonte atrasada", status: "desatualizada", ultima_atualizacao: AGORA }),
      fonte("sisagua", { nome: "Fonte com falha", status: "com_falha", ultima_atualizacao: null }),
    ],
  });
  window.history.pushState({}, "", "/app/fontes");
  render(<App />);
  expect(await screen.findByText("Previsão em dia")).toBeInTheDocument();
  expect(screen.queryByText("Fonte atrasada")).not.toBeInTheDocument();
  expect(screen.queryByText("Fonte com falha")).not.toBeInTheDocument();
  expect(screen.queryByText("Nunca carregada")).not.toBeInTheDocument();
});
