import { useMemo, useState, type ReactNode } from "react";
import ReactECharts from "echarts-for-react";
import type { EChartsOption } from "echarts";
import type { FonteDado } from "@/design-system/componentes/EstadoDados";
import { Tabela } from "@/design-system/componentes/Tabela";
import { quandoRelativo } from "@/lib/formatos";
import { temaClimaSense, useTemaAtual } from "./tema";
import estilos from "./QuadroGrafico.module.css";

export interface TabelaAlternativa {
  colunas: string[];
  linhas: (string | number | null)[][];
}

export interface QuadroGraficoProps {
  /** A pergunta que o gráfico responde, em linguagem simples (“Quanto choveu em …?”). */
  titulo: string;
  /** Uma frase dizendo o que o gráfico mostra (RNF-ACE-09). Também vira a descrição acessível. */
  resumo: string;
  opcao: EChartsOption;
  /** Os mesmos valores do gráfico, para “Ver como tabela”. */
  tabela: TabelaAlternativa;
  /** Fonte escrita no pé do gráfico. Omita quando a tela já diz a fonte uma vez, no rodapé. */
  fontes?: FonteDado[];
  altura?: number;
  extra?: ReactNode;
  /** Pílulas curtas ao lado do título: cobertura, série curta, experimental. Cada uma com seu (i). */
  selos?: ReactNode;
  /** Controles do gráfico (legenda de cores, por exemplo), logo abaixo do gráfico. */
  legenda?: ReactNode;
}

function celula(v: string | number | null): ReactNode {
  if (v === null || v === undefined) return <em>sem dado</em>;
  return typeof v === "number" ? new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 2 }).format(v) : v;
}

/** “Fonte: Open-Meteo, atualizada hoje, 14h05.” Escrita, não atrás de um (i): todo gráfico diz de onde e de quando. */
function textoFontes(fontes: FonteDado[]) {
  if (!fontes.length) return "não informada";
  return fontes
    .map((f) => (f.atualizadoEm ? `${f.nome}, atualizada ${quandoRelativo(f.atualizadoEm)}` : f.nome))
    .join("; ");
}

export function QuadroGrafico({
  titulo,
  resumo,
  opcao,
  tabela,
  fontes,
  altura = 320,
  extra,
  selos,
  legenda,
}: QuadroGraficoProps) {
  const [comoTabela, setComoTabela] = useState(false);
  const [texturas, setTexturas] = useState(false);
  const modo = useTemaAtual();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const tema = useMemo(() => temaClimaSense(), [modo]);
  const opcaoFinal = useMemo<EChartsOption>(
    () => ({
      ...opcao,
      aria: { enabled: texturas, label: { enabled: false }, decal: { show: texturas } },
    }),
    [opcao, texturas],
  );

  return (
    <section className={estilos.quadro} aria-label={titulo}>
      <header className={estilos.cabecalho}>
        <div className={estilos.linhaTitulo}>
          <h3 className={estilos.titulo}>{titulo}</h3>
          {selos && <div className={estilos.selos}>{selos}</div>}
        </div>
        <p className={estilos.resumo}>{resumo}</p>
      </header>
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
      {legenda}
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
      {fontes && <p className={estilos.fonte}>Fonte: {textoFontes(fontes)}.</p>}
    </section>
  );
}
