/** Landing e páginas públicas com respostas simuladas da API (T9.1–T9.6, parte pública do T13.1). */
import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

const AMANHA = new Date(Date.now() + 26 * 3_600_000).toISOString();
const ONTEM = new Date(Date.now() - 26 * 3_600_000).toISOString();
const AVISO_ALERTA = {
  id: "11111111-1111-1111-1111-111111111111",
  titulo: "Alerta de alagamento em Afogados e Mustardinha",
  nivel: "alerta",
  territorios: [
    { id: "bairro-afogados", tipo: "bairro", nome_exibicao: "Afogados" },
    { id: "bairro-mustardinha", tipo: "bairro", nome_exibicao: "Mustardinha" },
  ],
  texto: "Chuva forte prevista para a tarde, com maré alta às 15h.",
  orientacoes: ["Evite atravessar ruas alagadas.", "Desligue a energia se a água entrar em casa."],
  validade_inicio: ONTEM,
  validade_fim: AMANHA,
  emitido_por: "Vigilância em Saúde do Recife",
  publicado_em: ONTEM,
  publico: "populacao",
};
const AVISO_ATENCAO = {
  ...AVISO_ALERTA,
  id: "22222222-2222-2222-2222-222222222222",
  nivel: "atencao",
  titulo: "Atenção em Boa Viagem",
};

async function simular(page: Page, avisos: (typeof AVISO_ALERTA)[], niveis: Record<string, string> = {}) {
  const autenticadas: string[] = [];
  await page.route("**/api/v1/**", (r) => {
    const url = r.request().url();
    if (!url.includes("/api/v1/publico/")) autenticadas.push(url);
    if (url.includes("/publico/estado"))
      return r.fulfill({
        json: {
          avisos_ativos: avisos.length,
          distritos_afetados: Object.keys(niveis),
          niveis_por_distrito: niveis,
          nivel_mais_alto: avisos[0]?.nivel ?? null,
          principal: avisos[0] ?? null,
          atualizado_em: new Date().toISOString(),
        },
      });
    if (url.match(/\/publico\/avisos\/[0-9a-f-]+$/)) {
      const a = avisos.find((x) => url.endsWith(x.id));
      return a
        ? r.fulfill({ json: a })
        : r.fulfill({ status: 404, json: { detail: "Este aviso não está mais em vigor." } });
    }
    if (url.includes("/publico/avisos")) return r.fulfill({ json: avisos });
    if (url.includes("/publico/fontes"))
      return r.fulfill({
        json: [
          {
            id: "open-meteo-previsao",
            nome: "Chuva prevista",
            orgao: "Open-Meteo",
            tipo: "prevista",
            status: "atualizada",
            ultima_atualizacao: ONTEM,
          },
          {
            id: "ana-telemetria",
            nome: "Chuva e nível dos rios",
            orgao: "ANA",
            tipo: "observada",
            status: "planejada",
            ultima_atualizacao: null,
          },
        ],
      });
    if (url.includes("/publico/territorios/busca"))
      return r.fulfill({
        json: [{ id: "bairro-brasilia-teimosa", nome: "Brasília Teimosa", distrito_id: "ds-6" }],
      });
    if (url.includes("/auth/eu"))
      return r.fulfill({ status: 401, json: { detail: "Entre para continuar." } });
    return r.fulfill({ status: 404, json: { detail: "não simulado" } });
  });
  return autenticadas;
}

async function semViolacoes(page: Page) {
  const r = await new AxeBuilder({ page } as unknown as ConstructorParameters<typeof AxeBuilder>[0])
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"])
    .analyze();
  const graves = r.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
  expect(graves.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(" ")).join(", ")}`)).toEqual([]);
}

test("sem aviso: diz “Nenhum aviso ativo publicado pela equipe.”, nunca “sem risco” (T9.1)", async ({
  page,
}) => {
  const autenticadas = await simular(page, []);
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(
    "Nenhum aviso ativo publicado pela equipe.",
  );
  await expect(page.getByText(/sem risco|tudo seguro/i)).toHaveCount(0);
  await expect(page.locator("p", { hasText: "Nenhum distrito com aviso publicado." })).toBeVisible();
  // RF-01.11 / T9.6: a landing nunca chama rota autenticada
  await page.waitForLoadState("networkidle");
  expect(autenticadas).toEqual([]);
});

test("com alerta: a régua chega ao nível 3 e só o distrito afetado é pintado (T9.1, T9.4)", async ({
  page,
}, info) => {
  await simular(page, [AVISO_ALERTA, AVISO_ATENCAO], { "ds-5": "alerta" });
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Alerta para 2 bairros até amanhã");
  await expect(page.getByText(/E mais 1 aviso em vigor/)).toBeVisible();
  if (info.project.name === "desktop")
    await expect(page.locator('figure[data-nivel="alerta"]')).toBeVisible();
  else await expect(page.locator('span[data-nivel="alerta"]').first()).toBeVisible();
  const pintados = page.locator('svg g[data-afetado="true"]');
  await expect(pintados).toHaveCount(1);
  await expect(
    page.locator("li", { hasText: "Distrito Sanitário 5" }).filter({ hasText: "Alerta" }),
  ).toBeVisible();
});

test("avisos em vigor seguem a ordem da API (nível, depois data) com o que fazer e a validade (T9.3)", async ({
  page,
}) => {
  await simular(page, [AVISO_ALERTA, AVISO_ATENCAO], { "ds-5": "alerta", "ds-6": "atencao" });
  await page.goto("/");
  const cartoes = page.locator("#avisos article");
  await expect(cartoes).toHaveCount(2);
  await expect(cartoes.first()).toHaveAttribute("data-nivel", "alerta");
  await expect(cartoes.first()).toContainText("O que fazer");
  await expect(cartoes.first()).toContainText("Vale até amanhã");
  await cartoes.first().getByRole("link").click();
  await expect(page).toHaveURL(/\/avisos\/1111/);
  await expect(page.getByRole("heading", { level: 2, name: AVISO_ALERTA.titulo })).toBeVisible();
});

test("aviso vencido ou encerrado não aparece no detalhe (T9.3)", async ({ page }) => {
  await simular(page, []);
  await page.goto("/avisos/33333333-3333-3333-3333-333333333333");
  await expect(page.getByText("Este aviso não está mais em vigor.")).toBeVisible();
});

test("busca de bairro sem acento (RF-01.5)", async ({ page }) => {
  await simular(page, [AVISO_ALERTA]);
  await page.goto("/");
  await page.locator("input[type=search]:visible").fill("brasilia");
  await expect(page.locator("button:visible", { hasText: "Brasília Teimosa" })).toBeVisible();
});

test("em 375 × 667 os três telefones de emergência estão visíveis sem rolar (T9.2)", async ({
  page,
}, info) => {
  test.skip(info.project.name !== "desktop", "a largura é controlada aqui");
  await page.setViewportSize({ width: 375, height: 667 });
  await simular(page, [AVISO_ALERTA], { "ds-5": "alerta" });
  await page.goto("/");
  for (const n of ["199", "193", "192"]) {
    const link = page.locator(`a[href="tel:${n}"]`).first();
    await expect(link).toBeInViewport();
  }
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(375);
});

for (const caminho of ["/", "/entrar", `/avisos/${AVISO_ALERTA.id}`]) {
  test(`${caminho} sem violações sérias de acessibilidade (axe)`, async ({ page }) => {
    await simular(page, [AVISO_ALERTA], { "ds-5": "alerta" });
    await page.goto(caminho);
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(800); // a água da régua termina de subir
    await semViolacoes(page);
  });
}
