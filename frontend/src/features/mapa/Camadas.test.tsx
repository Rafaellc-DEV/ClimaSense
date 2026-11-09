import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { App } from "@/app/App";
import { AGORA, itemEstagio, simularApi, usuarioTeste } from "@/features/evento/testes";
import { clienteConsultas } from "@/lib/api";
import { cortes, faixaDe, textoCobertura, textoPessoas, tipoEquipamento } from "./modeloCamadas";

// o Leaflet é apoio visual: o mapa de mentira só expõe o que recebeu, em atributos
vi.mock("@/map/MapaBairros", () => ({
  MapaBairros: ({
    territorios,
    aoSelecionar,
    modo,
    modoCor,
    areasRisco,
    equipamentos,
  }: {
    territorios: GeoJSON.FeatureCollection<GeoJSON.Geometry, { id: string; nome: string }>;
    aoSelecionar: (id: string) => void;
    modo?: string;
    modoCor?: string;
    areasRisco?: { colecao: { features: unknown[] } } | null;
    equipamentos?: { colecao: { features: unknown[] } } | null;
  }) => (
    <ul
      data-testid="mapa"
      data-modo={modo}
      data-modo-cor={modoCor}
      data-areas={areasRisco ? areasRisco.colecao.features.length : "off"}
      data-equipamentos={equipamentos ? equipamentos.colecao.features.length : "off"}
    >
      {territorios.features.map((f) => (
        <li key={f.properties.id}>
          <button onClick={() => aoSelecionar(f.properties.id)}>mapa: {f.properties.nome}</button>
        </li>
      ))}
    </ul>
  ),
}));

afterEach(() => {
  vi.unstubAllGlobals();
  clienteConsultas.clear();
});

const bairros = [
  itemEstagio({
    territorio_id: "bairro-ibura",
    territorio_nome: "Ibura",
    nivel: "bairro",
    distrito_id: "ds-8",
    alertas_oficiais: [],
  }),
  itemEstagio({
    territorio_id: "bairro-cohab",
    territorio_nome: "Cohab",
    nivel: "bairro",
    distrito_id: "ds-8",
    alertas_oficiais: [],
  }),
];

function base(extra: Record<string, unknown> = {}) {
  return {
    "/auth/eu": usuarioTeste(),
    "/estagios/oficial": { dados: null, meta: { fontes: [] } },
    "/estagios?nivel=distrito": { dados: { itens: [] }, meta: { fontes: [] } },
    "/estagios?nivel=bairro": { dados: { itens: bairros }, meta: { fontes: [] } },
    "/territorios/bairros.geojson": {
      type: "FeatureCollection",
      features: bairros.map((b) => ({
        type: "Feature",
        geometry: { type: "Point", coordinates: [0, 0] },
        properties: { id: b.territorio_id, nome: b.territorio_nome },
      })),
    },
    "/territorios/distritos.geojson": { type: "FeatureCollection", features: [] },
    "/territorios/prioridade": { dados: { itens: [] }, meta: { fontes: [] } },
    ...extra,
  };
}

async function abrir(rotas: Record<string, unknown>) {
  const pedidos = simularApi(rotas);
  window.history.pushState({}, "", "/app");
  render(<App />);
  await screen.findByRole("heading", { level: 1, name: "Mapa" });
  return pedidos;
}

const ponto = (nome: string, tipo: string) => ({
  type: "Feature",
  geometry: { type: "Point", coordinates: [-34.9, -8.1] },
  properties: { cnes: nome, nome, tipo, esfera: "Municipal", bairro_id: "bairro-ibura", distrito_id: "ds-8" },
});

const resumoIbura = {
  dados: {
    idosos_60_mais: 4210,
    criancas_0_14: null,
    suprimido: { criancas_0_14: true },
    deficiencia: null,
    equipamentos: [
      { cnes: "111", nome: "UBS Ibura", tipo: "Unidade básica" },
      { cnes: "222", nome: "UPA Ibura", tipo: "UPA" },
    ],
    equipamentos_em_area_de_risco: ["222"],
    areas_risco: 7,
    cobertura_risco_parcial: true,
  },
  meta: { fontes: [{ id: "censo", nome: "IBGE, Censo 2022", atualizado_em: AGORA, desatualizado: false }] },
};

describe("regras das camadas", () => {
  it("suprimido vira < 5; sem dado vira Dados insuficientes; nunca 0", () => {
    expect(textoPessoas({ valor: null, suprimido: true })).toBe("< 5");
    expect(textoPessoas({ valor: null, suprimido: false })).toBe("Dados insuficientes");
    expect(textoPessoas({ valor: 1200, suprimido: false })).toBe("1.200");
  });

  it("cortes por faixa não repetem limite e valor cai na faixa certa", () => {
    const c = cortes([1, 1, 1, 1, 1, 1, 1, 1, 1, 100], 5);
    expect(new Set(c).size).toBe(c.length);
    expect(faixaDe(100, c)).toBe(c.length);
    expect(faixaDe(0, c)).toBe(0);
    expect(cortes([], 5)).toEqual([]);
  });

  it("tipo de equipamento tem família própria e cobertura parcial gera texto", () => {
    expect(tipoEquipamento("HOSPITAL GERAL").chave).toBe("hospital");
    expect(tipoEquipamento("Unidade Básica de Saúde").chave).toBe("basica");
    expect(tipoEquipamento("Pronto Atendimento (UPA 24h)").chave).toBe("urgencia");
    expect(tipoEquipamento(null).chave).toBe("outro");
    expect(textoCobertura({ parcial: true, regionais_com_dado: ["RPA 3"] })).toBe(
      "Cobertura parcial: só RPA 3",
    );
    expect(textoCobertura({ parcial: false })).toBeNull();
  });
});

describe("Mapa: camadas e painel do bairro", () => {
  it("painel do bairro: idosos e crianças com fonte, < 5, deficiência insuficiente, equipamentos e cobertura parcial", async () => {
    await abrir(base({ "/territorios/bairro-ibura/resumo-vulnerabilidade": resumoIbura }));
    const u = userEvent.setup();
    const botao = await screen.findByRole("button", { name: "mapa: Ibura" });
    await u.click(botao); // primeiro o distrito, depois o bairro
    await u.click(botao);
    const painel = await screen.findByRole("complementary", { name: "Ibura" });
    expect(await within(painel).findByText("4.210")).toBeInTheDocument();
    expect(within(painel).getByText("< 5")).toBeInTheDocument();
    expect(within(painel).getAllByText("Fonte: IBGE, Censo 2022")).toHaveLength(2);
    expect(
      within(painel).getByText(/Dados insuficientes: não há dado público por bairro/),
    ).toBeInTheDocument();
    expect(within(painel).getByText("UPA Ibura").closest("li")).toHaveTextContent("em área de risco");
    expect(within(painel).getByText("UBS Ibura").closest("li")).not.toHaveTextContent("em área de risco");
    expect(within(painel).getAllByText(/cobertura parcial/i).length).toBeGreaterThan(0);
    expect(within(painel).getAllByText("Fonte: CNES").length).toBeGreaterThan(0);
    expect(within(painel).getByText("Fonte: Defesa Civil")).toBeInTheDocument();
  });

  it("painel do bairro: dados_insuficientes nomeia a fonte e não mostra número", async () => {
    await abrir(
      base({
        "/territorios/bairro-ibura/resumo-vulnerabilidade": {
          dados_insuficientes: true,
          fonte_faltante: "IBGE, Censo 2022",
        },
      }),
    );
    const u = userEvent.setup();
    const botao = await screen.findByRole("button", { name: "mapa: Ibura" });
    await u.click(botao); // primeiro o distrito, depois o bairro
    await u.click(botao);
    const painel = await screen.findByRole("complementary", { name: "Ibura" });
    expect(await within(painel).findByText(/Falta a fonte IBGE, Censo 2022/)).toBeInTheDocument();
    expect(within(painel).queryByText("0")).not.toBeInTheDocument();
  });

  it("camadas: só o estágio ligado e nada é pedido à API até ligar", async () => {
    const pedidos = await abrir(base());
    const grupo = await screen.findByRole("group", { name: "Camadas do mapa" });
    expect(within(grupo).queryByRole("checkbox", { name: /Estágio dos bairros/ })).not.toBeInTheDocument();
    for (const nome of [/Equipamentos de saúde/, /População vulnerável/, /Áreas de risco/])
      expect(within(grupo).getByRole("checkbox", { name: nome })).not.toBeChecked();
    expect(pedidos.some((p) => p.url.includes("/camadas/"))).toBe(false);
    expect(await screen.findByTestId("mapa")).toHaveAttribute("data-equipamentos", "off");
  });

  it("equipamentos: liga, desenha os pontos, legenda com fonte e hora", async () => {
    await abrir(
      base({
        "/territorios/camadas/equipamentos-saude": {
          type: "FeatureCollection",
          features: [ponto("UBS A", "Unidade básica"), ponto("Hospital B", "Hospital")],
          meta: { fontes: [{ id: "cnes", nome: "CNES", atualizado_em: AGORA, desatualizado: false }] },
        },
      }),
    );
    await userEvent.setup().click(await screen.findByRole("checkbox", { name: /Equipamentos de saúde/ }));
    await waitFor(() => expect(screen.getByTestId("mapa")).toHaveAttribute("data-equipamentos", "2"));
    const legenda = await screen.findByRole("region", { name: "Legenda: Equipamentos de saúde" });
    expect(legenda).toHaveTextContent("2 equipamentos");
    expect(legenda).toHaveTextContent(/CNES, atualizado/);
  });

  it("camada sem endpoint (404) diz Ainda não disponível e não desenha nada", async () => {
    await abrir(base());
    await userEvent.setup().click(await screen.findByRole("checkbox", { name: /Equipamentos de saúde/ }));
    const legenda = await screen.findByRole("region", { name: "Legenda: Equipamentos de saúde" });
    expect(await within(legenda).findByText("Ainda não disponível")).toBeInTheDocument();
    expect(screen.getByTestId("mapa")).toHaveAttribute("data-equipamentos", "off");
  });

  it("camada com dados_insuficientes nomeia a fonte que falta", async () => {
    await abrir(
      base({
        "/territorios/camadas/equipamentos-saude": { dados_insuficientes: true, fonte_faltante: "CNES" },
      }),
    );
    await userEvent.setup().click(await screen.findByRole("checkbox", { name: /Equipamentos de saúde/ }));
    const legenda = await screen.findByRole("region", { name: "Legenda: Equipamentos de saúde" });
    expect(await within(legenda).findByText(/Falta a fonte CNES/)).toBeInTheDocument();
  });

  it("áreas de risco com cobertura parcial: rótulo permanente no mapa e na legenda", async () => {
    await abrir(
      base({
        "/territorios/camadas/areas-risco": {
          type: "FeatureCollection",
          features: [
            {
              type: "Feature",
              geometry: {
                type: "Polygon",
                coordinates: [
                  [
                    [0, 0],
                    [1, 0],
                    [1, 1],
                    [0, 0],
                  ],
                ],
              },
              properties: { id: "1", tipo: "deslizamento", grau: "alto", regional: "RPA 3", bairro_id: "x" },
            },
          ],
          meta: {
            cobertura: {
              regionais_com_dado: ["RPA 3", "RPA 5"],
              bairros_com_dado: 20,
              total_bairros: 94,
              parcial: true,
              texto: "Bairro sem área desenhada não quer dizer bairro sem risco.",
            },
          },
        },
      }),
    );
    await userEvent.setup().click(await screen.findByRole("checkbox", { name: /Áreas de risco/ }));
    expect(await screen.findByTestId("cobertura-parcial")).toHaveTextContent(
      "Cobertura parcial: só RPA 3 e RPA 5",
    );
    expect(screen.getByTestId("mapa")).toHaveAttribute("data-areas", "1");
    const legenda = screen.getByRole("region", { name: "Legenda: Áreas de risco" });
    expect(legenda).toHaveTextContent("Deslizamento");
    expect(legenda).toHaveTextContent("Bairro sem área desenhada");
  });

  it("população: deficiência desabilitada com aviso, troca o estágio, muda o indicador", async () => {
    await abrir(
      base({
        "/territorios/camadas/vulneraveis": {
          dados: {
            itens: [
              {
                bairro_id: "bairro-ibura",
                nome: "Ibura",
                distrito_id: "ds-8",
                idosos_60_mais: 4000,
                idosos_70_mais: 900,
                criancas_0_4: 1000,
                criancas_0_14: 5000,
                total: 30000,
                suprimido: {},
                deficiencia: null,
              },
              {
                bairro_id: "bairro-cohab",
                nome: "Cohab",
                distrito_id: "ds-8",
                idosos_60_mais: null,
                idosos_70_mais: null,
                criancas_0_4: null,
                criancas_0_14: null,
                total: null,
                suprimido: { idosos_60_mais: true },
                deficiencia: null,
              },
            ],
          },
          meta: { ano: 2022, fontes: [] },
        },
      }),
    );
    const u = userEvent.setup();
    await u.click(await screen.findByRole("checkbox", { name: /População vulnerável/ }));
    await waitFor(() => expect(screen.getByTestId("mapa")).toHaveAttribute("data-modo", "populacao"));
    const grupo = screen.getByRole("group", { name: "População a mostrar" });
    expect(within(grupo).getByRole("radio", { name: "Idosos 60+" })).toBeChecked();
    const def = within(grupo).getByRole("radio", { name: "Pessoas com deficiência" });
    expect(def).toBeDisabled();
    expect(def).toHaveAccessibleDescription(/Dados insuficientes: não há dado público por bairro/);
    await u.click(within(grupo).getByRole("radio", { name: "Crianças 0–14" }));
    const legenda = screen.getByRole("region", { name: "Legenda: População vulnerável" });
    expect(legenda).toHaveTextContent("Crianças 0–14");
    expect(legenda).toHaveTextContent("< 5");
    expect(legenda).toHaveTextContent("Contagem, não percentual");
    await u.click(screen.getByRole("checkbox", { name: /População vulnerável/ }));
    expect(screen.getByRole("checkbox", { name: /População vulnerável/ })).not.toBeChecked();
    // desligada a população, o mapa volta à cor escolhida em "Colorir por" (padrão: distritos)
    expect(screen.getByTestId("mapa")).toHaveAttribute("data-modo-cor", "distrito");
  });
});
