import { render, screen, within } from "@testing-library/react";
import { App } from "@/app/App";
import { AGORA, itemEstagio, simularApi, usuarioTeste } from "@/features/evento/testes";
import { clienteConsultas } from "@/lib/api";
import { faixaDeIncerteza, linhasMedidas } from "./dados";
import { normalizarMensagem } from "./Blocos";

const FONTES = [
  { id: "apac-chuva", nome: "Pluviômetros (APAC)", atualizado_em: AGORA, desatualizado: false },
  {
    id: "open-meteo-previsao",
    nome: "Chuva prevista por distrito",
    atualizado_em: AGORA,
    desatualizado: false,
  },
  { id: "open-meteo-mare", nome: "Nível do mar previsto", atualizado_em: AGORA, desatualizado: false },
];

const distrito = (id: string, nome: string, extra = {}) =>
  itemEstagio({
    territorio_id: id,
    territorio_nome: nome,
    sugerido: {
      estagio: "observacao",
      motivos: [],
      insumos: {
        chuva_24h_mm: 12,
        chuva_24h_fontes: ["apac-chuva"],
        chuva_prev_24h_mm: 10,
        chuva_prev_72h_mm: 20,
        mare_max_m: 1.14,
        mare_max_em: AGORA,
        ...extra,
      },
      calculado_em: AGORA,
    },
  });

const hora = (k: number) => ({ t: new Date(Date.parse(AGORA) + k * 3_600_000).toISOString() });
const cenario = {
  dados: {
    territorio_id: "recife",
    territorio_nome: "Recife inteiro",
    previsao_emitida_em: AGORA,
    mare_emitida_em: AGORA,
    chuva: [0, 1, 2].map((k) => ({ ...hora(k), valor: 2, min: 1, max: 4 })),
    mare: [0, 1, 2].map((k) => ({ ...hora(k), valor: 0.5 + k })),
  },
  meta: { fontes: FONTES },
};

function api(itens: unknown[], oficial: unknown = { estagio: null }) {
  return {
    "/auth/eu": usuarioTeste(),
    "/estagios/oficial": { dados: oficial, meta: { fontes: [] } },
    "/estagios?": { dados: { nivel: "distrito", itens }, meta: { fontes: FONTES } },
    "/cenarios/estimativa": cenario,
    "/fontes": [
      { id: "apac-chuva", nome: "x", ultima_atualizacao: AGORA, desatualizado: true },
      { id: "open-meteo-previsao", nome: "x", ultima_atualizacao: AGORA, desatualizado: false },
    ],
  };
}

function abrir() {
  window.history.pushState({}, "", "/app/situacao");
  render(<App />);
}

afterEach(() => {
  vi.unstubAllGlobals();
  clienteConsultas.clear();
});

test("mostra faixa oficial, quatro cartões e distritos com nome Distrito N, cada um com fonte e hora", async () => {
  simularApi(
    api(
      [
        distrito("ds-1", "Distrito Sanitário I", { chuva_24h_mm: 5 }),
        distrito("ds-5", "Distrito Sanitário V", { chuva_24h_mm: 62.4, chuva_prev_24h_mm: 58 }),
        distrito("ds-8", "Distrito Sanitário VIII", { chuva_24h_mm: null }),
      ],
      { estagio: "alerta", informado_em: AGORA, autor_nome: "Mari Lima" },
    ),
  );
  abrir();
  const oficial = await screen.findByRole("region", { name: /Estágio oficial da cidade/ });
  expect(await within(oficial).findByText(/Registrado por Mari Lima/)).toBeInTheDocument();
  const medida = await screen.findByRole("group", { name: "Chuva medida 24 h" });
  expect(await within(medida).findByText("62,4")).toBeInTheDocument();
  expect(within(medida).getByText(/Distrito 5/)).toBeInTheDocument();
  expect(within(medida).getByText(/Pluviômetros \(APAC\), atualizado/)).toBeInTheDocument();
  const mare = screen.getByRole("group", { name: "Maré máxima prevista" });
  expect(within(mare).getByText("1,14")).toBeInTheDocument();
  expect(
    within(screen.getByRole("group", { name: "Chuva prevista 24 h" })).getByText(/Faixa de 3 a 12 mm/),
  ).toBeInTheDocument();
  const lista = await screen.findByRole("list", { name: /Chuva medida nas últimas 24 h/ });
  const linhas = within(lista).getAllByRole("listitem");
  expect(linhas[0]).toHaveTextContent("Distrito 5");
  expect(linhas[2]).toHaveTextContent("Distrito 8");
  expect(linhas[2]).toHaveTextContent("Sem leitura");
  expect(screen.getAllByText(/1 de 3 distritos sem leitura/).length).toBeGreaterThan(0);
  expect(document.body.textContent).not.toMatch(/Sanit|DS [IV]/);
  expect(screen.getByRole("link", { name: "Simular este cenário" })).toHaveAttribute(
    "href",
    "/app/simulador",
  );
});

test("sem dado vira Dados insuficientes com a fonte que falta, nunca zero", async () => {
  simularApi(
    api([
      distrito("ds-1", "Distrito Sanitário I", {
        chuva_24h_mm: null,
        chuva_prev_24h_mm: null,
        chuva_prev_72h_mm: null,
        mare_max_m: null,
        mare_max_em: null,
      }),
    ]),
  );
  abrir();
  const medida = await screen.findByRole("group", { name: "Chuva medida 24 h" });
  expect(await within(medida).findByText(/falta a chuva medida nas últimas 24 h/)).toBeInTheDocument();
  expect(screen.getByRole("group", { name: "Maré máxima prevista" })).toHaveTextContent(
    /falta a previsão de maré/,
  );
  expect(screen.getAllByText(/falta o estágio informado pelo COP/).length).toBeGreaterThan(0);
  expect(screen.getByText(/falta o estágio informado pelo COP para montar a mensagem/)).toBeInTheDocument();
});

test("estágio oficial ainda não disponível no servidor (404) diz Dados insuficientes", async () => {
  simularApi({ ...api([distrito("ds-1", "Distrito Sanitário I")]), "/estagios/oficial": { status: 404 } });
  abrir();
  expect(await screen.findAllByText(/falta o estágio informado pelo COP/)).not.toHaveLength(0);
});

test("fontes: chuva medida vencida aparece como Desatualizado", async () => {
  simularApi(api([distrito("ds-1", "Distrito Sanitário I")]));
  abrir();
  const bloco = await screen.findByRole("region", { name: "Fontes e atualização" });
  expect(await within(bloco).findByText("Desatualizado")).toBeInTheDocument();
});

describe("regras", () => {
  test("distritos ordenados por chuva medida; sem leitura ao fim", () => {
    const l = linhasMedidas([
      distrito("ds-1", "Distrito Sanitário I", { chuva_24h_mm: null }),
      distrito("ds-2", "Distrito Sanitário II", { chuva_24h_mm: 3 }),
      distrito("ds-3", "Distrito Sanitário III", { chuva_24h_mm: 9 }),
    ]);
    expect(l.map((x) => x.id)).toEqual(["ds-3", "ds-2", "ds-1"]);
  });
  test("faixa de incerteza soma mínimos e máximos; sem faixa, null", () => {
    expect(faixaDeIncerteza(cenario.dados, 24)).toEqual({ min: 3, max: 12 });
    expect(faixaDeIncerteza(undefined)).toBeNull();
  });
  test("mensagem de WhatsApp troca o romano pelo número no texto e no link", () => {
    const m = normalizarMensagem({
      texto: "Territórios: Distrito Sanitário VII",
      wa_me_url: "https://wa.me/?text=x",
    });
    expect(m.texto).toBe("Territórios: Distrito 7");
    expect(decodeURIComponent(m.wa_me_url)).toContain("Distrito 7");
  });
});
