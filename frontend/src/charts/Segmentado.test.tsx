import { useState } from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Segmentado } from "./Segmentado";

function Exemplo() {
  const [v, setV] = useState("diaria");
  return (
    <Segmentado
      rotulo="Frequência"
      valor={v}
      aoMudar={setV}
      opcoes={[
        { valor: "diaria", rotulo: "Diária" },
        { valor: "mensal", rotulo: "Mensal" },
        { valor: "semanal", rotulo: "Semanal", desabilitada: true },
      ]}
    />
  );
}

test("escolha única em pílulas: grupo nomeado, seta muda a opção e a desabilitada fica fora", async () => {
  render(<Exemplo />);
  expect(screen.getByRole("radiogroup", { name: "Frequência" })).toBeInTheDocument();
  const diaria = screen.getByRole("radio", { name: "Diária" });
  expect(diaria).toBeChecked();
  expect(screen.getByRole("radio", { name: "Semanal" })).toBeDisabled();
  diaria.focus();
  await userEvent.keyboard("{ArrowRight}");
  expect(screen.getByRole("radio", { name: "Mensal" })).toBeChecked();
});
