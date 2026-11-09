/** Capturas para revisão visual das cinco telas e do relatório (não roda no CI). Exige E2E_SENHA e a API no ar. */
import { test } from "@playwright/test";
import { entrar } from "../integrado/apoio";

const LARGURAS = [375, 1440];
const TELAS = ["/app", "/app/situacao", "/app/saude", "/app/acoes", "/app/simulador", "/app/fontes"];
const PASTA = process.env.PASTA_CAPTURAS ?? "test-results/capturas";

test("telas da equipe", async ({ page }) => {
  test.setTimeout(300_000);
  await entrar(page);
  for (const t of TELAS) {
    for (const w of LARGURAS) {
      await page.setViewportSize({ width: w, height: 1000 });
      await page.goto(t);
      await page.waitForTimeout(1800);
      const nome = t.replace(/\//g, "_").replace(/^_/, "");
      await page.screenshot({ path: `${PASTA}/${nome}-${w}.png`, fullPage: true });
    }
  }
});
