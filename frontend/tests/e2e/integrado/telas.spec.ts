/**
 * Cada tela do PRD e o relatório, a 1440 e 375 px, contra a API real: sem erro de JavaScript, sem resposta de erro
 * da API, sem rolagem horizontal, com fonte e hora, e sem violação grave de acessibilidade (RF-19, RF-21, RNF-08).
 */
import { expect, test } from "@playwright/test";
import { entrar, semViolacoes } from "./apoio";

const TELAS = [
  { rota: "/app", titulo: "Mapa" },
  { rota: "/app/situacao", titulo: "Situação do evento" },
  { rota: "/app/saude", titulo: "Saúde depois da chuva" },
  { rota: "/app/acoes", titulo: "Ações" },
  { rota: "/app/simulador", titulo: "Simulador de cenário" },
  { rota: "/app/acoes/relatorio", titulo: "Relatório executivo — Secretaria de Saúde" },
];

for (const largura of [1440, 375]) {
  test(`cinco telas e relatório a ${largura} px`, async ({ page }) => {
    test.setTimeout(240_000);
    const problemas: string[] = [];
    page.on("pageerror", (e) => problemas.push(`js: ${e.message}`));
    page.on("response", (r) => {
      if (r.url().includes("/api/") && r.status() >= 400) problemas.push(`${r.status()} ${r.url()}`);
    });
    await page.setViewportSize({ width: largura, height: 900 });
    await entrar(page);
    problemas.length = 0; // o 401 de /auth/eu antes do login é esperado
    for (const t of TELAS) {
      await page.goto(t.rota);
      await expect(page.getByRole("heading", { level: 1, name: t.titulo })).toBeVisible();
      await page.waitForTimeout(1500);
      expect(
        await page.evaluate(() => document.documentElement.scrollWidth),
        `rolagem horizontal em ${t.rota}`,
      ).toBeLessThanOrEqual(largura);
      await expect(page.getByText(/atualizado|Atualizado/).first(), `hora em ${t.rota}`).toBeVisible();
      await semViolacoes(page);
    }
    expect(problemas).toEqual([]);
  });
}

test("dados reais, não simulados: nenhuma tela mostra texto de exemplo nem a vitrine (RNF-10)", async ({
  page,
}) => {
  await entrar(page);
  for (const t of TELAS) {
    await page.goto(t.rota);
    await page.waitForTimeout(800);
    const texto = await page.locator("body").innerText();
    expect(texto, t.rota).not.toMatch(/dados (simulados|fict[ií]cios|de exemplo)|lorem ipsum/i);
  }
  await page.goto("/_vitrine"); // só existe em desenvolvimento com VITE_VITRINE
  await expect(page.getByRole("heading", { name: "Vitrine do design system" })).toHaveCount(0);
});

test("sem login, as telas da equipe mandam para o login", async ({ page }) => {
  await page.goto("/app/situacao");
  await expect(page).toHaveURL(/\/entrar/);
});
