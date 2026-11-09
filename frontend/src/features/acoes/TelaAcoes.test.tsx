import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { App } from "@/app/App";
import { AGORA, simularApi, usuarioTeste } from "@/features/evento/testes";
import { clienteConsultas } from "@/lib/api";

const acao = (id: string, extra = {}) => ({
  id,
  territorio_id: "ds-1",
  territorio_nome: "Distrito Sanitário I",
  territorio_nivel: "distrito",
  distrito_id: "ds-1",
  distrito_nome: "Distrito Sanitário I",
  tipo: "outro",
  descricao: `Ação ${id}`,
  responsavel: "Vigilância",
  situacao: "em_andamento",
  inicio_em: AGORA,
  criada_em: AGORA,
  atualizada_em: AGORA,
  autor_nome: "Mari Lima",
  ...extra,
});

function base(itens: unknown[] = []) {
  return {
    "/auth/eu": usuarioTeste(),
    "/territorios/prioridade": {
      dados: {
        itens: [
          { territorio_id: "ds-7", nome: "Distrito Sanitário VII", nivel: "distrito", posicao: 1 },
          { territorio_id: "ds-1", nome: "Distrito Sanitário I", nivel: "distrito", posicao: 2 },
        ],
      },
      meta: { fontes: [] },
    },
    "/territorios": [
      { id: "recife", tipo: "municipio", nome_exibicao: "Recife inteiro", pai_id: null },
      { id: "ds-1", tipo: "distrito", nome_exibicao: "Distrito Sanitário I", pai_id: "recife" },
      { id: "ds-7", tipo: "distrito", nome_exibicao: "Distrito Sanitário VII", pai_id: "recife" },
      { id: "bairro-ibura", tipo: "bairro", nome_exibicao: "Ibura", pai_id: "ds-7" },
    ],
    "/acoes": {
      itens: itens.length
        ? itens
        : [
            acao("a1"),
            acao("a2", {
              territorio_id: "ds-7",
              territorio_nome: "Distrito Sanitário VII",
              distrito_id: "ds-7",
            }),
            acao("a3", { situacao: "concluida", fim_em: AGORA }),
            acao("a4", { situacao: "planejada" }),
          ],
      contagens: {},
      total: 4,
      por_distrito: [],
    },
  };
}

function abrir() {
  window.history.pushState({}, "", "/app/acoes");
  return render(<App />);
}

afterEach(() => {
  vi.unstubAllGlobals();
  clienteConsultas.clear();
});

test("três cartões com selo Derivado, fonte e hora, e a contagem do registro", async () => {
  simularApi(base());
  abrir();
  const grupo = await screen.findByRole("region", { name: "Totais das ações" });
  const andamento = await within(grupo).findByRole("group", { name: "Em andamento" });
  expect(within(andamento).getByText("2")).toBeInTheDocument();
  expect(within(andamento).getByText("Derivado")).toBeInTheDocument();
  expect(within(andamento).getByText(/Registro da equipe/)).toBeInTheDocument();
  expect(within(grupo).getByRole("group", { name: "Planejadas" })).toHaveTextContent("1");
  expect(within(grupo).getByRole("group", { name: "Concluídas" })).toHaveTextContent("1");
});

test("tabela com Ação, Onde, Responsável, Status, Horário e Excluir; distrito mais vulnerável primeiro", async () => {
  simularApi(base());
  abrir();
  const tabela = await screen.findByRole("table", { name: "Ações do evento" });
  expect(
    within(tabela)
      .getAllByRole("columnheader")
      .map((c) => c.textContent),
  ).toEqual(["Ação", "Onde", "Responsável", "Status", "Horário", "Excluir"]);
  const linhas = within(tabela).getAllByRole("row").slice(1);
  expect(linhas[0]).toHaveTextContent("Distrito 7");
  expect(
    screen.getByText(/A exclusão fica registrada na auditoria, com quem, quando e o quê/),
  ).toBeInTheDocument();
  expect(screen.getAllByText(/Fonte: registro da equipe/).length).toBeGreaterThan(0);
  expect(document.body).not.toHaveTextContent(/Distrito Sanit|DS [IV]/);
});

test("filtros de Território e Período mudam a consulta", async () => {
  const pedidos = simularApi(base());
  abrir();
  const u = userEvent.setup();
  await screen.findByRole("table", { name: "Ações do evento" });
  await waitFor(() => expect(screen.getByLabelText("Território")).toBeEnabled());
  await u.selectOptions(screen.getByLabelText("Território"), "ds-7");
  await waitFor(() => expect(pedidos.some((p) => p.url.includes("territorio_id=ds-7"))).toBe(true));
  await u.selectOptions(screen.getByLabelText("Período"), "7d");
  await waitFor(() => expect(pedidos.some((p) => p.url.includes("desde="))).toBe(true));
});

test("mudança rápida de status manda PATCH com a situação", async () => {
  const pedidos = simularApi(base(), { "/acoes/a1": acao("a1") });
  abrir();
  const u = userEvent.setup();
  const sel = await screen.findAllByLabelText(/Mudar o status da ação em Distrito 1$/);
  await u.selectOptions(sel[0], "concluida");
  await waitFor(() =>
    expect(pedidos.find((p) => p.metodo === "PATCH")?.corpo).toMatchObject({ situacao: "concluida" }),
  );
});

test("formulário: Cidade, Distrito ou Bairro; pede território, descrição e responsável; envia o corpo", async () => {
  const pedidos = simularApi(base(), { "/acoes": { status: 201, corpo: acao("n1") } });
  abrir();
  const u = userEvent.setup();
  const form = await screen.findByRole("form", { name: "Registrar ação" });
  await u.click(within(form).getByRole("button", { name: "Registrar ação" }));
  expect(await within(form).findByText("Escolha o distrito.")).toBeInTheDocument();
  expect(within(form).getByText(/Escreva o que foi feito/)).toBeInTheDocument();
  expect(within(form).getByText("Informe quem é o responsável.")).toBeInTheDocument();
  await waitFor(() => expect(within(form).getByRole("combobox", { name: "Distrito" })).toBeEnabled());
  await u.selectOptions(within(form).getByRole("combobox", { name: "Distrito" }), "ds-7");
  await u.type(within(form).getByLabelText("Descrição"), "Visita à escola");
  await u.type(within(form).getByLabelText("Responsável"), "Assistência Social");
  await u.click(within(form).getByRole("button", { name: "Registrar ação" }));
  await waitFor(() =>
    expect(pedidos.find((p) => p.metodo === "POST")?.corpo).toMatchObject({
      territorio_id: "ds-7",
      descricao: "Visita à escola",
      responsavel: "Assistência Social",
      situacao: "em_andamento",
    }),
  );
});

test("formulário: Cidade não pede território; Bairro agrupa os bairros por distrito", async () => {
  const pedidos = simularApi(base(), { "/acoes": { status: 201, corpo: acao("n2") } });
  abrir();
  const u = userEvent.setup();
  const form = await screen.findByRole("form", { name: "Registrar ação" });
  await u.click(within(form).getByRole("radio", { name: "Bairro" }));
  await waitFor(() => expect(within(form).getByRole("combobox", { name: "Bairro" })).toBeEnabled());
  const grupo = within(form).getByRole("group", { name: "Distrito 7" });
  expect(within(grupo).getByRole("option", { name: "Ibura" })).toBeInTheDocument();
  await u.selectOptions(within(form).getByRole("combobox", { name: "Bairro" }), "bairro-ibura");
  await u.type(within(form).getByLabelText("Descrição"), "Limpeza de canal");
  await u.type(within(form).getByLabelText("Responsável"), "Prefeitura");
  await u.click(within(form).getByRole("button", { name: "Registrar ação" }));
  await waitFor(() =>
    expect(pedidos.find((p) => p.metodo === "POST")?.corpo).toMatchObject({ territorio_id: "bairro-ibura" }),
  );
  await u.click(within(form).getByRole("radio", { name: "Cidade" }));
  expect(within(form).queryByRole("combobox", { name: "Bairro" })).not.toBeInTheDocument();
  expect(within(form).queryByRole("combobox", { name: "Distrito" })).not.toBeInTheDocument();
});

test("ação em bairro mostra o bairro e o distrito", async () => {
  simularApi(
    base([
      acao("b1", {
        territorio_id: "bairro-ibura",
        territorio_nome: "Ibura",
        territorio_nivel: "bairro",
        distrito_id: "ds-7",
        distrito_nome: "Distrito Sanitário VII",
      }),
    ]),
  );
  abrir();
  const tabela = await screen.findByRole("table", { name: "Ações do evento" });
  expect(within(tabela).getByText("Ibura")).toBeInTheDocument();
  expect(within(tabela).getByText(/· Distrito 7/)).toBeInTheDocument();
});

test("ação da cidade aparece como Cidade", async () => {
  simularApi(
    base([
      acao("c1", {
        territorio_id: "recife",
        territorio_nome: "Recife inteiro",
        territorio_nivel: "municipio",
      }),
    ]),
  );
  abrir();
  const tabela = await screen.findByRole("table", { name: "Ações do evento" });
  expect(within(tabela).getByText("Cidade")).toBeInTheDocument();
});

test.each(["planejada", "em_andamento", "concluida", "cancelada"])(
  "ação %s tem Excluir; confirmar chama DELETE e recarrega a lista",
  async (situacao) => {
    const pedidos = simularApi(base([acao("x1", { situacao })]), { "/acoes/x1": { status: 204 } });
    abrir();
    const u = userEvent.setup();
    await u.click(await screen.findByRole("button", { name: /Excluir a ação em Distrito 1/ }));
    const dialogo = await screen.findByRole("dialog");
    expect(within(dialogo).getByText("Excluir esta ação?")).toBeInTheDocument();
    expect(within(dialogo).getByText("Isso não pode ser desfeito.")).toBeInTheDocument();
    const listas = () => pedidos.filter((p) => p.metodo === "GET" && /\/acoes\?/.test(p.url)).length;
    const antes = listas();
    await u.click(within(dialogo).getByRole("button", { name: "Excluir" }));
    await waitFor(() =>
      expect(pedidos.some((p) => p.metodo === "DELETE" && p.url.endsWith("/acoes/x1"))).toBe(true),
    );
    await waitFor(() => expect(listas()).toBeGreaterThan(antes));
  },
);

test("cancelar a confirmação não exclui nada", async () => {
  const pedidos = simularApi(base());
  abrir();
  const u = userEvent.setup();
  await u.click((await screen.findAllByRole("button", { name: /Excluir a ação em/ }))[0]);
  await u.click(within(await screen.findByRole("dialog")).getByRole("button", { name: "Cancelar" }));
  expect(pedidos.some((p) => p.metodo === "DELETE")).toBe(false);
});

test("falha ao excluir mostra erro em português", async () => {
  simularApi(base([acao("a1")]), { "/acoes/a1": { status: 500, corpo: { detail: "Falha no servidor." } } });
  abrir();
  const u = userEvent.setup();
  await u.click(await screen.findByRole("button", { name: /Excluir a ação em/ }));
  await u.click(within(await screen.findByRole("dialog")).getByRole("button", { name: "Excluir" }));
  expect(await screen.findByText("Não foi possível excluir a ação.")).toBeInTheDocument();
});

test("relatório executivo: checklist com a fonte de cada item e a nota de revisão", async () => {
  simularApi(base());
  abrir();
  const bloco = await screen.findByRole("region", { name: "Relatório executivo" });
  expect(within(bloco).getAllByRole("listitem")).toHaveLength(4);
  expect(within(bloco).getByText("InfoDengue, SINAN")).toBeInTheDocument();
  expect(within(bloco).getByText(/ninguém aprova o próprio conteúdo/)).toBeInTheDocument();
  expect(within(bloco).getByRole("link", { name: /Abrir o relatório/ })).toHaveAttribute(
    "href",
    "/app/acoes/relatorio",
  );
});

test("auditoria: inclusões e mudanças de status da trilha real, com autor e hora", async () => {
  const dados = base([acao("a1", { descricao: "Busca ativa" })]);
  simularApi({
    ...dados,
    "/acoes/a1": {
      ...acao("a1"),
      linha_do_tempo: [
        {
          id: 1,
          em: AGORA,
          autor_nome: "M. Siqueira",
          situacao: "em_andamento",
          texto: "Ação registrada como em andamento.",
        },
        { id: 2, em: AGORA, autor_nome: "M. Lima", situacao: "concluida", texto: "Situação: concluída." },
      ],
    },
  });
  abrir();
  const bloco = await screen.findByRole("region", { name: "Auditoria" });
  expect(await within(bloco).findByText(/M\. Siqueira: “Busca ativa”/)).toBeInTheDocument();
  expect(within(bloco).getByText(/Situação: concluída/)).toBeInTheDocument();
  expect(within(bloco).getByText(/Fonte: registro da equipe/)).toBeInTheDocument();
});

test("sem permissão de edição: não há formulário nem Excluir", async () => {
  simularApi({ ...base(), "/auth/eu": usuarioTeste(["consultar"], ["leitor"]) });
  abrir();
  await screen.findByRole("table", { name: "Ações do evento" });
  expect(screen.queryByRole("form", { name: "Registrar ação" })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: /Excluir a ação/ })).not.toBeInTheDocument();
});
