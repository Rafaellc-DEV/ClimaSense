import { render, screen, within } from "@testing-library/react";
import { App } from "@/app/App";
import { AGORA, simularApi, usuarioTeste } from "@/features/evento/testes";
import { clienteConsultas } from "@/lib/api";

const bloco = (extra = {}) => ({
  abrigos_abertos: 2,
  abrigos_cadastrados: 4,
  pessoas_abrigadas: 60,
  desabrigados: 14,
  parcial: false,
  abertos_sem_contagem: 0,
  atualizado_em: AGORA,
  atualizado_por_nome: "Mari Lima",
  ...extra,
});
const distrito = (id: string, nome: string, extra = {}) => ({
  distrito_id: id,
  distrito_nome: nome,
  ...bloco(extra),
});

const FONTES = [
  { id: "recife-abrigos", nome: "Feed do COP", atualizado_em: AGORA, desatualizado: false },
  {
    id: "recife-abrigos-ocupacao",
    nome: "Registro da equipe (ocupação e desabrigados)",
    atualizado_em: AGORA,
    desatualizado: false,
  },
];

function api(situacao: unknown, meta: unknown = { fontes: FONTES }) {
  return {
    "/auth/eu": usuarioTeste(),
    "/abrigos/situacao": { dados: situacao, meta },
    "/abrigos": { itens: [], totais: {} },
    "/territorios/prioridade": {
      dados: {
        itens: [
          { territorio_id: "ds-7", nome: "Distrito Sanitário VII", nivel: "distrito", posicao: 1 },
          { territorio_id: "ds-2", nome: "Distrito Sanitário II", nivel: "distrito", posicao: 2 },
          { territorio_id: "ds-1", nome: "Distrito Sanitário I", nivel: "distrito", posicao: 3 },
        ],
      },
      meta: { fontes: [] },
    },
  };
}

afterEach(() => {
  vi.unstubAllGlobals();
  clienteConsultas.clear();
});

test("mostra os dois números da cidade com fonte e hora, e a tabela com o distrito mais vulnerável primeiro", async () => {
  simularApi(
    api({
      cidade: bloco({ abrigos_abertos: 5, desabrigados: 120 }),
      distritos: [
        distrito("ds-1", "Distrito Sanitário I"),
        distrito("ds-2", "Distrito Sanitário II"),
        distrito("ds-7", "Distrito Sanitário VII"),
      ],
      ocupacao_atualizada_em: AGORA,
    }),
  );
  window.history.pushState({}, "", "/app/situacao");
  render(<App />);
  const cidade = await screen.findByRole("region", { name: "Recife" });
  const abertos = await within(cidade).findByRole("group", { name: "Abrigos abertos" });
  expect(within(abertos).getByText("5")).toBeInTheDocument();
  const des = within(cidade).getByRole("group", { name: "Desabrigados" });
  expect(within(des).getByText("120")).toBeInTheDocument();
  expect(within(des).getByText(/Registro da equipe/)).toBeInTheDocument();
  const tabela = await screen.findByRole("table", { name: /por distrito sanitário/ });
  const linhas = within(tabela).getAllByRole("row").slice(1);
  expect(linhas.map((l) => within(l).getAllByRole("rowheader")[0].textContent)).toEqual([
    "DS VII",
    "DS II",
    "DS I",
  ]);
});

test("sem dado vira Dados insuficientes, nunca zero; soma parcial é dita", async () => {
  simularApi(
    api({
      cidade: bloco({ abrigos_abertos: null, desabrigados: 9, parcial: true, abertos_sem_contagem: 2 }),
      distritos: [distrito("ds-7", "Distrito Sanitário VII", { pessoas_abrigadas: null, parcial: true })],
      ocupacao_atualizada_em: AGORA,
    }),
  );
  window.history.pushState({}, "", "/app/situacao");
  render(<App />);
  const cidade = await screen.findByRole("region", { name: "Recife" });
  const abertos = await within(cidade).findByRole("group", { name: "Abrigos abertos" });
  expect(within(abertos).getByText("Dados insuficientes")).toBeInTheDocument();
  expect(within(cidade).getByText("Soma parcial")).toBeInTheDocument();
  const tabela = await screen.findByRole("table", { name: /por distrito sanitário/ });
  expect(within(tabela).getAllByText("Dados insuficientes").length).toBeGreaterThan(0);
  expect(within(tabela).getAllByText("soma parcial").length).toBeGreaterThan(0);
});

test("fonte vencida ou sem hora aparece com aviso, e a falta é nomeada", async () => {
  simularApi(
    api(
      { cidade: bloco({ desabrigados: null }), distritos: [], ocupacao_atualizada_em: null },
      {
        fontes: [
          {
            id: "recife-abrigos",
            nome: "Feed do COP",
            atualizado_em: "2026-01-01T00:00:00Z",
            desatualizado: true,
          },
          {
            id: "recife-abrigos-ocupacao",
            nome: "Registro da equipe",
            atualizado_em: null,
            desatualizado: null,
          },
        ],
      },
    ),
  );
  window.history.pushState({}, "", "/app/situacao");
  render(<App />);
  const cidade = await screen.findByRole("region", { name: "Recife" });
  expect((await within(cidade).findAllByText("Desatualizado"))[0]).toBeInTheDocument();
  expect(within(cidade).getAllByText(/falta a fonte Registro da equipe/)[0]).toBeInTheDocument();
});
