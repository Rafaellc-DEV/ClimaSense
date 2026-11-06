import { render, screen } from "@testing-library/react";
import { AreaTexto } from "./Campo";

test("texto livre com privacidade mostra a dica, junto da ajuda existente", () => {
  render(<AreaTexto rotulo="Observação" ajuda="Ex.: portão lateral." privacidade />);
  expect(screen.getByText("Não escreva nome, CPF ou dado de saúde de pessoas.")).toBeInTheDocument();
  expect(screen.getByLabelText("Observação")).toHaveAccessibleDescription(
    "Ex.: portão lateral. Não escreva nome, CPF ou dado de saúde de pessoas.",
  );
});

test("sem a prop privacidade, a dica não aparece", () => {
  render(<AreaTexto rotulo="Qualquer" />);
  expect(screen.queryByText(/Não escreva nome/)).not.toBeInTheDocument();
});
