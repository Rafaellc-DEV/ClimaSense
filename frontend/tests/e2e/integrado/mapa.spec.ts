/**
 * T10.5 — porte do `tests/browser.cjs` da Aula 07 (Desktop/AVD): as mesmas verificações, agora no mapa ligado à
 * API: 8 distritos, 94 bairros, 81 faixas, 8 caminhos no overlay, busca “boa viagem” → 1, CSV, camadas,
 * intensidade, zoom, teclado, “Sobre os dados” e larguras de 1440 e 375 px.
 */
import fs from "node:fs";
import { expect, test } from "@playwright/test";
import { entrar } from "./apoio";

test("mapa do território: checklist RF-07 da Aula 07", async ({ page }) => {
  test.setTimeout(120_000);
  const erros: string[] = [];
  page.on("pageerror", (e) => erros.push(e.message));
  await entrar(page, "analista", "/app/mapa");
  const lista = page.getByRole("complementary", { name: "Busca e camadas" }).locator("ul li button");
  await expect(lista).toHaveCount(8);
  await expect(page.getByText(/8 distritos sanitários, 94 bairros e 81 faixas hídricas/)).toBeVisible();
  await expect(page.locator(".leaflet-overlay-pane path")).toHaveCount(8);
  await expect(page.locator(".leaflet-hidrografia-pane path")).toHaveCount(81);

  // busca sem acento filtra lista e mapa; a escala não muda (RF-07.3, 07.4)
  await page.getByLabel("Distrito ou bairro").fill("boa viagem");
  await expect(lista).toHaveCount(1);
  await expect(page.locator(".leaflet-overlay-pane path")).toHaveCount(1);
  await lista.first().click();
  await expect(page).toHaveURL(/territorio=ds-6/);
  const detalhe = page.getByRole("complementary", { name: "Detalhes do distrito" });
  await expect(detalhe.getByRole("heading", { level: 2 })).toHaveText(/Distrito Sanitário VI/);
  await expect(detalhe).toContainText("Boa Viagem");
  await expect(detalhe.locator("dd").first()).toHaveText("5");

  // CSV do resultado filtrado: BOM, “;”, vírgula decimal (RF-07.10)
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Exportar CSV" }).click();
  const csv = fs.readFileSync(await (await download).path(), "utf8");
  expect(csv.charCodeAt(0)).toBe(0xfeff);
  expect(csv.split("\r\n")).toHaveLength(2);
  expect(csv).toContain(";");
  expect(csv).toMatch(/"\d+,\d+"/);

  // nenhum resultado
  await page.getByLabel("Distrito ou bairro").fill("inexistente");
  await expect(page.getByText("Nenhum distrito encontrado.")).toBeVisible();
  await expect(page.locator(".leaflet-overlay-pane path")).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Exportar CSV" })).toBeDisabled();
  await page.getByRole("button", { name: "Limpar filtros e ver todos" }).click();
  await expect(lista).toHaveCount(8);

  // camadas (RF-07.7)
  await page.getByRole("switch", { name: "Faixas marginais dos recursos hídricos" }).uncheck();
  await expect(page.locator(".leaflet-hidrografia-pane path")).toHaveCount(0);
  await page.getByRole("switch", { name: "Faixas marginais dos recursos hídricos" }).check();
  await page.getByRole("switch", { name: "Distritos sanitários" }).uncheck();
  await expect(page.locator(".leaflet-overlay-pane path")).toHaveCount(0);
  await page.getByRole("switch", { name: "Distritos sanitários" }).check();

  // intensidade (RF-07.8)
  await page.getByRole("slider").fill("40");
  await expect(page.getByText("40%")).toBeVisible();
  await expect(page.locator(".leaflet-overlay-pane path").first()).toHaveAttribute("fill-opacity", "0.4");
  await page.getByRole("slider").fill("85");

  // colorir por área: a legenda muda (RF-07.2, 07.9)
  await page.getByRole("combobox", { name: "Colorir por" }).click();
  await page.getByRole("option", { name: "Área do distrito (km²)" }).click();
  await expect(page.getByLabel("Legenda do mapa")).toContainText("km²");
  await expect(page.getByText(/não representa população/)).toBeVisible();

  // zoom e teclado (RF-07.14)
  const antes = await page.locator(".leaflet-overlay-pane path").first().getAttribute("d");
  await page.getByRole("button", { name: "Zoom in" }).click();
  await page.waitForTimeout(400);
  expect(await page.locator(".leaflet-overlay-pane path").first().getAttribute("d")).not.toBe(antes);
  await page.locator(".leaflet-container").focus();
  const painel = page.locator(".leaflet-map-pane");
  const t1 = await painel.getAttribute("style");
  await page.keyboard.press("ArrowRight");
  await page.waitForTimeout(400);
  expect(await painel.getAttribute("style"), "as setas movem o mapa").not.toBe(t1);

  // sobre os dados, com a nota dos DS VII e VIII (RF-07.13)
  await page.getByRole("button", { name: "Sobre os dados" }).click();
  await expect(page.getByRole("dialog")).toContainText("Distritos Sanitários VII e VIII");
  await page.keyboard.press("Escape");

  // Enter com um único resultado seleciona (RF-07.4)
  await page.getByLabel("Distrito ou bairro").fill("Cohab");
  await page.getByLabel("Distrito ou bairro").press("Enter");
  await expect(
    page.getByRole("complementary", { name: "Detalhes do distrito" }).getByRole("heading", { level: 2 }),
  ).toHaveText(/Distrito Sanitário VIII/);

  for (const largura of [1440, 375]) {
    await page.setViewportSize({ width: largura, height: 1000 });
    await page.waitForTimeout(300);
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(largura);
    await page.screenshot({ path: `test-results/mapa-${largura}.png`, fullPage: true });
  }
  expect(erros).toEqual([]);
});

test("falha dos tiles mostra o aviso e mantém os polígonos (RF-07.11)", async ({ page }) => {
  await page.route(/arcgisonline/, (r) => r.abort());
  await entrar(page, "analista", "/app/mapa");
  await expect(page.getByText("O mapa de ruas não carregou.")).toBeVisible();
  await expect(page.locator(".leaflet-overlay-pane path")).toHaveCount(8);
});

test("indicador sem fonte integrada mostra Dados insuficientes, nunca zero (RF-07.15)", async ({ page }) => {
  await entrar(page, "analista", "/app/mapa");
  await page.getByRole("combobox", { name: "Colorir por" }).click();
  await page.getByRole("option", { name: "Ocorrências de alagamento" }).click();
  await expect(page.getByText("Dados insuficientes para este indicador")).toBeVisible();
  await expect(page.getByLabel("Legenda do mapa")).toContainText("Sem dado");
});
