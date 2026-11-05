import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { simularApi } from "@/features/evento/testes";
import { clienteConsultas } from "@/lib/api";
import { PaginaInicial } from "./PaginaInicial";
import type { AbrigoPublico } from "./abrigosPublicos";

// o mapa (Leaflet) é apoio visual; a lista carrega a informação e é o que se testa aqui
vi.mock("./MapaAbrigos", () => ({ default: () => <div data-testid="mapa" /> }));

const AGORA = new Date().toISOString();
const DEPOIS = new Date(Date.now() + 5 * 3_600_000).toISOString();

const AVISO = {
  id: "a1",
  titulo: "Alerta de alagamento em Afogados",
  nivel: "alerta",
  territorios: [{ id: "bairro-afogados", tipo: "bairro", nome_exibicao: "Afogados" }],
  texto: "Chuva forte.",
  orientacoes: ["Evite atravessar ruas alagadas."],
  validade_inicio: AGORA,
  validade_fim: DEPOIS,
  emitido_por: "Vigilância em Saúde do Recife",
  publicado_em: AGORA,
  publico: "populacao",
};

const ESTADO_SEM = {
  avisos_ativos: 0,
  distritos_afetados: [],
  niveis_por_distrito: {},
  nivel_mais_alto: null,
  principal: null,
  atualizado_em: AGORA,
};

const local = (p: Partial<AbrigoPublico> & { id: string; nome: string }): AbrigoPublico => ({
  endereco: "Rua do Canal, 10",
  bairro_nome: "Várzea",
  distrito_nome: "Distrito Sanitário IV",
  latitude: -8.04,
  longitude: -34.95,
  aberto: null,
  aberto_fonte: null,
  aberto_lido_em: null,
  capacidade: null,
  tipo: "abrigo_temporario",
  atualizado_em: AGORA,
  origem: "Prefeitura do Recife",
  fonte_url: "https://dados.recife.pe.gov.br/",
  ...p,
});

const AFOGADOS = { id: "bairro-afogados", nome: "Afogados", distrito_id: "ds-5" };

const BASE = {
  "/publico/estado": ESTADO_SEM,
  "/publico/avisos": [],
  "/publico/fontes": [],
  "/publico/abrigos": { itens: [] },
};

function montar() {
  return render(
    <MemoryRouter>
      <QueryClientProvider client={clienteConsultas}>
        <PaginaInicial />
      </QueryClientProvider>
    </MemoryRouter>,
  );
}

async function buscar(u: ReturnType<typeof userEvent.setup>, texto: string) {
  await u.type(screen.getByLabelText("Digite o nome do seu bairro"), texto);
  await u.click(screen.getByRole("button", { name: "Ver avisos do bairro" }));
}

afterEach(() => {
  vi.unstubAllGlobals();
  clienteConsultas.clear();
});

test("a primeira coisa é a pergunta, com o campo, o botão e a localização", async () => {
  simularApi(BASE);
  montar();
  expect(screen.getByRole("heading", { level: 1, name: "Há aviso no meu bairro?" })).toBeInTheDocument();
  expect(screen.getByRole("search")).toBeInTheDocument();
  expect(screen.getByLabelText("Digite o nome do seu bairro")).toHaveAttribute("type", "search");
  expect(screen.getByRole("button", { name: "Usar minha localização" })).toBeInTheDocument();
  expect(screen.getAllByRole("link", { name: /Defesa Civil, 199/ })[0]).toHaveAttribute("href", "tel:199");
});

test("com aviso: nível, o que fazer, fonte, link do comunicado e abrigos do bairro primeiro", async () => {
  simularApi({
    ...BASE,
    "/publico/territorios/busca": [AFOGADOS],
    "/publico/avisos?bairro=": [AVISO],
    "/publico/abrigos": {
      itens: [
        local({ id: "1", nome: "Escola da Várzea" }),
        local({
          id: "2",
          nome: "Escola de Afogados",
          bairro_nome: "Afogados",
          distrito_nome: "Distrito Sanitário V",
        }),
      ],
    },
  });
  montar();
  const u = userEvent.setup();
  await buscar(u, "afogados");
  expect(await screen.findByRole("heading", { name: "Avisos para Afogados" })).toBeInTheDocument();
  expect(screen.getByText(/^Alerta para Afogados até/)).toBeInTheDocument();
  expect(screen.getByText("Evite atravessar ruas alagadas.")).toBeInTheDocument();
  expect(screen.getByText(/Fonte: Vigilância em Saúde do Recife/)).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /Ler o comunicado completo/ })).toHaveAttribute(
    "href",
    "/avisos/a1",
  );
  const perto = screen.getByRole("heading", { name: "Abrigos perto de Afogados" }).closest("section")!;
  const cartoes = within(perto).getAllByRole("listitem");
  expect(within(cartoes[0]).getByText("Escola de Afogados")).toBeInTheDocument();
  expect(within(cartoes[0]).getByText(/No bairro Afogados/)).toBeInTheDocument();
  expect(
    within(cartoes[0]).getByRole("link", { name: /Ligar para confirmar a abertura de Escola de Afogados/ }),
  ).toHaveAttribute("href", "tel:08000813400");
  expect(within(cartoes[0]).getByRole("link", { name: /Como chegar/ })).toBeInTheDocument();
  expect(within(cartoes[0]).queryByText(/Aberto agora/)).not.toBeInTheDocument();
});

test("sem aviso: diz que não significa ausência de risco", async () => {
  simularApi({ ...BASE, "/publico/territorios/busca": [AFOGADOS], "/publico/avisos?bairro=": [] });
  montar();
  await buscar(userEvent.setup(), "Afogados");
  expect(
    await screen.findByRole("heading", { name: "Sem aviso publicado para Afogados" }),
  ).toBeInTheDocument();
  expect(
    screen.getByText(
      /Nenhum aviso ativo publicado pela equipe para Afogados. Isso não significa ausência de risco/,
    ),
  ).toBeInTheDocument();
  expect(screen.queryByText(/sem risco|tudo seguro/i)).not.toBeInTheDocument();
});

test("bairro não encontrado: orienta a conferir a escrita ou escolher no mapa", async () => {
  simularApi({ ...BASE, "/publico/territorios/busca": [] });
  montar();
  const u = userEvent.setup();
  await buscar(u, "xyzzy");
  expect(await screen.findByText(/Não achamos esse bairro/)).toBeInTheDocument();
  await u.click(screen.getByRole("button", { name: "Escolher no mapa" }));
  expect(screen.getByRole("tab", { name: "Mapa" })).toHaveAttribute("aria-selected", "true");
});

test("erro de rede na busca: nunca vira “sem aviso” e permite tentar de novo", async () => {
  simularApi({
    ...BASE,
    "/publico/territorios/busca": [AFOGADOS],
    "/publico/avisos?bairro=": { status: 503 },
  });
  montar();
  const u = userEvent.setup();
  await buscar(u, "Afogados");
  expect(
    await screen.findByText("Não foi possível verificar os avisos agora.", { selector: "h2" }),
  ).toBeInTheDocument();
  expect(screen.getByText(/Em emergência, ligue 199/)).toBeInTheDocument();
  expect(screen.queryByText(/Sem aviso publicado/)).not.toBeInTheDocument();
  simularApi({ ...BASE, "/publico/territorios/busca": [AFOGADOS], "/publico/avisos?bairro=": [AVISO] });
  await u.click(screen.getByRole("button", { name: "Tentar de novo" }));
  expect(await screen.findByRole("heading", { name: "Avisos para Afogados" })).toBeInTheDocument();
});

test("campo curto: a mensagem fica junto ao campo", async () => {
  simularApi(BASE);
  montar();
  await buscar(userEvent.setup(), "a");
  expect(screen.getByText("Digite pelo menos duas letras do nome do bairro.")).toBeInTheDocument();
  expect(screen.getByLabelText("Digite o nome do seu bairro")).toHaveAttribute("aria-invalid", "true");
});

test("sem aviso: o herói não tem “Recife agora” nem banner; a aba Comunicados diz que não significa ausência de risco", async () => {
  simularApi(BASE);
  montar();
  expect(await screen.findByText("Nenhum comunicado em vigor agora.")).toBeInTheDocument();
  expect(screen.getByText(/Isso não significa ausência de risco\. Em chuva forte/)).toBeInTheDocument();
  expect(screen.queryByText("Recife agora")).not.toBeInTheDocument();
  expect(screen.queryByText(/Verificado/)).not.toBeInTheDocument();
  expect(screen.queryByRole("link", { name: "Ler o comunicado completo" })).not.toBeInTheDocument();
  expect(screen.queryByText(/sem risco|tudo seguro/i)).not.toBeInTheDocument();
});

test("com aviso ativo: um banner fino no topo do herói, com o nível, o link e a região aria-live única", async () => {
  simularApi({
    ...BASE,
    "/publico/estado": {
      ...ESTADO_SEM,
      avisos_ativos: 2,
      niveis_por_distrito: { "ds-5": "alerta" },
      principal: AVISO,
    },
    "/publico/avisos": [AVISO],
  });
  montar();
  const u = userEvent.setup();
  const banner = (await screen.findByText(/^Alerta para Afogados até/)).closest("[data-nivel]")!;
  expect(banner).toHaveAttribute("data-nivel", "alerta");
  expect(within(banner as HTMLElement).getByText(/E mais 1 aviso em vigor/)).toBeInTheDocument();
  expect(
    within(banner as HTMLElement).getByRole("link", { name: "Ler o comunicado completo" }),
  ).toHaveAttribute("href", "/avisos/a1");
  // o banner é a única região de status do herói; o resultado da busca não repete o anúncio
  expect(banner.closest('[role="status"]')).not.toBeNull();
  await u.click(screen.getByRole("tab", { name: "Mapa" }));
  await u.click(within(banner as HTMLElement).getByRole("button", { name: "Ver comunicados" }));
  expect(screen.getByRole("tab", { name: /Comunicados/ })).toHaveAttribute("aria-selected", "true");
});

test("falha ao consultar o estado: nenhum banner e nunca “sem aviso” no herói", async () => {
  simularApi({ ...BASE, "/publico/estado": { status: 503 } });
  montar();
  expect(await screen.findByText("Nenhum comunicado em vigor agora.")).toBeInTheDocument();
  expect(screen.queryByText("Nenhum aviso ativo publicado pela equipe.")).not.toBeInTheDocument();
  expect(screen.queryByRole("link", { name: "Ler o comunicado completo" })).not.toBeInTheDocument();
});

test("falha ao carregar os comunicados: nunca vira “sem aviso”; diz que não quer dizer sem risco e permite tentar de novo", async () => {
  simularApi({ ...BASE, "/publico/avisos": { status: 503 } });
  montar();
  const u = userEvent.setup();
  expect(
    await screen.findByText("Não foi possível verificar os avisos agora.", {}, { timeout: 4000 }),
  ).toBeInTheDocument();
  expect(
    screen.getByText(/Isso não quer dizer que não há risco\. Em emergência, ligue 199\./),
  ).toBeInTheDocument();
  expect(screen.queryByText(/Nenhum comunicado em vigor/)).not.toBeInTheDocument();
  simularApi({ ...BASE, "/publico/avisos": [AVISO] });
  await u.click(screen.getByRole("button", { name: "Tentar de novo" }));
  expect(await screen.findByRole("list", { name: "Comunicados em vigor" })).toBeInTheDocument();
});

test("abas: três, com role e aria-selected, e as setas do teclado trocam de aba", async () => {
  simularApi(BASE);
  montar();
  const u = userEvent.setup();
  const abas = screen.getAllByRole("tab");
  expect(abas.map((a) => a.textContent)).toEqual(["Comunicados", "Abrigos", "Mapa"]);
  expect(screen.getByRole("tablist")).toBeInTheDocument();
  expect(abas[0]).toHaveAttribute("aria-selected", "true");
  abas[0].focus();
  await u.keyboard("{ArrowRight}");
  expect(screen.getByRole("tab", { name: "Abrigos" })).toHaveAttribute("aria-selected", "true");
  await u.keyboard("{ArrowRight}");
  expect(screen.getByRole("tab", { name: "Mapa" })).toHaveAttribute("aria-selected", "true");
  expect(screen.getByRole("tabpanel")).toBeInTheDocument();
});

test("a aba Comunicados mostra 3 e “Ver todos”, em lista vertical", async () => {
  const avisos = ["1", "2", "3", "4"].map((n) => ({ ...AVISO, id: `a${n}`, titulo: `Aviso ${n}` }));
  simularApi({ ...BASE, "/publico/avisos": avisos });
  montar();
  const u = userEvent.setup();
  const lista = await screen.findByRole("list", { name: "Comunicados em vigor" });
  expect(within(lista).getAllByRole("article")).toHaveLength(3);
  expect(screen.getByRole("tab", { name: /Comunicados \(4 em vigor\)/ })).toBeInTheDocument();
  await u.click(screen.getByRole("button", { name: "Ver todos os 4 comunicados" }));
  expect(within(lista).getAllByRole("article")).toHaveLength(4);
});

test("aba Abrigos: sem aberto confirmado nunca diz “aberto”; CRAS só no filtro à parte", async () => {
  simularApi({
    ...BASE,
    "/publico/abrigos": {
      itens: [
        local({ id: "1", nome: "Abrigo da Várzea" }),
        local({ id: "3", nome: "CRAS Várzea", tipo: "cras" }),
      ],
    },
  });
  montar();
  const u = userEvent.setup();
  await u.click(screen.getByRole("tab", { name: "Abrigos" }));
  expect(await screen.findByText("Nenhum abrigo ativo neste momento.")).toBeInTheDocument();
  const lista = screen.getByRole("list", { name: "Locais de abrigo" });
  expect(within(lista).getByText("Abrigo da Várzea")).toBeInTheDocument();
  expect(within(lista).queryByText("CRAS Várzea")).not.toBeInTheDocument();
  expect(within(lista).getByText(/Confirme a abertura com a Defesa Civil/)).toBeInTheDocument();
  expect(within(lista).queryByText(/Aberto agora/)).not.toBeInTheDocument();
  await u.selectOptions(screen.getByLabelText("Tipo de local"), "cras");
  expect(
    within(screen.getByRole("list", { name: "Locais de abrigo" })).getByText("CRAS Várzea"),
  ).toBeInTheDocument();
  expect(screen.getByText(/não um abrigo/)).toBeInTheDocument();
});

test("aba Abrigos: aberto só com confirmação, com quem informou, e vai primeiro", async () => {
  simularApi({
    ...BASE,
    "/publico/abrigos": {
      itens: [
        local({ id: "1", nome: "A fechado", bairro_nome: "Afogados" }),
        local({ id: "2", nome: "B aberto", aberto: true, aberto_fonte: "cop", aberto_lido_em: AGORA }),
      ],
    },
  });
  montar();
  const u = userEvent.setup();
  await u.click(screen.getByRole("tab", { name: "Abrigos" }));
  expect(await screen.findByText("1 abrigo aberto agora.")).toBeInTheDocument();
  const itens = within(screen.getByRole("list", { name: "Locais de abrigo" })).getAllByRole("listitem");
  expect(within(itens[0]).getByText("B aberto")).toBeInTheDocument();
  expect(within(itens[0]).getByText(/informado pela Defesa Civil/)).toBeInTheDocument();
});

test("lista de abrigos fora do ar (404): diz a verdade e dá o 0800", async () => {
  simularApi({ ...BASE, "/publico/abrigos": { status: 404 } });
  montar();
  await userEvent.setup().click(screen.getByRole("tab", { name: "Abrigos" }));
  expect(
    await screen.findByText("A lista de abrigos ainda não está disponível. Ligue 0800 081 3400."),
  ).toBeInTheDocument();
});

test("lista de abrigos vazia: “Nenhum local de abrigo cadastrado ainda.”", async () => {
  simularApi(BASE);
  montar();
  await userEvent.setup().click(screen.getByRole("tab", { name: "Abrigos" }));
  expect(await screen.findByText(/Nenhum local de abrigo cadastrado ainda/)).toBeInTheDocument();
});

describe("localização", () => {
  const geo = (impl: (ok: PositionCallback, err: PositionErrorCallback) => void) =>
    vi.stubGlobal("navigator", { ...navigator, geolocation: { getCurrentPosition: impl } });

  test("só é pedida depois do toque", async () => {
    const pedir = vi.fn();
    geo(pedir);
    simularApi(BASE);
    montar();
    expect(pedir).not.toHaveBeenCalled();
    await userEvent.setup().click(screen.getByRole("button", { name: "Usar minha localização" }));
    expect(pedir).toHaveBeenCalledTimes(1);
  });

  test("negada: volta ao campo manual com mensagem clara", async () => {
    geo((_ok, err) => err({ code: 1, message: "" } as GeolocationPositionError));
    simularApi(BASE);
    montar();
    await userEvent.setup().click(screen.getByRole("button", { name: "Usar minha localização" }));
    expect(await screen.findByText("Sem problema. Digite o nome do bairro acima.")).toBeInTheDocument();
    expect(screen.queryByText(/Sem aviso publicado/)).not.toBeInTheDocument();
  });

  test("imprecisa: não afirma nada sobre avisos", async () => {
    geo((ok) =>
      ok({ coords: { latitude: -8.05, longitude: -34.9, accuracy: 20000 } } as GeolocationPosition),
    );
    simularApi(BASE);
    montar();
    await userEvent.setup().click(screen.getByRole("button", { name: "Usar minha localização" }));
    expect(await screen.findByRole("heading", { name: "A localização está imprecisa" })).toBeInTheDocument();
    expect(screen.queryByText(/Abrigos mais perto/)).not.toBeInTheDocument();
  });

  test("ok: abrigos com a distância real, dizendo que o bairro é desconhecido", async () => {
    geo((ok) => ok({ coords: { latitude: -8.04, longitude: -34.95, accuracy: 50 } } as GeolocationPosition));
    simularApi({ ...BASE, "/publico/abrigos": { itens: [local({ id: "1", nome: "Escola da Várzea" })] } });
    montar();
    await userEvent.setup().click(screen.getByRole("button", { name: "Usar minha localização" }));
    expect(await screen.findByRole("heading", { name: "Abrigos mais perto de você" })).toBeInTheDocument();
    expect(screen.getByText(/a \d+ m de você/)).toBeInTheDocument();
    expect(screen.getByText(/não dá para saber o seu bairro/)).toBeInTheDocument();
  });
});
