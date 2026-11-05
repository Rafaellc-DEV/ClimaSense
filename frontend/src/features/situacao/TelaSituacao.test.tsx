import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { App } from "@/app/App";
import { AGORA, itemEstagio, simularApi, usuarioTeste } from "@/features/evento/testes";
import { clienteConsultas } from "@/lib/api";
import { fraseAgora, motivosComuns } from "./TelaSituacao";

const COMUM = "A previsão cobre 52 das próximas 72 h.";

const distritos = [
  itemEstagio({
    territorio_id: "ds-1",
    territorio_nome: "Distrito Sanitário I",
    sugerido: {
      estagio: "observacao",
      motivos: ["Nenhum gatilho passou dos limites de atenção.", COMUM],
      insumos: {},
      calculado_em: AGORA,
    },
  }),
  itemEstagio({
    territorio_id: "ds-5",
    territorio_nome: "Distrito Sanitário V",
    sugerido: {
      estagio: "alerta",
      motivos: ["Chuva prevista de 62 mm em 24 h.", COMUM],
      insumos: {},
      calculado_em: AGORA,
    },
    declarado: { estagio: "atencao", justificativa: "x", autor_nome: "Mari Lima", declarado_em: AGORA },
  }),
  itemEstagio({
    territorio_id: "ds-6",
    territorio_nome: "Distrito Sanitário VI",
    sugerido: {
      estagio: "observacao",
      motivos: ["Nenhum gatilho passou dos limites de atenção.", COMUM],
      insumos: {},
      calculado_em: AGORA,
    },
  }),
];
const bairros = [
  itemEstagio({
    territorio_id: "bairro-ibura",
    territorio_nome: "Ibura",
    nivel: "bairro",
    distrito_id: "ds-5",
    sugerido: {
      estagio: "critico",
      motivos: [],
      insumos: { ocorrencias_historicas: 63 },
      calculado_em: AGORA,
    },
  }),
];

function base(permissoes = ["consultar", "editar"]) {
  return {
    "/auth/eu": usuarioTeste(permissoes),
    "/painel/resumo": { contadores: { avaliacoes: 0, comunicados: 0 }, fontes: [] },
    "/estagios?nivel=distrito": { dados: { itens: distritos }, meta: { fontes: [] } },
    "/estagios?nivel=bairro": { itens: bairros },
    "/estagios/parametros": { limiares: { chuva_prev_24h_atencao_mm: 25 }, padrao: true },
    "/abrigos": {
      itens: [{ id: "a1", nome: "Escola Ibura", bairro_nome: "Ibura", aberto: true }],
      totais: { abrigos_abertos: 1, abrigos_cadastrados: 199, atualizado_em: AGORA },
    },
  };
}

afterEach(() => {
  vi.unstubAllGlobals();
  clienteConsultas.clear();
});

test("a frase do topo diz o que fazer; o motivo comum aparece uma vez; APAC e Cemaden uma vez", async () => {
  simularApi(base());
  window.history.pushState({}, "", "/app");
  render(<App />);
  expect(
    await screen.findByText("DS V pede a sua decisão: a sugestão está acima da situação declarada."),
  ).toBeInTheDocument();
  const tabela = screen.getByRole("table", { name: /Situação declarada e sugerida/ });
  expect(within(tabela).getAllByRole("row")).toHaveLength(4);
  expect(screen.getAllByText(new RegExp(COMUM.replace(/\./g, "\\.")))).toHaveLength(1);
  expect(within(tabela).getByText("Chuva prevista de 62 mm em 24 h.")).toBeInTheDocument();
  expect(within(tabela).getAllByText("sem declaração")).toHaveLength(2);
  expect(within(tabela).getByText("acima da declarada")).toBeInTheDocument();
  expect(screen.getAllByRole("link", { name: /Cemaden/ })).toHaveLength(1);
  expect(await screen.findByText("Escola Ibura")).toBeInTheDocument();
  expect(screen.getByText("Como o sistema sugere")).toBeInTheDocument();
  expect(screen.queryByText(/Atenção primeiro|tudo seguro|sem risco/i)).not.toBeInTheDocument();
});

test("os bairros só carregam ao abrir o distrito", async () => {
  const pedidos = simularApi(base());
  window.history.pushState({}, "", "/app");
  render(<App />);
  const u = userEvent.setup();
  const abrir = await screen.findByRole("button", { name: "Bairros de Distrito Sanitário V" });
  expect(pedidos.some((p) => p.url.includes("nivel=bairro"))).toBe(false);
  await u.click(abrir);
  expect(abrir).toHaveAttribute("aria-expanded", "true");
  const lista = await screen.findByRole("list", { name: "Bairros de Distrito Sanitário V" });
  expect(within(lista).getByText("Ibura")).toBeInTheDocument();
  expect(within(lista).getByText("63 alagamentos registrados")).toBeInTheDocument();
});

test("declarar grava a situação e abre a mensagem pronta para o WhatsApp", async () => {
  const pedidos = simularApi(base(), {
    "/estagios/mensagem": { texto: "DS V em Alerta.", wa_me_url: "https://wa.me/?text=DS" },
    "/estagios": { status: 201, corpo: [] },
  });
  window.history.pushState({}, "", "/app");
  render(<App />);
  const u = userEvent.setup();
  await u.click(await screen.findByRole("button", { name: "Declarar situação de Distrito Sanitário V" }));
  const dialogo = await screen.findByRole("dialog", { name: "Declarar situação" });
  await u.type(within(dialogo).getByLabelText(/Justificativa/), "Chuva forte prevista.");
  await u.click(within(dialogo).getByRole("button", { name: "Declarar situação" }));
  await waitFor(() =>
    expect(pedidos.find((p) => p.metodo === "POST" && p.url.endsWith("/estagios"))?.corpo).toEqual({
      territorio_ids: ["ds-5"],
      estagio: "alerta",
      justificativa: "Chuva forte prevista.",
    }),
  );
  expect(await screen.findByDisplayValue("DS V em Alerta.")).toBeInTheDocument();
});

test("o botão WhatsApp de uma linha gera o texto da situação em vigor", async () => {
  const pedidos = simularApi(base(), {
    "/estagios/mensagem": { texto: "DS I em Observação.", wa_me_url: "https://wa.me/?text=DS" },
  });
  window.history.pushState({}, "", "/app");
  render(<App />);
  await userEvent
    .setup()
    .click(await screen.findByRole("button", { name: "WhatsApp para Distrito Sanitário I" }));
  expect(await screen.findByDisplayValue("DS I em Observação.")).toBeInTheDocument();
  expect(pedidos.find((p) => p.url.endsWith("/estagios/mensagem"))?.corpo).toEqual({
    territorio_ids: ["ds-1"],
    estagio: "observacao",
  });
});

test("sem permissão de editar, não há botão de declarar", async () => {
  simularApi(base(["consultar"]));
  window.history.pushState({}, "", "/app");
  render(<App />);
  await screen.findByRole("table", { name: /Situação declarada e sugerida/ });
  expect(screen.queryByRole("button", { name: /^Declarar/ })).not.toBeInTheDocument();
  expect(screen.getAllByRole("button", { name: /^WhatsApp/ })).toHaveLength(3);
});

test("frase e motivo comum: sem dados nunca vira calmaria", () => {
  const semDados = distritos.map((d) => ({
    ...d,
    declarado: null,
    sugerido: { ...d.sugerido, estagio: "sem_dados" as const, faltando: ["previsão de maré"] },
  }));
  expect(fraseAgora(semDados, [])).toBe(
    "O sistema não consegue sugerir agora: falta previsão de maré. Declare pelo que a equipe sabe.",
  );
  const calmos = distritos.map((d) => ({
    ...d,
    declarado: null,
    sugerido: { ...d.sugerido, estagio: "observacao" as const },
  }));
  expect(fraseAgora(calmos, [])).toBe("Nada a decidir agora: nenhum distrito passou dos limites.");
  expect(motivosComuns(distritos)).toEqual([COMUM]);
});
