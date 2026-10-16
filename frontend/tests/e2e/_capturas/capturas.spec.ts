/** Capturas para revisão visual (não roda no CI). */
import { test } from "@playwright/test";
import { entrar } from "../integrado/apoio";

const LARGURAS = [390, 1440, 2560];
const TELAS = ["/app", "/app/mapa", "/app/series", "/app/cenarios", "/app/avaliacoes", "/app/comunicados", "/app/fontes", "/app/admin", "/app/comunicados/novo"];
const PASTA = process.env.PASTA_CAPTURAS ?? "test-results/capturas";

test("landing", async ({ page }) => {
  for (const w of LARGURAS) {
    await page.setViewportSize({ width: w, height: 1000 });
    await page.goto("/");
    await page.waitForTimeout(1200);
    await page.screenshot({ path: `${PASTA}/landing-${w}.png`, fullPage: true });
  }
});

test("telas da equipe", async ({ page }) => {
  test.setTimeout(300_000);
  await entrar(page, "coordenacao");
  for (const t of TELAS) {
    for (const w of LARGURAS) {
      await page.setViewportSize({ width: w, height: 1000 });
      await page.goto(t);
      await page.waitForTimeout(1800);
      const nome = t.replace(/\//g, "_").replace(/^_/, "");
      await page.screenshot({ path: `${PASTA}/${nome}-${w}.png`, fullPage: w !== 2560 });
    }
  }
});
