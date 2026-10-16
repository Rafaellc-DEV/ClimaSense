/** T13.1 — axe em TODAS as rotas autenticadas, contra o sistema real. O relatório vai para docs/qualidade/. */
import fs from "node:fs";
import path from "node:path";
import { expect, test } from "@playwright/test";
import { entrar, semViolacoes } from "./apoio";

const ROTAS = [
  "/app",
  "/app/mapa",
  "/app/series",
  "/app/cenarios",
  "/app/avaliacoes",
  "/app/avaliacoes/nova",
  "/app/comunicados",
  "/app/comunicados/novo",
  "/app/fontes",
  "/app/fontes/open-meteo-historico",
  "/app/admin",
  "/app/admin/execucoes",
  "/app/admin/auditoria",
  "/app/conta",
];
const relatorio: { rota: string; largura: number; graves: number; menores: string[] }[] = [];

for (const largura of [1440, 375]) {
  test(`axe em todas as rotas autenticadas (${largura} px)`, async ({ page }) => {
    test.setTimeout(180_000);
    await page.setViewportSize({ width: largura, height: 900 });
    await entrar(page, "coordenacao");
    for (const rota of ROTAS) {
      await page.goto(rota);
      await page.waitForLoadState("networkidle");
      await page.waitForTimeout(600);
      expect(
        await page.evaluate(() => document.documentElement.scrollWidth),
        `rolagem horizontal em ${rota}`,
      ).toBeLessThanOrEqual(largura);
      const todas = await semViolacoes(page);
      relatorio.push({ rota, largura, graves: 0, menores: todas.map((v) => `${v.id} (${v.impact})`) });
    }
  });
}

test.afterAll(() => {
  const destino = path.resolve(process.cwd(), "../docs/qualidade/axe-rotas.json");
  fs.mkdirSync(path.dirname(destino), { recursive: true });
  fs.writeFileSync(
    destino,
    JSON.stringify({ gerado_em: new Date().toISOString(), rotas: relatorio }, null, 2),
  );
});
