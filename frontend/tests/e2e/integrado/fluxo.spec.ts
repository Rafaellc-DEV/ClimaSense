/**
 * M11/M12 contra o sistema real. T11.6: o analista cria e envia; o revisor aprova; a coordenação publica → aparece
 * na landing e no mapa vivo → vence → some. T12.3: a publicação aparece na auditoria.
 */
import { expect, test, type Page } from "@playwright/test";
import { entrar } from "./apoio";

function horarioRecife(d: Date) {
  return new Date(d.getTime() - 3 * 3_600_000).toISOString().slice(0, 16);
}

async function sair(page: Page) {
  await page.getByRole("button", { name: "Sair" }).first().click();
  await page.waitForURL((u) => u.pathname === "/");
}

test("avaliações: o autor não vê Aprovar; devolver exige justificativa; as abas contam (T11.1, T11.2)", async ({
  page,
}) => {
  await entrar(page, "analista", "/app/avaliacoes/nova?territorio=ds-7");
  const justificativa = `Teste E2E ${Date.now()}: chuva acima do comum prevista para o DS VII.`;
  await page.getByText("Alerta", { exact: true }).click();
  await page.getByLabel("Justificativa").fill(justificativa);
  await page.getByRole("button", { name: "Salvar rascunho" }).click();
  await expect(page.getByRole("heading", { name: /Avaliação: Distrito Sanitário VII/ })).toBeVisible();
  await page.getByRole("button", { name: "Enviar para revisão" }).click();
  await expect(page.getByText("Enviado para revisão.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Aprovar esta versão" })).toHaveCount(0);
  const endereco = page.url();
  await sair(page);

  await entrar(page, "revisor", endereco.replace(/^https?:\/\/[^/]+/, ""));
  await page.getByRole("button", { name: "Devolver com justificativa" }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Devolver" }).click();
  await expect(page.getByText("Escreva o motivo da devolução.")).toBeVisible();
  await page.getByRole("dialog").getByLabel("Motivo").fill("Inclua a maré prevista nas evidências.");
  await page.getByRole("dialog").getByRole("button", { name: "Devolver" }).click();
  await expect(page.getByText("Devolvido com o motivo.")).toBeVisible();
  await expect(page.getByText("“Inclua a maré prevista nas evidências.”")).toBeVisible();

  await page.goto("/app/avaliacoes?territorio=recife&inicio=2021-01-01");
  const aba = page.getByRole("button", { name: /^Devolvida/ });
  const n = Number(await aba.locator("span").innerText());
  expect(n).toBeGreaterThanOrEqual(1);
  await aba.click();
  await expect(page.locator("tbody tr")).toHaveCount(n);
});

test("jornada do comunicado: rascunho → revisão → publicação → landing e mapa → vence → some (T11.3–T11.6)", async ({
  page,
}) => {
  test.setTimeout(240_000);
  const titulo = `Teste E2E ${Date.now()}: alerta em Afogados`;
  const agora = new Date();
  const fim = new Date(agora.getTime() + 2 * 60_000);
  fim.setSeconds(0, 0);

  // 1. analista escreve; a prévia é o mesmo cartão da landing (T11.4)
  await entrar(page, "analista", "/app/comunicados/novo");
  await page.getByRole("button", { name: "Adicionar território" }).click();
  await page.getByRole("dialog").getByLabel("Procurar").fill("afogados");
  await page.getByRole("dialog").getByRole("checkbox", { name: "Afogados" }).check();
  await page.getByRole("dialog").getByRole("button", { name: "Pronto" }).click();
  await page.getByText("Alerta", { exact: true }).click();
  await page.getByLabel("Título").fill(titulo);
  const longa =
    "Esta é uma frase de teste propositalmente comprida para verificar que o editor avisa quando uma frase passa de vinte e cinco palavras e fica difícil de ler para a população idosa.";
  await page.getByLabel("Texto").fill(longa);
  await expect(page.getByText(/tem \d+ palavras/)).toBeVisible();
  await page
    .getByLabel("Texto")
    .fill("Chuva forte prevista para a tarde. Evite as áreas que costumam alagar.");
  await expect(
    page.getByText(
      `${"Chuva forte prevista para a tarde. Evite as áreas que costumam alagar.".length} de 1200 caracteres.`,
    ),
  ).toBeVisible();
  await page.getByLabel("Orientação 1").fill("Evite atravessar ruas alagadas.");
  await page.getByLabel("Vale a partir de").fill(horarioRecife(new Date(agora.getTime() - 60_000)));
  await page.getByLabel("Vale até").fill(horarioRecife(fim));
  const previa = page.getByRole("article", { name: "Prévia do aviso" });
  await expect(previa).toContainText(titulo);
  await expect(previa).toContainText("Afogados");
  await page.getByRole("button", { name: "Salvar rascunho" }).click();
  await expect(page.getByText("Rascunho salvo.")).toBeVisible();
  await page.getByRole("button", { name: "Enviar para revisão" }).click();
  await expect(page.getByText("Enviado para revisão.")).toBeVisible();
  const endereco = page.url().replace(/^https?:\/\/[^/]+/, "");
  await sair(page);

  // 2. revisor aprova a versão
  await entrar(page, "revisor");
  await expect(page.getByRole("region", { name: "Aguardando sua revisão" })).toContainText(titulo);
  await page.goto(endereco);
  await page.getByRole("button", { name: "Aprovar esta versão" }).click();
  await expect(page.getByText("Versão aprovada.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Publicar" })).toHaveCount(0); // revisor não publica
  await sair(page);

  // 3. coordenação publica, com o diálogo de consequência (T11.5, RNF-ACE-11)
  await entrar(page, "coordenacao", endereco);
  await page.getByRole("button", { name: "Publicar" }).click();
  const confirmar = page.getByRole("dialog", { name: "Publicar na página inicial?" });
  await expect(confirmar).toContainText("visível para qualquer pessoa na página inicial até");
  await confirmar.getByRole("button", { name: "Publicar" }).click();
  await expect(page.getByText("Publicado na página inicial.")).toBeVisible();

  // T12.3: a publicação aparece na auditoria
  await page.goto("/app/admin/auditoria");
  await expect(page.locator("tbody")).toContainText("comunicado publicado");
  await sair(page);

  // 4. aparece na landing e no mapa vivo (DS V é o distrito de Afogados)
  await page.goto("/");
  await expect(page.locator("#avisos article", { hasText: titulo })).toBeVisible();
  await expect(page.locator('svg g[data-afetado="true"]').first()).toBeVisible();
  await expect(
    page.locator("li", { hasText: "Distrito Sanitário V" }).filter({ hasText: "Alerta" }).first(),
  ).toBeVisible();

  // 5. vence e some sozinho (RN-14)
  const espera = fim.getTime() - Date.now() + 2_000;
  await page.waitForTimeout(Math.max(0, espera));
  await page.reload();
  await expect(page.locator("#avisos article", { hasText: titulo })).toHaveCount(0);
});

test("administração: criar conta mostra a senha uma vez; desativar pede confirmação (T12.2)", async ({
  page,
}) => {
  await entrar(page, "coordenacao", "/app/admin");
  const email = `teste.e2e.${Date.now()}@climasense.dev`;
  await page.getByRole("button", { name: "Criar conta" }).click();
  const dialogo = page.getByRole("dialog", { name: "Criar conta" });
  await dialogo.getByLabel("Nome").fill("Pessoa de Teste");
  await dialogo.getByLabel("E-mail").fill(email);
  await dialogo.getByRole("button", { name: "Criar conta" }).click();
  await expect(page.getByRole("dialog", { name: "Senha temporária" })).toBeVisible();
  await page.getByRole("button", { name: "Já anotei" }).click();
  const linha = page.locator("tbody tr", { hasText: email });
  await expect(linha).toContainText("aguardando o 1º acesso");
  await linha.getByRole("button", { name: /Desativar/ }).click();
  await expect(page.getByRole("dialog")).toContainText("não consegue mais entrar");
  await page.getByRole("dialog").getByRole("button", { name: "Desativar" }).click();
  await expect(linha).toContainText("Desativada");
  await page.getByRole("link", { name: "Execuções do ETL" }).click();
  await expect(page.locator("tbody tr").first()).toBeVisible();
});
