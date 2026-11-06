import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { App } from "@/app/App";
import { AGORA, itemEstagio, simularApi, usuarioTeste } from "@/features/evento/testes";
import { clienteConsultas } from "@/lib/api";
import { fraseAgora, motivosComuns } from "./TelaSituacao";

const INSUMOS = { chuva_24h_mm: 4, chuva_prev_24h_mm: 10, chuva_prev_72h_mm: 22, mare_max_m: 2.1 };
const COMUM = "A previsão cobre 52 das próximas 72 h.";

const distritos = [
  itemEstagio({
    territorio_id: "ds-1",
    territorio_nome: "Distrito Sanitário I",
    sugerido: {
      estagio: "observacao",
      motivos: ["Nenhum gatilho passou dos limites de atenção.", COMUM],
      insumos: INSUMOS,
      calculado_em: AGORA,
    },
  }),
  itemEstagio({
    territorio_id: "ds-5",
    territorio_nome: "Distrito Sanitário V",
    sugerido: {
      estagio: "alerta",
      motivos: ["Chuva prevista de 62 mm em 24 h.", COMUM],
      insumos: INSUMOS,
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
      insumos: INSUMOS,
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
  ...["Aflitos", "Boa Vista"].map((nome) =>
    itemEstagio({
      territorio_id: `bairro-${nome}`,
      territorio_nome: nome,
      nivel: "bairro",
      distrito_id: "ds-1",
    }),
  ),
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

test("a frase do topo diz o que fazer; quem pede decisão sobe; motivo comum e APAC/Cemaden uma vez", async () => {
  simularApi(base());
  window.history.pushState({}, "", "/app/situacao");
  render(<App />);
  expect(
    await screen.findByText("DS V pede a sua decisão: a sugestão está acima da situação declarada."),
  ).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Pedem a sua decisão (1)" })).toBeInTheDocument();
  const cartoes = screen.getAllByRole("article");
  expect(cartoes).toHaveLength(3);
  expect(within(cartoes[0]).getByRole("heading", { name: /DS V/ })).toBeInTheDocument();
  expect(within(cartoes[0]).getByText(/O sistema sugere Alerta/)).toBeInTheDocument();
  expect(within(cartoes[0]).getByText(/a equipe declarou Atenção/)).toBeInTheDocument();
  expect(within(cartoes[0]).getByText("Chuva prevista de 62 mm em 24 h.")).toBeInTheDocument();
  expect(within(cartoes[1]).getByText(/sugerida pelo sistema, ninguém declarou/)).toBeInTheDocument();
  expect(within(cartoes[1]).queryByText(/O sistema sugere/)).not.toBeInTheDocument();
  expect(screen.queryByText("igual ao de cima")).not.toBeInTheDocument();
  expect(screen.getAllByText(new RegExp(COMUM.replace(/\./g, "."))).length).toBe(1);
  expect(screen.getAllByRole("link", { name: /Cemaden/ })).toHaveLength(1);
  expect(await screen.findByText("Escola Ibura")).toBeInTheDocument();
  expect(screen.getByText("Como o sistema sugere")).toBeInTheDocument();
  expect(screen.queryByText(/Atenção primeiro|tudo seguro|sem risco/i)).not.toBeInTheDocument();
});

test("o resumo conta os distritos por situação e mostra a chuva e a maré com a fonte", async () => {
  simularApi(base());
  window.history.pushState({}, "", "/app/situacao");
  render(<App />);
  const contagens = await screen.findByRole("list", { name: "Distritos por situação" });
  expect(
    within(contagens)
      .getAllByRole("listitem")
      .map((li) => li.textContent),
  ).toEqual([
    "2Observação: 2 distritos",
    "1Atenção: 1 distrito",
    "0Alerta: 0 distritos",
    "0Crítico: 0 distritos",
  ]);
  const medidas = screen.getByLabelText("Chuva e maré que importam agora");
  expect(within(medidas).getByText("Choveu nas últimas 24 h")).toBeInTheDocument();
  expect(within(medidas).getByText("Previsto para as próximas 72 h")).toBeInTheDocument();
  expect(within(medidas).getByText("Maré alta prevista")).toBeInTheDocument();
  expect(within(medidas).getByText(/^2,10/)).toBeInTheDocument();
  expect(within(medidas).getAllByText(/Open-Meteo, /).length).toBeGreaterThanOrEqual(3);
});

test("os bairros que passam do distrito aparecem no cartão, com a situação sugerida de cada um", async () => {
  simularApi(base());
  window.history.pushState({}, "", "/app/situacao");
  render(<App />);
  const lista = await screen.findByRole("list", {
    name: "Bairros de Distrito Sanitário V que pedem atenção",
  });
  expect(within(lista).getByText("Ibura")).toBeInTheDocument();
  expect(within(lista).getByText("Crítico")).toBeInTheDocument();
  expect(within(lista).getByText(/63 alagamentos registrados/)).toBeInTheDocument();
  expect(screen.getByText("1 bairro passa do distrito")).toBeInTheDocument();
  expect(screen.getByText("Ver os 2 bairros")).toBeInTheDocument();
});

test("escolher o distrito no cartão marca o destaque; sem falta de dado vira calmaria", async () => {
  simularApi(base());
  window.history.pushState({}, "", "/app/situacao");
  render(<App />);
  const botao = await screen.findByRole("button", { name: /DS I \(Distrito Sanitário I\)/ });
  expect(botao).toHaveAttribute("aria-pressed", "false");
  await userEvent.setup().click(botao);
  expect(botao).toHaveAttribute("aria-pressed", "true");
  expect(botao.closest("article")).toHaveAttribute("data-selecionado", "true");
});

test("quando nada pede decisão, diz isso numa frase e não repete motivos", async () => {
  const calmos = distritos.map((d) => ({ ...d, declarado: null }));
  simularApi({
    ...base(),
    "/estagios?nivel=distrito": {
      dados: {
        itens: calmos.map((d) => ({
          ...d,
          sugerido: { ...d.sugerido, estagio: "observacao" as const },
        })),
      },
      meta: { fontes: [] },
    },
    "/estagios?nivel=bairro": { itens: [] },
  });
  window.history.pushState({}, "", "/app/situacao");
  render(<App />);
  expect(await screen.findByText("Nenhum distrito pede decisão agora.")).toBeInTheDocument();
  expect(screen.queryByRole("heading", { name: /Pedem a sua decisão/ })).not.toBeInTheDocument();
  expect(screen.getAllByRole("article")).toHaveLength(3);
});

test("sem dado nunca vira calmaria: o cartão diz o que falta", async () => {
  simularApi({
    ...base(),
    "/estagios?nivel=distrito": {
      dados: {
        itens: [
          {
            ...distritos[0],
            sugerido: {
              ...distritos[0].sugerido,
              estagio: "sem_dados",
              faltando: ["previsão de chuva"],
              motivos: [],
              insumos: INSUMOS,
            },
          },
          { ...distritos[2], sugerido: { ...distritos[2].sugerido, estagio: "observacao" } },
        ],
      },
      meta: { fontes: [] },
    },
  });
  window.history.pushState({}, "", "/app/situacao");
  render(<App />);
  expect(await screen.findByText("Sem dado: falta previsão de chuva.")).toBeInTheDocument();
  expect(screen.getByText("Sem dado")).toBeInTheDocument();
  expect(screen.queryByText(/tudo seguro|sem risco/i)).not.toBeInTheDocument();
});

test("erro ao carregar mostra o motivo e permite tentar de novo", async () => {
  simularApi({ ...base(), "/estagios?nivel=distrito": { status: 500, corpo: { detail: "Falhou." } } });
  window.history.pushState({}, "", "/app/situacao");
  render(<App />);
  expect(await screen.findByText("Não foi possível carregar.")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /Tentar de novo/ })).toBeInTheDocument();
});

test("declarar grava a situação e abre a mensagem pronta para o WhatsApp", async () => {
  const pedidos = simularApi(base(), {
    "/estagios/mensagem": { texto: "DS V em Alerta.", wa_me_url: "https://wa.me/?text=DS" },
    "/estagios": { status: 201, corpo: [] },
  });
  window.history.pushState({}, "", "/app/situacao");
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
  window.history.pushState({}, "", "/app/situacao");
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
  window.history.pushState({}, "", "/app/situacao");
  render(<App />);
  await screen.findAllByRole("article");
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
