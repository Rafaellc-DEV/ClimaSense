/** T10.2 — os 4 testes de `tests/model.test.cjs` (Desktop/AVD), portados sem mudar as asserções. */
import { classIndex, csvCell, makeScale, matches } from "./model";

test("intensity boundaries are exhaustive and the maximum stays in the last class", () => {
  const scale = makeScale([4, 5, 11, 12, 12, 16, 16, 18]);
  expect(classIndex(4, scale)).toBe(0);
  expect(classIndex(6.8, scale)).toBe(1);
  expect(classIndex(18, scale)).toBe(4);
  expect(classIndex(null, scale)).toBe(-1);
  expect(classIndex(undefined, scale)).toBe(-1);
});

test("constant data use one class without division by zero", () => {
  const scale = makeScale([5, 5]);
  expect(scale.bins.length).toBe(1);
  expect(classIndex(5, scale)).toBe(0);
});

test("search ignores accents and searches neighborhoods too", () => {
  const p = { nome_distrito: "DS VI", bairros: ["Boa Viagem", "Brasília Teimosa"] };
  expect(matches(p, "  brasilia  ")).toBe(true);
  expect(matches(p, "DS VI")).toBe(true);
  expect(matches(p, "inexistente")).toBe(false);
});

test("CSV escapes quotes and blocks spreadsheet formula interpretation", () => {
  expect(csvCell("=1+1")).toBe('"\'=1+1"');
  expect(csvCell('A "B"')).toBe('"A ""B"""');
});
