import { noFiltro, proximoPasso } from "./Estado";

const EU = "eu";
const quando = (iso: string) => `[${iso}]`;
const tudo = () => true;
const nada = () => false;

test("em revisão: aguarda a sua revisão só para quem revisa e não escreveu", () => {
  const item = { tipo: "comunicado" as const, estado: "em_revisao", autor_id: "outra", validade_fim: "x" };
  expect(proximoPasso(item, EU, tudo, quando)).toEqual({ texto: "Aguarda a sua revisão", comVoce: true });
  expect(proximoPasso({ ...item, autor_id: EU }, EU, tudo, quando).comVoce).toBe(false);
  expect(proximoPasso(item, EU, nada, quando).texto).toBe("Aguarda a revisão de outra pessoa");
});

test("aprovado: pronto para publicar para a coordenação; avaliação aprovada pede encerrar", () => {
  const c = { tipo: "comunicado" as const, estado: "aprovado", autor_id: "outra", validade_fim: "x" };
  expect(proximoPasso(c, EU, (p) => p === "publicar", quando).texto).toBe("Pronto para publicar");
  expect(proximoPasso(c, EU, nada, quando).texto).toMatch(/aguarda a coordenação/);
  expect(proximoPasso({ tipo: "avaliacao", estado: "aprovado" }, EU, tudo, quando).texto).toMatch(/encerre/);
});

test("publicado: diz até quando vale e avisa quando venceu", () => {
  const futuro = new Date(Date.now() + 3_600_000).toISOString();
  const passado = new Date(Date.now() - 3_600_000).toISOString();
  const c = { tipo: "comunicado" as const, estado: "publicado", autor_id: "x" };
  expect(proximoPasso({ ...c, validade_fim: futuro }, EU, tudo, quando).texto).toBe(
    `Publicado, no ar até [${futuro}]`,
  );
  const vencido = proximoPasso({ ...c, validade_fim: passado }, EU, tudo, quando);
  expect(vencido.texto).toMatch(/^Venceu .*encerre o aviso$/);
  expect(vencido.comVoce).toBe(true);
});

test("rascunho e devolvido são com você só quando você escreveu", () => {
  expect(
    proximoPasso({ tipo: "comunicado", estado: "devolvido", autor_id: EU }, EU, tudo, quando).comVoce,
  ).toBe(true);
  expect(
    proximoPasso(
      { tipo: "comunicado", estado: "rascunho", autor_id: "x", autor_nome: "Ana" },
      EU,
      tudo,
      quando,
    ).texto,
  ).toBe("Rascunho de Ana, ainda não enviado");
});

test("filtros simples agrupam os estados técnicos", () => {
  const p = { texto: "", comVoce: false };
  expect(noFiltro("andamento", "devolvido", p)).toBe(true);
  expect(noFiltro("no_ar", "publicado", p)).toBe(true);
  expect(noFiltro("comigo", "publicado", p)).toBe(false);
  expect(noFiltro("comigo", "em_revisao", { texto: "", comVoce: true })).toBe(true);
});
