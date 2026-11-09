import { render, screen, waitFor, within, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { App } from "@/app/App";
import { AGORA, simularApi, usuarioTeste } from "@/features/evento/testes";
import { clienteConsultas } from "@/lib/api";
import { contar, fraseResumo, ordemDaClasse, type ItemSimulado, type Premissas } from "./tipos";
import { dicaDoControle } from "./Premissas";
import { textoArboviroses } from "./DistritosArboviroses";

vi.mock("@/map/MapaBairros", () => ({
  MapaBairros: () => <div data-testid="mapa" />,
}));

afterEach(() => {
  vi.unstubAllGlobals();
  clienteConsultas.clear();
});

const fonte = (id: string, nome: string, extra = {}) => ({
  id,
  nome,
  atualizado_em: AGORA,
  limite_frescor_h: 6,
  desatualizado: false,
  ...extra,
});

const atuais = (
  extra = {},
  fontes = [fonte("open-meteo-previsao", "Open-Meteo"), fonte("apac-chuva", "APAC")],
) => ({
  dados: {
    chuva_prevista_mm: 58,
    duracao_h: 12,
    chuva_acumulada_mm: 118,
    mare_m: 2.3,
    horizonte_h: 24,
    ...extra,
  },
  meta: {
    fontes: [...fontes, fonte("open-meteo-mare", "Open-Meteo (maré)")],
    fonte_por_premissa: {
      chuva_prevista_mm: "open-meteo-previsao",
      duracao_h: "open-meteo-previsao",
      chuva_acumulada_mm: "apac-chuva",
      mare_m: "open-meteo-mare",
    },
  },
});

const parametros = {
  limiares: {
    chuva_prev_24h_atencao_mm: 30,
    chuva_prev_24h_alerta_mm: 50,
    chuva_prev_72h_atencao_mm: 60,
    chuva_prev_72h_alerta_mm: 100,
    mare_alta_m: 0.6,
  },
};

const agravo = (a: string, nome: string, extra = {}) => ({
  agravo: a,
  nome,
  semana_recente: {
    ano: 2026,
    semana: 44,
    inicio: "2026-10-25",
    casos: 12,
    suprimido: false,
    incompleta: true,
  },
  serie_semanal: [],
  ano_distrito: 2026,
  casos_ano_distrito: 340,
  casos_ano_suprimido: false,
  classe_impacto: "alta",
  dados_insuficientes: false,
  motivo: null,
  ...extra,
});

const ROMANOS = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII"];
const distrito = (n: number, estagio: string, extra = {}) => ({
  territorio_id: `ds-${n}`,
  nome: `Distrito Sanitário ${ROMANOS[n - 1]}`,
  nivel: "distrito",
  classe_alagamento: estagio,
  classe_deslizamento: "sem_dados",
  estagio_sugerido: estagio,
  confianca: "média",
  motivos: [`Chuva de 58 mm passa do gatilho no Distrito Sanitário ${ROMANOS[n - 1]}.`],
  impacto_pessoas: {
    idosos_60_mais: 9840,
    criancas_0_14: 14210,
    equipamentos_saude: 3,
    deficiencia: null,
  },
  arboviroses: {
    classe_impacto: "alta",
    agravos_em_destaque: ["dengue"],
    agravos: [
      agravo("dengue", "Dengue"),
      agravo("chikungunya", "Chikungunya", {
        casos_ano_distrito: null,
        casos_ano_suprimido: true,
        classe_impacto: null,
      }),
      agravo("zika", "Zika", {
        semana_recente: null,
        casos_ano_distrito: null,
        classe_impacto: null,
        dados_insuficientes: true,
        motivo: "Sem fonte pública de casos de zika por distrito.",
      }),
    ],
  },
  ...extra,
});

const resultado = {
  dados: {
    itens: [
      distrito(7, "critico"),
      distrito(3, "alerta", { arboviroses: null, impacto_pessoas: null }),
      {
        territorio_id: "bairro-ibura",
        nome: "Ibura",
        nivel: "bairro",
        distrito_id: "ds-8",
        classe_alagamento: "alerta",
        estagio_sugerido: "alerta",
        motivos: ["Bairro com 3 ocorrências de alagamento."],
        impacto_pessoas: {
          idosos_60_mais: 1200,
          criancas_0_14: 2100,
          equipamentos_saude: 2,
          deficiencia: null,
        },
      },
      {
        territorio_id: "bairro-cohab",
        nome: "Cohab",
        nivel: "bairro",
        distrito_id: "ds-8",
        classe_alagamento: "critico",
        estagio_sugerido: "critico",
        motivos: [],
        impacto_pessoas: {
          idosos_60_mais: 300,
          criancas_0_14: 400,
          equipamentos_saude: 1,
          deficiencia: null,
        },
      },
      {
        territorio_id: "bairro-sem-dado",
        nome: "Sem Dado",
        nivel: "bairro",
        distrito_id: "ds-1",
        classe_alagamento: "sem_dados",
        estagio_sugerido: "sem_dados",
        motivos: [],
        impacto_pessoas: null,
      },
    ],
    resumo: {
      por_classe: {},
      ordem_de_atencao_distritos: [
        {
          distrito_id: "ds-7",
          nome: "Distrito Sanitário VII",
          estagio_sugerido: "critico",
          classe_arboviroses: "alta",
          agravos_em_destaque: ["dengue"],
        },
        {
          distrito_id: "ds-3",
          nome: "Distrito Sanitário III",
          estagio_sugerido: "alerta",
          classe_arboviroses: null,
          agravos_em_destaque: [],
        },
      ],
      arboviroses: {
        experimental: true,
        contexto: true,
        aviso: "Arboviroses são contexto, não previsão causal da chuva.",
        granularidade_semanal: "municipio",
        granularidade_anual: "distrito",
        fontes: [{ id: "infodengue", nome: "InfoDengue", atualizado_em: AGORA, status: "atualizada" }],
      },
    },
    experimental: true,
    calculado_em: AGORA,
    tempo_calculo_ms: 420,
  },
  meta: { fontes: [fonte("open-meteo", "Open-Meteo")] },
};

const rotas = (extra: Record<string, unknown> = {}) => ({
  "/auth/eu": usuarioTeste(),
  "/cenarios/premissas-atuais": atuais(),
  "/estagios/parametros": parametros,
  "/territorios/bairros.geojson": { type: "FeatureCollection", features: [] },
  "/territorios/distritos.geojson": { type: "FeatureCollection", features: [] },
  "/cenarios": { dados: [] },
  ...extra,
});

function abrir() {
  window.history.pushState({}, "", "/app/simulador");
  return render(<App />);
}

describe("regras do Simulador", () => {
  const item = (c: string | null, e: string | null = null): ItemSimulado => ({
    territorio_id: "x",
    nome: "X",
    classe_alagamento: c,
    estagio_sugerido: e,
  });

  it("classe sem reconhecimento é falta de dado, não baixa", () => {
    expect(ordemDaClasse("sem_dados")).toBeNull();
    expect(ordemDaClasse("critico")).toBe(3);
    expect(contar([item("alerta"), item(null), item("observacao")], "alagamento")).toEqual({
      por: [1, 0, 1, 0],
      sem: 1,
    });
  });

  it("a frase cita chuva e maré e conta os sem dados", () => {
    const p = {
      chuva_prevista_mm: 80,
      duracao_h: 24,
      chuva_acumulada_mm: null,
      mare_m: 2.4,
      horizonte_h: 24,
    } as Premissas;
    expect(fraseResumo(p, [item("alerta"), item(null)], "alagamento")).toContain("sem dados");
  });

  it("gatilhos só aparecem se a configuração trouxer o número", () => {
    expect(dicaDoControle("chuva_prevista_mm", parametros.limiares)).toBe(
      "Gatilhos: atenção 30 mm · alerta 50 mm",
    );
    expect(dicaDoControle("chuva_prevista_mm", {})).toBeNull();
    expect(dicaDoControle("mare_m", parametros.limiares)).toBe("Maré alta a partir de 0,6 m");
  });

  it("arboviroses em uma linha: sem classe vira dados insuficientes", () => {
    expect(textoArboviroses(null)).toBe("Dados insuficientes");
    expect(textoArboviroses(distrito(1, "alerta").arboviroses as never)).toBe(
      "Dengue alta · Chikungunya: dados insuficientes · Zika: dados insuficientes",
    );
  });
});

describe("Simulador", () => {
  it("pré-preenche com os valores atuais, calcula sozinho e mostra gatilhos, fonte e selo Experimental", async () => {
    const pedidos = simularApi(rotas(), { "/cenarios/simular": resultado });
    abrir();
    const chuva = await screen.findByLabelText("Chuva prevista em 24 h");
    await waitFor(() => expect(chuva).toHaveValue("58"));
    expect(screen.getByLabelText("Chuva acumulada em 72 h")).toHaveValue("118");
    expect(screen.getByLabelText("Maré prevista no pico")).toHaveValue("2.3");
    expect(await screen.findByText("Gatilhos: atenção 30 mm · alerta 50 mm")).toBeInTheDocument();
    expect(screen.getAllByText("Experimental").length).toBeGreaterThan(0);
    expect(document.body).toHaveTextContent(/Fonte: Open-Meteo, atualizada/);
    await waitFor(() => expect(pedidos.some((p) => p.metodo === "POST")).toBe(true));
    expect(pedidos.find((p) => p.metodo === "POST")?.corpo).toMatchObject({
      chuva_prevista_mm: 58,
      chuva_acumulada_mm: 118,
      mare_m: 2.3,
    });
    expect(screen.queryByText(/Cenário demonstrativo/)).not.toBeInTheDocument();
    expect(screen.queryByText("Desatualizado")).not.toBeInTheDocument();
  });

  it("mexer no controle recalcula, e Usar a previsão atual volta ao valor da fonte", async () => {
    const pedidos = simularApi(rotas(), { "/cenarios/simular": resultado });
    abrir();
    const u = userEvent.setup();
    const chuva = await screen.findByLabelText("Chuva prevista em 24 h");
    await waitFor(() => expect(chuva).toHaveValue("58"));
    fireEvent.change(chuva, { target: { value: "90" } });
    await waitFor(() =>
      expect(
        pedidos
          .filter((p) => p.metodo === "POST")
          .some((p) => (p.corpo as Premissas).chuva_prevista_mm === 90),
      ).toBe(true),
    );
    await u.click(screen.getByRole("button", { name: "Usar a previsão atual" }));
    expect(chuva).toHaveValue("58");
  });

  it("campo sem dado da fonte aparece como Sem dado e vai como null", async () => {
    const pedidos = simularApi(
      rotas({ "/cenarios/premissas-atuais": atuais({ chuva_acumulada_mm: null }) }),
      {
        "/cenarios/simular": resultado,
      },
    );
    abrir();
    const acumulada = await screen.findByLabelText("Chuva acumulada em 72 h");
    expect(acumulada.closest("div")!.parentElement).toHaveTextContent("Sem dado");
    await waitFor(() => expect(pedidos.some((p) => p.metodo === "POST")).toBe(true));
    expect(pedidos.find((p) => p.metodo === "POST")?.corpo).toMatchObject({ chuva_acumulada_mm: null });
  });

  it("blocos por distrito com nome 'Distrito N'; escolher abre o detalhe com motivos e pessoas expostas", async () => {
    simularApi(rotas(), { "/cenarios/simular": resultado });
    abrir();
    const u = userEvent.setup();
    const blocos = await screen.findByRole("region", { name: "Estágio sugerido por distrito" });
    expect(within(blocos).getByText("Distrito 7")).toBeInTheDocument();
    expect(
      within(blocos).getByText(
        "Esquemático por distrito (a posição não é a do mapa). Cinza é falta de dado, não risco baixo.",
      ),
    ).toBeInTheDocument();
    await u.click(within(blocos).getByRole("button", { name: /Distrito 7/ }));
    const detalhe = await screen.findByTestId("detalhe-distrito");
    expect(within(detalhe).getByRole("heading", { level: 2 })).toHaveTextContent("Distrito 7 · Crítico");
    expect(within(detalhe).getByText("Chuva de 58 mm passa do gatilho no Distrito 7.")).toBeInTheDocument();
    expect(within(detalhe).getByText("9.840")).toBeInTheDocument();
    const deficiencia = within(detalhe).getByText("Com deficiência").closest("div")!;
    expect(deficiencia).toHaveTextContent("Dados insuficientes");
    expect(within(detalhe).getByText(/Casos no ano \(2026\), neste distrito: 340/)).toBeInTheDocument();
    expect(detalhe.querySelector('[data-suprimido="true"]')).not.toBeNull();
    expect(detalhe).toHaveTextContent("Sem fonte pública de casos de zika por distrito.");
  });

  it("distrito sem pessoas expostas no resultado mostra Dados insuficientes, nunca zero", async () => {
    simularApi(rotas(), { "/cenarios/simular": resultado });
    abrir();
    const u = userEvent.setup();
    const blocos = await screen.findByRole("region", { name: "Estágio sugerido por distrito" });
    await u.click(within(blocos).getByRole("button", { name: /Distrito 3/ }));
    const detalhe = await screen.findByTestId("detalhe-distrito");
    expect(within(detalhe).getAllByText(/Dados insuficientes/).length).toBeGreaterThan(0);
    expect(within(detalhe).queryByText("0")).not.toBeInTheDocument();
  });

  it("tabela de ordem de atenção: ordem, estágio, alagamento, arboviroses e confiança; sem percentual", async () => {
    simularApi(rotas(), { "/cenarios/simular": resultado });
    abrir();
    const secao = await screen.findByRole("region", { name: "Ordem de atenção dos distritos" });
    const tabela = within(secao).getByRole("table");
    const cab = within(tabela)
      .getAllByRole("columnheader")
      .map((c) => c.textContent);
    expect(cab).toEqual([
      "#",
      "Distrito",
      "Estágio sugerido",
      "Alagamento",
      "Deslizamento",
      "Arboviroses em destaque",
      "Confiança",
    ]);
    const linhas = within(tabela).getAllByRole("row").slice(1);
    expect(linhas).toHaveLength(2);
    expect(linhas[0]).toHaveTextContent("Distrito 7");
    expect(linhas[0]).toHaveTextContent(
      "Dengue alta · Chikungunya: dados insuficientes · Zika: dados insuficientes",
    );
    expect(linhas[1]).toHaveTextContent("Distrito 3");
    expect(linhas[1]).toHaveTextContent("Dados insuficientes");
    expect(secao).toHaveTextContent("não previsão causal");
    expect(secao).toHaveTextContent(/InfoDengue/);
    expect(secao).not.toHaveTextContent("%");
    expect(document.body).not.toHaveTextContent(/Distrito Sanit|DS [IV]/);
  });

  it("previsão atual velha: um aviso só, no topo", async () => {
    const velha = fonte("open-meteo-previsao", "Open-Meteo", { desatualizado: true });
    simularApi(rotas({ "/cenarios/premissas-atuais": atuais({}, [velha, fonte("apac-chuva", "APAC")]) }), {
      "/cenarios/simular": resultado,
    });
    abrir();
    expect(await screen.findByText("A previsão atual está desatualizada")).toBeInTheDocument();
    expect(screen.getAllByText(/desatualizada/i)).toHaveLength(1);
  });

  it("o mapa de bairros é o elemento principal: seletor Ver, legenda, lista dos mais afetados e clique abre o porquê", async () => {
    simularApi(rotas(), { "/cenarios/simular": resultado });
    abrir();
    const u = userEvent.setup();
    const secao = await screen.findByRole("region", { name: "Quais áreas são afetadas" });
    expect(await within(secao).findByTestId("mapa")).toBeInTheDocument();
    expect(within(secao).getByRole("radio", { name: "Estágio" })).toBeChecked();
    expect(within(secao).getByRole("radio", { name: "Alagamento" })).toBeInTheDocument();
    expect(within(secao).getByRole("radio", { name: "Deslizamento" })).toBeInTheDocument();
    expect(within(secao).getByRole("list", { name: "Legenda: Estágio" })).toHaveTextContent(
      "Dados insuficientes",
    );
    const itens = within(secao).getAllByRole("button", { name: /Distrito 8|Distrito 1/ });
    expect(itens[0]).toHaveTextContent("Cohab");
    expect(itens[1]).toHaveTextContent("Ibura");
    expect(itens[2]).toHaveTextContent("Sem Dado");
    expect(itens[2]).toHaveTextContent("Pessoas expostas: dados insuficientes");
    await u.click(itens[1]);
    const escolhido = await screen.findByTestId("bairro-escolhido");
    expect(escolhido).toHaveTextContent("Ibura");
    expect(escolhido).toHaveTextContent("Distrito 8");
    expect(within(escolhido).getByText("Bairro com 3 ocorrências de alagamento.")).toBeInTheDocument();
    expect(within(escolhido).getByText("1.200")).toBeInTheDocument();
    expect(within(escolhido).getByText("Com deficiência").closest("div")).toHaveTextContent(
      "Dados insuficientes",
    );
  });

  it("cenários prontos saem dos gatilhos reais, mostram o valor no botão e preenchem as premissas", async () => {
    const pedidos = simularApi(rotas(), { "/cenarios/simular": resultado });
    abrir();
    const u = userEvent.setup();
    const grupo = await screen.findByRole("group", { name: "Cenários prontos" });
    expect(within(grupo).getByRole("button", { name: "Moderada · 24 mm em 24 h" })).toBeInTheDocument();
    expect(within(grupo).getByRole("button", { name: "Extrema · 80 mm em 24 h" })).toBeInTheDocument();
    await u.click(within(grupo).getByRole("button", { name: "Forte · 40 mm em 24 h" }));
    expect(screen.getByLabelText("Chuva prevista em 24 h")).toHaveValue("40");
    expect(screen.getByLabelText("Chuva acumulada em 72 h")).toHaveValue("80");
    await waitFor(() =>
      expect(
        pedidos
          .filter((p) => p.metodo === "POST")
          .some((p) => {
            const c = p.corpo as Premissas;
            return c.chuva_prevista_mm === 40 && c.chuva_acumulada_mm === 80 && c.duracao_h === 12;
          }),
      ).toBe(true),
    );
  });

  it("quando todos os distritos ficam no mesmo estágio, diz que a diferença está nos bairros", async () => {
    const todos = {
      ...resultado,
      dados: {
        ...resultado.dados,
        itens: resultado.dados.itens.map((i) =>
          i.nivel === "distrito" ? { ...i, estagio_sugerido: "critico" } : i,
        ),
      },
    };
    simularApi(rotas(), { "/cenarios/simular": todos });
    abrir();
    expect(await screen.findByText(/a diferença está no risco de cada/)).toBeInTheDocument();
  });

  it("endpoint ainda inexistente (404) diz Ainda não disponível", async () => {
    simularApi(rotas(), { "/cenarios/simular": { status: 404, corpo: { detail: "x" } } });
    abrir();
    expect(await screen.findByText("Ainda não disponível.")).toBeInTheDocument();
  });

  it("salva o cenário com nome, pelo botão do cabeçalho", async () => {
    const pedidos = simularApi(rotas(), {
      "/cenarios/simular": resultado,
      "/cenarios": { status: 201, corpo: { dados: { id: "c1", nome: "Chuva forte" } } },
    });
    abrir();
    const u = userEvent.setup();
    await screen.findByLabelText("Chuva prevista em 24 h");
    await u.click(screen.getByRole("button", { name: "Salvar cenário" }));
    const dialogo = await screen.findByRole("dialog");
    await u.type(within(dialogo).getByLabelText("Nome do cenário"), "Chuva forte");
    const salvar = within(dialogo).getByRole("button", { name: "Salvar cenário" });
    await waitFor(() => expect(salvar).toBeEnabled());
    await u.click(salvar);
    await waitFor(
      () =>
        expect(pedidos.find((p) => p.metodo === "POST" && p.url.endsWith("/cenarios"))?.corpo).toMatchObject({
          nome: "Chuva forte",
        }),
      { timeout: 10000 },
    );
  }, 20000);

  it("Cenários salvos lista os cenários e abre um", async () => {
    simularApi(rotas({ "/cenarios": { dados: [{ id: "c1", nome: "Chuva de maio", criado_em: AGORA }] } }), {
      "/cenarios/simular": resultado,
    });
    abrir();
    const u = userEvent.setup();
    await screen.findByLabelText("Chuva prevista em 24 h");
    await u.click(screen.getByRole("button", { name: "Cenários salvos" }));
    const dialogo = await screen.findByRole("dialog");
    expect(await within(dialogo).findByText(/Chuva de maio/)).toBeInTheDocument();
  });
});
