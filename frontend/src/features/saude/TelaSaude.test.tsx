import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { App } from "@/app/App";
import { simularApi, usuarioTeste } from "@/features/evento/testes";
import { clienteConsultas } from "@/lib/api";
import { bairrosDoDistrito } from "./bairros";
import { agruparPorDistrito, CHECKLIST_LEPTO, fraseAgravo } from "./TelaSaude";

const RESUMO_SAUDE = {
  dados: {
    agravos: [
      {
        agravo: "dengue",
        nome: "Dengue",
        fonte_id: "infodengue",
        ultima_semana: { ano: 2026, semana: 43, inicio: "2026-10-25" },
        casos: 36,
        casos_estimados: 221,
        variacao_4s_pct: 18,
        nivel_alerta: 2,
        incompleta: true,
      },
      {
        agravo: "chikungunya",
        nome: "Chikungunya",
        fonte_id: "infodengue",
        ultima_semana: { ano: 2026, semana: 43, inicio: "2026-10-25" },
        casos: 4,
        casos_estimados: null,
        variacao_4s_pct: -5,
        nivel_alerta: 1,
        incompleta: false,
      },
      {
        agravo: "leptospirose",
        nome: "Leptospirose",
        fonte_id: "sinan-lepto",
        ultima_semana: null,
        casos: null,
        casos_estimados: null,
        variacao_4s_pct: null,
        nivel_alerta: null,
        incompleta: false,
      },
    ],
    janela_leptospirose: {
      ativa: true,
      inicio: "2026-10-27",
      fim: "2026-11-26",
      motivo: "Alagamento registrado no Ibura.",
      territorios: [{ id: "ds-6", nome: "Distrito Sanitário VI" }],
    },
    gerado_em: "2026-11-05T12:00:00Z",
  },
  meta: { fontes: [], avisos: [] },
};

function base() {
  return {
    "/auth/eu": usuarioTeste(),
    "/painel/resumo": {
      contadores: { avaliacoes: 0, comunicados: 0 },
      fontes: [
        {
          id: "infodengue",
          nome: "InfoDengue",
          status: "atualizada",
          ultima_atualizacao: "2026-11-05T12:00:00Z",
        },
      ],
    },
    "/saude/resumo": RESUMO_SAUDE,
    "/territorios": [
      { id: "ds-6", tipo: "distrito", nome_exibicao: "Distrito Sanitário VI", pai_id: "recife" },
      { id: "bairro-ibura", tipo: "bairro", nome_exibicao: "Ibura", pai_id: "ds-6" },
      { id: "bairro-cohab", tipo: "bairro", nome_exibicao: "Cohab", pai_id: "ds-6" },
      { id: "bairro-boa-viagem", tipo: "bairro", nome_exibicao: "Boa Viagem", pai_id: "ds-6" },
      { id: "bairro-imbiribeira", tipo: "bairro", nome_exibicao: "Imbiribeira", pai_id: "ds-6" },
    ],
    "/saude/semanal": {
      dados: {
        itens: [
          {
            ano: 2026,
            semana: 41,
            inicio: "2026-10-11",
            casos: 50,
            casos_estimados: 52,
            ic_inf: null,
            ic_sup: null,
            nivel_alerta: 2,
            incompleta: false,
          },
          {
            ano: 2026,
            semana: 42,
            inicio: "2026-10-18",
            casos: 61,
            casos_estimados: 70,
            ic_inf: null,
            ic_sup: null,
            nivel_alerta: 2,
            incompleta: false,
          },
          {
            ano: 2026,
            semana: 43,
            inicio: "2026-10-25",
            casos: 36,
            casos_estimados: 221,
            ic_inf: 123,
            ic_sup: 414,
            nivel_alerta: 2,
            incompleta: true,
          },
        ],
        chuva: [
          { inicio: "2026-10-11", chuva_mm: 12 },
          { inicio: "2026-10-18", chuva_mm: null },
          { inicio: "2026-10-25", chuva_mm: 40 },
        ],
      },
    },
    "/saude/bairros": {
      dados: {
        ano: 2025,
        anos_disponiveis: [2024, 2025],
        itens: [
          { bairro_id: "bairro-ibura", bairro_nome: "Ibura", distrito_id: "ds-6", casos: 120 },
          { bairro_id: "bairro-cohab", bairro_nome: "Cohab", distrito_id: "ds-6", casos: 80 },
          { bairro_id: "bairro-boa-viagem", bairro_nome: "Boa Viagem", distrito_id: "ds-6", casos: null },
          { bairro_id: "bairro-casa-forte", bairro_nome: "Casa Forte", distrito_id: "ds-3", casos: 150 },
        ],
      },
    },
  };
}

afterEach(() => {
  vi.unstubAllGlobals();
  clienteConsultas.clear();
});

test("janela de leptospirose com checklist, KPIs por agravo, gráfico semanal e ranking", async () => {
  const pedidos = simularApi(base());
  window.history.pushState({}, "", "/app/saude");
  render(<App />);
  expect(
    await screen.findByRole("heading", {
      name: "Janela de vigilância de leptospirose até 26/11: 30 dias após o alagamento de 27/10",
    }),
  ).toBeInTheDocument();
  for (const item of CHECKLIST_LEPTO) expect(screen.getByText(item)).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /Nota Técnica 138\/2022/ })).toBeInTheDocument();

  expect(
    screen.getByText(
      "36 casos na semana de 25/10, 18% a mais que nas 4 semanas anteriores. Nível de alerta 2 de 4: atenção.",
    ),
  ).toBeInTheDocument();
  expect(screen.getByText("Nível 2, amarelo")).toBeInTheDocument();
  expect(screen.getByText(/Os últimos dias ainda estão chegando/)).toBeInTheDocument();
  expect(
    screen.getByText("Casos por semana e chuva: depois de chuva forte os casos sobem?"),
  ).toBeInTheDocument();
  // leptospirose sem dado: “Sem dado”, nunca zero
  const kpis = screen.getByRole("region", { name: "Casos na última semana" });
  expect(within(kpis).getAllByText(/sem dado/i).length).toBeGreaterThan(0);
  expect(within(kpis).queryByText("0")).not.toBeInTheDocument();

  expect(await screen.findByRole("region", { name: "Dengue nos últimos 12 meses" })).toBeInTheDocument();
  expect(pedidos.some((p) => p.url.includes("/saude/semanal?agravo=dengue&desde="))).toBe(true);

  const ranking = await screen.findByRole("list", { name: "Casos de dengue por distrito" });
  expect(within(ranking).getAllByRole("listitem")[0]).toHaveTextContent("DS VI");
  expect(within(ranking).getAllByRole("listitem")[0]).toHaveTextContent("200");
  expect(screen.getByText(/leptospirose só tem dado do Recife inteiro/)).toBeInTheDocument();
});

test("trocar o agravo do gráfico e o recorte do ranking pede os dados certos", async () => {
  const pedidos = simularApi(base());
  window.history.pushState({}, "", "/app/saude");
  render(<App />);
  const u = userEvent.setup();
  await screen.findByRole("region", { name: "Dengue nos últimos 12 meses" });
  await u.click(
    within(screen.getByRole("group", { name: "Agravo do gráfico" })).getByLabelText("Leptospirose"),
  );
  await waitFor(() => expect(pedidos.some((p) => p.url.includes("agravo=leptospirose"))).toBe(true));
  await u.click(within(screen.getByRole("group", { name: "Agrupar por" })).getByLabelText("Bairro"));
  const ranking = await screen.findByRole("list", { name: "Casos de dengue por bairro" });
  expect(
    within(ranking)
      .getAllByRole("listitem")
      .map((l) => l.firstChild?.textContent),
  ).toEqual(["Casa Forte", "Ibura", "Cohab", "Boa Viagem"]);
  expect(within(ranking).getAllByRole("listitem")[3]).toHaveTextContent("sem registro");
  await u.selectOptions(screen.getByLabelText("Ano"), "2024");
  await waitFor(() =>
    expect(pedidos.some((p) => p.url.includes("/saude/bairros?agravo=dengue&ano=2024"))).toBe(true),
  );
});

test("sem as rotas de saúde (404), um aviso só: ainda não disponível", async () => {
  const b = base() as Record<string, unknown>;
  for (const k of ["/saude/resumo", "/saude/semanal", "/saude/bairros"]) delete b[k];
  simularApi(b);
  window.history.pushState({}, "", "/app/saude");
  render(<App />);
  await waitFor(() => expect(screen.getByText("Ainda não disponível.")).toBeInTheDocument());
  expect(screen.getAllByText("Ainda não disponível.")).toHaveLength(1);
  expect(screen.queryByText(/Janela de vigilância/)).not.toBeInTheDocument();
});

test("agrupar por distrito soma os bairros e não transforma falta de dado em zero", () => {
  const r = agruparPorDistrito([
    { bairro_id: "a", bairro_nome: "A", distrito_id: "ds-1", casos: null },
    { bairro_id: "b", bairro_nome: "B", distrito_id: "ds-2", casos: 3 },
    { bairro_id: "c", bairro_nome: "C", distrito_id: "ds-2", casos: null },
  ]);
  expect(r.find((x) => x.id === "ds-1")?.casos).toBeNull();
  expect(r.find((x) => x.id === "ds-2")?.casos).toBe(3);
});

test("o (i) do distrito abre por clique, lista todos os bairros (sem registro, nunca zero) e fecha com Esc", async () => {
  simularApi(base());
  window.history.pushState({}, "", "/app/saude");
  render(<App />);
  const u = userEvent.setup();
  const botao = await screen.findByRole("button", { name: "Bairros de DS VI" });
  expect(botao).toHaveAttribute("aria-expanded", "false");
  await u.click(botao);
  expect(botao).toHaveAttribute("aria-expanded", "true");
  const lista = await screen.findByRole("list", { name: "Lista de bairros de DS VI" });
  const itens = within(lista).getAllByRole("listitem");
  expect(itens.map((i) => i.textContent)).toEqual([
    "Ibura120",
    "Cohab80",
    "Boa Viagemsem registro",
    "Imbiribeirasem registro",
  ]);
  expect(within(lista).queryByText("0")).not.toBeInTheDocument();
  await u.keyboard("{Escape}");
  expect(botao).toHaveAttribute("aria-expanded", "false");
  // pelo teclado
  botao.focus();
  await u.keyboard("{Enter}");
  expect(botao).toHaveAttribute("aria-expanded", "true");
});

test("bairrosDoDistrito junta /territorios e os casos; sem registro vai ao fim", () => {
  const r = bairrosDoDistrito(
    "ds-1",
    [
      { id: "b1", tipo: "bairro", nome_exibicao: "Zumbi", pai_id: "ds-1" },
      { id: "b2", tipo: "bairro", nome_exibicao: "Alto", pai_id: "ds-1" },
      { id: "b3", tipo: "bairro", nome_exibicao: "Outro", pai_id: "ds-2" },
    ],
    [{ bairro_id: "b1", bairro_nome: "Zumbi", distrito_id: "ds-1", casos: 5 }],
  );
  expect(r.map((b) => [b.nome, b.casos])).toEqual([
    ["Zumbi", 5],
    ["Alto", null],
  ]);
});

test("frase do indicador: sobe, desce, estável e sem dado", () => {
  const item = {
    agravo: "dengue" as const,
    nome: "Dengue",
    fonte_id: "x",
    ultima_semana: { ano: 2026, semana: 43, inicio: "2026-10-25" },
    casos: 1,
    casos_estimados: null,
    variacao_4s_pct: -30,
    nivel_alerta: 1 as const,
    incompleta: false,
  };
  expect(fraseAgravo(item)).toBe(
    "1 caso na semana de 25/10, 30% a menos que nas 4 semanas anteriores. Nível de alerta 1 de 4: situação normal.",
  );
  expect(fraseAgravo({ ...item, variacao_4s_pct: 2, nivel_alerta: null })).toContain("quase o mesmo");
  expect(fraseAgravo({ ...item, casos: null })).toBe("Sem dado desta semana.");
  expect(fraseAgravo(undefined)).toBe("Sem dado desta semana.");
});
