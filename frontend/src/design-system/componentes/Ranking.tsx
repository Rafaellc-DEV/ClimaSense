import type { CSSProperties, ReactNode } from "react";
import { ChevronRight } from "lucide-react";
import { Link, type To } from "react-router-dom";
import { NIVEIS, type ChaveNivel } from "../niveis";
import { Dica } from "./Dica";
import { Pilula } from "./Pilula";
import estilos from "./Ranking.module.css";

export type Confianca = "alta" | "media" | "baixa" | "insuficiente";
const CONF: Record<Confianca, { n: number; rotulo: string }> = {
  alta: { n: 3, rotulo: "Confiança alta" },
  media: { n: 2, rotulo: "Confiança média" },
  baixa: { n: 1, rotulo: "Confiança baixa" },
  insuficiente: { n: 0, rotulo: "Confiança insuficiente" },
};

export interface ItemRankingProps {
  /** Posição na fila de atenção (1 = olhar primeiro). */
  posicao: number;
  nome: string;
  /** Linha de contexto curta: “Distrito Sanitário 5”. */
  contexto?: string;
  nivel: ChaveNivel;
  /** Por que está na fila: até 3 chips curtos (“chuva 62 mm”, “maré alta”). Os demais viram “+n”. */
  motivos?: string[];
  /** Confiança da leitura. Omita quando não se aplica; nunca invente. */
  confianca?: Confianca;
  /** Explicação da confiança, atrás do (i). */
  explicacaoConfianca?: ReactNode;
  /** Torna o item um link para o detalhe. */
  para?: To;
  /** Alternativa ao link: torna o item um botão. */
  aoAbrir?: () => void;
  /** Item escolhido numa lista mestre-detalhe (Cenários): realce, `aria-pressed` no botão e `aria-current` no link. */
  selecionado?: boolean;
}

/** Linha de “territórios em atenção”: posição, nome, nível, motivos e confiança, sempre no mesmo lugar. */
export function ItemRanking({
  posicao,
  nome,
  contexto,
  nivel,
  motivos = [],
  confianca,
  explicacaoConfianca,
  para,
  aoAbrir,
  selecionado,
}: ItemRankingProps) {
  const visiveis = motivos.slice(0, 3);
  const resto = motivos.length - visiveis.length;
  const conteudoNome = (
    <>
      <span className={estilos.nome}>{nome}</span>
      {contexto && <span className={estilos.contexto}>{contexto}</span>}
    </>
  );
  return (
    <li
      className={estilos.item}
      style={{ "--cor-nivel": NIVEIS[nivel].cor } as CSSProperties}
      data-nivel={nivel}
      data-selecionado={selecionado ? "true" : undefined}
    >
      <span className={estilos.posicao} aria-hidden="true">
        {posicao}
      </span>
      <div className={estilos.identidade}>
        {para ? (
          <Link to={para} className={estilos.alvo} aria-current={selecionado ? "true" : undefined}>
            {conteudoNome}
          </Link>
        ) : aoAbrir ? (
          <button
            type="button"
            className={estilos.alvo}
            onClick={aoAbrir}
            aria-pressed={selecionado === undefined ? undefined : selecionado}
          >
            {conteudoNome}
          </button>
        ) : (
          <span className={estilos.alvo}>{conteudoNome}</span>
        )}
      </div>
      <div className={estilos.nivel}>
        <Pilula nivel={nivel}>{NIVEIS[nivel].rotulo}</Pilula>
        {(para || aoAbrir) && <ChevronRight aria-hidden="true" size={20} className={estilos.seta} />}
      </div>
      {visiveis.length > 0 && (
        <ul className={estilos.motivos} aria-label="Motivos">
          {visiveis.map((m) => (
            <li key={m}>
              <Pilula pequena semMarca>
                {m}
              </Pilula>
            </li>
          ))}
          {resto > 0 && (
            <li>
              <Pilula pequena semMarca>
                +{resto}
              </Pilula>
            </li>
          )}
        </ul>
      )}
      {confianca && (
        <span className={estilos.confianca}>
          <span className={estilos.barras} aria-hidden="true">
            {[1, 2, 3].map((i) => (
              <i key={i} data-cheio={i <= CONF[confianca].n} />
            ))}
          </span>
          {CONF[confianca].rotulo}
          {explicacaoConfianca && (
            <Dica texto={explicacaoConfianca} rotulo="Como a confiança é calculada" alinhar="fim" />
          )}
        </span>
      )}
    </li>
  );
}

/** Lista ordenada de `ItemRanking`. O rótulo nomeia a lista para leitores de tela. */
export function Ranking({
  rotulo,
  children,
  compacto,
}: {
  rotulo: string;
  children: ReactNode;
  /** Layout empilhado também em tela larga: para colunas estreitas (lista ao lado de um detalhe). */
  compacto?: boolean;
}) {
  return (
    <ol
      className={[estilos.lista, compacto && estilos.compacto].filter(Boolean).join(" ")}
      aria-label={rotulo}
    >
      {children}
    </ol>
  );
}
