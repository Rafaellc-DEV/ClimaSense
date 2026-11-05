import estilos from "./Onda.module.css";

/**
 * Linha d’água entre o herói (ou o conteúdo) e a próxima seção. Desenho estático (SVG puro, sem animação).
 */
export function Onda({
  cor,
  linha = false,
  alto = false,
}: {
  /** cor do que fica depois da onda (a seção seguinte) */
  cor: string;
  /** linha fina clara por cima, como a maré que acabou de baixar (sobre o azul) */
  linha?: boolean;
  /** fica acima do elemento pai (a onda que sobe da página para o rodapé azul) em vez de dentro dele */
  alto?: boolean;
}) {
  return (
    <div className={estilos.onda} data-alto={alto || undefined} aria-hidden="true">
      <svg viewBox="0 0 2880 120" preserveAspectRatio="none" focusable="false">
        {linha && (
          <path
            d="M0,44 C240,4 480,84 720,44 S1200,4 1440,44 S1920,84 2160,44 S2640,4 2880,44"
            fill="none"
            stroke="rgba(255,255,255,0.7)"
            strokeWidth="2"
            vectorEffect="non-scaling-stroke"
          />
        )}
        <path
          d="M0,66 C240,26 480,106 720,66 S1200,26 1440,66 S1920,106 2160,66 S2640,26 2880,66 V121 H0 Z"
          fill={cor}
        />
      </svg>
    </div>
  );
}
