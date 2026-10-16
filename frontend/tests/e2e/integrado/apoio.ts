import fs from "node:fs";
import path from "node:path";
import AxeBuilder from "@axe-core/playwright";
import { expect, type Page } from "@playwright/test";

/** Contas locais (tmp/ fica fora do Git): uma linha `email;senha` por pessoa. */
const ARQUIVO = path.resolve(process.cwd(), "../tmp/senhas-equipe-local.txt");
const CONTAS = Object.fromEntries(
  fs
    .readFileSync(ARQUIVO, "utf8")
    .split(/\r?\n/)
    .filter(Boolean)
    .map((l) => {
      const i = l.indexOf(";");
      return [l.slice(0, i), l.slice(i + 1)];
    }),
);

export type Pessoa = "analista" | "revisor" | "coordenacao";
const EMAIL: Record<Pessoa, string> = {
  analista: "ana@climasense.dev",
  revisor: "rui@climasense.dev",
  coordenacao: "rafael@climasense.dev", // coordenação + administrador
};

export async function entrar(page: Page, pessoa: Pessoa, destino = "/app") {
  await page.goto(`/entrar`);
  await page.getByLabel("E-mail").fill(EMAIL[pessoa]);
  await page.getByLabel("Senha", { exact: true }).fill(CONTAS[EMAIL[pessoa]]);
  await page.getByRole("button", { name: "Entrar" }).click();
  await page.waitForURL("**/app**");
  if (destino !== "/app") await page.goto(destino);
}

export async function semViolacoes(page: Page) {
  const r = await new AxeBuilder({ page } as unknown as ConstructorParameters<typeof AxeBuilder>[0])
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"])
    .exclude(".leaflet-container") // tiles e controles de terceiros; a navegação do mapa é testada à parte
    .exclude("[_echarts_instance_]") // o gráfico tem alternativa em tabela e descrição (RNF-ACE-09)
    .analyze();
  const graves = r.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
  expect(graves.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(" ")).join(", ")}`)).toEqual([]);
  return r.violations;
}
