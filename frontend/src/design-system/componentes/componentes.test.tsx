import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Botao } from "./Botao";
import { Campo } from "./Campo";
import { ReguaMare } from "./ReguaMare";
import { SeloNivel } from "./SeloNivel";
import { EstadoDados, LegendaFonte } from "./EstadoDados";
import { Tabela, semDado } from "./Tabela";
import { NIVEIS, type ChaveNivel } from "../niveis";

const TODOS: ChaveNivel[] = ["sem", "informativo", "atencao", "alerta", "critico", "insuficiente"];

describe("Botao", () => {
  test("é um botão com nome acessível e não envia formulário por padrão", async () => {
    const aoClicar = vi.fn();
    render(<Botao onClick={aoClicar}>Enviar para revisão</Botao>);
    const b = screen.getByRole("button", { name: "Enviar para revisão" });
    expect(b).toHaveAttribute("type", "button");
    await userEvent.click(b);
    expect(aoClicar).toHaveBeenCalledOnce();
  });
});

describe("Campo", () => {
  test("rótulo visível ligado ao campo e erro anunciado", () => {
    render(<Campo rotulo="E-mail" ajuda="Use o e-mail cadastrado." erro="Informe um e-mail válido." />);
    const entrada = screen.getByLabelText("E-mail");
    expect(entrada).toHaveAttribute("aria-invalid", "true");
    expect(entrada).toHaveAccessibleDescription("Use o e-mail cadastrado. Informe um e-mail válido.");
    expect(screen.getByRole("alert")).toHaveTextContent("Informe um e-mail válido.");
  });
});

describe("SeloNivel", () => {
  test.each(TODOS)("o nível %s sempre mostra o nome em texto (RN-17)", (nivel) => {
    render(<SeloNivel nivel={nivel} />);
    expect(screen.getByText(NIVEIS[nivel].rotulo)).toBeInTheDocument();
  });

  test("a régua compacta preenche as marcas do nível", () => {
    const { container } = render(<SeloNivel nivel="alerta" />);
    expect(container.querySelectorAll('i[data-cheio="true"]')).toHaveLength(3);
  });
});

describe("ReguaMare", () => {
  test.each(TODOS)("o nível %s aparece em texto na legenda da figura", (nivel) => {
    render(<ReguaMare nivel={nivel} animar={false} />);
    const esperado = nivel === "sem" ? "nenhum" : NIVEIS[nivel].rotulo;
    expect(screen.getByRole("figure")).toHaveTextContent(`Nível do aviso mais alto em vigor: ${esperado}`);
  });

  test("sem animação, o ponteiro já começa no meio do arco do nível", () => {
    render(<ReguaMare nivel="alerta" animar={false} />);
    expect(screen.getByTestId("ponteiro").style.getPropertyValue("--angulo")).toBe("112.5deg");
  });

  test("dados insuficientes não desenham ponteiro (não é nível baixo)", () => {
    render(<ReguaMare nivel="insuficiente" animar={false} />);
    expect(screen.queryByTestId("ponteiro")).toBeNull();
  });
});

describe("Estados dos dados", () => {
  test("dados insuficientes têm estado próprio, sem zero", () => {
    render(<EstadoDados tipo="insuficiente">A estação não envia dados desde ontem.</EstadoDados>);
    const estado = screen.getByRole("status");
    expect(estado).toHaveTextContent("Dados insuficientes");
    expect(estado.textContent).not.toMatch(/\b0\b/);
  });

  test("a legenda da fonte traz o nome e o horário no fuso do Recife (CA-02)", () => {
    render(
      <LegendaFonte
        fontes={[
          { nome: "Dados Abertos do Recife", tipo: "observada", atualizadoEm: "2026-03-02T14:38:37Z" },
        ]}
      />,
    );
    expect(
      screen.getByText(/Fonte: Dados Abertos do Recife, atualizada em 02\/03\/2026, 11h38/),
    ).toBeInTheDocument();
  });
});

describe("Tabela", () => {
  test("valor ausente aparece como 'sem dado', e zero como 0", () => {
    render(
      <Tabela
        legenda="Chuva por distrito"
        colunas={[
          { chave: "n", titulo: "Distrito", celula: (l: { n: string; v: number | null }) => l.n },
          { chave: "v", titulo: "Chuva", numerica: true, celula: (l) => semDado(l.v) },
        ]}
        linhas={[
          { n: "DS IV", v: null },
          { n: "DS V", v: 0 },
        ]}
        chaveLinha={(l) => l.n}
      />,
    );
    expect(screen.getByRole("table", { name: "Chuva por distrito" })).toBeInTheDocument();
    expect(screen.getByRole("row", { name: /DS IV sem dado/ })).toBeInTheDocument();
    expect(screen.getByRole("row", { name: /DS V 0/ })).toBeInTheDocument();
  });
});
