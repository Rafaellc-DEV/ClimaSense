import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { App } from "@/app/App";
import { AGORA, simularApi, usuarioTeste } from "@/features/evento/testes";
import { clienteConsultas } from "@/lib/api";
import { contar, fraseResumo, ordemDaClasse, type ItemSimulado, type Premissas } from "./tipos";

vi.mock("@/map/MapaBairros", () => ({
  MapaBairros: ({
    territorios,
    aoSelecionar,
    aparencia,
  }: {
    territorios: GeoJSON.FeatureCollection<GeoJSON.Geometry, { id: string; nome: string }>;
    aoSelecionar: (id: string) => void;
    aparencia: (id: string) => { ordem: number | null; origem: string };
  }) => (
    <ul data-testid="mapa">
      {territorios.features.map((f) => (
        <li key={f.properties.id} data-ordem={String(aparencia(f.properties.id).ordem)}>
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

const fonte = (id: string, nome: string) => ({
  id,
  nome,
  atualizado_em: AGORA,
  limite_frescor_h: 6,
  desatualizado: false,
});

const geo = {
  type: "FeatureCollection",
  features: ["Ibura", "Aflitos"].map((nome) => ({
    type: "Feature",
    geometry: { type: "Point", coordinates: [-34.9, -8.05] },
    properties: { id: `bairro-${nome.toLowerCase()}`, nome },
  })),
};

const resultado = {
  dados: {
    itens: [
      {
        territorio_id: "bairro-ibura",
        nome: "Ibura",
        nivel: "bairro",
        distrito_id: "ds-8",
        classe_alagamento: "alerta",
        classe_deslizamento: "atencao",
        estagio_sugerido: "alerta",
        confianca: "média",
        motivos: ["Chuva de 80 mm passa do gatilho de alerta."],
        impacto_pessoas: null,
      },
      {
        territorio_id: "bairro-aflitos",
        nome: "Aflitos",
        nivel: "bairro",
        distrito_id: "ds-3",
        classe_alagamento: "sem_dados",
        classe_deslizamento: null,
        estagio_sugerido: "sem_dados",
        confianca: null,
        motivos: [],
        impacto_pessoas: null,
      },
    ],
    resumo: { por_classe: {}, pressao_abrigos: null },
    experimental: true,
    calculado_em: AGORA,
    tempo_calculo_ms: 420,
  },
  meta: { fontes: [fonte("open-meteo", "Open-Meteo")] },
};

const atuais = {
  dados: {
    chuva_prevista_mm: 80,
    duracao_h: 24,
    chuva_acumulada_mm: null,
    mare_m: 2.4,
    horizonte_h: 24,
    abrigos_abertos: null,
    capacidade_abrigos: null,
  },
  meta: { fontes: [fonte("open-meteo", "Open-Meteo"), fonte("marinha-mare", "Marinha (maré)")] },
};

function abrir() {
  window.history.pushState({}, "", "/app/simulador");
  return render(<App />);
}

const rotas = (extra: Record<string, unknown> = {}) => ({
  "/auth/eu": usuarioTeste(),
  "/cenarios/premissas-atuais": atuais,
  "/territorios/bairros.geojson": geo,
  "/territorios/distritos.geojson": { type: "FeatureCollection", features: [] },
  "/territorios/prioridade": { dados: { itens: [] } },
  "/cenarios": { dados: [] },
  ...extra,
});

describe("Simulador", () => {
  it("mostra uma só fonte por campo, com o mapa da API, e envia null para o campo sem dado", async () => {
    const velha = {
      ...fonte("apac-chuva", "APAC"),
      atualizado_em: "2020-01-01T00:00:00Z",
      desatualizado: true,
    };
    const comMapa = {
      ...atuais,
      meta: {
        fontes: [fonte("open-meteo", "Open-Meteo"), fonte("marinha-mare", "Marinha (maré)"), velha],
        fonte_por_premissa: {
          chuva_prevista_mm: "open-meteo",
          mare_m: "marinha-mare",
          chuva_acumulada_mm: "apac-chuva",
        },
      },
    };
    const pedidos = simularApi(rotas({ "/cenarios/premissas-atuais": comMapa }), {
      "/cenarios/simular": resultado,
    });
    abrir();
    const campo = await screen.findByLabelText("Chuva prevista (mm)");
    await waitFor(() => expect(campo).toHaveValue("80"));
    const ajuda = document.getElementById(campo.getAttribute("aria-describedby")!)!;
    expect(ajuda.textContent).toContain("Open-Meteo");
    expect(ajuda.textContent).not.toContain("Marinha");
    const acumulada = screen.getByLabelText("Chuva dos dias anteriores (mm)");
    const ajuda2 = document.getElementById(acumulada.getAttribute("aria-describedby")!)!;
    expect(ajuda2.textContent).toContain("deixe vazio ou digite um valor");
    expect(ajuda2.textContent).toContain("APAC");
    expect(ajuda2.textContent).toContain("Desatualizado");
    await waitFor(() => expect(pedidos.some((p) => p.metodo === "POST")).toBe(true));
    expect(pedidos.filter((p) => p.metodo === "POST")[0].corpo).toMatchObject({ chuva_acumulada_mm: null });
  });

  it("preenche com os valores atuais, calcula sozinho e mostra a frase e o selo Experimental", async () => {
    const pedidos = simularApi(rotas(), { "/cenarios/simular": resultado });
    abrir();
    await waitFor(() => expect(screen.getByLabelText("Chuva prevista (mm)")).toHaveValue("80"));
    expect(screen.getByLabelText("Maré (m)")).toHaveValue("2,4");
    expect(screen.getByLabelText("Chuva dos dias anteriores (mm)")).toHaveValue("");
    expect(screen.getAllByText(/Sem dado da fonte/).length).toBeGreaterThan(0);
    expect(
      await screen.findByText(
        /Com 80 mm em 24 h e maré de 2,4 m: 1 bairro em alerta ou acima, 1 sem dados\./,
      ),
    ).toBeInTheDocument();
    expect(screen.getByText(/Calculado em 0,4 s/)).toBeInTheDocument();
    expect(screen.getAllByText("Experimental").length).toBeGreaterThan(0);
    expect(pedidos.filter((p) => p.metodo === "POST")[0].corpo).toMatchObject({
      chuva_prevista_mm: 80,
      mare_m: 2.4,
    });
    // sem dado nunca é zero nem verde
    expect(screen.getByText("mapa: Aflitos").closest("li")).toHaveAttribute("data-ordem", "null");
    expect(screen.getByText("mapa: Ibura").closest("li")).toHaveAttribute("data-ordem", "2");
  });

  it("recalcula ao mudar a premissa e volta aos valores atuais", async () => {
    const pedidos = simularApi(rotas(), { "/cenarios/simular": resultado });
    abrir();
    const campo = await screen.findByLabelText("Chuva prevista (mm)");
    await screen.findByText(/Calculado em/);
    await userEvent.clear(campo);
    await userEvent.type(campo, "120");
    await waitFor(() =>
      expect(
        pedidos.some((p) => p.metodo === "POST" && (p.corpo as Premissas).chuva_prevista_mm === 120),
      ).toBe(true),
    );
    await userEvent.click(screen.getByRole("button", { name: "Voltar aos valores atuais" }));
    expect(screen.getByLabelText("Chuva prevista (mm)")).toHaveValue("80");
  });

  it("clique no bairro mostra motivos e população vulnerável como dados insuficientes", async () => {
    simularApi(rotas(), { "/cenarios/simular": resultado });
    abrir();
    await userEvent.click(await screen.findByText("mapa: Ibura"));
    const painel = await screen.findByTestId("painel-bairro");
    expect(painel).toHaveTextContent("Chuva de 80 mm passa do gatilho de alerta.");
    expect(painel).toHaveTextContent("População vulnerável exposta");
    expect(painel).toHaveTextContent("Dados insuficientes");
    expect(painel).not.toHaveTextContent(/%/);
  });

  it("mostra residentes expostos do bairro e a soma em bairros em alerta, sem percentual", async () => {
    const comImpacto = {
      ...resultado,
      dados: {
        ...resultado.dados,
        itens: resultado.dados.itens.map((i) =>
          i.territorio_id === "bairro-ibura"
            ? {
                ...i,
                impacto_pessoas: {
                  idosos_60_mais: 4210,
                  criancas_0_14: null,
                  equipamentos_saude: 6,
                  deficiencia: null,
                  total_pessoas: 4210,
                  criterio: "residentes",
                },
              }
            : i,
        ),
        resumo: {
          ...resultado.dados.resumo,
          pessoas_vulneraveis_em_alerta: {
            bairros_em_alerta: 1,
            idosos_60_mais: 4210,
            criancas_0_14: null,
            parcial: true,
            criterio: "residentes",
          },
        },
      },
    };
    simularApi(rotas(), { "/cenarios/simular": comImpacto });
    abrir();
    const resumo = await screen.findByTestId("expostos-resumo");
    expect(resumo).toHaveTextContent("4.210 idosos 60+");
    expect(resumo).toHaveTextContent("crianças 0–14: dados insuficientes");
    expect(resumo).toHaveTextContent("Soma parcial");
    await userEvent.click(await screen.findByText("mapa: Ibura"));
    const painel = await screen.findByTestId("painel-bairro");
    expect(painel).toHaveTextContent("4.210");
    expect(painel).toHaveTextContent("residentes");
    expect(painel).toHaveTextContent("Equipamentos de saúde6");
    expect(painel).toHaveTextContent("Dados insuficientes: não há dado público por bairro");
    expect(painel).not.toHaveTextContent(/%/);
  });

  it("tem as mesmas camadas do mapa principal, desligadas, e a classe do cenário ligada", async () => {
    simularApi(rotas(), { "/cenarios/simular": resultado });
    abrir();
    const grupo = await screen.findByRole("group", { name: "Camadas do mapa" });
    expect(within(grupo).getByRole("checkbox", { name: /Classe do cenário/ })).toBeChecked();
    for (const nome of [/Equipamentos de saúde/, /População vulnerável/, /Áreas de risco/, /Abrigos/])
      expect(within(grupo).getByRole("checkbox", { name: nome })).not.toBeChecked();
  });

  it("endpoint ainda inexistente (404) diz Ainda não disponível", async () => {
    simularApi(rotas(), { "/cenarios/simular": { status: 404 } });
    abrir();
    expect(await screen.findAllByText("Ainda não disponível.")).not.toHaveLength(0);
  });

  it("salva o cenário com nome", async () => {
    const pedidos = simularApi(rotas(), {
      "/cenarios/simular": resultado,
      "/cenarios": { dados: { id: "1" } },
    });
    abrir();
    await screen.findByText(/Calculado em/);
    await userEvent.type(screen.getByLabelText("Nome do cenário"), "Maio forte");
    await userEvent.click(screen.getByRole("button", { name: "Salvar cenário" }));
    await waitFor(() =>
      expect(pedidos.find((p) => p.metodo === "POST" && p.url.endsWith("/cenarios"))?.corpo).toMatchObject({
        nome: "Maio forte",
      }),
    );
  });
});

describe("regras do simulador", () => {
  const itens = (classes: (string | null)[]): ItemSimulado[] =>
    classes.map((c, i) => ({ territorio_id: String(i), nome: `B${i}`, classe_alagamento: c }));
  it("classe desconhecida é sem dado", () => {
    expect(ordemDaClasse("muito_alto")).toBeNull();
    expect(ordemDaClasse("sem_dados")).toBeNull();
    expect(contar(itens(["critico", "xyz", null]), "alagamento")).toEqual({ por: [0, 0, 0, 1], sem: 2 });
  });
  it("a frase não usa percentual", () => {
    const p = { chuva_prevista_mm: 80, duracao_h: 24, mare_m: 2.4 } as Premissas;
    const f = fraseResumo(p, itens(["alerta", "atencao"]), "alagamento");
    expect(f).not.toMatch(/%/);
    expect(f).toContain("1 bairro em alerta ou acima, 1 em atenção");
  });
});
