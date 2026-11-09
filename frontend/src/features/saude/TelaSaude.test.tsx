import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { App } from "@/app/App";
import { simularApi, usuarioTeste } from "@/features/evento/testes";
import { clienteConsultas } from "@/lib/api";
import { inicioDaSemana, tendenciaDe, utilizavel } from "./TelaSaude";
import type { ResumoAgravo, SerieSemanal } from "./tipos";

const HOJE = new Date();
const dia = (atras: number) => new Date(HOJE.getTime() - atras * 86_400_000).toISOString().slice(0, 10);

const agravo = (extra: Partial<ResumoAgravo> & Pick<ResumoAgravo, "agravo" | "nome" | "fonte_id">) =>
  ({
    ultima_semana: null,
    casos: null,
    casos_estimados: null,
    variacao_4s_pct: null,
    nivel_alerta: null,
    incompleta: false,
    ...extra,
  }) as ResumoAgravo;

const semana = (atras: number) => ({ ano: 2026, semana: 40, inicio: dia(atras) });

const FONTES = [
  {
    id: "infodengue",
    nome: "InfoDengue",
    atualizado_em: HOJE.toISOString(),
    limite_frescor_h: 192,
    desatualizado: false,
  },
  {
    id: "sinan-leptospirose",
    nome: "SINAN",
    atualizado_em: HOJE.toISOString(),
    limite_frescor_h: 360,
    desatualizado: false,
  },
];

const resumo = (janela: unknown = null, agravos?: ResumoAgravo[]) => ({
  dados: {
    agravos: agravos ?? [
      agravo({
        agravo: "dengue",
        nome: "Dengue",
        fonte_id: "infodengue",
        ultima_semana: semana(10),
        casos: 36,
        incompleta: true,
      }),
      agravo({
        agravo: "chikungunya",
        nome: "Chikungunya",
        fonte_id: "infodengue",
        ultima_semana: semana(10),
        casos: null,
        suprimido: true,
      }),
      agravo({
        agravo: "leptospirose",
        nome: "Leptospirose",
        fonte_id: "sinan-leptospirose",
        ultima_semana: semana(25),
        casos: 3,
      }),
    ],
    janela_leptospirose: janela,
    gerado_em: HOJE.toISOString(),
  },
  meta: { fontes: FONTES, supressao_minima: 5 },
});

const itens = (casos: number[]) => ({
  dados: {
    itens: casos.map((c, k) => ({
      ano: 2026,
      semana: k,
      inicio: dia((casos.length - k) * 7),
      casos: c,
      casos_estimados: null,
      ic_inf: null,
      ic_sup: null,
      nivel_alerta: null,
      incompleta: false,
    })),
    chuva: [],
  },
  meta: { fontes: FONTES },
});

afterEach(() => {
  vi.unstubAllGlobals();
  clienteConsultas.clear();
});

function abrir(mapa: Record<string, unknown>) {
  simularApi({ "/auth/eu": usuarioTeste(), ...mapa });
  window.history.pushState({}, "", "/app/saude");
  render(<App />);
}

test("mostra só arboviroses recentes e recolhe o velho e o sem fonte, sem cartão com número", async () => {
  abrir({ "/saude/resumo": resumo(), "/saude/semanal": itens([10, 12, 14, 20, 30, 36]) });
  const dengue = await screen.findByRole("region", { name: "Dengue" });
  expect(within(dengue).getByText("36")).toBeInTheDocument();
  expect(await within(dengue).findByText("subindo")).toBeInTheDocument();
  expect(within(dengue).getByText(/InfoDengue, atualizado/)).toBeInTheDocument();
  const chik = screen.getByRole("region", { name: "Chikungunya" });
  expect(within(chik).getByText(/< 5/)).toBeInTheDocument();
  // velhos: leptospirose (25 dias) e zika (sem fonte) só no item recolhido
  expect(screen.queryByRole("region", { name: "Leptospirose" })).not.toBeInTheDocument();
  expect(screen.queryByRole("region", { name: "Zika" })).not.toBeInTheDocument();
  const resumoVelhos = screen.getByText(/Dados que não estão atualizados \(2\)/);
  await userEvent.click(resumoVelhos);
  expect(screen.getByText(/Leptospirose:/).closest("li")).toHaveTextContent(/há \d+ dias/);
  expect(screen.getByText(/Zika:/).closest("li")).toHaveTextContent(
    "Dados insuficientes: falta a fonte de casos de zika",
  );
  expect(document.body.textContent).not.toMatch(/%/);
});

test("janela de leptospirose só aparece com alagamento declarado, curta e com a fonte", async () => {
  const janela = {
    ativa: true,
    inicio: dia(2),
    fim: dia(-28),
    motivo: null,
    territorios: [{ id: "ds-1", nome: "Distrito Sanitário I" }],
  };
  abrir({ "/saude/resumo": resumo(janela), "/saude/semanal": itens([5, 5, 5, 5]) });
  expect(await screen.findByText(/Leptospirose: vigilância até/)).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /Nota Técnica 138\/2022/ })).toBeInTheDocument();
});

test("sem janela ativa, não fala de leptospirose fora do item recolhido", async () => {
  abrir({ "/saude/resumo": resumo(), "/saude/semanal": itens([5, 5, 5, 5]) });
  await screen.findByRole("region", { name: "Dengue" });
  expect(screen.queryByText(/vigilância até/)).not.toBeInTheDocument();
});

test("sem nenhum dado recente diz Dados insuficientes, nunca zero", async () => {
  abrir({
    "/saude/resumo": resumo(null, [
      agravo({
        agravo: "dengue",
        nome: "Dengue",
        fonte_id: "infodengue",
        ultima_semana: semana(40),
        casos: 0,
      }),
    ]),
  });
  expect(await screen.findByText(/nenhuma arbovirose tem dado recente/)).toBeInTheDocument();
  expect(screen.queryByRole("region", { name: "Dengue" })).not.toBeInTheDocument();
});

describe("regras", () => {
  const dengue = (extra: Partial<ResumoAgravo> = {}) =>
    agravo({ agravo: "dengue", nome: "Dengue", fonte_id: "infodengue", casos: 4, ...extra });

  test("utilizável: o campo do backend vale; sem ele, até 14 dias", () => {
    expect(utilizavel(dengue({ ultima_semana: semana(14) }))).toBe(true);
    expect(utilizavel(dengue({ ultima_semana: semana(20) }))).toBe(false);
    expect(utilizavel(dengue({ ultima_semana: semana(2), utilizavel: false }))).toBe(false);
    expect(utilizavel(dengue({ ultima_semana: semana(60), utilizavel: true }))).toBe(true);
    expect(utilizavel(dengue({ ultima_semana: semana(2), casos: null }))).toBe(false);
    expect(utilizavel(undefined)).toBe(false);
  });

  test("a semana com dado do backend tem preferência", () => {
    expect(inicioDaSemana(dengue({ ultima_semana: semana(30), ultima_semana_com_dado: "2026-10-25" }))).toBe(
      "2026-10-25",
    );
  });

  test("tendência em palavras, pela estimativa corrigida quando existe", () => {
    const s = (v: number[]) => itens(v).dados as SerieSemanal;
    expect(tendenciaDe(s([20, 20, 20, 40, 40, 40]))).toBe("subindo");
    expect(tendenciaDe(s([40, 40, 40, 20, 20, 20]))).toBe("caindo");
    expect(tendenciaDe(s([20, 21, 20, 20, 21, 20]))).toBe("estável");
    expect(tendenciaDe(s([20, 40]))).toBeNull();
    const comEstimativa = s([40, 40, 40, 20, 10, 5]);
    comEstimativa.itens.forEach((i) => {
      i.incompleta = true;
      i.casos_estimados = 40;
    });
    expect(tendenciaDe(comEstimativa)).toBe("estável");
  });
});
