import { render, screen } from "@testing-library/react";
import { App } from "./App";

test("a página inicial abre com a marca e os telefones de emergência", () => {
  window.history.pushState({}, "", "/");
  render(<App />);
  expect(screen.getByRole("img", { name: "ClimaSense" })).toBeInTheDocument();
  expect(screen.getByText(/199 \(Defesa Civil\), 193 \(Bombeiros\) ou 192 \(SAMU\)/)).toBeInTheDocument();
});
