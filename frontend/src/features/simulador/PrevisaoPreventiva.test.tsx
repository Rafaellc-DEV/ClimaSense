import { render, screen, within } from "@testing-library/react";
import { PrevisaoPreventiva, SeletorDias } from "./PrevisaoPreventiva";
import type { ResultadoSimulacao } from "./tipos";
import type { FonteMeta } from "@/lib/frescor";

type Dia = NonNullable<ResultadoSimulacao["dias"]>[number];
type Distrito = Dia["distritos"][number];
const ATUALIZACAO = "2026-05-10T12:00:00Z";
const distrito = (extra: Partial<Distrito> = {}): Distrito => ({
  territorio_id: "ds-1",
  nome: "Distrito I",
  chuva_prevista_mm: 4,
  chuva_disponivel_mm: 4,
  horas_validas: 24,
  horas_esperadas: 24,
  cobertura_completa: true,
  desatualizada: false,
  referencia_em: ATUALIZACAO,
  sinalizacao: "observacao",
  chuva_intensa: false,
  ...extra,
});
const dia = (extra: Partial<Dia> = {}): Dia => ({
  data: "2026-05-11",
  inicio: "2026-05-11T03:00:00Z",
  fim: "2026-05-12T03:00:00Z",
  periodo_parcial: false,
  horas_periodo: 24,
  criterios: { atencao_mm: 25, alerta_mm: 50, critico_mm: 90 },
  distritos_em_atencao: [],
  distritos: [
    distrito(),
    distrito({ territorio_id: "ds-2", nome: "Distrito II", chuva_prevista_mm: 12, chuva_disponivel_mm: 12 }),
  ],
  ...extra,
});

function resumo(d: Dia) {
  render(<SeletorDias dias={[d]} dia="" aoDia={() => {}} />);
  return screen.getByRole("list", { name: "Resumo dos dias sem distritos em atenção" });
}

test("identifica a Open-Meteo, o papel do ClimaSense e as limitações do período", () => {
  resumo(dia());
  expect(screen.getByText(/As previsões de chuva vêm da Open-Meteo/)).toHaveTextContent(
    "não são alertas oficiais da Defesa Civil",
  );
  expect(screen.getByText(/Consulte as próximas 72 horas/)).toHaveTextContent(
    "primeiro e o último dia podem ser parciais",
  );
});

test("zero distritos em atenção informa o maior acumulado e a cobertura completa", () => {
  const lista = resumo(dia());
  expect(screen.getByRole("radio", { name: /0 distritos em atenção/ })).toBeInTheDocument();
  expect(lista).toHaveTextContent("Maior acumulado previsto: 12 mm");
  expect(lista).toHaveTextContent("Dados completos nas 24 h");
  expect(lista).toHaveTextContent("Nenhum limite de chuva atingido");
});

test("zero previsto continua zero e dia parcial não é confundido com falta de horas", () => {
  const lista = resumo(
    dia({
      periodo_parcial: true,
      horas_periodo: 6,
      distritos: [
        distrito({ chuva_prevista_mm: 0, chuva_disponivel_mm: 0, horas_validas: 6, horas_esperadas: 6 }),
      ],
    }),
  );
  expect(lista).toHaveTextContent("Maior acumulado previsto: 0 mm");
  expect(lista).toHaveTextContent("Dados completos nas 6 h do período. Dia parcial.");
});

test("soma incompleta é apresentada como mínimo conhecido, sem afirmar ausência de ultrapassagem", () => {
  const lista = resumo(
    dia({
      distritos: [
        distrito({
          cobertura_completa: false,
          chuva_prevista_mm: null,
          chuva_disponivel_mm: 5,
          horas_validas: 10,
          sinalizacao: "sem_dados",
          chuva_intensa: null,
        }),
      ],
    }),
  );
  expect(lista).toHaveTextContent("Maior acumulado disponível: pelo menos 5 mm");
  expect(lista).toHaveTextContent("Dados parciais ou ausentes");
  expect(lista).toHaveTextContent("Dados insuficientes para confirmar");
  expect(lista).not.toHaveTextContent("Nenhum limite de chuva atingido");
});

test("ausência de valores não cria acumulado zero", () => {
  const lista = resumo(
    dia({
      distritos: [
        distrito({
          cobertura_completa: false,
          chuva_prevista_mm: null,
          chuva_disponivel_mm: null,
          horas_validas: 0,
          referencia_em: null,
          sinalizacao: "sem_dados",
        }),
      ],
    }),
  );
  expect(lista).toHaveTextContent("Acumulado previsto indisponível");
  expect(lista).not.toHaveTextContent("0 mm");
});

test("previsão antiga é identificada mesmo quando há todas as horas", () => {
  const lista = resumo(dia({ distritos: [distrito({ desatualizada: true, sinalizacao: "sem_dados" })] }));
  expect(lista).toHaveTextContent("Há previsões desatualizadas");
  expect(lista).not.toHaveTextContent("Nenhum limite de chuva atingido");
});

function comparar(fontes: FonteMeta[] = [], comparacoes: ResultadoSimulacao["comparacoes_recentes"] = []) {
  render(
    <PrevisaoPreventiva
      resultado={{ dias: [dia()], itens: [], comparacoes_recentes: comparacoes }}
      dia="2026-05-11"
      bairros={[]}
      ml={undefined}
      atualizando={false}
      fontes={fontes}
    />,
  );
}

test("APAC sem leitura recente informa motivo e última atualização, preservando a previsão", () => {
  comparar([{ id: "apac-chuva", nome: "APAC", atualizado_em: ATUALIZACAO, desatualizado: true }]);
  const aviso = screen.getByRole("status", { name: "Comparação com a APAC" });
  expect(aviso).toHaveTextContent("Comparação Open-Meteo × APAC não realizada");
  expect(aviso).toHaveTextContent("Não há leitura recente");
  expect(aviso).toHaveTextContent("Última atualização disponível da APAC: 10/05, 09:00");
  expect(within(screen.getByRole("table")).getByText("12 mm")).toBeInTheDocument();
});

test("APAC sem atualização conhecida informa a ausência em vez de inventar horário", () => {
  comparar();
  expect(screen.getByRole("status", { name: "Comparação com a APAC" })).toHaveTextContent(
    "A última atualização da APAC não foi informada",
  );
});

test("APAC incompatível explica a comparação indisponível e mostra a atualização mais recente disponível", () => {
  comparar(
    [{ id: "apac-chuva", nome: "APAC", atualizado_em: "2026-05-09T12:00:00Z" }],
    [
      {
        territorio_id: "ds-1",
        inicio: "2026-05-10T11:00:00Z",
        fim: ATUALIZACAO,
        observada_mm: 2,
        estacao: "Estação I",
        atualizada_em: ATUALIZACAO,
        previsao_referencia_em: null,
        prevista_mm: null,
        compativel: false,
        motivo: "Horários de medição e previsão diferentes.",
      },
    ],
  );
  const aviso = screen.getByRole("status", { name: "Comparação com a APAC" });
  expect(aviso).toHaveTextContent("não têm uma previsão arquivada para o mesmo período");
  expect(aviso).toHaveTextContent("10/05, 09:00");
  expect(screen.getByText(/Horários de medição e previsão diferentes/)).toBeInTheDocument();
  expect(within(screen.getByRole("table")).getByText("12 mm")).toBeInTheDocument();
});
