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
  }: {
    territorios: GeoJSON.FeatureCollection<GeoJSON.Geometry, { id: string; nome: string }>;
    aoSelecionar: (id: string) => void;
    aparencia: (id: string) => { ordem: number | null; origem: string };
  }) => (
    <ul data-testid="mapa">
      {territorios.features.map((f) => (
        <li key={f.properties.id} data-origem={aparencia(f.properties.id).origem}>
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

const abrigo = (id: string, nome: string, bairro: string, distrito: string, aberto = true) => ({
  id,
  nome,
  bairro_id: bairro,
  bairro_nome: bairro,
  distrito_id: distrito,
  aberto,
  status_fonte: "equipe",
  atualizado_em: AGORA,
  endereco: "Rua A",
});

function base(extra: Record<string, unknown> = {}, permissoes = ["consultar", "editar"]) {
  return {
    "/auth/eu": usuarioTeste(permissoes),
    "/painel/resumo": { contadores: { avaliacoes: 0, comunicados: 0 }, fontes: [] },
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
            nome: "Distrito Sanitário VII",
            nivel: "alerta",
            posicao: 1,
            ocorrencias_alagamento: 120,
            ocorrencias_deslizamento: 8,
            criterio: "Mais ocorrências de alagamento e deslizamento registradas.",
          },
          {
            territorio_id: "bairro-ibura",
            nome: "Ibura",
            nivel: "critico",
            posicao: 2,
            ocorrencias_alagamento: 63,
            ocorrencias_deslizamento: null,
            criterio: "Histórico de alagamento.",
          },
        ],
      },
      meta: { fontes: [] },
    },
    "/abrigos": {
      itens: [
        abrigo("a1", "Escola do Ibura", "bairro-ibura", "ds-8"),
        abrigo("a2", "Igreja da Cohab", "bairro-cohab", "ds-8"),
      ],
      totais: { abrigos_abertos: 2, abrigos_cadastrados: 2, atualizado_em: AGORA },
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

test("/app abre o Mapa; o menu tem Mapa primeiro e a Situação continua acessível", async () => {
  await abrir(base());
  const menu = (await screen.findAllByRole("navigation", { name: "Menu principal" }))[0];
  const links = within(menu).getAllByRole("link");
  expect(links[0]).toHaveTextContent("Mapa");
  expect(within(menu).getByRole("link", { name: "Situação" })).toHaveAttribute("href", "/app/situacao");
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
  expect(within(faixa).getAllByText("Alerta").length).toBeGreaterThan(1); // selo do COP e linha da contagem
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
  await u.click(await screen.findByRole("button", { name: "mapa: Ibura" }));
  await screen.findByRole("heading", { level: 2, name: "Ibura" });
  expect(screen.queryByRole("button", { name: /Declarar/ })).not.toBeInTheDocument();
});

test("a contagem separa declarado e sugerido, e sem dados não vira observação", async () => {
  await abrir(base());
  const contagem = await screen.findByRole("region", { name: "Bairros por estágio" });
  await within(contagem).findByText("1 declarado, 0 sugeridos");
  expect(within(contagem).getByText("0 declarados, 1 sugerido", { exact: false })).toBeInTheDocument();
  const semDados = within(contagem).getByText("Sem dados").closest("li")!;
  expect(semDados).toHaveTextContent("o sistema não consegue sugerir");
  const obs = within(contagem).getByText("Observação").closest("li")!;
  expect(obs).toHaveTextContent("0");
  expect(obs).toHaveTextContent("nenhum");
});

test("o mapa recebe os bairros e diz a origem (declarado, sugerido ou sem dados)", async () => {
  await abrir(base());
  const mapa = await screen.findByTestId("mapa");
  const itens = await within(mapa).findAllByRole("listitem");
  expect(itens.map((i) => i.getAttribute("data-origem"))).toEqual(["declarado", "sugerido", "sem_dados"]);
});

test("clicar no bairro abre o painel: estágio declarado e sugerido, alertas, abrigos e Em breve", async () => {
  await abrir(base());
  const u = userEvent.setup();
  await u.click(await screen.findByRole("button", { name: "mapa: Ibura" }));
  const painel = await screen.findByRole("complementary", { name: "Ibura" });
  expect(within(painel).getByText("Distrito Sanitário VIII")).toBeInTheDocument();
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
  // abrigo do bairro e abrigo próximo (mesmo distrito)
  expect(within(painel).getByText("Escola do Ibura")).toBeInTheDocument();
  expect(within(painel).getByText("Outros abrigos do mesmo distrito")).toBeInTheDocument();
  expect(within(painel).getByText("Igreja da Cohab")).toBeInTheDocument();
  // espaço reservado, sem números
  expect(within(painel).getByText("Em breve.")).toBeInTheDocument();
  expect(within(painel).getByRole("button", { name: /Declarar/ })).toBeInTheDocument();
});

test("bairro sem alerta e sem sugestão: diz o que falta e não diz que está seguro", async () => {
  await abrir(base());
  const u = userEvent.setup();
  await u.click(await screen.findByRole("button", { name: "mapa: Aflitos" }));
  const painel = await screen.findByRole("complementary", { name: "Aflitos" });
  expect(within(painel).getByText("Dados insuficientes")).toBeInTheDocument();
  expect(within(painel).getByText(/Falta previsão de chuva/)).toBeInTheDocument();
  expect(within(painel).getByText(/Nenhum alerta oficial ativo registrado/)).toBeInTheDocument();
  expect(painel).not.toHaveTextContent(/seguro|risco baixo\.$/i);
  expect(within(painel).getByText(/Nenhum abrigo cadastrado neste bairro/)).toBeInTheDocument();
});

test("declarar a partir do painel envia o território escolhido", async () => {
  const pedidos = await abrir(base(), {
    "/estagios": { ok: true },
    "/estagios/mensagem": { texto: "msg", wa_me_url: "https://wa.me/?text=msg" },
  });
  const u = userEvent.setup();
  await u.click(await screen.findByRole("button", { name: "mapa: Cohab" }));
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
  expect(itens[0]).toHaveTextContent("Distrito Sanitário VII");
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
        properties: { cdistscodi: 7, nome_distrito: "DS VII" },
      },
    ],
  };
  await abrir(m);
  expect(await screen.findByText("O mapa dos bairros ainda não está disponível.")).toBeInTheDocument();
  expect(await screen.findByRole("button", { name: "mapa: Distrito Sanitário VII" })).toBeInTheDocument();
});

test("mostra fonte e hora na legenda e o 'Atualizado às'", async () => {
  await abrir(base());
  const legenda = await screen.findByRole("group", { name: "Legenda do mapa" });
  expect(await within(legenda).findByText(/Estágios do ClimaSense/)).toBeInTheDocument();
  expect(
    within(legenda).getByText("Cinza tracejado não quer dizer risco baixo: falta dado."),
  ).toBeInTheDocument();
  expect(document.querySelector("[data-atualizado-as]")).toHaveTextContent(/Atualizado às \d{2}:\d{2}/);
});
