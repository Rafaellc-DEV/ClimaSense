import { describe, expect, it } from "vitest";

import { nomeDistrito, siglaDistrito } from "./distritos";

describe("nomeDistrito", () => {
  it("troca o romano pelo número, sem 'Sanitário' nem 'DS'", () => {
    expect(nomeDistrito("Distrito Sanitário V")).toBe("Distrito 5");
    expect(nomeDistrito("Distrito Sanitario VIII")).toBe("Distrito 8");
    expect(nomeDistrito("DS VII")).toBe("Distrito 7");
    expect(nomeDistrito("Distrito III")).toBe("Distrito 3");
  });

  it("converte dentro de frases e em listas", () => {
    expect(nomeDistrito("Estágio em DS V e DS VII (antes: Atenção)")).toBe(
      "Estágio em Distrito 5 e Distrito 7 (antes: Atenção)",
    );
  });

  it("não confunde VIII com VII nem mexe em outros textos", () => {
    expect(nomeDistrito("DS VIII e DS VI")).toBe("Distrito 8 e Distrito 6");
    expect(nomeDistrito("Bairro Distrito Federal")).toBe("Bairro Distrito Federal");
    expect(nomeDistrito("Recife")).toBe("Recife");
  });
});

describe("siglaDistrito", () => {
  it("encurta para D + número", () => {
    expect(siglaDistrito("Distrito Sanitário IV")).toBe("D4");
  });
});
