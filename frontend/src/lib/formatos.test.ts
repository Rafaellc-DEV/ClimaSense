import { formatarData, formatarDataHora, formatarHora, formatarNumero } from "./formatos";

test("converte UTC para o horário do Recife, inclusive na troca de dia", () => {
  // 02h30 UTC do dia 16 = 23h30 do dia 15 no Recife (UTC−3)
  expect(formatarDataHora("2026-10-16T02:30:00Z")).toBe("15/10/2026, 23h30");
  expect(formatarData("2026-10-16T02:30:00Z")).toBe("15/10/2026");
  expect(formatarHora("2026-10-15T21:04:00Z")).toBe("18h04");
});

test("números usam vírgula e ausente não vira zero", () => {
  expect(formatarNumero(9.4, 1)).toBe("9,4");
  expect(formatarNumero(1400000)).toBe("1.400.000");
  expect(formatarNumero(null)).toBe("sem dado");
  expect(formatarNumero(0)).toBe("0");
});
