import type { ReactNode } from "react";
import { CarregandoLista } from "@/design-system/componentes/Esqueleto";
import estilos from "./ListaAdaptavel.module.css";

export interface ColunaLista<T> {
  chave: string;
  titulo: string;
  numerica?: boolean;
  /** Fica fora do cartão no celular quando a informação já aparece em outra coluna. */
  soDesktop?: boolean;
  /** Mantém data e hora numa linha só. */
  semQuebra?: boolean;
  /** No cartão do celular a célula aparece sem o rótulo da coluna (ex.: botões de ação). */
  semRotulo?: boolean;
  celula: (linha: T) => ReactNode;
}

/**
 * Tabela que vira lista de cartões no celular (a partir de 720 px): cada célula leva o rótulo da coluna.
 * Continua uma <table> de verdade para leitores de tela; só o desenho muda.
 */
export function ListaAdaptavel<T>({
  legenda,
  colunas,
  linhas,
  chaveLinha,
  carregando,
  vazio,
}: {
  legenda: string;
  colunas: ColunaLista<T>[];
  linhas: T[];
  chaveLinha: (l: T) => string;
  carregando?: boolean;
  vazio?: ReactNode;
}) {
  if (carregando) return <CarregandoLista linhas={4} altura="3.5rem" />;
  if (!linhas.length && vazio) return <>{vazio}</>;
  return (
    <div className={estilos.moldura}>
      <table className={estilos.tabela}>
        <caption className="so-leitor">{legenda}</caption>
        <thead>
          <tr>
            {colunas.map((c) => (
              <th
                key={c.chave}
                scope="col"
                className={[
                  c.numerica && estilos.numero,
                  c.soDesktop && estilos.soDesktop,
                  c.semQuebra && estilos.semQuebra,
                ]
                  .filter(Boolean)
                  .join(" ")}
              >
                {c.titulo}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {linhas.map((l) => (
            <tr key={chaveLinha(l)}>
              {colunas.map((c, i) => {
                const classe = [
                  c.numerica && estilos.numero,
                  c.soDesktop && estilos.soDesktop,
                  c.semQuebra && estilos.semQuebra,
                ]
                  .filter(Boolean)
                  .join(" ");
                return i === 0 ? (
                  <th key={c.chave} scope="row" className={classe}>
                    {c.celula(l)}
                  </th>
                ) : (
                  <td key={c.chave} data-rotulo={c.semRotulo ? undefined : c.titulo} className={classe}>
                    {c.celula(l)}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
