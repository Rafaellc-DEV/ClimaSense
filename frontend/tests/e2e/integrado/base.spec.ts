/** M8 (frontend base) e M10/M12 contra o sistema real: menu por papel, recorte na URL, sessão, telas analíticas. */
import { expect, test } from "@playwright/test";
import { entrar } from "./apoio";

test("o analista não vê Administração; em 800 px o menu vira gaveta com o botão Menu (T8.2)", async ({
  page,
}) => {
  await entrar(page, "analista");
  const menu = page.getByRole("navigation", { name: "Menu principal" });
  await expect(menu.getByRole("link", { name: "Mapa do território" })).toBeVisible();
  await expect(menu.getByRole("link", { name: "Administração" })).toHaveCount(0);
  await page.setViewportSize({ width: 800, height: 900 });
  await expect(page.getByRole("navigation", { name: "Menu principal" })).toHaveCount(0);
  await page.getByRole("button", { name: "Menu" }).click();
  await expect(
    page.getByRole("dialog").getByRole("link", { name: "Painel inicial", exact: true }),
  ).toBeVisible();
});

test("a coordenação com papel de administrador vê Administração (RF-03.3)", async ({ page }) => {
  await entrar(page, "coordenacao");
  await expect(
    page.getByRole("navigation", { name: "Menu principal" }).getByRole("link", { name: "Administração" }),
  ).toBeVisible();
});

test("escolher o DS IV, trocar de tela e recarregar mantém o recorte (T8.3, CA-01)", async ({ page }) => {
  await entrar(page, "analista");
  await page.getByRole("button", { name: /Território:/ }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Distrito Sanitário IV" }).click();
  await expect(page).toHaveURL(/territorio=ds-4/);
  await page.getByRole("button", { name: /Início do período/ }).click();
  await page.getByRole("button", { name: "Últimos 30 dias" }).click();
  await page
    .getByRole("navigation", { name: "Menu principal" })
    .getByRole("link", { name: "Séries e sazonalidade" })
    .click();
  await expect(page).toHaveURL(/\/app\/series\?.*territorio=ds-4/);
  await page.reload();
  await expect(page.getByRole("button", { name: /Território:/ })).toHaveText(/Distrito Sanitário IV/);
  await expect(
    page.getByRole("heading", { name: /Chuva ao longo do tempo: Distrito Sanitário IV/ }),
  ).toBeVisible();
  // o mapa reflete o mesmo recorte: o DS IV aparece selecionado
  await page
    .getByRole("navigation", { name: "Menu principal" })
    .getByRole("link", { name: "Mapa do território" })
    .click();
  await expect(page.getByRole("heading", { level: 2, name: /Distrito Sanitário IV/ })).toBeVisible();
});

test("aos 58 minutos sem uso aparece o aviso, e “Continuar conectado” renova a sessão (T8.4)", async ({
  page,
}) => {
  await page.clock.install();
  await entrar(page, "analista");
  await expect(page.getByRole("heading", { name: "Painel inicial" })).toBeVisible();
  await page.clock.fastForward("58:05");
  const dialogo = page.getByRole("dialog", { name: "Você continua aí?" });
  await expect(dialogo).toBeVisible();
  const renovar = page.waitForResponse((r) => r.url().includes("/auth/renovar") && r.status() === 200);
  await dialogo.getByRole("button", { name: "Continuar conectado" }).click();
  await renovar;
  await expect(dialogo).toBeHidden();
});

test("sem resposta ao aviso, a interface sai e explica o motivo (RF-02.5)", async ({ page }) => {
  await page.clock.install();
  await entrar(page, "analista");
  await page.clock.fastForward(60 * 60_000 + 5_000);
  await expect(page.getByText("Sua sessão terminou por inatividade. Entre novamente.")).toBeVisible();
});

test("painel por papel: o revisor vê a fila; a analista vê a explicação (T10.1)", async ({ page }) => {
  await entrar(page, "revisor");
  await expect(page.getByRole("region", { name: "Aguardando sua revisão" })).toBeVisible();
  await expect(page.getByRole("region", { name: "Saúde das fontes" })).toContainText("Atualizada");
  await page.getByRole("button", { name: "Sair" }).first().click();
  await entrar(page, "analista");
  await expect(page.getByText("Quem revisa é outra pessoa da equipe")).toBeVisible();
});

test("fontes: o administrador atualiza uma fonte e vê o status; a analista não vê o botão (T12.1)", async ({
  page,
}) => {
  test.setTimeout(120_000);
  await entrar(page, "analista", "/app/fontes/open-meteo-mare");
  await expect(page.getByRole("heading", { name: /Nível do mar previsto/ })).toBeVisible();
  await expect(page.getByRole("button", { name: "Atualizar agora" })).toHaveCount(0);
  await page.getByRole("button", { name: "Sair" }).first().click();
  await entrar(page, "coordenacao", "/app/fontes/open-meteo-mare");
  await page.getByRole("button", { name: "Atualizar agora" }).click();
  await expect(page.getByText("Atualização iniciada.").first()).toBeVisible();
  await expect(page.getByText("Atualização concluída.").first()).toBeVisible({ timeout: 90_000 });
  await expect(page.locator("table").first()).toContainText("Concluída");
  await page.goto("/app/fontes");
  await expect(page.getByRole("region", { name: "Planejadas" })).toContainText("Planejada");
});
