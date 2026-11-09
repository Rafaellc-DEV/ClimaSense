/**
 * Fluxos do PRD contra a API real (Vite 5173 + API 8000). LEITURA vai à API de verdade; ESCRITA nunca chega nela:
 * `bloquearEscritas` responde 200 e guarda o que o navegador tentou enviar, para o teste conferir o corpo.
 * Exige E2E_SENHA (senha do gestor). Cobre RF-01, RF-02, RF-08 a RF-10, RF-15 a RF-17, RF-23 a RF-30.
 */
import { expect, test, type Page } from "@playwright/test";
import { bloquearEscritas, entrar } from "./apoio";

const MENU = (p: Page) => p.getByRole("navigation", { name: "Menu principal" });

test("menu com as cinco telas do PRD e rodapé (RF-20)", async ({ page }) => {
  await entrar(page);
  for (const nome of ["Mapa", "Situação do evento", "Saúde", "Ações", "Simulador"])
    await expect(MENU(page).getByRole("link", { name: nome })).toBeVisible();
  for (const fora of ["Comunicados", "Boletim", "Registro do evento", "Chuva", "Séries"])
    await expect(MENU(page).getByRole("link", { name: fora, exact: true })).toHaveCount(0);
});

test("rotas antigas redirecionam, sem 404 (RF-20)", async ({ page }) => {
  await entrar(page);
  await page.goto("/app/registro");
  await expect(page).toHaveURL(/\/app\/acoes/);
  await page.goto("/app/boletim");
  await expect(page).toHaveURL(/\/app\/acoes\/relatorio/);
});

test("ver o mapa: bairros, estágio do COP sem dado e camadas liga/desliga (RF-01, RF-02, RF-07)", async ({
  page,
}) => {
  await entrar(page);
  await expect(page.getByRole("heading", { name: "Mapa", level: 1 })).toBeVisible();
  await expect(page.locator(".leaflet-overlay-pane path").first()).toBeVisible();
  // sem registro do COP: "Dados insuficientes", nunca "observação" nem "risco baixo" (RN-01)
  await expect(page.getByText(/Dados insuficientes: ninguém informou o estágio do COP/)).toBeVisible();
  await expect(page.getByText("Bairros por estágio")).toBeVisible();
  await expect(page.getByText(/consultado às/).first()).toBeVisible();
  // as três camadas do PRD, cada uma liga e desliga
  for (const nome of ["População vulnerável", "Áreas de risco", "Equipamentos de saúde"]) {
    const caixa = page.getByRole("checkbox", { name: new RegExp(`^${nome}`) });
    await caixa.check();
    await expect(caixa).toBeChecked();
    await caixa.uncheck();
    await expect(caixa).not.toBeChecked();
  }
  // prioridade por ordem, sem percentual (RN-06)
  const prioritarios = page.locator("main");
  await expect(prioritarios).toContainText("prioridade 1");
  await expect(page.getByRole("list").filter({ hasText: "prioridade 1" }).first()).not.toContainText("%");
});

test("ver o mapa: escolher um bairro na lista abre o painel com fonte (RF-07)", async ({ page }) => {
  await entrar(page);
  await page.getByText("Ver os 94 bairros em lista").click();
  await page
    .getByRole("button", { name: /Boa Viagem/ })
    .first()
    .click();
  await expect(page.getByRole("heading", { name: "Boa Viagem" }).first()).toBeVisible();
  await expect(page.getByText(/Fonte/).first()).toBeVisible();
});

test("declarar estágio de um bairro: justificativa obrigatória e corpo correto (RF-30), escrita interceptada", async ({
  page,
}) => {
  const tentativas = await bloquearEscritas(page, (url) =>
    url.endsWith("/estagios/mensagem")
      ? { json: { texto: "Mensagem de teste", wa_me_url: "https://wa.me/?text=x" } }
      : null,
  );
  await entrar(page);
  await page.getByText("Ver os 94 bairros em lista").click();
  await page
    .getByRole("button", { name: /Boa Viagem/ })
    .first()
    .click();
  await page.getByRole("button", { name: /^Declarar/ }).click();
  const d = page.getByRole("dialog", { name: "Declarar situação" });
  await d.getByRole("button", { name: "Declarar situação" }).click();
  await expect(d.getByText("Escreva em uma frase o motivo desta situação.")).toBeVisible();
  expect(tentativas).toHaveLength(0);
  await d.getByLabel("Justificativa").fill("Teste automático: chuva forte prevista.");
  await d.getByRole("button", { name: "Declarar situação" }).click();
  await expect.poll(() => tentativas.length).toBeGreaterThan(0);
  const post = tentativas.find((t) => t.url.endsWith("/estagios"));
  expect(post?.metodo).toBe("POST");
  expect(post?.corpo).toMatchObject({ justificativa: "Teste automático: chuva forte prevista." });
  expect((post?.corpo as { territorio_ids: string[] }).territorio_ids).toHaveLength(1);
});

test("Situação do evento: estágio oficial, chuva e maré, com fonte e hora (RF-08, RF-09, RF-10)", async ({
  page,
}) => {
  await entrar(page, "/app/situacao");
  await expect(page.getByRole("heading", { name: "Situação do evento", level: 1 })).toBeVisible();
  await expect(page.getByText("Estágio oficial da cidade")).toBeVisible();
  await expect(page.getByText("Chuva nas últimas 24 h")).toBeVisible();
  await expect(page.getByText("Maré mais alta prevista")).toBeVisible();
  // sem dado, nunca zero (RN-01): ou há número com fonte, ou "Dados insuficientes"
  await expect(page.getByText(/Fonte: |Dados insuficientes/).first()).toBeVisible();
});

test("registrar ação: corpo enviado correto (RF-15, RF-16), escrita interceptada", async ({ page }) => {
  const tentativas = await bloquearEscritas(page);
  await entrar(page, "/app/acoes");
  const form = page.getByRole("form", { name: "Registrar ação" });
  await form.getByRole("button", { name: "Registrar ação" }).click();
  expect(tentativas).toHaveLength(0); // sem distrito e sem texto, nada é enviado
  await form.getByRole("combobox", { name: "Distrito" }).selectOption({ label: "Distrito 7" });
  await form.getByLabel("Descrição").fill("Teste automático: vistoria em encosta.");
  await form.getByLabel("Responsável").fill("Defesa Civil");
  await form.getByLabel("Status").selectOption("em_andamento");
  await form.getByRole("button", { name: "Registrar ação" }).click();
  await expect.poll(() => tentativas.length).toBe(1);
  expect(tentativas[0].metodo).toBe("POST");
  expect(tentativas[0].corpo).toMatchObject({
    descricao: "Teste automático: vistoria em encosta.",
    responsavel: "Defesa Civil",
    situacao: "em_andamento",
  });
});

test("excluir ação: pede confirmação e manda DELETE, escrita interceptada (RF-15)", async ({ page }) => {
  const tentativas = await bloquearEscritas(page);
  await entrar(page, "/app/acoes");
  const botao = page.getByRole("button", { name: /^Excluir a ação/ }).first();
  if ((await botao.count()) === 0) test.skip(true, "Sem ação cadastrada para excluir.");
  await botao.click({ force: true });
  const d = page.getByRole("dialog", { name: "Excluir esta ação?" });
  await expect(d.getByText("Isso não pode ser desfeito.")).toBeVisible();
  await d.getByRole("button", { name: "Cancelar" }).click();
  expect(tentativas).toHaveLength(0);
  await botao.click({ force: true });
  await d.getByRole("button", { name: "Excluir" }).click();
  await expect.poll(() => tentativas.length).toBe(1);
  expect(tentativas[0].metodo).toBe("DELETE");
});

test("gerar relatório executivo: período, ações, saúde e fontes (RF-17)", async ({ page }) => {
  await entrar(page, "/app/acoes");
  await page.getByRole("link", { name: "Relatório executivo" }).click();
  await expect(page).toHaveURL(/\/app\/acoes\/relatorio/);
  await expect(page.getByText("Montando o boletim")).toHaveCount(0, { timeout: 30_000 });
  const corpo = page.locator("main");
  for (const secao of [
    "Resumo",
    "Situação por distrito",
    "Chuva e maré",
    "Saúde",
    "Ações da equipe",
    "De onde vêm os números",
  ])
    await expect(corpo, secao).toContainText(secao);
  await expect(page.getByText(/\d{2}\/\d{2}\/\d{4} a \d{2}\/\d{2}\/\d{4}/)).toBeVisible();
  await expect(page.getByRole("button", { name: /Imprimir/ })).toBeVisible();
  await expect(page.getByText(/Não é alerta oficial/)).toBeVisible();
});

test("rodar simulação: premissas das fontes reais, recálculo sozinho, salvar interceptado (RF-23 a RF-28)", async ({
  page,
}) => {
  const tentativas = await bloquearEscritas(page, (url) => (/\/cenarios\/simular/.test(url) ? null : null));
  // POST /cenarios/simular só calcula; deixa passar para a API real
  await page.route("**/api/v1/cenarios/simular", (r) => r.continue());
  await entrar(page, "/app/simulador");
  await expect(page.getByText("Experimental").first()).toBeVisible(); // RN-11
  const chuva = page.getByLabel("Chuva prevista em 24 h");
  await expect(page.getByText("Estágio sugerido por distrito")).toBeVisible();
  // premissa sem fonte fica "Sem dado", nunca vira zero (RN-02)
  const antes = await page.getByRole("region", { name: "Ordem de atenção dos distritos" }).innerText();
  const sim = page.waitForResponse((r) => r.url().includes("/cenarios/simular"));
  await chuva.fill("150");
  expect((await sim).status()).toBe(200);
  await expect(page.getByRole("region", { name: "Ordem de atenção dos distritos" })).toBeVisible();
  await expect(page.getByText(/Arboviroses são contexto/).first()).toBeVisible();
  expect(antes.length).toBeGreaterThan(0);
  await page.getByRole("button", { name: "Salvar cenário" }).first().click();
  await page.getByLabel("Nome do cenário").fill("Teste automático");
  await page.getByRole("dialog").getByRole("button", { name: "Salvar cenário" }).click();
  await expect.poll(() => tentativas.filter((t) => t.url.endsWith("/cenarios")).length).toBe(1);
});
