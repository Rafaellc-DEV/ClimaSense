/** Respostas reais da API ASGI local após ETL com GETs públicos. Sem acesso ao Neon/Atlas pelo navegador.
 * Gerar antes: python scripts/validar_operacao_local.py (Postgres local fixo + Bronze mongomock).
 */
import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

const arquivo = resolve(process.cwd(), "../tmp/operacao-local.json");
test.skip(!existsSync(arquivo), "Requer captura do roteiro isolado validar_operacao_local.py");

test("apresenta previsão real dos oito distritos, seus insumos e limitações", async ({ page }) => {
  const captura = JSON.parse(readFileSync(arquivo, "utf8"));
  const respostas = captura.respostas as Record<string, unknown>;
  const locais = new Map<string, unknown>(Object.entries(respostas));
  const atual = respostas["/cenarios/impacto-previsto?horizonte_h=24"] as {
    dados: {
      itens: {
        territorio_id: string;
        nome: string;
        nivel: string;
        avaliacao: { chuva_no_horizonte_mm: number | null };
      }[];
    };
  };
  const distritos = atual.dados.itens.filter((i) => i.nivel === "distrito");
  expect(distritos).toHaveLength(8);
  expect(distritos.every((i) => i.avaliacao.chuva_no_horizonte_mm !== null)).toBe(true);
  await page.route("**/api/v1/**", async (route) => {
    const u = new URL(route.request().url());
    const caminho = u.pathname.replace("/api/v1", "");
    const chave = caminho + u.search;
    let corpo = locais.get(chave) ?? locais.get(caminho);
    if (caminho === "/auth/eu" && corpo)
      corpo = {
        ...(corpo as object),
        expira_em: new Date(Date.now() + 3600000).toISOString(),
        mapa_tiles_url: "",
      };
    await route.fulfill({
      status: corpo ? 200 : 404,
      json: corpo ?? { detail: "Fora do recorte da captura local" },
    });
  });
  await page.goto("/app/simulador");
  await page.getByRole("radio", { name: "Previsão por distrito", exact: true }).check();
  await expect(page.getByText(/ML de alagamento indisponível/)).toBeVisible();
  await expect(page.locator(".leaflet-container")).toBeVisible();
  const bairro = atual.dados.itens.find((i) => i.nivel === "bairro")!;
  await page.getByRole("button", { name: bairro.nome }).click();
  await expect(page.getByRole("heading", { name: "Insumos da previsão atual" })).toBeVisible();
  await expect(page.getByText(/Chuva prevista em 24 h:/)).toBeVisible();
  await expect(page.getByText(/Fonte: open-meteo-previsao/)).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  const a11y = await new AxeBuilder({ page } as unknown as ConstructorParameters<typeof AxeBuilder>[0])
    .withTags(["wcag2a", "wcag2aa"])
    .analyze();
  expect(a11y.violations.filter((v) => ["critical", "serious"].includes(v.impact ?? ""))).toEqual([]);
  await page.screenshot({ path: `../tmp/operacao-${test.info().project.name}.png`, fullPage: true });
});
