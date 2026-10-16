import { useMemo, useState, type ReactNode } from "react";
import ReactECharts from "echarts-for-react";
import type { EChartsOption } from "echarts";
import { LegendaFonte, type FonteDado } from "@/design-system/componentes/EstadoDados";
import { Tabela } from "@/design-system/componentes/Tabela";
import { temaClimaSense } from "./tema";
import estilos from "./QuadroGrafico.module.css";

export interface TabelaAlternativa {
  colunas: string[];
  linhas: (string | number | null)[][];
}

export interface QuadroGraficoProps {
  titulo: string;
  /** Uma frase dizendo o que o gráfico mostra (RNF-ACE-09). Também vira a descrição acessível. */
  resumo: string;
  opcao: EChartsOption;
  /** Os mesmos valores do gráfico, para “Ver como tabela”. */
  tabela: TabelaAlternativa;
  fontes: FonteDado[];
  altura?: number;
  extra?: ReactNode;
}

function celula(v: string | number | null): ReactNode {
  if (v === null || v === undefined) return <em>sem dado</em>;
  return typeof v === "number" ? new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 2 }).format(v) : v;
}

export function QuadroGrafico({
  titulo,
  resumo,
  opcao,
  tabela,
  fontes,
  altura = 320,
  extra,
}: QuadroGraficoProps) {
  const [comoTabela, setComoTabela] = useState(false);
  const [texturas, setTexturas] = useState(false);
  const tema = useMemo(() => temaClimaSense(), []);
  const opcaoFinal = useMemo<EChartsOption>(
    () => ({
      ...opcao,
      aria: { enabled: texturas, label: { enabled: false }, decal: { show: texturas } },
    }),
    [opcao, texturas],
  );

  return (
    <section className={estilos.quadro} aria-label={titulo}>
      <h3 className={estilos.titulo}>{titulo}</h3>
      <p className={estilos.resumo}>{resumo}</p>
      {comoTabela ? (
        <Tabela
          legenda={`${titulo} em tabela`}
          legendaVisivel={false}
          colunas={tabela.colunas.map((c, i) => ({
            chave: String(i),
            titulo: c,
            numerica: i > 0,
            celula: (l: (string | number | null)[]) => celula(l[i]),
          }))}
          linhas={tabela.linhas}
          chaveLinha={(l) => String(l[0])}
        />
      ) : (
        <div className={estilos.grafico} role="img" aria-label={`${titulo}. ${resumo}`}>
          <ReactECharts
            option={opcaoFinal}
            theme={tema}
            style={{ height: altura, width: "100%" }}
            notMerge
            opts={{ renderer: "svg" }}
          />
        </div>
      )}
      <LegendaFonte fontes={fontes} />
      <div className={estilos.acoes}>
        <button
          type="button"
          className={estilos.alternar}
          onClick={() => setComoTabela((v) => !v)}
          aria-pressed={comoTabela}
        >
          {comoTabela ? "Ver como gráfico" : "Ver como tabela"}
        </button>
        {!comoTabela && (
          <button
            type="button"
            className={estilos.alternar}
            onClick={() => setTexturas((v) => !v)}
            aria-pressed={texturas}
          >
            {texturas ? "Desligar texturas" : "Usar texturas nas cores"}
          </button>
        )}
        {extra}
      </div>
    </section>
  );
}
