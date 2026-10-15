import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { contraste } from "./contraste";

const css = readFileSync(resolve(__dirname, "tokens.css"), "utf-8");

function bloco(seletor: string): Record<string, string> {
  const inicio = css.indexOf(seletor + " {");
  const corpo = css.slice(inicio, css.indexOf("}", inicio));
  const tokens: Record<string, string> = {};
  for (const m of corpo.matchAll(/(--[\w-]+):\s*(#[0-9a-fA-F]{6})/g)) tokens[m[1]] = m[2].toLowerCase();
  return tokens;
}

const claro = bloco(":root");
const escuro = { ...claro, ...bloco(':root[data-tema="escuro"]') };

// [texto, fundo, mínimo, motivo]
const pares: [string, string, number, string][] = [
  ["--cs-tinta", "--cs-papel", 7, "texto principal"],
  ["--cs-tinta", "--cs-nevoa", 7, "texto principal no fundo da página"],
  ["--cs-tinta-2", "--cs-papel", 4.5, "texto secundário"],
  ["--cs-tinta-2", "--cs-nevoa", 4.5, "texto secundário no fundo da página"],
  ["--cs-mangue", "--cs-papel", 4.5, "links"],
  ["--cs-mare", "--cs-papel", 4.5, "títulos e botão secundário"],
  ["--cs-sobre-mare", "--cs-mare", 4.5, "texto do botão principal"],
  ["--cs-foco", "--cs-papel", 3, "anel de foco"],
  ["--cs-linha-forte", "--cs-papel", 3, "borda de campo (componente)"],
  ["--n-texto", "--n-sem-bg", 7, "selo: nenhum aviso (aviso público)"],
  ["--n-texto", "--n-info-bg", 7, "selo: fique atento"],
  ["--n-texto", "--n-atencao-bg", 7, "selo: atenção"],
  ["--n-texto", "--n-alerta-bg", 7, "selo: alerta"],
  ["--n-critico-texto", "--n-critico-bg", 7, "selo: situação crítica"],
  ["--n-texto", "--n-insuf-bg", 7, "selo: dados insuficientes"],
];

describe.each([
  ["claro", claro],
  ["escuro", escuro],
])("contraste dos tokens no modo %s", (_modo, t) => {
  test.each(pares)("%s sobre %s ≥ %s:1 (%s)", (texto, fundo, minimo) => {
    expect(t[texto], `token ${texto} ausente`).toBeDefined();
    expect(t[fundo], `token ${fundo} ausente`).toBeDefined();
    expect(contraste(t[texto], t[fundo])).toBeGreaterThanOrEqual(minimo);
  });
});

test("as 6 cores de série dos gráficos têm contraste ≥ 3:1 com o painel (claro)", () => {
  for (const i of [1, 2, 3, 4, 5, 6])
    expect(contraste(claro[`--g-${i}`], claro["--cs-papel"])).toBeGreaterThanOrEqual(3);
});
