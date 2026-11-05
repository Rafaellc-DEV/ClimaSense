import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { classesBotao } from "./Botao";
import { FaixaMare } from "./FaixaMare";
import { Indicador } from "./Indicador";
import { Experimental } from "./Pilula";
import { ItemRanking, Ranking } from "./Ranking";
import { Segmentado } from "./Segmentado";

test("Segmentado: rádios nativos, uma opção marcada e troca por clique", async () => {
  const aoMudar = vi.fn();
  render(
    <Segmentado
      rotulo="Horizonte"
      opcoes={[
        { valor: 24, rotulo: "24 h" },
        { valor: 72, rotulo: "72 h" },
      ]}
      valor={72}
      aoMudar={aoMudar}
    />,
  );
  expect(screen.getByRole("group", { name: "Horizonte" })).toBeInTheDocument();
  expect(screen.getByRole("radio", { name: "72 h" })).toBeChecked();
  await userEvent.click(screen.getByRole("radio", { name: "24 h" }));
  expect(aoMudar).toHaveBeenCalledWith(24);
});

test("FaixaMare nomeia a região pelo título e guarda o conteúdo", () => {
  render(
    <FaixaMare titulo="Situação agora" id="f">
      <p>Conteúdo</p>
    </FaixaMare>,
  );
  expect(screen.getByRole("region", { name: "Situação agora" })).toHaveTextContent("Conteúdo");
});

test("Experimental escreve a palavra; Botao ganha variantes para fundo azul", () => {
  render(<Experimental />);
  expect(screen.getByText("Experimental")).toBeInTheDocument();
  expect(classesBotao("claro")).toContain("claro");
  expect(classesBotao("contornoClaro")).toContain("contornoClaro");
});

test("Indicador mostra o selo no rodapé e mantém Sem dado", () => {
  render(<Indicador rotulo="Desabrigados" valor={null} selo={<span>Amostra</span>} />);
  expect(screen.getByText("Sem dado")).toBeInTheDocument();
  expect(screen.getByText("Amostra")).toBeInTheDocument();
});

test("ItemRanking selecionado marca aria-pressed e aceita confiança insuficiente", () => {
  render(
    <MemoryRouter>
      <Ranking rotulo="Fila" compacto>
        <ItemRanking
          posicao={1}
          nome="DS 3"
          nivel="alerta"
          confianca="insuficiente"
          selecionado
          aoAbrir={() => {}}
        />
        <ItemRanking posicao={2} nome="DS 5" nivel="atencao" selecionado={false} aoAbrir={() => {}} />
      </Ranking>
    </MemoryRouter>,
  );
  expect(screen.getByRole("button", { name: /DS 3/ })).toHaveAttribute("aria-pressed", "true");
  expect(screen.getByRole("button", { name: /DS 5/ })).toHaveAttribute("aria-pressed", "false");
  expect(screen.getByText("Confiança insuficiente")).toBeInTheDocument();
});
