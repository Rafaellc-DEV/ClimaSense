import type { ReactNode } from "react";
import estilos from "./Tabela.module.css";

export interface ColunaTabela<T> {
  chave: string;
  titulo: string;
  numerica?: boolean;
  celula: (linha: T) => ReactNode;
}

export interface TabelaProps<T> {
  /** Legenda obrigatória: diz do que a tabela trata (acessibilidade). */
  legenda: string;
  legendaVisivel?: boolean;
  colunas: ColunaTabela<T>[];
  linhas: T[];
  chaveLinha: (linha: T) => string;
}

/** Valor ausente nunca aparece como zero (RN-02). */
export function semDado(
  valor: number | null | undefined,
  formatar: (v: number) => string = String,
): ReactNode {
  return valor === null || valor === undefined ? (
    <span className={estilos.vazio}>sem dado</span>
  ) : (
    formatar(valor)
  );
}

export function Tabela<T>({ legenda, legendaVisivel = true, colunas, linhas, chaveLinha }: TabelaProps<T>) {
  return (
    <div className={estilos.moldura}>
      <table className={estilos.tabela}>
        <caption className={legendaVisivel ? estilos.legenda : "so-leitor"}>{legenda}</caption>
        <thead>
          <tr>
            {colunas.map((c) => (
              <th key={c.chave} scope="col" className={c.numerica ? estilos.numero : undefined}>
                {c.titulo}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {linhas.map((l) => (
            <tr key={chaveLinha(l)}>
              {colunas.map((c, i) =>
                i === 0 ? (
                  <th key={c.chave} scope="row" className={c.numerica ? estilos.numero : undefined}>
                    {c.celula(l)}
                  </th>
                ) : (
                  <td key={c.chave} className={c.numerica ? estilos.numero : undefined}>
                    {c.celula(l)}
                  </td>
                ),
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
