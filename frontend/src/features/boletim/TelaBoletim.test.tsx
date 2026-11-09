import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { App } from "@/app/App";
import { AGORA, simularApi, usuarioTeste } from "@/features/evento/testes";
import { clienteConsultas } from "@/lib/api";
import { numeroBoletim } from "./TelaBoletim";

const sugerido = (estagio: string) => ({
  estagio,
  rotulo: estagio,
  motivos: [],
  faltando: [],
  insumos: {},
  calculado_em: AGORA,
});

const boletim = {
  dados: {
    territorio_id: "recife",
    territorio_nome: "Recife inteiro",
    gerado_em: AGORA,
    estagios: [
      {
        territorio_id: "ds-5",
        territorio_nome: "Distrito Sanitário V",
        estagio: "alerta",
        rotulo: "Alerta",
        origem: "declarado",
        sugerido: sugerido("alerta"),
        declarado: {
          estagio: "alerta",
          rotulo: "Alerta",
          justificativa: "x",
          autor_nome: "Mari Lima",
          declarado_em: AGORA,
        },
      },
      {
        territorio_id: "ds-1",
        territorio_nome: "Distrito Sanitário I",
        estagio: "atencao",
        rotulo: "Atenção",
        origem: "sugerido",
        sugerido: sugerido("atencao"),
        declarado: null,
      },
    ],
    territorios_em_atencao: [],
    chuva: {
      chuva_24h_mm: 18.2,
      chuva_24h_territorio: "Distrito Sanitário V",
      chuva_prev_24h_mm: 64.5,
      chuva_prev_24h_territorio: "Distrito Sanitário V",
      chuva_prev_72h_mm: 90,
      chuva_prev_72h_territorio: "Distrito Sanitário V",
      previsao_emitida_em: AGORA,
    },
    mare: { maxima_m: 2.45, maxima_em: AGORA, emitida_em: AGORA },
    acoes_em_andamento: [
      {
        id: "r1",
        territorio_id: "bairro-ibura",
        territorio_nome: "Ibura",
        tipo: "outro",
        descricao: "Equipe no Ibura.",
        responsavel: "Defesa Civil",
        situacao: "em_andamento",
        inicio_em: AGORA,
        criada_em: AGORA,
        autor_nome: "Mari Lima",
      },
    ],
  },
  meta: { fontes: [], avisos: [] },
};

const saude = {
  agravos: [
    {
      agravo: "dengue",
      nome: "Dengue",
      fonte_id: "infodengue",
      ultima_semana: { ano: 2026, semana: 43, inicio: "2026-10-25" },
      casos: 36,
      casos_estimados: 221,
      variacao_4s_pct: 3,
      nivel_alerta: 2,
      incompleta: true,
    },
    {
      agravo: "leptospirose",
      nome: "Leptospirose",
      fonte_id: "sinan",
      ultima_semana: null,
      casos: null,
      casos_estimados: null,
      variacao_4s_pct: null,
      nivel_alerta: null,
      incompleta: false,
    },
  ],
  janela_leptospirose: {
    ativa: true,
    inicio: "2026-10-27",
    fim: "2026-11-26",
    motivo: null,
    territorios: [],
  },
  gerado_em: AGORA,
};

function base() {
  return {
    "/auth/eu": usuarioTeste(),
    "/fontes": [
      {
        id: "apac-chuva",
        nome: "Chuva observada nos pluviômetros (APAC)",
        status: "atualizada",
        ultima_atualizacao: AGORA,
      },
      { id: "inmet", nome: "Estação planejada", status: "planejada", ultima_atualizacao: null },
    ],
    "/boletim": boletim,
    "/saude/resumo": { dados: saude },
  };
}

afterEach(() => {
  vi.unstubAllGlobals();
  clienteConsultas.clear();
});

test("documento com marca, número, resumo, destaques e as seções fixas; só a situação declarada", async () => {
  simularApi(base());
  window.history.pushState({}, "", "/app/acoes/relatorio");
  render(<App />);
  const folha = await screen.findByRole("article", { name: "Relatório executivo — Secretaria de Saúde" });
  expect(within(folha).getByRole("img", { name: "ClimaSense" })).toBeInTheDocument();
  expect(within(folha).getByText("Vigilância em Saúde · Recife/PE")).toBeInTheDocument();
  expect(within(folha).getByText(/^BOL-\d{4}-\d{4}-\d{4}$/)).toBeInTheDocument();
  expect(within(folha).getByText("Emitido")).toBeInTheDocument();
  expect(
    within(folha).getByText("Chuvas, desastres e saúde · consolidado automaticamente"),
  ).toBeInTheDocument();

  const resumo = await within(folha).findByRole("region", { name: "Resumo" });
  expect(resumo).toHaveTextContent("Distrito 5 em Alerta. Um distrito está sem declaração.");
  expect(resumo).toHaveTextContent("Janela de vigilância de leptospirose aberta até 26/11.");
  const destaques = within(folha).getByRole("region", { name: "Destaques" });
  expect(destaques).toHaveTextContent("Distrito 1: o sistema sugere Atenção, acima do declarado.");

  const situacao = within(folha).getByRole("region", { name: "Situação por distrito" });
  expect(within(situacao).getByText("sem declaração")).toBeInTheDocument();
  expect(within(situacao).queryByText("Atenção")).not.toBeInTheDocument();

  for (const s of ["Chuva e maré", "Saúde", "Ações da equipe"])
    expect(within(folha).getByRole("region", { name: s })).toBeInTheDocument();
  expect(await within(folha).findByText("Nível 2, amarelo")).toBeInTheDocument();
  expect(await within(folha).findByText(/Equipe no Ibura/)).toBeInTheDocument();
  expect(within(folha).getByText("De onde vêm os números")).toBeInTheDocument();
  expect(
    within(folha).getByText(/Chuva observada nos pluviômetros \(APAC\), atualizada hoje/),
  ).toBeInTheDocument();
  expect(within(folha).queryByText(/Estação planejada/)).not.toBeInTheDocument();
  expect(within(folha).queryByText(/Desabrigados|ocupação/i)).not.toBeInTheDocument();
});

test("imprimir chama o navegador; copiar manda o texto para o WhatsApp, sem criar registro", async () => {
  const pedidos = simularApi(base());
  const imprimir = vi.fn();
  vi.stubGlobal("print", imprimir);
  window.history.pushState({}, "", "/app/acoes/relatorio");
  render(<App />);
  const u = userEvent.setup();
  const escrever = vi.spyOn(navigator.clipboard, "writeText").mockResolvedValue();
  await screen.findByRole("region", { name: "Resumo" });
  await u.click(screen.getByRole("button", { name: "Imprimir / salvar PDF" }));
  expect(imprimir).toHaveBeenCalled();
  await u.click(screen.getByRole("button", { name: "Copiar para WhatsApp" }));
  const texto = escrever.mock.calls[0][0];
  expect(texto).toMatch(/^\*Relatório executivo ClimaSense — Secretaria de Saúde\* BOL-/);
  expect(texto).toContain("- Distrito 1: sem declaração");
  expect(texto).toContain("Confira na APAC e no Cemaden.");
  expect(pedidos.filter((p) => p.metodo === "POST")).toHaveLength(0);
});

test("sem a rota de saúde (404), a seção Saúde diz que ainda não está disponível", async () => {
  const b = base() as Record<string, unknown>;
  delete b["/saude/resumo"];
  simularApi(b);
  window.history.pushState({}, "", "/app/acoes/relatorio");
  render(<App />);
  const saudeSecao = await screen.findByRole("region", { name: "Saúde" });
  expect(await within(saudeSecao).findByText("Ainda não disponível.")).toBeInTheDocument();
  expect(screen.getByRole("region", { name: "Resumo" })).toHaveTextContent(
    "Dados de saúde ainda não disponíveis",
  );
});

test("o número do boletim é a data e a hora da emissão no Recife", () => {
  expect(numeroBoletim(new Date("2026-11-05T20:00:00Z"))).toBe("BOL-2026-1105-1700");
});

test("bairros de cada distrito, em ordem alfabética, só na página e não no texto do WhatsApp", async () => {
  simularApi({
    ...base(),
    "/territorios": [
      { id: "ds-5", tipo: "distrito", nome_exibicao: "Distrito Sanitário V", pai_id: "recife" },
      { id: "b-2", tipo: "bairro", nome_exibicao: "Ibura", pai_id: "ds-5" },
      { id: "b-1", tipo: "bairro", nome_exibicao: "Areias", pai_id: "ds-5" },
      { id: "b-3", tipo: "bairro", nome_exibicao: "Boa Vista", pai_id: "ds-1" },
    ],
  });
  window.history.pushState({}, "", "/app/acoes/relatorio");
  render(<App />);
  const folha = await screen.findByRole("article", { name: "Relatório executivo — Secretaria de Saúde" });
  expect(await within(folha).findByText("Bairros: Areias, Ibura")).toBeInTheDocument();
  expect(within(folha).getByText("Bairros: Boa Vista")).toBeInTheDocument();
  await userEvent.setup().click(screen.getByText("Ver o texto para o WhatsApp"));
  const caixa = (await screen.findByLabelText("Texto para o WhatsApp")) as HTMLTextAreaElement;
  expect(caixa.value).toContain("Distrito 5");
  expect(caixa.value).not.toContain("Areias");
});

test("sem a lista de territórios, a linha de bairros some e o boletim continua inteiro", async () => {
  simularApi(base());
  window.history.pushState({}, "", "/app/acoes/relatorio");
  render(<App />);
  const situacao = await screen.findByRole("region", { name: "Situação por distrito" });
  expect(within(situacao).queryByText(/^Bairros:/)).not.toBeInTheDocument();
  expect(within(situacao).getByText("Distrito Sanitário V")).toBeInTheDocument();
});
