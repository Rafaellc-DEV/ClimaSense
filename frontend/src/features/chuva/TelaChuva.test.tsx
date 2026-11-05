import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { App } from "@/app/App";
import { AGORA, itemEstagio, simularApi, usuarioTeste } from "@/features/evento/testes";
import { clienteConsultas } from "@/lib/api";
import { anosComDado, esteAno } from "./Historico";
import { fraseProximosDias } from "./ProximosDias";

const ANO = new Date().getFullYear();
const daqui = (h: number) => new Date(Date.now() + h * 3_600_000).toISOString();

function distrito(id: string, nome: string, p24: number | null, p72: number | null, estagio = "observacao") {
  return itemEstagio({
    territorio_id: id,
    territorio_nome: nome,
    sugerido: {
      estagio: estagio as "observacao",
      motivos: [],
      insumos: {
        chuva_prev_24h_mm: p24,
        chuva_prev_72h_mm: p72,
        pico_chuva_em: daqui(2),
        mare_no_pico_m: 1.1,
      },
      calculado_em: AGORA,
    },
  });
}
const LIMITES = { lim24: 25, lim72: 60, mareAlta: 0.6 };

const sazonal = {
  dados: {
    anos: [2020, ANO - 3, ANO - 2, ANO - 1, ANO],
    celulas: [
      { ano: 2020, mes: 12, valor: null, cobertura_pct: 3 },
      ...[ANO - 3, ANO - 2, ANO - 1].flatMap((a) =>
        Array.from({ length: 12 }, (_, i) => ({ ano: a, mes: i + 1, valor: 100, cobertura_pct: 100 })),
      ),
      { ano: ANO, mes: 1, valor: 150, cobertura_pct: 100 },
      { ano: ANO, mes: 2, valor: 150, cobertura_pct: 100 },
    ],
  },
  meta: { fontes: [], avisos: [], dados_insuficientes: false, cobertura_pct: 100, amostra: null },
};

function base() {
  return {
    "/auth/eu": usuarioTeste(),
    "/painel/resumo": {
      contadores: { avaliacoes: 0, comunicados: 0 },
      fontes: [
        { id: "open-meteo-historico", nome: "ERA5", status: "atualizada", ultima_atualizacao: AGORA },
        { id: "open-meteo-previsao", nome: "Previsão", status: "atualizada", ultima_atualizacao: AGORA },
      ],
    },
    "/estagios?nivel=distrito": {
      itens: [
        distrito("ds-1", "Distrito Sanitário I", 3, 8),
        distrito("ds-5", "Distrito Sanitário V", 62, 90, "alerta"),
      ],
    },
    "/estagios?nivel=bairro": {
      itens: [
        itemEstagio({
          territorio_id: "bairro-ibura",
          territorio_nome: "Ibura",
          nivel: "bairro",
          sugerido: {
            estagio: "observacao",
            motivos: [],
            insumos: { ocorrencias_historicas: 63 },
            calculado_em: AGORA,
          },
        }),
        itemEstagio({
          territorio_id: "bairro-areias",
          territorio_nome: "Areias",
          nivel: "bairro",
          sugerido: {
            estagio: "observacao",
            motivos: [],
            insumos: { ocorrencias_historicas: 182 },
            calculado_em: AGORA,
          },
        }),
      ],
    },
    "/estagios/parametros": {
      limiares: { chuva_prev_24h_atencao_mm: 25, chuva_prev_72h_atencao_mm: 60, mare_alta_m: 0.6 },
    },
    "/cenarios": {
      dados: {
        territorio_id: "ds-5",
        territorio_nome: "Distrito Sanitário V",
        horizonte_h: 72,
        emissoes_na_faixa: 1,
        chuva: [{ t: daqui(1), valor: 4, min: null, max: null }],
        mare: [{ t: daqui(1), valor: 1.1 }],
        estimativa: { mare_maxima_m: 1.1, mare_maxima_em: daqui(1) },
      },
      meta: { fontes: [], avisos: [], dados_insuficientes: false },
    },
    "/series/sazonalidade": sazonal,
  };
}

afterEach(() => {
  vi.unstubAllGlobals();
  clienteConsultas.clear();
});

test("próximos 3 dias: uma frase, só os distritos acima do limite e o gráfico de chuva com maré", async () => {
  const pedidos = simularApi(base());
  window.history.pushState({}, "", "/app/chuva");
  render(<App />);
  expect(
    await screen.findByRole("heading", { name: /^DS V pode passar do limite (hoje|amanhã)\.$/ }),
  ).toBeInTheDocument();
  const acima = screen.getByRole("list", { name: "Distritos acima do limite" });
  expect(within(acima).getAllByRole("listitem")).toHaveLength(1);
  expect(within(acima).getByText("Maré alta junto com a chuva")).toBeInTheDocument();
  expect(await screen.findByRole("region", { name: "Chuva e maré, hora a hora" })).toBeInTheDocument();
  expect(pedidos.some((p) => p.url.includes("/cenarios?territorio_id=ds-5"))).toBe(true);
  for (const saiu of [/Variável/, /Frequência/, /Média histórica/, /Série curta/, /Mediana/, /Cobertura/])
    expect(screen.queryByText(saiu)).not.toBeInTheDocument();
  expect(screen.getAllByText(/É uma previsão, não um alerta oficial/)).toHaveLength(1);
  expect(screen.queryByText(/^Fonte:/)).not.toBeInTheDocument();
});

test("histórico: este ano contra a média, o calendário e onde já alagou, com a fonte uma vez", async () => {
  simularApi(base());
  window.history.pushState({}, "", "/app/chuva?aba=historico");
  render(<App />);
  expect(await screen.findByRole("region", { name: "Este ano até agora" })).toBeInTheDocument();
  expect(
    screen.getByText(new RegExp(`Em ${ANO} choveu 300 mm no Recife até fevereiro, 50% acima`)),
  ).toBeInTheDocument();
  expect(screen.getByRole("region", { name: "Em que meses choveu mais?" })).toBeInTheDocument();
  const alagou = screen.getByRole("list", { name: /mais atendimentos de alagamento/ });
  expect(within(alagou).getAllByRole("listitem")[0]).toHaveTextContent("Areias");
  expect(screen.getAllByText(/Chuva estimada por satélite e modelo \(ERA5\), atualizada hoje/)).toHaveLength(
    1,
  );
  expect(screen.queryByText(/^Fonte:/)).not.toBeInTheDocument();
  await userEvent.setup().click(screen.getByRole("tab", { name: "Próximos 3 dias" }));
  expect(window.location.search).toBe("");
});

test("sem previsão não vira “sem chuva”; abaixo do limite diz o máximo previsto", () => {
  const vazio = [distrito("ds-1", "Distrito Sanitário I", null, null)];
  expect(fraseProximosDias(vazio, LIMITES).frase).toBe("Sem previsão de chuva agora.");
  const calmo = fraseProximosDias([distrito("ds-1", "Distrito Sanitário I", 1, 3)], LIMITES);
  expect(calmo.frase).toBe("Nenhum distrito passa do limite nos próximos 3 dias.");
  expect(calmo.apoio).toMatch(/3,0 mm em 3 dias, no DS I/);
});

test("o calendário começa no primeiro ano com dado e a média usa só os anos anteriores", () => {
  const d = anosComDado(sazonal.dados);
  expect(d.anos[0]).toBe(ANO - 3);
  const r = esteAno(d, ANO);
  expect(r.media[0]).toBe(100);
  expect(r.atual[2]).toBeNull();
});
