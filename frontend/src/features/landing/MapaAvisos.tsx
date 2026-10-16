import type { CSSProperties } from "react";
import tracos from "@/assets/tracos/distritos.json";
import { NIVEIS, type ChaveNivel } from "@/design-system/niveis";
import estilos from "./PaginaInicial.module.css";

interface Props {
  /** distrito → nível do aviso mais alto nele; null = não foi possível verificar */
  niveis: Record<string, string> | null;
}

/**
 * “Onde há aviso agora” (design §8.8): os 8 distritos em traço fino, desenhados das geometrias oficiais.
 * O distrito com aviso ganha a cor do nível, e a lista ao lado diz o mesmo em texto (RN-17). O aviso vale para
 * os bairros citados nele, não para o distrito inteiro (RN-07).
 */
export function MapaAvisos({ niveis }: Props) {
  const nivelDe = (id: string): ChaveNivel | null =>
    ((niveis?.[id] ?? niveis?.recife) as ChaveNivel | undefined) ?? null;
  const algum = niveis && Object.keys(niveis).length > 0;
  return (
    <div className={estilos.mapa}>
      <svg
        viewBox={`0 0 ${tracos.largura} ${tracos.altura}`}
        role="img"
        aria-labelledby="mapa-titulo mapa-desc"
      >
        <title id="mapa-titulo">Mapa dos 8 distritos sanitários do Recife</title>
        <desc id="mapa-desc">
          {algum
            ? `Distritos com aviso: ${tracos.distritos
                .filter((d) => nivelDe(d.id))
                .map((d) => `${d.nome}, ${NIVEIS[nivelDe(d.id)!].rotulo}`)
                .join("; ")}.`
            : "Nenhum distrito com aviso publicado."}
        </desc>
        {tracos.distritos.map((d) => {
          const n = nivelDe(d.id);
          return (
            <g
              key={d.id}
              data-afetado={!!n}
              data-nivel={n ?? undefined}
              style={n ? ({ "--cor-nivel": NIVEIS[n].cor } as CSSProperties) : undefined}
            >
              <path d={d.d} className={estilos.distrito} />
              <text
                x={d.x}
                y={d.y}
                className={estilos.rotuloDistrito}
                textAnchor="middle"
                dominantBaseline="middle"
              >
                {d.rotulo}
              </text>
            </g>
          );
        })}
      </svg>
      <div>
        <ul className={estilos.listaDistritos}>
          {tracos.distritos.map((d) => {
            const n = nivelDe(d.id);
            return (
              <li
                key={d.id}
                data-afetado={!!n}
                style={n ? ({ "--cor-nivel": NIVEIS[n].cor } as CSSProperties) : undefined}
              >
                <span className={estilos.marcador} aria-hidden="true" />
                <span>{d.nome}</span>
                <span className={estilos.situacaoDistrito}>
                  {niveis === null ? "Não verificado" : n ? NIVEIS[n].rotulo : "Sem aviso publicado"}
                </span>
              </li>
            );
          })}
        </ul>
        <p className={estilos.notaMapa}>
          {niveis === null
            ? "Não foi possível verificar os avisos agora."
            : algum
              ? "O aviso vale para os bairros citados nele. Veja a lista de bairros em cada aviso."
              : "Nenhum distrito com aviso publicado."}
        </p>
      </div>
    </div>
  );
}
