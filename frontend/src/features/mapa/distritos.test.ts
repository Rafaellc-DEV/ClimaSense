import { CLASSES_PRIORIDADE, classePrioridade, distritosPorPrioridade, rotulosPrioridade } from "./distritos";

describe("prioridade por faixas", () => {
  it("1º é a classe mais intensa, o último a menos; sem posição é sem dado (nunca baixo)", () => {
    expect(classePrioridade(1, 94)).toBe(CLASSES_PRIORIDADE - 1);
    expect(classePrioridade(94, 94)).toBe(0);
    expect(classePrioridade(undefined, 94)).toBeNull();
    expect(classePrioridade(3, 0)).toBeNull();
  });

  it("os rótulos da legenda batem com as faixas usadas na cor", () => {
    const total = 94;
    const rotulos = rotulosPrioridade(total);
    expect(rotulos).toHaveLength(CLASSES_PRIORIDADE);
    expect(rotulos[0]).toBe("1º a 19º");
    expect(rotulos[4]).toBe("77º a 94º");
    // 19º ainda é da primeira faixa, 20º já é da segunda
    expect(classePrioridade(19, total)).toBe(4);
    expect(classePrioridade(20, total)).toBe(3);
    expect(classePrioridade(77, total)).toBe(0);
    expect(classePrioridade(76, total)).toBe(1);
  });
});

describe("ordem dos distritos", () => {
  it("o mais vulnerável primeiro; sem lista, ordem numérica", () => {
    const lista = [
      { territorio_id: "ds-7", nome: "VII", nivel: "distrito", posicao: 1 },
      { territorio_id: "ds-2", nome: "II", nivel: "distrito", posicao: 2 },
    ];
    expect(distritosPorPrioridade(lista).slice(0, 3)).toEqual(["ds-7", "ds-2", "ds-1"]);
    expect(distritosPorPrioridade([])[0]).toBe("ds-1");
    expect(distritosPorPrioridade([])).toHaveLength(8);
  });
});
