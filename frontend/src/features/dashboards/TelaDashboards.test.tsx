import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { App } from "@/app/App";
import { AGORA, itemEstagio, simularApi, usuarioTeste } from "@/features/evento/testes";
import { clienteConsultas } from "@/lib/api";

vi.mock("echarts-for-react", () => ({ default: () => <div data-testid="echarts" /> }));

afterEach(() => {
  vi.unstubAllGlobals();
  clienteConsultas.clear();
});

const FONTES = [
  { id: "apac-chuva", nome: "Pluviômetros (APAC)", atualizado_em: AGORA, desatualizado: false },
  { id: "open-meteo-previsao", nome: "Previsão de chuva", atualizado_em: AGORA, desatualizado: false },
];

const distrito = (id: string, nome: string, estagio: string, insumos: Record<string, number>) =>
  itemEstagio({
    territorio_id: id,
    territorio_nome: nome,
    sugerido: { estagio: estagio as never, motivos: [], insumos, calculado_em: AGORA },
  });

const distritos = [
  distrito("ds-4", "Distrito Sanitário IV", "alerta", {
    chuva_24h_mm: 38,
    chuva_prev_24h_mm: 62,
    chuva_prev_72h_mm: 90,
  }),
  distrito("ds-1", "Distrito Sanitário I", "observacao", {
    chuva_24h_mm: 4,
    chuva_prev_24h_mm: 10,
    chuva_prev_72h_mm: 52,
  }),
];

function api(extra: Record<string, unknown> = {}) {
  return {
    "/auth/eu": usuarioTeste(["consultar", "editar"]),
    "/estagios/oficial": {
      dados: { estagio: "atencao", informado_em: AGORA, autor_nome: "Rita" },
      meta: { fontes: [] },
    },
    "/estagios?nivel=distrito": { dados: { itens: distritos }, meta: { fontes: FONTES } },
    "/estagios?nivel=bairro": {
      dados: {
        itens: [
          itemEstagio({
            territorio_id: "bairro-ibura",
            territorio_nome: "Ibura",
            nivel: "bairro",
            distrito_id: "ds-4",
            sugerido: { estagio: "alerta", motivos: [], insumos: {}, calculado_em: AGORA },
          }),
        ],
      },
      meta: { fontes: [] },
    },
    "/estagios/parametros": {
      limiares: {
        chuva_prev_24h_atencao_mm: 25,
        chuva_prev_72h_atencao_mm: 60,
        chuva_prev_24h_critico_mm: 90,
      },
      padrao: true,
    },
    "/situacao/chuva": {
      dados: {
        distritos: [
          {
            territorio_id: "ds-4",
            territorio_nome: "Distrito Sanitário IV",
            chuva_24h_mm: 38,
            chuva_72h_mm: 50,
          },
          {
            territorio_id: "ds-1",
            territorio_nome: "Distrito Sanitário I",
            chuva_24h_mm: null,
            chuva_72h_mm: null,
          },
        ],
        maior_24h: { territorio_id: "ds-4", territorio_nome: "Distrito Sanitário IV", mm: 38 },
        maior_72h: null,
        estacoes: { total: 19, com_leitura: 12, sem_leitura: 7 },
        previsao: { previsao_emitida_em: null, mare_emitida_em: null, chuva: [], mare: [] },
      },
      meta: { fontes: FONTES },
    },
    "/territorios/prioridade": { dados: { itens: [] }, meta: { fontes: [] } },
    ...extra,
  };
}

async function abrir(mapa: Record<string, unknown>, endereco = "/app/dashboards") {
  simularApi(mapa);
  window.history.pushState({}, "", endereco);
  render(<App />);
  await screen.findByRole("heading", { level: 1, name: /equipe/ });
}

test("cartões curtos: Chuva por distrito, Pessoas e unidades expostas, Onde agir primeiro e Dengue nas últimas semanas", async () => {
  await abrir(api());
  const titulos = (await screen.findAllByRole("heading", { level: 2 })).map((h) => h.textContent);
  expect(titulos).toEqual(
    expect.arrayContaining([
      "Chuva por distrito",
      "Pessoas e unidades de saúde expostas",
      "Onde agir primeiro",
      "Dengue nas últimas semanas",
    ]),
  );
  expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(
    /^(Bom dia|Boa tarde|Boa noite), equipe$/,
  );
});

test("KPIs curtos com fonte e hora; sem dado diz Dados insuficientes e o que falta, nunca zero", async () => {
  await abrir(api({ "/estagios/oficial": { dados: null, meta: { fontes: [] } } }));
  const numeros = await screen.findByRole("list", { name: "Números principais" });
  expect(await within(numeros).findByText(/Distrito 4 · 12 de 19 estações/)).toBeInTheDocument();
  expect(numeros).toHaveTextContent("Situação agora");
  expect(numeros).toHaveTextContent("Decisões pendentes");
  expect(numeros).toHaveTextContent("Falta para Atenção");
  expect(numeros).toHaveTextContent(/APAC \d{2}:\d{2}/);
  // sem estágio do COP: Dados insuficientes e o que falta, não "baixo"
  expect(await within(numeros).findByText("Falta: estágio do COP")).toBeInTheDocument();
  expect(numeros).toHaveTextContent("Sistema sugere Alerta");
});

test("aviso de dado vencido é um só, no topo, e leva aos Detalhes; os cartões não repetem selos", async () => {
  const vencida = [{ ...FONTES[0], desatualizado: true }, FONTES[1]];
  await abrir(
    api({
      "/estagios?nivel=distrito": { dados: { itens: distritos }, meta: { fontes: vencida } },
    }),
  );
  const aviso = await screen.findByRole("button", { name: /Alguns dados estão desatualizados/ });
  expect(screen.queryAllByText("Desatualizado")).toHaveLength(0);
  await userEvent.setup().click(aviso);
  const dialogo = await screen.findByRole("dialog", { name: "Detalhes do painel" });
  expect(within(dialogo).getByText(/Dá para confiar nos números de agora/)).toBeInTheDocument();
  expect(await within(dialogo).findByText("Desatualizado")).toBeInTheDocument();
});

test("filtros ficam no endereço e abrem do jeito que o link manda", async () => {
  await abrir(api(), "/app/dashboards?territorio=ds-4&janela=72&foco=saude");
  expect(await screen.findByLabelText("Território")).toHaveValue("ds-4");
  expect(screen.getByRole("radio", { name: "72 h" })).toBeChecked();
  expect(screen.getByLabelText("Foco")).toHaveValue("saude");
  const u = userEvent.setup();
  await u.click(screen.getByRole("radio", { name: "24 h" }));
  expect(window.location.search).not.toContain("janela");
  await u.selectOptions(screen.getByLabelText("Foco"), "deslizamento");
  expect(window.location.search).toContain("foco=deslizamento");
  expect(window.location.search).toContain("territorio=ds-4");
});

test("o foco deixa os cartões fora dele mais claros, sem tirá-los da tela", async () => {
  await abrir(api(), "/app/dashboards?foco=saude");
  const saude = (await screen.findByRole("heading", { name: "Dengue nas últimas semanas" })).closest(
    "section",
  )!;
  const chuva = screen.getByRole("heading", { name: "Chuva por distrito" }).closest("section")!;
  expect(saude).not.toHaveAttribute("data-esmaecido");
  expect(chuva).toHaveAttribute("data-esmaecido", "true");
});

test("Compartilhar copia o link com os filtros", async () => {
  await abrir(api(), "/app/dashboards?janela=72");
  const u = userEvent.setup(); // o user-event instala o próprio clipboard: o espião vem depois
  const escrever = vi.fn().mockResolvedValue(undefined);
  Object.defineProperty(navigator, "clipboard", { value: { writeText: escrever }, configurable: true });
  await u.click(await screen.findByRole("button", { name: /Compartilhar/ }));
  expect(escrever).toHaveBeenCalledWith(expect.stringContaining("janela=72"));
});

test("decisões pendentes e o ranking levam ao Mapa no território", async () => {
  await abrir(api());
  const link = (await screen.findAllByRole("link", { name: /Ibura/ }))[0];
  expect(link).toHaveAttribute("href", "/app?territorio=bairro-ibura");
});

test("Pessoas e unidades expostas: sem bairro em Atenção, mostra os 3 bairros com mais moradores no distrito mais perto do gatilho", async () => {
  const bairro = (id: string, nome: string, idosos: number, criancas: number) => ({
    bairro_id: id,
    nome,
    distrito_id: "ds-1",
    idosos_60_mais: idosos,
    criancas_0_14: criancas,
    suprimido: {},
  });
  await abrir(
    api({
      "/territorios/camadas/vulneraveis": {
        dados: {
          itens: [
            bairro("b1", "Boa Vista", 100, 100),
            bairro("b2", "Santo Amaro", 400, 300),
            bairro("b3", "Soledade", 50, 10),
            bairro("b4", "Recife Antigo", 200, 100),
            bairro("b5", "Outro Distrito", 9999, 9999),
          ].map((b) => (b.nome === "Outro Distrito" ? { ...b, distrito_id: "ds-4" } : b)),
        },
        meta: { fontes: [] },
      },
      "/cenarios/impacto-previsto": {
        dados: {
          itens: [
            {
              territorio_id: "ds-4",
              nome: "Distrito Sanitário IV",
              nivel: "distrito",
              distrito_id: "ds-4",
              estagio_sugerido: "observacao",
              impacto_pessoas: null,
            },
            {
              territorio_id: "bairro-ibura",
              nome: "Ibura",
              nivel: "bairro",
              distrito_id: "ds-4",
              estagio_sugerido: "observacao",
              impacto_pessoas: null,
            },
          ],
        },
        meta: { fontes: [] },
      },
    }),
  );
  const cartao = (
    await screen.findByRole("heading", { name: "Pessoas e unidades de saúde expostas" })
  ).closest("section")!;
  expect(await within(cartao).findByText("Nenhum bairro em Atenção agora")).toBeInTheDocument();
  // Distrito 1 é o mais perto do gatilho (52 de 60 mm em 72 h; 10 de 25 mm em 24 h): três bairros dele, do maior para o menor
  const nomes = (await within(cartao).findAllByRole("listitem")).map(
    (l) => l.querySelector("b")?.textContent,
  );
  expect(nomes.slice(0, 3)).toEqual(["Santo Amaro", "Recife Antigo", "Boa Vista"]);
  expect(cartao).toHaveTextContent(/Referência, não previsão/);
});
