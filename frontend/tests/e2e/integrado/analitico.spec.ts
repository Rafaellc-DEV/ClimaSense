/** T10.6–T10.8 contra os dados reais: séries com lacunas, série curta e os dois estados dos cenários. */
import { expect, test } from "@playwright/test";
import { entrar } from "./apoio";

test("séries: com lacunas o gráfico mostra o vão e a tabela diz “sem dado” (T10.6)", async ({ page }) => {
  // os últimos dias ainda não chegaram na reanálise (cerca de 7 dias de atraso): lacuna real
  await entrar(page, "analista", "/app/series?territorio=ds-4");
  await expect(
    page.getByRole("heading", { name: /Chuva ao longo do tempo: Distrito Sanitário IV/ }),
  ).toBeVisible();
  await expect(page.getByText(/Faltam dados em \d+ dias/)).toBeVisible();
  await expect(
    page.getByText(/Fonte: Chuva horária por distrito \(reanálise ERA5\) \(derivada/),
  ).toBeVisible();
  await page.getByRole("button", { name: "Ver como tabela" }).first().click();
  await expect(page.getByRole("table").first()).toContainText("sem dado");
});

test("séries: série curta recebe o aviso; o calendário mostra os anos (T10.7)", async ({ page }) => {
  await entrar(page, "analista", "/app/series?territorio=recife&inicio=2026-09-01&fim=2026-09-20");
  await expect(page.getByText("Série curta: não use para caracterizar o clima.").first()).toBeVisible();
  await expect(page.getByRole("heading", { name: "Chuva por mês e ano" })).toBeVisible();
  await expect(page.getByText(/em média, o mês mais chuvoso/)).toBeVisible();
});

test("cenários: os dois gráficos usam o mesmo domínio de tempo e há o cartão de decisão (T10.8)", async ({
  page,
}) => {
  await entrar(page, "analista", "/app/cenarios?territorio=ds-5");
  await expect(page.getByText("Experimental: não validado para uso operacional.")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Prioridade operacional indicada" })).toBeVisible();
  await expect(page.getByRole("heading", { name: /Chuva prevista: Distrito Sanitário V/ })).toBeVisible();
  await expect(page.getByRole("heading", { name: /Maré prevista/ })).toBeVisible();
  // os eixos alinhados: um único domínio de tempo para os dois gráficos, e os mesmos rótulos de hora
  await expect(page.locator("[data-dominio]")).toHaveAttribute("data-dominio", /^[0-9]+[/][0-9]+$/);
  // os dois gráficos estão dentro do mesmo contêiner de domínio e usam a mesma grade
  await expect(page.locator("[data-dominio] [_echarts_instance_]")).toHaveCount(2);
  await page.getByRole("radio", { name: "24 horas" }).check();
  await expect(page.getByText(/nas próximas 24 horas/)).toBeVisible();
  await expect(page.getByText(/chance de alagar/).first()).toBeVisible(); // só no aviso de que NÃO é chance
});

test("cenários: sem maré, “Dados insuficientes para estimar” com a régua tracejada (T10.8)", async ({
  page,
}) => {
  await entrar(page, "analista");
  await page.route("**/api/v1/cenarios**", async (r) => {
    const resposta = await r.fetch();
    const corpo = await resposta.json();
    corpo.dados.mare = [];
    corpo.dados.estimativa.prioridade = "dados_insuficientes";
    corpo.dados.estimativa.qualidade = "insuficiente";
    corpo.dados.estimativa.janela_atencao = null;
    corpo.dados.estimativa.fatores = [];
    corpo.dados.estimativa.limitacoes = [
      "Falta a previsão de maré. Sem esses insumos a regra não estima nada.",
    ];
    corpo.meta.dados_insuficientes = true;
    await r.fulfill({ response: resposta, json: corpo });
  });
  await page.goto("/app/cenarios?territorio=ds-2");
  await expect(page.getByText("Dados insuficientes para estimar")).toBeVisible();
  await expect(page.locator('figure[data-nivel="insuficiente"]')).toBeVisible();
  await expect(page.getByText("Sem previsão de maré")).toBeVisible();
});

test("“Encaminhar para avaliação” pré-preenche a avaliação com as evidências do cenário (RF-09.7)", async ({
  page,
}) => {
  await entrar(page, "analista", "/app/cenarios?territorio=ds-3");
  await page.getByRole("button", { name: "Encaminhar para avaliação" }).click();
  await expect(page.getByRole("heading", { name: "Registrar avaliação" })).toBeVisible();
  await expect(page.getByLabel("Justificativa")).toHaveValue(/Cenário experimental de 72 h/);
  await expect(page.getByText(/Cenário de 72 h para Distrito Sanitário III/)).toBeVisible();
});
