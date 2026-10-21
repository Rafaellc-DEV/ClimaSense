import { useId } from "react";
import "@fontsource-variable/outfit";
import estilos from "./Marca.module.css";

/**
 * Logo do ClimaSense em uma cor só (currentColor): o símbolo de sempre — sol, nuvem, barras e onda — redesenhado
 * em traço único, e o nome em Outfit fina e em minúsculas. Branco sobre a maré, maré sobre o papel.
 * O tamanho vem de --marca (altura da letra), definido por quem usa.
 */
export function Marca({ className, decorativa = false }: { className?: string; decorativa?: boolean }) {
  const recorte = useId();
  return (
    <span
      className={[estilos.marca, className].filter(Boolean).join(" ")}
      {...(decorativa ? { "aria-hidden": true } : { role: "img", "aria-label": "ClimaSense" })}
    >
      <svg viewBox="0 0 64 64" aria-hidden="true" focusable="false" className={estilos.simbolo}>
        <defs>
          {/* o sol fica atrás da nuvem: um respiro em volta do traço da nuvem separa as duas formas */}
          <mask id={recorte}>
            <rect width="64" height="64" fill="#fff" />
            <path
              d="M14.5 45.5C8.6 45.5 5 41.6 5 36.8c0-4.7 3.6-8.4 8.4-8.6C14.8 20.6 21 15.5 28.3 15.5c6.6 0 12.2 4.2 14.2 10.2 5.4.3 9.5 4.6 9.5 10 0 5.4-4.3 9.8-9.6 9.8"
              fill="#000"
              stroke="#000"
              strokeWidth="10"
            />
          </mask>
        </defs>
        <g mask={`url(#${recorte})`}>
          <g stroke="currentColor" strokeWidth="2.6" strokeLinecap="round">
            <path d="M44 4.5v4M52.6 8l-2.8 2.8M56.5 16.5h-4M36 7.4l1.7 3.6M55 25l-3.4-1.6" />
          </g>
          <circle cx="45" cy="17" r="7.2" fill="currentColor" />
        </g>
        <path
          d="M14.5 45.5C8.6 45.5 5 41.6 5 36.8c0-4.7 3.6-8.4 8.4-8.6C14.8 20.6 21 15.5 28.3 15.5c6.6 0 12.2 4.2 14.2 10.2 5.4.3 9.5 4.6 9.5 10 0 5.4-4.3 9.8-9.6 9.8"
          fill="none"
          stroke="currentColor"
          strokeWidth="4.2"
          strokeLinecap="round"
        />
        <g fill="currentColor">
          <rect x="15" y="37" width="5" height="9" rx="1.5" />
          <rect x="22.5" y="34" width="5" height="12" rx="1.5" />
          <rect x="30" y="30.5" width="5" height="15.5" rx="1.5" />
          <rect x="37.5" y="26.5" width="5" height="19.5" rx="1.5" />
        </g>
        <path
          d="M3 54c9-6 17-3.5 26-1.5 9 2 17 2 29-6.5-7 10-17 13.5-29 11C19 55 11 52.5 3 54Z"
          fill="currentColor"
        />
      </svg>
      <span className={estilos.nome} aria-hidden="true">
        climasense
      </span>
    </span>
  );
}
