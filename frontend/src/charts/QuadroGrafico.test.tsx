import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QuadroGrafico } from "./QuadroGrafico";

vi.mock("echarts-for-react", () => ({ default: () => <div data-testid="echarts" /> }));

// Valores reais: bairros e área (km²) dos Distritos Sanitários I e VIII; DS IX não existe e entra como lacuna.
const linhas: (string | number | null)[][] = [
  ["DS I", 11, 15.25],
  ["DS IX", null, null],
  ["DS VIII", 3, 17.257],
];

test("“Ver como tabela” mostra os mesmos valores do gráfico, e a lacuna como “sem dado”", async () => {
  render(
    <QuadroGrafico
      titulo="Distritos"
      resumo="Bairros e área por distrito."
      opcao={{ series: [{ type: "bar", data: [11, null, 3] }] }}
      tabela={{ colunas: ["Distrito", "Bairros", "Área (km²)"], linhas }}
      fontes={[{ nome: "Dados Abertos do Recife", tipo: "observada" }]}
    />,
  );
  expect(screen.getByRole("img", { name: "Distritos. Bairros e área por distrito." })).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Ver como tabela" }));
  expect(screen.getByRole("table", { name: "Distritos em tabela" })).toBeInTheDocument();
  expect(screen.getByRole("row", { name: /DS I 11 15,25/ })).toBeInTheDocument();
  expect(screen.getByRole("row", { name: /DS IX sem dado sem dado/ })).toBeInTheDocument();
  expect(screen.getByRole("row", { name: /DS VIII 3 17,26/ })).toBeInTheDocument();
});
