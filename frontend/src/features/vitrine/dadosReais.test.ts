import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { DISTRITOS_REAIS } from "./dadosReais";

test("os números da vitrine batem com o arquivo oficial enriquecido (sem dados inventados)", () => {
  const caminho = resolve(__dirname, "../../../../data/territorio/distritos-enriquecidos.geojson");
  const geo = JSON.parse(readFileSync(caminho, "utf-8"));
  for (const f of geo.features) {
    const d = DISTRITOS_REAIS.find((x) => x.codigo === f.properties.cdistscodi)!;
    expect(d.areaKm2).toBe(f.properties.area_km2);
  }
  expect(DISTRITOS_REAIS.reduce((s, d) => s + d.bairros, 0)).toBe(94);
});
