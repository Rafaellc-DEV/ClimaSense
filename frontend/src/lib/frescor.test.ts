import { fontesDe, haQuanto, juntarFontes, supressaoMinima } from "./frescor";

test("fontesDe lê meta.fontes e, sem ela, devolve lista vazia (fallback)", () => {
  const f = { id: "a", nome: "APAC", atualizado_em: null, limite_frescor_h: 6, desatualizado: null };
  expect(fontesDe({ dados: [], meta: { fontes: [f] } })).toEqual([f]);
  expect(fontesDe({ dados: [] })).toEqual([]);
  expect(fontesDe(undefined)).toEqual([]);
  expect(fontesDe({ meta: { fontes: "x" } })).toEqual([]);
});

test("juntarFontes não repete a mesma fonte", () => {
  const a = { meta: { fontes: [{ id: "a", nome: "A" }] } };
  const b = {
    meta: {
      fontes: [
        { id: "a", nome: "A" },
        { id: "b", nome: "B" },
      ],
    },
  };
  expect(juntarFontes(a, b).map((f) => f.id)).toEqual(["a", "b"]);
});

test("supressaoMinima usa meta.supressao_minima e cai em 5", () => {
  expect(supressaoMinima({ meta: { supressao_minima: 10 } })).toBe(10);
  expect(supressaoMinima({ meta: {} })).toBe(5);
  expect(supressaoMinima(null)).toBe(5);
});

test("haQuanto fala em minutos, horas e dias", () => {
  const agora = new Date("2026-11-06T12:00:00Z");
  expect(haQuanto("2026-11-06T11:59:40Z", agora)).toBe("agora há pouco");
  expect(haQuanto("2026-11-06T11:15:00Z", agora)).toBe("há 45 min");
  expect(haQuanto("2026-11-06T09:00:00Z", agora)).toBe("há 3 h");
  expect(haQuanto("2026-11-02T12:00:00Z", agora)).toBe("há 4 dias");
});
