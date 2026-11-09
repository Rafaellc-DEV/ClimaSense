import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { App } from "@/app/App";
import { AGORA, itemEstagio, simularApi, usuarioTeste } from "@/features/evento/testes";
import { clienteConsultas } from "@/lib/api";
import { contarPorEstagio, emVigor, ordenarPorGravidade } from "./tipos";

// o mapa (Leaflet) é apoio visual; aqui cada território vira um botão "mapa: Nome" para testar a escolha
vi.mock("@/map/MapaBairros", () => ({
  MapaBairros: ({
    territorios,
    aoSelecionar,
    aparencia,
    modoCor,
    distritoEmFoco,
    selecionado,
    pronto,
    valorPorBairro,
  }: {
    territorios: GeoJSON.FeatureCollection<GeoJSON.Geometry, { id: string; nome: string }>;
    aoSelecionar: (id: string) => void;
    aparencia: (id: string) => { ordem: number | null; origem: string };
    modoCor?: string;
    distritoEmFoco?: string | null;
    selecionado?: string | null;
    pronto?: boolean;
    valorPorBairro?: (id: string) => number | null;
  }) => (
    <ul
      data-testid="mapa"
      data-modo-cor={modoCor}
      data-foco={distritoEmFoco ?? ""}
      data-selecionado={selecionado ?? ""}
      data-pronto={String(pronto)}
    >
      {territorios.features.map((f) => (
        <li
          key={f.properties.id}
          data-origem={aparencia(f.properties.id).origem}
          data-valor={String(valorPorBairro?.(f.properties.id) ?? "")}
        >
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
    sugerido: {
      estagio: "alerta",
      motivos: ["Chuva prevista de 62 mm em 24 h."],
      insumos: {},
      calculado_em: AGORA,
    },
    declarado: {
      estagio: "critico",
      justificativa: "Encosta instável",
      autor_nome: "Mari Lima",
      declarado_em: AGORA,
    },
    alertas_oficiais: [
      {
        origem: "APAC",
        nivel: "alerta",
        emitido_em: AGORA,
        area: "Região Metropolitana do Recife",
      },
    ],
  }),
  itemEstagio({
    territorio_id: "bairro-cohab",
    territorio_nome: "Cohab",
    nivel: "bairro",
    distrito_id: "ds-8",
    sugerido: { estagio: "atencao", motivos: [], insumos: {}, calculado_em: AGORA },
    alertas_oficiais: [],
  }),
  itemEstagio({
    territorio_id: "bairro-aflitos",
    territorio_nome: "Aflitos",
    nivel: "bairro",
    distrito_id: "ds-3",
    sugerido: {
      estagio: "sem_dados",
      motivos: [],
      insumos: {},
      calculado_em: AGORA,
      faltando: ["previsão de chuva"],
    },
    alertas_oficiais: [],
  }),
];

const geoBairros = {
  type: "FeatureCollection",
  features: bairros.map((b) => ({
    type: "Feature",
    geometry: { type: "Point", coordinates: [0, 0] },
    properties: { id: b.territorio_id, nome: b.territorio_nome, distrito_id: b.distrito_id },
  })),
};

function base(extra: Record<string, unknown> = {}, permissoes = ["consultar", "editar"]) {
  return {
    "/auth/eu": usuarioTeste(permissoes),
    "/estagios/oficial": { dados: null, meta: { fontes: [] } },
    "/estagios?nivel=distrito": { dados: { itens: [] }, meta: { fontes: [] } },
    "/estagios?nivel=bairro": {
      dados: { itens: bairros },
      meta: {
        fontes: [
          { id: "estagios", nome: "Estágios do ClimaSense", atualizado_em: AGORA, desatualizado: false },
        ],
      },
    },
    "/territorios/bairros.geojson": geoBairros,
    "/territorios/distritos.geojson": { type: "FeatureCollection", features: [] },
    "/territorios/prioridade": {
      dados: {
        itens: [
          {
            territorio_id: "ds-7",
            nome: "Distrito 7",
            nivel: "distrito",
            posicao: 1,
            idosos_60_mais: 24619,
            criancas_0_14: null,
            ocorrencias_alagamento: 120,
            ocorrencias_deslizamento: 8,
            criterio: "Mais ocorrências de alagamento e deslizamento registradas.",
          },
          {
            territorio_id: "bairro-ibura",
            nome: "Ibura",
            nivel: "bairro",
            posicao: 2,
            ocorrencias_alagamento: 63,
            ocorrencias_deslizamento: null,
            criterio: "Histórico de alagamento.",
          },
        ],
      },
      meta: { fontes: [] },
    },
    ...extra,
  };
}

async function abrir(mapa: Record<string, unknown>, metodos: Record<string, unknown> = {}) {
  const pedidos = simularApi(mapa, metodos);
  window.history.pushState({}, "", "/app");
  render(<App />);
  await screen.findByRole("heading", { level: 1, name: "Mapa" });
  return pedidos;
}

/** O clique no mapa abre primeiro o distrito; o segundo clique, no mesmo bairro, abre o bairro. */
async function escolherBairro(u: ReturnType<typeof userEvent.setup>, nome: string) {
  const botao = await screen.findByRole("button", { name: `mapa: ${nome}` });
  await u.click(botao);
  await screen.findByRole("heading", { level: 2, name: /^Distrito \d/ });
  await u.click(botao);
  await screen.findByRole("heading", { level: 2, name: nome });
}

test("regras: o declarado vale; sem declaração, o sugerido; sem nenhum, sem dados (nunca observação)", () => {
  expect(emVigor(bairros[0])).toMatchObject({ estagio: "critico", origem: "declarado", ordem: 3 });
  expect(emVigor(bairros[1])).toMatchObject({ estagio: "atencao", origem: "sugerido", ordem: 1 });
  expect(emVigor(bairros[2])).toMatchObject({ estagio: "sem_dados", origem: "sem_dados", ordem: null });
  expect(emVigor(undefined).estagio).toBe("sem_dados");
  const c = Object.fromEntries(contarPorEstagio(bairros).map((x) => [x.estagio, x]));
  expect(c.critico).toMatchObject({ declarados: 1, sugeridos: 0 });
  expect(c.atencao).toMatchObject({ declarados: 0, sugeridos: 1 });
  expect(c.observacao).toMatchObject({ declarados: 0, sugeridos: 0 });
  expect(c.sem_dados).toMatchObject({ declarados: 0, sugeridos: 1 });
  expect(ordenarPorGravidade(bairros, new Map()).map((b) => b.territorio_nome)).toEqual([
    "Ibura",
    "Cohab",
    "Aflitos",
  ]);
});

test("/app abre o Mapa; o menu tem Mapa primeiro e a Situação do evento continua acessível", async () => {
  await abrir(base());
  const menu = (await screen.findAllByRole("navigation", { name: "Menu principal" }))[0];
  const links = within(menu).getAllByRole("link");
  expect(links[0]).toHaveTextContent("Mapa");
  expect(within(menu).getByRole("link", { name: "Situação do evento" })).toHaveAttribute(
    "href",
    "/app/situacao",
  );
});

test("sem estágio do COP: Dados insuficientes, nunca observação, e o botão para informar", async () => {
  await abrir(base());
  const faixa = await screen.findByRole("region", { name: "Estágio oficial da cidade (COP)" });
  expect(await within(faixa).findByText(/ninguém informou o estágio do COP/)).toBeInTheDocument();
  expect(within(faixa).getByText(/Dados insuficientes:/)).toBeInTheDocument();
  expect(within(faixa).getByRole("button", { name: "Informar estágio do COP" })).toBeInTheDocument();
});

test("com estágio do COP: estágio, hora, autor e fonte", async () => {
  await abrir(
    base({
      "/estagios/oficial": {
        dados: {
          estagio: "alerta",
          informado_em: AGORA,
          registrado_em: AGORA,
          autor_nome: "Rita Souza",
          observacao: "Chuva forte na zona sul",
          fonte: "COP do Recife",
        },
        meta: { fontes: [] },
      },
    }),
  );
  const faixa = await screen.findByRole("region", { name: "Estágio oficial da cidade (COP)" });
  expect(await within(faixa).findByText(/Informado pelo COP/)).toBeInTheDocument();
  expect(within(faixa).getAllByText("Alerta").length).toBeGreaterThanOrEqual(1); // selo do COP
  expect(within(faixa).getByText(/registrado por Rita Souza/)).toBeInTheDocument();
  expect(within(faixa).getByText(/Fonte: COP do Recife/)).toBeInTheDocument();
  expect(within(faixa).getByText(/Chuva forte na zona sul/)).toBeInTheDocument();
});

test("informar o estágio do COP envia estágio, hora e observação, com o aviso de privacidade", async () => {
  const pedidos = await abrir(base(), { "/estagios/oficial": { ok: true } });
  const u = userEvent.setup();
  await u.click(await screen.findByRole("button", { name: "Informar estágio do COP" }));
  const dialogo = await screen.findByRole("dialog");
  expect(within(dialogo).getByText(/Não escreva nome, CPF ou dado de saúde/)).toBeInTheDocument();
  await u.click(within(dialogo).getByRole("radio", { name: "Atenção" }));
  await u.type(within(dialogo).getByLabelText("Observação (opcional)"), "Reunião das 14h");
  await u.click(within(dialogo).getByRole("button", { name: "Registrar estágio" }));
  await waitFor(() => expect(pedidos.some((p) => p.metodo === "POST")).toBe(true));
  const post = pedidos.find((p) => p.metodo === "POST")!;
  expect(post.url).toContain("/estagios/oficial");
  expect(post.corpo).toMatchObject({ estagio: "atencao", observacao: "Reunião das 14h" });
  expect((post.corpo as { informado_em: string }).informado_em).toMatch(/^\d{4}-\d{2}-\d{2}T/);
});

test("sem permissão de editar, não há botão de informar nem de declarar", async () => {
  await abrir(base({}, ["consultar"]));
  await screen.findByText(/ninguém informou o estágio do COP/);
  expect(screen.queryByRole("button", { name: "Informar estágio do COP" })).not.toBeInTheDocument();
  const u = userEvent.setup();
  await escolherBairro(u, "Ibura");
  await screen.findByRole("heading", { level: 2, name: "Ibura" });
  expect(screen.queryByRole("button", { name: /Declarar/ })).not.toBeInTheDocument();
});

test("a contagem vira chips pequenos: só estágios com bairro, declarado e sugerido na dica, sem dados não vira observação", async () => {
  await abrir(base());
  const contagem = await screen.findByRole("region", { name: "Bairros por estágio" });
  const critico = (await within(contagem).findByText("Crítico")).closest("li")!;
  expect(critico).toHaveTextContent("1");
  expect(critico).toHaveAttribute("title", "1 declarado, 0 sugeridos");
  const atencao = within(contagem).getByText("Atenção").closest("li")!;
  expect(atencao).toHaveAttribute("title", "0 declarados, 1 sugerido");
  const semDados = within(contagem).getByText("Sem dados").closest("li")!;
  expect(semDados).toHaveAttribute("title", "o sistema não consegue sugerir");
  expect(within(contagem).queryByText("Observação")).not.toBeInTheDocument();
  expect(contagem).toHaveTextContent("3 bairros: 1 declarado pela equipe, 1 sugerido pelo sistema");
});

test("o mapa recebe os bairros e diz a origem (declarado, sugerido ou sem dados)", async () => {
  await abrir(base());
  const mapa = await screen.findByTestId("mapa");
  const itens = await within(mapa).findAllByRole("listitem");
  expect(itens.map((i) => i.getAttribute("data-origem"))).toEqual(["declarado", "sugerido", "sem_dados"]);
});

test("clicar no bairro abre o painel: estágio declarado e sugerido, alertas e Em breve", async () => {
  await abrir(base());
  const u = userEvent.setup();
  await escolherBairro(u, "Ibura");
  const painel = await screen.findByRole("complementary", { name: "Ibura" });
  expect(within(painel).getAllByText("Distrito 8").length).toBeGreaterThan(0);
  expect(within(painel).getByText(/por Mari Lima/)).toBeInTheDocument();
  expect(within(painel).getByText(/Encosta instável/)).toBeInTheDocument();
  expect(within(painel).getByText("Chuva prevista de 62 mm em 24 h.")).toBeInTheDocument();
  // alerta oficial: fonte, hora, território exato e a conferência na APAC/Cemaden
  expect(within(painel).getByText(/APAC: ?alerta|APAC \(alerta\)/)).toBeInTheDocument();
  expect(within(painel).getByText("Território: Região Metropolitana do Recife")).toBeInTheDocument();
  expect(within(painel).getByRole("link", { name: /APAC/ })).toHaveAttribute(
    "href",
    expect.stringContaining("apac"),
  );
  expect(within(painel).getByRole("link", { name: /Cemaden/ })).toBeInTheDocument();
  // sem o resumo no servidor: avisa, sem número inventado
  expect(await within(painel).findByText("Ainda não disponível")).toBeInTheDocument();
  expect(within(painel).queryByText("Em breve.")).not.toBeInTheDocument();
  expect(within(painel).getByRole("button", { name: /Declarar/ })).toBeInTheDocument();
});

test("bairro sem alerta e sem sugestão: diz o que falta e não diz que está seguro", async () => {
  await abrir(base());
  const u = userEvent.setup();
  await escolherBairro(u, "Aflitos");
  const painel = await screen.findByRole("complementary", { name: "Aflitos" });
  expect(within(painel).getByText("Dados insuficientes")).toBeInTheDocument();
  expect(within(painel).getByText(/Falta previsão de chuva/)).toBeInTheDocument();
  expect(within(painel).getByText(/Nenhum alerta oficial ativo registrado/)).toBeInTheDocument();
  expect(painel).not.toHaveTextContent(/seguro|risco baixo\.$/i);
});

test("declarar a partir do painel envia o território escolhido", async () => {
  const pedidos = await abrir(base(), {
    "/estagios": { ok: true },
    "/estagios/mensagem": { texto: "msg", wa_me_url: "https://wa.me/?text=msg" },
  });
  const u = userEvent.setup();
  await escolherBairro(u, "Cohab");
  const painel = await screen.findByRole("complementary", { name: "Cohab" });
  await u.click(within(painel).getByRole("button", { name: /Declarar/ }));
  const dialogo = await screen.findByRole("dialog");
  await u.type(within(dialogo).getByLabelText(/Justificativa/), "Chuva forte");
  await u.click(within(dialogo).getByRole("button", { name: "Declarar situação" }));
  await waitFor(() =>
    expect(pedidos.some((p) => p.metodo === "POST" && p.url.endsWith("/estagios"))).toBe(true),
  );
  expect(pedidos.find((p) => p.metodo === "POST" && p.url.endsWith("/estagios"))!.corpo).toMatchObject({
    territorio_ids: ["bairro-cohab"],
    justificativa: "Chuva forte",
  });
});

test("territórios prioritários: o mais vulnerável primeiro, com critério e números; clicar escolhe o território", async () => {
  await abrir(base());
  const lista = await screen.findByRole("region", { name: "Territórios prioritários" });
  const itens = await within(lista).findAllByRole("listitem");
  expect(itens[0]).toHaveTextContent("Distrito 7");
  expect(itens[0]).toHaveTextContent("120 ocorrências de alagamento");
  expect(itens[0]).toHaveTextContent("8 ocorrências de deslizamento");
  expect(itens[0]).toHaveTextContent("Mais ocorrências de alagamento e deslizamento registradas.");
  // sem dado não vira zero
  expect(itens[1]).toHaveTextContent("ocorrências de deslizamento: sem dado");
  expect(lista).not.toHaveTextContent("%");
  const u = userEvent.setup();
  await u.click(within(itens[1]).getByRole("button"));
  expect(await screen.findByRole("complementary", { name: "Ibura" })).toBeInTheDocument();
});

test("a lista de bairros é a alternativa ao mapa: mais grave primeiro, com busca", async () => {
  await abrir(base());
  const u = userEvent.setup();
  const resumo = await screen.findByText("Ver os 3 bairros em lista");
  await u.click(resumo);
  const detalhes = resumo.closest("details")!;
  const nomes = within(detalhes)
    .getAllByRole("listitem")
    .map((li) => li.textContent);
  expect(nomes[0]).toContain("Ibura");
  expect(nomes[2]).toContain("Aflitos");
  await u.type(within(detalhes).getByRole("searchbox", { name: "Buscar bairro" }), "afli");
  expect(within(detalhes).getAllByRole("listitem")).toHaveLength(1);
  await u.click(within(detalhes).getByRole("button", { name: /Aflitos/ }));
  expect(await screen.findByRole("complementary", { name: "Aflitos" })).toBeInTheDocument();
});

test("rotas novas ainda não prontas (404): dizem Ainda não disponível, sem inventar dado", async () => {
  const m = base();
  delete (m as Record<string, unknown>)["/estagios/oficial"];
  delete (m as Record<string, unknown>)["/territorios/prioridade"];
  await abrir(m);
  const faixa = await screen.findByRole("region", { name: "Estágio oficial da cidade (COP)" });
  expect(await within(faixa).findByText("Ainda não disponível.")).toBeInTheDocument();
  expect(within(faixa).queryByRole("button", { name: "Informar estágio do COP" })).not.toBeInTheDocument();
  const lista = screen.getByRole("region", { name: "Territórios prioritários" });
  expect(await within(lista).findByText("Ainda não disponível.")).toBeInTheDocument();
});

test("sem o arquivo de bairros, o mapa mostra os distritos e diz isso", async () => {
  const m = base();
  delete (m as Record<string, unknown>)["/territorios/bairros.geojson"];
  (m as Record<string, unknown>)["/territorios/distritos.geojson"] = {
    type: "FeatureCollection",
    features: [
      {
        type: "Feature",
        geometry: { type: "Point", coordinates: [0, 0] },
        properties: { cdistscodi: 7, nome_distrito: "D7" },
      },
    ],
  };
  await abrir(m);
  expect(await screen.findByText("O mapa dos bairros ainda não está disponível.")).toBeInTheDocument();
  expect(await screen.findByRole("button", { name: "mapa: Distrito 7" })).toBeInTheDocument();
});

test("no modo Estágio: legenda com fonte e hora, cinza não é risco baixo, e o 'Atualizado às'", async () => {
  await abrir(base());
  const u = userEvent.setup();
  expect(screen.queryByRole("group", { name: "Legenda do mapa" })).not.toBeInTheDocument();
  await u.click(await screen.findByRole("radio", { name: "Estágio" }));
  const legenda = await screen.findByRole("group", { name: "Legenda do mapa" });
  expect(await within(legenda).findByText(/Estágios do ClimaSense/)).toBeInTheDocument();
  expect(
    within(legenda).getByText("Cinza tracejado não quer dizer risco baixo: falta dado."),
  ).toBeInTheDocument();
  expect(document.querySelector("[data-atualizado-as]")).toHaveTextContent(/Atualizado às \d{2}:\d{2}/);
});

test("padrão: colore por distrito, com um chip por distrito, o mais vulnerável primeiro", async () => {
  await abrir(base());
  const mapa = await screen.findByTestId("mapa");
  expect(mapa).toHaveAttribute("data-modo-cor", "distrito");
  expect(mapa).toHaveAttribute("data-foco", "");
  expect(screen.getByRole("radio", { name: "Distritos" })).toBeChecked();
  const grupo = screen.getByRole("group", { name: "Distritos sanitários" });
  const chips = within(grupo).getAllByRole("button");
  expect(chips).toHaveLength(8);
  // DS VII é o 1 na lista de prioridade: sobe para o primeiro chip
  await waitFor(() => expect(within(grupo).getAllByRole("button")[0]).toHaveTextContent("D7"));
});

test("chip do distrito: aproxima e abre o painel; de novo, limpa; Voltar ao Recife inteiro também", async () => {
  await abrir(base());
  const u = userEvent.setup();
  const grupo = await screen.findByRole("group", { name: "Distritos sanitários" });
  const chip = within(grupo).getByRole("button", { name: /D8,/ });
  await u.click(chip);
  expect(await screen.findByTestId("mapa")).toHaveAttribute("data-foco", "ds-8");
  expect(chip).toHaveAttribute("aria-pressed", "true");
  const painel = await screen.findByRole("complementary", { name: /Distrito 8/ });
  // bairros do distrito em lista, clicáveis
  expect(within(painel).getByRole("button", { name: /Ibura/ })).toBeInTheDocument();
  expect(within(painel).getByRole("button", { name: /Cohab/ })).toBeInTheDocument();
  expect(within(painel).queryByRole("button", { name: /Aflitos/ })).not.toBeInTheDocument();
  await u.click(chip);
  expect(screen.getByTestId("mapa")).toHaveAttribute("data-foco", "");
  expect(screen.queryByRole("complementary", { name: /Distrito 8/ })).not.toBeInTheDocument();
  await u.click(chip);
  await u.click(screen.getAllByRole("button", { name: "Voltar ao Recife inteiro" })[0]);
  expect(screen.getByTestId("mapa")).toHaveAttribute("data-foco", "");
});

test("painel do distrito: números com fonte, sem dado nunca vira zero, e descer para o bairro e subir de novo", async () => {
  await abrir(base());
  const u = userEvent.setup();
  await u.click(await screen.findByRole("button", { name: "mapa: Aflitos" })); // abre o DS III
  const painel = await screen.findByRole("complementary", { name: /Distrito 3/ });
  expect(within(painel).getByText("Números do distrito")).toBeInTheDocument();
  expect(within(painel).getAllByText("Dados insuficientes").length).toBeGreaterThan(0);
  expect(painel).not.toHaveTextContent(/risco baixo|seguro/i);
  await u.click(within(painel).getByRole("button", { name: /Aflitos/ }));
  expect(await screen.findByRole("heading", { level: 2, name: "Aflitos" })).toBeInTheDocument();
  expect(screen.getByTestId("mapa")).toHaveAttribute("data-selecionado", "bairro-aflitos");
  await u.click(
    within(screen.getByRole("complementary", { name: "Aflitos" })).getByRole("button", {
      name: /Distrito 3/,
    }),
  );
  expect(await screen.findByRole("complementary", { name: /Distrito 3/ })).toBeInTheDocument();
  expect(screen.getByTestId("mapa")).toHaveAttribute("data-selecionado", "");
  await u.keyboard("{Escape}");
  expect(screen.getByTestId("mapa")).toHaveAttribute("data-foco", "");
});

test("painel do distrito mostra idosos do Censo e 'Dados insuficientes' para o que a fonte não trouxe", async () => {
  await abrir(base());
  const u = userEvent.setup();
  await u.click(await screen.findByRole("button", { name: "mapa: Ibura" })); // DS VIII
  await u.click(
    within(screen.getByRole("group", { name: "Distritos sanitários" })).getByRole("button", {
      name: /^D7,/,
    }),
  );
  const painel = await screen.findByRole("complementary", { name: /Distrito 7$/ });
  const idosos = within(painel).getByText("Idosos (60 anos ou mais)").closest("div")!;
  await waitFor(() => expect(idosos).toHaveTextContent("24.619"));
  const criancas = within(painel).getByText("Crianças (0 a 14 anos)").closest("div")!;
  expect(criancas).toHaveTextContent("Dados insuficientes");
  expect(painel).toHaveTextContent("1º de 1");
});

test("Estágio com todos os bairros iguais: uma linha explica em vez de pintar tudo igual sem aviso", async () => {
  const todosObservacao = bairros.map((b) =>
    itemEstagio({
      ...b,
      declarado: null,
      sugerido: { estagio: "observacao", motivos: [], insumos: {}, calculado_em: AGORA },
    }),
  );
  await abrir(
    base({
      "/estagios?nivel=bairro": { dados: { itens: todosObservacao }, meta: { fontes: [] } },
    }),
  );
  const u = userEvent.setup();
  expect(screen.queryByText(/Todos os bairros estão em/)).not.toBeInTheDocument();
  await u.click(await screen.findByRole("radio", { name: "Estágio" }));
  expect(await screen.findByText(/Todos os bairros estão em Observação/)).toBeInTheDocument();
  expect(screen.getByTestId("mapa")).toHaveAttribute("data-modo-cor", "estagio");
});

test("Estágio com estágios diferentes não mostra o aviso de 'todos iguais'", async () => {
  await abrir(base());
  await userEvent.setup().click(await screen.findByRole("radio", { name: "Estágio" }));
  await screen.findByRole("group", { name: "Legenda do mapa" });
  expect(screen.queryByText(/Todos os bairros estão em/)).not.toBeInTheDocument();
});

test("Prioridade: escala de uma cor, legenda do mais ao menos prioritário, sem posição vira sem dado", async () => {
  await abrir(
    base({
      "/territorios/prioridade": {
        dados: {
          itens: [
            { territorio_id: "ds-7", nome: "Distrito 7", nivel: "distrito", posicao: 1 },
            { territorio_id: "bairro-ibura", nome: "Ibura", nivel: "bairro", posicao: 1 },
          ],
        },
        meta: { fontes: [] },
      },
    }),
  );
  await userEvent.setup().click(await screen.findByRole("radio", { name: "Prioridade" }));
  const mapa = await screen.findByTestId("mapa");
  expect(mapa).toHaveAttribute("data-modo-cor", "valor");
  const itens = within(mapa).getAllByRole("listitem");
  // só o Ibura tem posição entre os bairros: classe mais alta; os outros, sem dado (nunca "baixo")
  expect(itens.map((i) => i.getAttribute("data-valor"))).toEqual(["4", "", ""]);
  const legenda = screen.getByRole("group", { name: "Legenda do mapa" });
  expect(legenda).toHaveTextContent("Mais prioritários");
  expect(legenda).toHaveTextContent("Menos prioritários");
  expect(legenda).toHaveTextContent("Dados insuficientes");
  expect(legenda).toHaveTextContent("Prioridade não é a chance de acontecer");
});

test("enquanto os dados lentos carregam: o mapa já está lá, cinza liso e com o texto Carregando", async () => {
  const lento = base();
  const pedidos = simularApi(lento, {});
  void pedidos;
  const original = globalThis.fetch;
  vi.stubGlobal("fetch", (url: RequestInfo | URL, init?: RequestInit) =>
    String(url).includes("/estagios?nivel=bairro")
      ? new Promise<Response>(() => undefined)
      : original(url, init),
  );
  window.history.pushState({}, "", "/app");
  render(<App />);
  await screen.findByRole("heading", { level: 1, name: "Mapa" });
  const u = userEvent.setup();
  const mapa = await screen.findByTestId("mapa");
  expect(mapa).toHaveAttribute("data-pronto", "true"); // distritos só dependem do GeoJSON
  await u.click(await screen.findByRole("radio", { name: "Estágio" }));
  expect(screen.getByTestId("mapa")).toHaveAttribute("data-pronto", "false");
  expect(screen.getAllByText(/Carregando os estágios/).length).toBeGreaterThan(0);
});

test("Camadas extras ficam recolhidas por padrão", async () => {
  await abrir(base());
  const resumo = await screen.findByText(/Mais camadas: unidades de saúde/);
  expect(resumo.closest("details")).not.toHaveAttribute("open");
});
