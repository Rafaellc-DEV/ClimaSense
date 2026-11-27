import { Component, useMemo, useState, type CSSProperties, type ReactNode } from "react";
import ReactECharts from "echarts-for-react";
import type { EChartsOption } from "echarts";
import { FlaskConical, Inbox, Table2 } from "lucide-react";
import { temaClimaSense, useTemaAtual } from "@/charts/tema";
import { Esqueleto } from "@/design-system/componentes/Esqueleto";
import { EstadoDados } from "@/design-system/componentes/EstadoDados";
import { Pilula, type TomPilula } from "@/design-system/componentes/Pilula";
import { Tabela } from "@/design-system/componentes/Tabela";
import { EstadoConsulta } from "@/features/evento/Evento";
import { formatarNumero } from "@/lib/formatos";
import type { TabelaGrafico } from "./graficos";
import estilos from "./Painel.module.css";

/** Frasco pequeno: previsão ou estágio sugerido ainda sem validação (RN-11). O texto fica para o leitor de tela e na dica. */
export function SeloExp() {
  return (
    <span
      className={estilos.exp}
      title="Experimental: usa previsão ou estágio sugerido, ainda sem validação."
    >
      <FlaskConical aria-hidden="true" size={14} />
      <span className="so-leitor">Experimental</span>
    </span>
  );
}

/** Cartão sem nada a mostrar agora (com dado, mas nada acima do limite): frase curta no meio do espaço. */
export function Vazio({ children }: { children: ReactNode }) {
  return (
    <p className={estilos.vazioCartao}>
      <Inbox aria-hidden="true" size={28} />
      <span>{children}</span>
    </p>
  );
}

/** Se um gráfico falhar ao desenhar, só ele cai: o cartão avisa e o resto da página continua. */
class GraficoSeguro extends Component<
  { chave: unknown; children: ReactNode },
  { falhou: boolean; chave: unknown }
> {
  state = { falhou: false, chave: this.props.chave };
  static getDerivedStateFromError() {
    return { falhou: true };
  }
  static getDerivedStateFromProps(props: { chave: unknown }, estado: { falhou: boolean; chave: unknown }) {
    return props.chave !== estado.chave ? { falhou: false, chave: props.chave } : null;
  }
  render() {
    if (this.state.falhou)
      return (
        <p className={estilos.vazioCartao} role="status">
          <Inbox aria-hidden="true" size={28} />
          <span>Não foi possível desenhar este gráfico. Os mesmos números estão em “Ver como tabela”.</span>
        </p>
      );
    return this.props.children;
  }
}

/**
 * Gráfico ECharts que preenche o espaço do cartão. O texto de `resumo` é a descrição para o leitor de tela.
 * `opcao` nulo = a montagem do gráfico falhou: mostra o aviso no lugar.
 */
export function GraficoPainel({
  opcao,
  rotulo,
  resumo,
}: {
  opcao: EChartsOption | null;
  rotulo: string;
  resumo: string;
}) {
  const modo = useTemaAtual();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const tema = useMemo(() => temaClimaSense(), [modo]);
  if (!opcao)
    return (
      <p className={estilos.vazioCartao} role="status">
        <Inbox aria-hidden="true" size={28} />
        <span>Não foi possível desenhar este gráfico. Os mesmos números estão em “Ver como tabela”.</span>
      </p>
    );
  return (
    <div className={estilos.grafico} role="img" aria-label={`${rotulo}. ${resumo}`}>
      <GraficoSeguro chave={JSON.stringify(resumo)}>
        <ReactECharts
          option={opcao}
          theme={tema}
          style={{ height: "100%", width: "100%" }}
          notMerge
          opts={{ renderer: "svg" }}
        />
      </GraficoSeguro>
    </div>
  );
}

interface Carga {
  isPending: boolean;
  isError: boolean;
  error: Error | null;
  refetch: () => unknown;
}

/**
 * Cartão do painel: título em forma de pergunta, a resposta em uma pílula curta, o conteúdo e uma linha de fonte e hora
 * (RF-19). Com `tabela`, um botão troca o gráfico pelos mesmos valores em tabela (RNF-ACE-09). Carregando, falha e
 * "Dados insuficientes" são tratados aqui, para nenhum cartão ficar vazio ou mostrar zero no lugar de falta (RN-01).
 */
export function CartaoPainel({
  id,
  titulo,
  resposta,
  experimental,
  acao,
  esmaecido,
  carga,
  oQue,
  insuficiente,
  tabela,
  rodape,
  alturaMin = 200,
  livre,
  children,
}: {
  id: string;
  titulo: string;
  /** A resposta curta ao título: "Maior: Distrito 3, 0,2 mm". */
  resposta?: { texto: string; tom: TomPilula } | null;
  experimental?: boolean;
  /** Controle pequeno à direita do título, como "Ver no Mapa ›". */
  acao?: ReactNode;
  /** O filtro "Foco" destaca outros cartões: este fica mais claro, sem sair da tela. */
  esmaecido?: boolean;
  carga?: Carga;
  /** "a chuva medida": completa "O servidor ainda não oferece …" e "Não foi possível carregar …". */
  oQue?: string;
  /** O que falta (fonte). Se vier, o cartão mostra "Dados insuficientes" no lugar do conteúdo. */
  insuficiente?: string | null;
  tabela?: TabelaGrafico;
  rodape: ReactNode;
  /** Altura mínima da área do gráfico, em px (nunca abaixo de 180). */
  alturaMin?: number;
  /** Conteúdo de lista: a altura vem do conteúdo. */
  livre?: boolean;
  children: ReactNode;
}) {
  const [comoTabela, setComoTabela] = useState(false);
  let corpo: ReactNode;
  if (carga?.isPending)
    corpo = (
      <div role="status" aria-busy="true" className={estilos.esqueleto}>
        <Esqueleto altura="100%" forma="bloco" />
        <span className="so-leitor">Carregando {oQue ?? titulo}…</span>
      </div>
    );
  else if (carga?.isError)
    corpo = <EstadoConsulta erro={carga.error} oQue={oQue ?? titulo} aoTentar={() => carga.refetch()} />;
  else if (insuficiente) corpo = <EstadoDados tipo="insuficiente">Falta: {insuficiente}.</EstadoDados>;
  else if (comoTabela && tabela)
    corpo = (
      <Tabela
        legenda={`${titulo} em tabela`}
        legendaVisivel={false}
        densidade="compacta"
        colunas={tabela.colunas.map((c, i) => ({
          chave: String(i),
          titulo: c,
          numerica: i > 0,
          celula: (l: (string | number | null)[]) =>
            l[i] === null ? (
              <em>sem dado</em>
            ) : typeof l[i] === "number" ? (
              formatarNumero(l[i] as number, 1)
            ) : (
              l[i]
            ),
        }))}
        linhas={tabela.linhas}
        chaveLinha={(l) => String(l[0])}
      />
    );
  else corpo = children;
  return (
    <section
      className={estilos.cartao}
      aria-labelledby={id}
      data-esmaecido={esmaecido ? "true" : undefined}
      style={{ "--altura-min": `${livre ? 0 : Math.max(alturaMin, 180)}px` } as CSSProperties}
    >
      <div className={estilos.cartaoTopo}>
        <h2 id={id}>{titulo}</h2>
        {resposta && !carga?.isPending && !insuficiente && (
          <Pilula tom={resposta.tom} pequena semMarca>
            {resposta.texto}
          </Pilula>
        )}
        {experimental && <SeloExp />}
        {acao}
        {tabela && !carga?.isPending && !insuficiente && (
          <button
            type="button"
            className={estilos.tabelaBotao}
            aria-pressed={comoTabela}
            aria-label={comoTabela ? `Ver ${titulo} como gráfico` : `Ver ${titulo} como tabela`}
            title={comoTabela ? "Ver como gráfico" : "Ver como tabela"}
            onClick={() => setComoTabela((v) => !v)}
          >
            <Table2 aria-hidden="true" size={18} />
          </button>
        )}
      </div>
      <div className={estilos.corpo}>{corpo}</div>
      <p className={estilos.rodape}>{rodape}</p>
    </section>
  );
}
