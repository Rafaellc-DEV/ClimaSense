import { token } from "@/charts/tema";
import { Dica, DicaFonte } from "@/design-system/componentes/Dica";
import type { FonteDado } from "@/design-system/componentes/EstadoDados";
import { formatarNumero } from "@/lib/formatos";
import type { Escala } from "@/map/model";
import {
  INDICADORES,
  ROTULO_ESTAGIO,
  ROTULO_PRIORIDADE,
  TOKEN_ESTAGIO,
  TOKEN_PRIORIDADE,
  rotuloClasse,
  type ChaveIndicador,
} from "./indicadoresMapa";
import estilos from "./Mapa.module.css";

interface Props {
  indicador: ChaveIndicador;
  escala: Escala;
  temSemDado: boolean;
  mostrarFaixas: boolean;
  fontes: FonteDado[];
  aoAbrirSobre: () => void;
}

/** Legenda fina sobre o mapa: título, faixa de cor com os limites, “Sem dado” e faixas hídricas. */
export function LegendaMapa({ indicador, escala, temSemDado, mostrarFaixas, fontes, aoAbrirSobre }: Props) {
  const info = INDICADORES[indicador];
  const un = info.unidade ? ` ${info.unidade}` : "";
  return (
    <div className={estilos.legenda} aria-label="Legenda do mapa" role="group">
      <div className={estilos.legendaTopo}>
        <h3>{info.rotulo}</h3>
        <Dica
          rotulo="Como interpretar as cores"
          lado="acima"
          texto={
            <>
              {info.ajuda} {info.interpretar}
            </>
          }
        />
        <DicaFonte fontes={fontes} rotulo="Fonte do mapa" />
      </div>
      {indicador === "estagio" ? (
        <ul className={estilos.niveisLegenda}>
          {ROTULO_ESTAGIO.map((r, i) => (
            <li key={r}>
              <i style={{ background: token(TOKEN_ESTAGIO[i]) }} aria-hidden="true" />
              {r}
            </li>
          ))}
        </ul>
      ) : indicador === "prioridade" ? (
        <ul className={estilos.niveisLegenda}>
          {ROTULO_PRIORIDADE.map((r, i) => (
            <li key={r}>
              <i style={{ background: token(TOKEN_PRIORIDADE[i]) }} aria-hidden="true" />
              {r}
            </li>
          ))}
        </ul>
      ) : escala.bins.length > 0 ? (
        <div className={estilos.faixa}>
          <div className={estilos.degrade} aria-hidden="true">
            {escala.bins.map((b, i) => (
              <i key={i} style={{ background: b.color }} />
            ))}
          </div>
          <div className={estilos.limites} aria-hidden="true">
            <span>{formatarNumero(escala.min, info.casas)}</span>
            <span>
              {formatarNumero(escala.max, info.casas)}
              {un}
            </span>
          </div>
          <ul className="so-leitor">
            {escala.bins.map((b, i) => (
              <li key={i}>
                {rotuloClasse(indicador, b.low, b.high, i === escala.bins.length - 1, info.casas)}
                {un}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      <ul className={estilos.extrasLegenda}>
        {temSemDado && (
          <li>
            <i className={estilos.hachura} aria-hidden="true" /> Sem dado
          </li>
        )}
        {mostrarFaixas && (
          <li>
            <i className={estilos.agua} aria-hidden="true" /> Faixas hídricas
          </li>
        )}
        <li>
          <button type="button" className={estilos.linkSobre} onClick={aoAbrirSobre}>
            Sobre os dados
          </button>
        </li>
      </ul>
    </div>
  );
}
