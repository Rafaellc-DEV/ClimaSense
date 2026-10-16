import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

const LARGURAS = [375, 768, 1440];

for (const largura of LARGURAS) {
  test(`vitrine em ${largura} px: sem rolagem horizontal e sem violações de acessibilidade`, async ({
    page,
  }, info) => {
    test.skip(info.project.name !== "desktop", "larguras controladas manualmente");
    await page.setViewportSize({ width: largura, height: 900 });
    await page.goto("/_vitrine");
    await expect(page.getByRole("heading", { name: "Vitrine do design system" })).toBeVisible();
    await page.waitForTimeout(900); // a água da régua termina de subir
    const larguraDocumento = await page.evaluate(() => document.documentElement.scrollWidth);
    expect(larguraDocumento).toBeLessThanOrEqual(largura);
    const resultado = await new AxeBuilder({ page } as unknown as ConstructorParameters<typeof AxeBuilder>[0])
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"])
      .analyze();
    const graves = resultado.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
    expect(graves.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(" ")).join(", ")}`)).toEqual([]);
    await page.screenshot({ path: `../docs/brand/capturas/vitrine-${largura}.png`, fullPage: true });
  });
}

test("toast usa o mesmo verbo do botão", async ({ page }, info) => {
  test.skip(info.project.name !== "desktop");
  await page.goto("/_vitrine");
  await page.getByRole("button", { name: "Enviar para revisão" }).click();
  await expect(page.getByText("Enviado para revisão.", { exact: true })).toBeVisible();
});
