import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { CabecalhoTela } from "./CabecalhoTela";
import { Dica } from "./Dica";
import { CarregandoLista } from "./Esqueleto";
import { Indicador } from "./Indicador";
import { Painel } from "./Painel";
import { Pilula } from "./Pilula";
import { ItemRanking, Ranking } from "./Ranking";
import { Tabela } from "./Tabela";

describe("Dica", () => {
  test("abre ao clicar, fecha com Esc e liga o texto ao botão", async () => {
    render(<Dica texto="Explicação curta" rotulo="Sobre o dado" />);
    const b = screen.getByRole("button", { name: "Sobre o dado" });
    expect(b).toHaveAttribute("aria-expanded", "false");
    expect(b).toHaveAccessibleDescription("Explicação curta");
    await userEvent.click(b);
    expect(b).toHaveAttribute("aria-expanded", "true");
    await userEvent.keyboard("{Escape}");
    expect(b).toHaveAttribute("aria-expanded", "false");
  });
});

describe("CabecalhoTela", () => {
  test("título é o h1, o propósito fica visível logo abaixo, o estado aparece e a aba recebe o nome", () => {
    render(
      <CabecalhoTela
        titulo="Cenários"
        proposito="Simule a chuva."
        estado={<span>3 pedem decisão</span>}
        acoes={<button>Exportar</button>}
      />,
    );
    expect(screen.getByRole("heading", { level: 1, name: "Cenários" })).toBeInTheDocument();
    // sem (i): a frase que explica a tela é lida sem clique
    expect(screen.getByText("Simule a chuva.")).toBeVisible();
    expect(screen.queryByRole("button", { name: "Sobre Cenários" })).not.toBeInTheDocument();
    expect(screen.getByText("3 pedem decisão")).toBeInTheDocument();
    expect(document.title).toBe("Cenários | ClimaSense");
  });
});

describe("Indicador", () => {
  test("mostra rótulo, valor, unidade, nível em texto e a fonte escrita", () => {
    render(
      <Indicador
        rotulo="Chuva em 24 h"
        valor="62,4"
        unidade="mm"
        nivel="alerta"
        tendencia={{ sentido: "sobe", texto: "+18 mm" }}
        fonte={[{ nome: "APAC" }]}
      />,
    );
    // “24 h” com espaço que não quebra: o rótulo nunca deixa o “h” sozinho na linha
    const g = screen.getByRole("group", { name: /^Chuva em 24\sh$/ });
    expect(within(g).getByText("62,4")).toBeInTheDocument();
    expect(within(g).getByText("Alerta")).toBeInTheDocument();
    expect(within(g).getByText(/Sobe:/)).toBeInTheDocument();
    // fonte e hora escritas, não escondidas atrás de um (i)
    expect(within(g).getByText("Fonte: APAC, sem hora de atualização.")).toBeInTheDocument();
  });

  test("valor ausente nunca vira zero (RN-02)", () => {
    render(<Indicador rotulo="Casos" valor={null} />);
    expect(screen.getByText("Sem dado")).toBeInTheDocument();
    expect(screen.queryByText("0")).not.toBeInTheDocument();
  });

  test("insuficiente diz Dados insuficientes", () => {
    render(<Indicador rotulo="Chuva" valor="10" insuficiente />);
    expect(screen.getByText("Dados insuficientes")).toBeInTheDocument();
    expect(screen.queryByText("10")).not.toBeInTheDocument();
  });
});

describe("Pilula", () => {
  test("com nível, escreve o texto recebido", () => {
    render(<Pilula nivel="critico">Situação crítica</Pilula>);
    expect(screen.getByText("Situação crítica").closest("[data-tom]")).toHaveAttribute("data-tom", "critico");
  });
});

describe("Ranking", () => {
  test("lista ordenada com posição, nível, motivos e confiança; excedente vira +n", async () => {
    const abrir = vi.fn();
    render(
      <MemoryRouter>
        <Ranking rotulo="Territórios em atenção">
          <ItemRanking
            posicao={1}
            nome="Afogados"
            nivel="critico"
            motivos={["a", "b", "c", "d"]}
            confianca="alta"
            aoAbrir={abrir}
          />
          <ItemRanking posicao={2} nome="Ibura" nivel="alerta" para="/app/mapa" />
        </Ranking>
      </MemoryRouter>,
    );
    const lista = screen.getByRole("list", { name: "Territórios em atenção" });
    expect(within(lista).getAllByRole("listitem", { name: "" }).length).toBeGreaterThan(1);
    expect(screen.getByText("Situação crítica")).toBeInTheDocument();
    expect(screen.getByText("Confiança alta")).toBeInTheDocument();
    expect(screen.getByText("+1")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /Afogados/ }));
    expect(abrir).toHaveBeenCalledOnce();
    expect(screen.getByRole("link", { name: /Ibura/ })).toHaveAttribute("href", "/app/mapa");
  });
});

describe("Painel, Tabela e esqueletos", () => {
  test("Painel nomeia a região e guarda a dica atrás do (i)", () => {
    render(
      <Painel id="p" titulo="Chuva" dica="Total do período.">
        conteúdo
      </Painel>,
    );
    expect(screen.getByRole("region", { name: /Chuva/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Sobre Chuva" })).toHaveAccessibleDescription(
      "Total do período.",
    );
  });

  test("Tabela mostra a mensagem de vazio e anuncia o carregamento", () => {
    const { rerender } = render(
      <Tabela legenda="L" colunas={[]} linhas={[]} chaveLinha={() => "x"} vazio="Nenhuma avaliação." />,
    );
    expect(screen.getByText("Nenhuma avaliação.")).toBeInTheDocument();
    rerender(<Tabela legenda="L" colunas={[]} linhas={[]} chaveLinha={() => "x"} carregando />);
    expect(screen.getByRole("status")).toHaveTextContent("Carregando…");
  });

  test("CarregandoLista anuncia uma vez", () => {
    render(<CarregandoLista linhas={3} />);
    expect(screen.getAllByRole("status")).toHaveLength(1);
  });
});
