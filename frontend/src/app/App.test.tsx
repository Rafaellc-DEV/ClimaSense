import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { clienteConsultas } from "@/lib/api";
import { App } from "./App";

const AVISO = {
  id: "a1",
  titulo: "Alerta de alagamento em Afogados",
  nivel: "alerta",
  territorios: [
    { id: "bairro-afogados", tipo: "bairro", nome_exibicao: "Afogados" },
    { id: "bairro-mustardinha", tipo: "bairro", nome_exibicao: "Mustardinha" },
  ],
  texto: "Chuva forte prevista para a tarde.",
  orientacoes: ["Evite atravessar ruas alagadas."],
  validade_inicio: "2026-10-15T12:00:00Z",
  validade_fim: "2099-10-16T21:00:00Z",
  emitido_por: "Vigilância em Saúde do Recife",
  publicado_em: "2026-10-15T17:20:00Z",
  publico: "populacao",
};

function respostas(mapa: Record<string, { status: number; corpo?: unknown }>) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => {
      const chave = Object.keys(mapa)
        .sort((a, b) => b.length - a.length)
        .find((k) => url.includes(k));
      const r = chave ? mapa[chave] : { status: 404, corpo: { detail: "não encontrado" } };
      return new Response(JSON.stringify(r.corpo ?? {}), { status: r.status });
    }),
  );
}

// A landing pública está desligada por padrão (ADR 0011); estes testes cobrem o código dela, então ligam a chave.
beforeEach(() => {
  vi.stubEnv("VITE_FUNC_LANDING_PUBLICA", "1");
});

afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
  clienteConsultas.clear();
});

test("a página inicial mostra o estado real dos avisos e os telefones de emergência", async () => {
  respostas({
    "/auth/eu": { status: 401 },
    "/publico/estado": {
      status: 200,
      corpo: {
        avisos_ativos: 2,
        distritos_afetados: ["ds-5"],
        niveis_por_distrito: { "ds-5": "alerta" },
        nivel_mais_alto: "alerta",
        principal: AVISO,
        atualizado_em: "2026-10-15T21:04:00Z",
      },
    },
    "/publico/avisos": { status: 200, corpo: [AVISO] },
    "/publico/fontes": { status: 200, corpo: [] },
  });
  window.history.pushState({}, "", "/");
  render(<App />);
  expect(await screen.findByText(/^Alerta para 2 bairros até/)).toBeInTheDocument();
  expect(await screen.findByText(/E mais 1 aviso em vigor/)).toBeInTheDocument();
  expect(screen.getAllByRole("link", { name: /Defesa Civil, 199/ })[0]).toHaveAttribute("href", "tel:199");
  // o distrito afetado aparece em texto, não só em cor (RN-17); o mapa fica na aba “Mapa”
  await userEvent.setup().click(screen.getByRole("tab", { name: "Mapa" }));
  const linha = (await screen.findAllByText("Distrito Sanitário 5"))
    .map((e) => e.closest("li"))
    .find(Boolean);
  expect(linha).toHaveAttribute("data-afetado", "true");
  expect(linha).toHaveTextContent("Alerta");
});

test("sem aviso, a página nunca diz “sem risco”", async () => {
  respostas({
    "/auth/eu": { status: 401 },
    "/publico/estado": {
      status: 200,
      corpo: {
        avisos_ativos: 0,
        distritos_afetados: [],
        niveis_por_distrito: {},
        nivel_mais_alto: null,
        principal: null,
        atualizado_em: "2026-10-15T21:04:00Z",
      },
    },
    "/publico/avisos": { status: 200, corpo: [] },
    "/publico/fontes": { status: 200, corpo: [] },
  });
  window.history.pushState({}, "", "/");
  render(<App />);
  expect(await screen.findByText("Nenhum comunicado em vigor agora.")).toBeInTheDocument();
  expect(screen.getByText(/Isso não significa ausência de risco/)).toBeInTheDocument();
  expect(screen.queryByText(/sem risco|tudo seguro/i)).not.toBeInTheDocument();
});

test("se a API falha, a página diz que não foi possível verificar — nunca “sem aviso”", async () => {
  respostas({ "/auth/eu": { status: 401 }, "/publico/estado": { status: 503 }, "/publico": { status: 503 } });
  window.history.pushState({}, "", "/");
  render(<App />);
  expect(
    await screen.findByText(/Não foi possível verificar os avisos agora/, {}, { timeout: 4000 }),
  ).toBeInTheDocument();
  expect(screen.queryByText(/Nenhum aviso ativo publicado/)).not.toBeInTheDocument();
});

test("a área da equipe sem sessão leva ao login (e o endereço antigo /equipe também)", async () => {
  respostas({ "/auth/eu": { status: 401 } });
  window.history.pushState({}, "", "/equipe");
  render(<App />);
  expect(await screen.findByRole("heading", { name: "Acesso da equipe" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Mostrar senha" })).toBeInTheDocument();
});
