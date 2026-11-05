import { useId, type CSSProperties, type ReactNode } from "react";
import { ArrowDownRight, ArrowRight, ArrowUpRight } from "lucide-react";
import { NIVEIS, type ChaveNivel } from "../niveis";
import { quandoRelativo } from "@/lib/formatos";
import { Dica } from "./Dica";
import type { FonteDado } from "./EstadoDados";
import { EsqueletoIndicador } from "./Esqueleto";
import { Pilula } from "./Pilula";
import estilos from "./Indicador.module.css";

export interface TendenciaIndicador {
  sentido: "sobe" | "desce" | "estavel";
  /** Texto curto: "+12% vs. semana anterior". */
  texto: string;
  /** Se subir é ruim (chuva, casos), use "ruim". Só muda o tom do texto; a seta e as palavras dizem o sentido. */
  efeito?: "bom" | "ruim" | "neutro";
}

export interface IndicadorProps {
  /** O que o número mede, em poucas palavras: "Chuva em 24 h". */
  rotulo: string;
  /** O valor já formatado (use `formatarNumero`). `null`/`undefined` mostra "Sem dado", nunca zero (RN-02). */
  valor: ReactNode | null;
  /** "mm", "casos", "%". Fica ao lado do valor, menor. */
  unidade?: string;
  tendencia?: TendenciaIndicador;
  /** Nível de aviso associado: fio colorido no topo e pílula com o nome. */
  nivel?: ChaveNivel;
  /** Explicação de como o número é calculado, atrás do (i). */
  explicacao?: ReactNode;
  /** Origem e hora do dado. Aparece escrita no rodapé do cartão (“Fonte: APAC, hoje, 14h”), nunca escondida. */
  fonte?: FonteDado[];
  /** Selo curto no rodapé: “Amostra”, “Experimental”. Use a `Pilula`. */
  selo?: ReactNode;
  carregando?: boolean;
  /** Sem leitura suficiente: mostra "Dados insuficientes" no lugar do número. */
  insuficiente?: boolean;
  className?: string;
}

const ICONE = { sobe: ArrowUpRight, desce: ArrowDownRight, estavel: ArrowRight };
const PALAVRA = { sobe: "Sobe", desce: "Desce", estavel: "Estável" };

/**
 * Cartão de indicador (KPI): rótulo, valor grande, tendência opcional, nível e, sempre escrita no rodapé, a fonte com
 * a hora. Um dado = um cartão. Só a explicação de como ler o número fica atrás do (i).
 */
export function Indicador({
  rotulo,
  valor,
  unidade,
  tendencia,
  nivel,
  explicacao,
  fonte,
  selo,
  carregando,
  insuficiente,
  className,
}: IndicadorProps) {
  const id = useId();
  if (carregando) return <EsqueletoIndicador />;
  const semDado = insuficiente || valor === null || valor === undefined;
  const Seta = tendencia && ICONE[tendencia.sentido];
  return (
    <div
      role="group"
      aria-labelledby={id}
      className={[estilos.cartao, nivel && estilos.comNivel, className].filter(Boolean).join(" ")}
      style={nivel ? ({ "--cor-nivel": NIVEIS[nivel].cor } as CSSProperties) : undefined}
      data-nivel={nivel}
    >
      <div className={estilos.topo}>
        <p id={id} className={estilos.rotulo}>
          {/* “24 h” e “72 h” nunca quebram no meio */}
          {rotulo.replace(/(\d) (?=(?:h|mm|m)\b)/g, "$1\u00a0")}
        </p>
        {explicacao && (
          <span className={estilos.dicas}>
            <Dica texto={explicacao} rotulo={`Como ler: ${rotulo}`} alinhar="fim" />
          </span>
        )}
      </div>
      {semDado ? (
        <p className={estilos.semDado}>{insuficiente ? "Dados insuficientes" : "Sem dado"}</p>
      ) : (
        <p className={estilos.valor}>
          <span className="numeros">{valor}</span>
          {unidade && <span className={estilos.unidade}>{unidade}</span>}
        </p>
      )}
      {(tendencia || nivel || selo) && (
        <div className={estilos.rodape}>
          {tendencia && Seta && (
            <span className={estilos.tendencia} data-efeito={tendencia.efeito ?? "neutro"}>
              <Seta aria-hidden="true" size={18} />
              <span className="so-leitor">{PALAVRA[tendencia.sentido]}: </span>
              {tendencia.texto}
            </span>
          )}
          {nivel && <Pilula nivel={nivel}>{NIVEIS[nivel].rotulo}</Pilula>}
          {selo}
        </div>
      )}
      {fonte && fonte.length > 0 && <LinhaFonte fontes={fonte} />}
    </div>
  );
}

/** “Fonte: APAC, hoje, 14h05.” Sem hora conhecida, diz isso em vez de calar. */
function LinhaFonte({ fontes }: { fontes: FonteDado[] }) {
  const horas = fontes.map((f) => f.atualizadoEm).filter((h): h is string => !!h);
  const ultima = horas.sort().pop();
  return (
    <p className={estilos.fonte}>
      Fonte: {fontes.map((f) => f.nome).join(", ")}
      {ultima ? `, ${quandoRelativo(ultima)}` : ", sem hora de atualização"}.
    </p>
  );
}
