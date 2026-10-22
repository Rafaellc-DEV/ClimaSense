import { useEffect, useLayoutEffect, useRef, useState, type CSSProperties } from "react";
import { ESCALA_REGUA, NIVEIS, type ChaveNivel } from "../niveis";
import estilos from "./ReguaMare.module.css";

export interface ReguaMareProps {
  nivel: ChaveNivel;
  compacta?: boolean;
  /** Anima o ponteiro uma vez ao montar (único movimento da landing — design §8.7). */
  animar?: boolean;
  /** Enquanto a situação é consultada: medidor neutro, sem afirmar nível nem "dados insuficientes". */
  carregando?: boolean;
  /** "medidor": meia-volta com ponteiro; "faixa": faixa horizontal com marcador "Agora" (telas estreitas). */
  formato?: "medidor" | "faixa";
}

/* Medidor de meia-volta, num viewBox de 280 × 160 com centro em (140, 140): cada nível ocupa 45° do arco,
   da esquerda (Fique atento) para a direita (Situação crítica). O ponteiro para no meio do arco do nível. */
const CX = 140;
const CY = 140;
const RAIO = 104;
const REPOUSO = 3;

const ponto = (graus: number, r = RAIO) => {
  const rad = (graus * Math.PI) / 180;
  return [CX - r * Math.cos(rad), CY - r * Math.sin(rad)].map((v) => v.toFixed(1));
};
const ARCOS = ESCALA_REGUA.map((_, i) => {
  const [x1, y1] = ponto(i * 45 + 1.5);
  const [x2, y2] = ponto((i + 1) * 45 - 1.5);
  return `M${x1} ${y1}A${RAIO} ${RAIO} 0 0 1 ${x2} ${y2}`;
});
const NUMERAIS = ESCALA_REGUA.map((_, i) => ponto(i * 45 + 22.5, RAIO + 26));

const anguloDe = (marcas: number) => (marcas ? (marcas - 0.5) * 45 : REPOUSO);
/** Na faixa, o marcador fica no meio do segmento do nível (cada um ocupa 25% da largura). */
const posicaoDe = (marcas: number) => (marcas ? (marcas - 0.5) * 25 : 0);

const semMovimento = () =>
  typeof matchMedia === "function" && matchMedia("(prefers-reduced-motion: reduce)").matches;

export function ReguaMare({
  nivel,
  compacta,
  animar = true,
  carregando,
  formato = "medidor",
}: ReguaMareProps) {
  const n = NIVEIS[nivel];
  const marcas = carregando ? 0 : n.marcas;
  // quantas marcas o ponteiro mostra agora: começa em 0 e sobe até o nível no quadro seguinte (animação)
  const [exibido, setExibido] = useState(() => (animar && !semMovimento() ? 0 : marcas));
  // de onde o ponteiro parte quando a busca termina: a posição em que a varredura estava (sem salto)
  const [partida, setPartida] = useState<string | null>(null);
  const movel = useRef<HTMLElement | SVGGElement | null>(null);

  // carregando, o ponteiro (ou o marcador da faixa) varre a escala, ida e volta
  useLayoutEffect(() => {
    const el = movel.current;
    if (!carregando || !el || semMovimento() || typeof el.animate !== "function") return;
    const quadros =
      formato === "faixa"
        ? [{ transform: "translateX(12.5%)" }, { transform: "translateX(87.5%)" }]
        : [{ transform: `rotate(${REPOUSO}deg)` }, { transform: `rotate(${180 - REPOUSO}deg)` }];
    const varredura = el.animate(quadros, {
      duration: 1200,
      iterations: Infinity,
      direction: "alternate",
      easing: "ease-in-out",
    });
    return () => {
      // a busca terminou: congela o ponteiro onde a varredura estava e deixa a transição levá-lo ao nível
      let ponto: string | null = null;
      try {
        const m = new DOMMatrixReadOnly(getComputedStyle(el).transform);
        ponto =
          formato === "faixa"
            ? `${(m.e / Math.max(1, (el as HTMLElement).offsetWidth)) * 100}%`
            : `${(Math.atan2(m.b, m.a) * 180) / Math.PI}deg`;
      } catch {
        // sem matriz legível (elemento já fora da página): segue sem ponto de partida
      }
      varredura.cancel();
      if (ponto) {
        el.style.transition = "none";
        setPartida(ponto);
      }
    };
  }, [carregando, formato]);

  useEffect(() => {
    const quadro = requestAnimationFrame(() => {
      if (movel.current) movel.current.style.transition = "";
      setPartida(null);
      setExibido(marcas);
    });
    return () => cancelAnimationFrame(quadro);
  }, [marcas, carregando]);

  const semDados = !carregando && nivel === "insuficiente";
  const temAviso = !carregando && nivel !== "sem" && nivel !== "insuficiente";
  // "nenhum" minúsculo continua a frase da legenda; o CSS capitaliza a manchete
  const descricao = nivel === "sem" ? "nenhum aviso ativo" : n.rotulo;
  const classes = [
    estilos.regua,
    compacta && estilos.compacta,
    formato === "faixa" && estilos.emFaixa,
    carregando && estilos.carregando,
    semDados && estilos.insuficiente,
  ];

  return (
    <figure
      className={classes.filter(Boolean).join(" ")}
      data-nivel={nivel}
      aria-busy={carregando || undefined}
    >
      <figcaption className={estilos.titulo}>
        {carregando ? (
          <>
            Nível do aviso mais alto em vigor: <strong key="verificando">verificando…</strong>
          </>
        ) : (
          <>
            Nível do aviso mais alto em vigor: <strong key={descricao}>{descricao}</strong>
            {temAviso && <span className="so-leitor"> (nível {n.marcas} de 4)</span>}
          </>
        )}
      </figcaption>
      {!compacta && !carregando && formato === "medidor" && n.acao && (
        <p className={estilos.acao}>{n.acao}</p>
      )}

      {formato === "faixa" ? (
        <div className={estilos.faixa} aria-hidden="true">
          <div className={estilos.trilho}>
            {/* carregando, o marcador corre a faixa de ponta a ponta; com aviso, para no nível */}
            {(temAviso || carregando) && (
              <div
                ref={(el) => {
                  movel.current = el;
                }}
                className={estilos.cursor}
                data-testid="ponteiro"
                style={{ "--posicao": partida ?? `${posicaoDe(exibido)}%` } as CSSProperties}
              >
                <span className={estilos.pino}>{carregando ? "Buscando" : "Agora"}</span>
              </div>
            )}
            {ESCALA_REGUA.map((chave) => (
              <i
                key={chave}
                className={estilos.segmento}
                data-cheio={!semDados && NIVEIS[chave].marcas <= marcas}
                style={{ "--cor": NIVEIS[chave].cor } as CSSProperties}
              />
            ))}
          </div>
          <ol className={estilos.rotulos}>
            {ESCALA_REGUA.map((chave) => (
              <li key={chave} data-ativo={temAviso && chave === nivel}>
                <b>{NIVEIS[chave].marcas}</b>
                {NIVEIS[chave].rotulo}
              </li>
            ))}
          </ol>
        </div>
      ) : (
        <div className={estilos.medidor} aria-hidden="true">
          <svg viewBox="0 0 280 160" focusable="false" aria-hidden="true">
            {ESCALA_REGUA.map((chave, i) => (
              <path
                key={chave}
                d={ARCOS[i]}
                className={estilos.arco}
                data-cheio={!semDados && NIVEIS[chave].marcas <= marcas}
                style={{ "--cor": NIVEIS[chave].cor } as CSSProperties}
              />
            ))}
            {ESCALA_REGUA.map((chave, i) => (
              <text
                key={chave}
                x={NUMERAIS[i][0]}
                y={Number(NUMERAIS[i][1]) + 5}
                className={estilos.numeral}
                data-ativo={temAviso && chave === nivel}
              >
                {NIVEIS[chave].marcas}
              </text>
            ))}
            {semDados ? (
              <text x={CX} y={CY + 10} className={estilos.interrogacao}>
                ?
              </text>
            ) : (
              <>
                {/* carregando, o ponteiro varre a escala de ponta a ponta, como quem procura a medida */}
                <g
                  ref={(el) => {
                    movel.current = el;
                  }}
                  className={estilos.ponteiro}
                  data-testid="ponteiro"
                  style={{ "--angulo": partida ?? `${anguloDe(exibido)}deg` } as CSSProperties}
                >
                  <path d={`M${CX} ${CY - 6}L${CX - 84} ${CY}L${CX} ${CY + 6}Z`} />
                </g>
                <circle cx={CX} cy={CY} r="12" className={estilos.eixo} />
                <circle cx={CX} cy={CY} r="4" className={estilos.eixoMiolo} />
              </>
            )}
          </svg>
          <div className={estilos.extremos}>
            <span>{NIVEIS[ESCALA_REGUA[0]].rotulo}</span>
            <span>{NIVEIS[ESCALA_REGUA[ESCALA_REGUA.length - 1]].rotulo}</span>
          </div>
        </div>
      )}
    </figure>
  );
}
