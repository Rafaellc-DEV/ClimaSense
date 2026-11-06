import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { App } from "@/app/App";
import { simularApi, usuarioTeste } from "@/features/evento/testes";
import { clienteConsultas } from "@/lib/api";
import { agruparPorDistrito } from "./TelaSaude";

const HORA = new Date(Date.now() - 3 * 3_600_000).toISOString();
const FONTES = [
  { id: "infodengue", nome: "InfoDengue", atualizado_em: HORA, limite_frescor_h: 48, desatualizado: true },
  {
    id: "sinan-lepto",
    nome: "SINAN/DATASUS",
    atualizado_em: null,
    limite_frescor_h: null,
    desatualizado: null,
  },
];
const TITULO = "Valor pequeno omitido para proteger a privacidade";
const agravo = (a: string, nome: string, fonte_id: string, casos: number | null, suprimido = false) => ({
  agravo: a,
  nome,
  fonte_id,
  ultima_semana: null,
  casos,
  suprimido,
  casos_estimados: null,
  variacao_4s_pct: null,
  nivel_alerta: null,
  incompleta: false,
});

function api() {
  return {
    "/auth/eu": usuarioTeste(),
    "/saude/resumo": {
      dados: {
        agravos: [
          agravo("dengue", "Dengue", "infodengue", 36),
          agravo("chikungunya", "Chikungunya", "infodengue", null, true),
          agravo("leptospirose", "Leptospirose", "sinan-lepto", null),
        ],
        janela_leptospirose: null,
        gerado_em: HORA,
      },
      meta: { fontes: FONTES, avisos: [], supressao_minima: 5 },
    },
    "/saude/semanal": { dados: { itens: [], chuva: [] }, meta: { fontes: FONTES } },
    "/territorios": [
      { id: "ds-6", tipo: "distrito", nome_exibicao: "Distrito Sanitário VI", pai_id: "recife" },
      { id: "b1", tipo: "bairro", nome_exibicao: "Ibura", pai_id: "ds-6" },
      { id: "b2", tipo: "bairro", nome_exibicao: "Cohab", pai_id: "ds-6" },
    ],
    "/saude/bairros": {
      dados: {
        ano: 2025,
        anos_disponiveis: [2025],
        itens: [
          { bairro_id: "b1", bairro_nome: "Ibura", distrito_id: "ds-6", casos: 120, suprimido: false },
          { bairro_id: "b2", bairro_nome: "Cohab", distrito_id: "ds-6", casos: null, suprimido: true },
          { bairro_id: "b3", bairro_nome: "Casa Forte", distrito_id: "ds-3", casos: null, suprimido: true },
          { bairro_id: "b4", bairro_nome: "Aflitos", distrito_id: "ds-2", casos: null, suprimido: false },
        ],
      },
      meta: { fontes: FONTES, supressao_minima: 5 },
    },
  };
}

afterEach(() => {
  vi.unstubAllGlobals();
  clienteConsultas.clear();
});

test("fonte vencida mostra o selo Desatualizado com a hora; fonte sem dado mostra Dados insuficientes e o nome", async () => {
  simularApi(api());
  window.history.pushState({}, "", "/app/saude");
  render(<App />);
  const kpis = await screen.findByRole("region", { name: "Casos na última semana" });
  expect((await within(kpis).findAllByText("Desatualizado")).length).toBeGreaterThan(0);
  expect(within(kpis).getAllByText(/InfoDengue, atualizado há 3 h/).length).toBeGreaterThan(0);
  expect(within(kpis).getAllByText(/falta a fonte SINAN\/DATASUS/).length).toBeGreaterThan(0);
  expect(screen.getByText(/Atualizado às \d\d:\d\d/)).toBeInTheDocument();
});

test("contagem suprimida aparece como “< 5” com a explicação, nunca como zero, e sem barra", async () => {
  simularApi(api());
  window.history.pushState({}, "", "/app/saude");
  render(<App />);
  const u = userEvent.setup();
  const ranking = await screen.findByRole("list", { name: "Casos de dengue por distrito" });
  const itens = within(ranking).getAllByRole("listitem");
  // com valor primeiro; depois os omitidos; por último os sem registro
  expect(itens).toHaveLength(3);
  expect(itens[0]).toHaveTextContent(/^DS VI/);
  expect(itens[1]).toHaveTextContent(/^DS III/);
  expect(itens[2]).toHaveTextContent(/^DS II/);
  // DS VI tem um bairro com 120 e outro omitido: a soma vale “no mínimo”
  expect(itens[0]).toHaveTextContent("≥");
  expect(within(itens[1]).getAllByTitle(TITULO)[0]).toHaveTextContent("< 5");
  expect(itens[1].querySelector("span[style]")).toBeNull();
  expect(itens[2]).toHaveTextContent("sem registro");
  expect(within(ranking).queryByText("0")).not.toBeInTheDocument();

  await u.click(screen.getByRole("button", { name: "Bairros de DS VI" }));
  const lista = await screen.findByRole("list", { name: "Lista de bairros de DS VI" });
  expect(within(lista).getByTitle(TITULO)).toHaveTextContent("< 5");
  expect(within(lista).queryByText("0")).not.toBeInTheDocument();
});

test("cartão do agravo com contagem suprimida mostra “< 5”, não “Sem dado”", async () => {
  simularApi(api());
  window.history.pushState({}, "", "/app/saude");
  render(<App />);
  const kpis = await screen.findByRole("region", { name: "Casos na última semana" });
  expect(await within(kpis).findByTitle(TITULO)).toBeInTheDocument();
});

test("agrupar por distrito: só omitidos vira suprimido; mistura vira parcial", () => {
  const r = agruparPorDistrito([
    { bairro_id: "a", bairro_nome: "A", distrito_id: "ds-1", casos: null, suprimido: true },
    { bairro_id: "b", bairro_nome: "B", distrito_id: "ds-2", casos: 7, suprimido: false },
    { bairro_id: "c", bairro_nome: "C", distrito_id: "ds-2", casos: null, suprimido: true },
  ]);
  expect(r.find((x) => x.id === "ds-1")).toMatchObject({ casos: null, suprimido: true });
  expect(r.find((x) => x.id === "ds-2")).toMatchObject({ casos: 7, parcial: true });
});
