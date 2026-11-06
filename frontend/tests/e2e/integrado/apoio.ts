import AxeBuilder from "@axe-core/playwright";
import { expect, type Page } from "@playwright/test";

/**
 * Conta do gestor para os testes contra a API real. A senha NÃO fica no código: vem de `E2E_SENHA`
 * (o e-mail pode ser trocado por `E2E_EMAIL`). Sem a variável, os testes falham com mensagem clara.
 */
const EMAIL = process.env.E2E_EMAIL ?? "gestor@climasense.dev";

export const SAIDAS_DE_ESCRITA = /\/api\/v1\/(estagios(\/oficial|\/mensagem)?|acoes|abrigos|cenarios\/simular|cenarios)(\/|\?|$)/;

export async function entrar(page: Page, destino = "/app") {
  const senha = process.env.E2E_SENHA;
  if (!senha) throw new Error("Defina E2E_SENHA com a senha da conta de teste (gestor).");
  await page.goto(`/entrar`);
  await page.getByLabel("E-mail").fill(EMAIL);
  await page.getByLabel("Senha", { exact: true }).fill(senha);
  await page.getByRole("button", { name: "Entrar" }).click();
  await page.waitForURL("**/app**");
  if (destino !== "/app") await page.goto(destino);
}

/**
 * Intercepta toda escrita (POST, PUT, PATCH, DELETE) em `/api/v1/` e responde com sucesso sem chegar à API real.
 * Devolve a lista do que foi tentado, para o teste conferir o corpo. O login e a renovação da sessão passam.
 */
export async function bloquearEscritas(
  page: Page,
  respostas: (url: string, metodo: string, corpo: unknown) => { status?: number; json: unknown } | null = () => null,
) {
  const tentativas: { metodo: string; url: string; corpo: unknown }[] = [];
  await page.route("**/api/v1/**", async (rota) => {
    const req = rota.request();
    const metodo = req.method();
    const url = req.url();
    if (metodo === "GET" || metodo === "HEAD" || /\/auth\//.test(url)) return rota.fallback();
    let corpo: unknown = null;
    try {
      corpo = req.postDataJSON();
    } catch {
      corpo = req.postData();
    }
    tentativas.push({ metodo, url, corpo });
    const r = respostas(url, metodo, corpo);
    if (r) return rota.fulfill({ status: r.status ?? 200, json: r.json });
    return rota.fulfill({ status: 200, json: {} });
  });
  return tentativas;
}

export async function semViolacoes(page: Page) {
  const r = await new AxeBuilder({ page } as unknown as ConstructorParameters<typeof AxeBuilder>[0])
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"])
    .exclude(".leaflet-container") // tiles e controles de terceiros; a navegação do mapa é testada à parte
    .exclude("[_echarts_instance_]") // o gráfico tem alternativa em tabela e descrição
    .analyze();
  const graves = r.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
  expect(graves.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(" ")).join(", ")}`)).toEqual([]);
  return r.violations;
}
