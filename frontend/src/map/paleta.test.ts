import { CORES_DISTRITO, IDS_DISTRITO, corDoDistrito, nomeDoDistrito, siglaDoDistrito } from "./paleta";

const lin = (c: number) => ((c /= 255) <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4);
const rgb = (h: string) => [1, 3, 5].map((i) => lin(parseInt(h.slice(i, i + 2), 16)));
// matrizes de Machado et al. (2009), severidade total
const CVD: Record<string, number[][]> = {
  normal: [
    [1, 0, 0],
    [0, 1, 0],
    [0, 0, 1],
  ],
  protanopia: [
    [0.152286, 1.052583, -0.204868],
    [0.114503, 0.786281, 0.099216],
    [-0.003882, -0.048116, 1.051998],
  ],
  deuteranopia: [
    [0.367322, 0.860646, -0.227968],
    [0.280085, 0.672501, 0.047413],
    [-0.01182, 0.04294, 0.968881],
  ],
  tritanopia: [
    [1.255528, -0.076749, -0.178779],
    [-0.078411, 0.930809, 0.147602],
    [0.004733, 0.691367, 0.3039],
  ],
};
function lab(c: number[]): number[] {
  const [r, g, b] = c;
  const f = (t: number) => (t > 0.008856 ? Math.cbrt(t) : 7.787 * t + 16 / 116);
  const x = f((0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047);
  const y = f(0.2126 * r + 0.7152 * g + 0.0722 * b);
  const z = f((0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883);
  return [116 * y - 16, 500 * (x - y), 200 * (y - z)];
}
const simular = (c: number[], m: number[][]) =>
  m.map((l) => Math.min(1, Math.max(0, l[0] * c[0] + l[1] * c[1] + l[2] * c[2])));

describe("paleta dos distritos", () => {
  it("tem uma cor diferente para cada um dos 8 distritos", () => {
    expect(IDS_DISTRITO).toHaveLength(8);
    expect(new Set(Object.values(CORES_DISTRITO)).size).toBe(8);
  });

  it.each(Object.keys(CVD))("mantém os pares distinguíveis em %s", (tipo) => {
    const labs = IDS_DISTRITO.map((id) => lab(simular(rgb(CORES_DISTRITO[id]), CVD[tipo])));
    let minimo = Infinity;
    for (let i = 0; i < labs.length; i++)
      for (let j = i + 1; j < labs.length; j++)
        minimo = Math.min(minimo, Math.hypot(...labs[i].map((v, k) => v - labs[j][k])));
    expect(minimo).toBeGreaterThanOrEqual(16);
  });

  it("cinza para id desconhecido e siglas com algarismo", () => {
    expect(corDoDistrito("ds-99")).toBe("#8fa3b1");
    expect(corDoDistrito(null)).toBe("#8fa3b1");
    expect(siglaDoDistrito("ds-3")).toBe("D3");
    expect(nomeDoDistrito("ds-3")).toBe("Distrito 3");
    expect(siglaDoDistrito("ds-8")).toBe("D8");
  });
});
