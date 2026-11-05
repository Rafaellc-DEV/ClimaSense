import type { ReactNode } from "react";
import { ChartLine, CloudRainWind, Database, ExternalLink, Map, X } from "lucide-react";
import { Botao } from "@/design-system/componentes/Botao";
import { Dica } from "@/design-system/componentes/Dica";
import { formatarDataHora } from "@/lib/formatos";
import estilos from "./Evidencias.module.css";

export interface EvidenciaForm {
  tipo: string;
  descricao: string;
  fonte_id: string;
  capturada_em: string;
  valor?: string | null;
  endereco?: string | null;
}

const TIPOS: Record<string, { rotulo: string; icone: ReactNode }> = {
  mapa: { rotulo: "Mapa", icone: <Map /> },
  serie: { rotulo: "Série", icone: <ChartLine /> },
  cenario: { rotulo: "Cenário", icone: <CloudRainWind /> },
  fonte: { rotulo: "Fonte", icone: <Database /> },
};

/** Evidências vinculadas: cada uma aponta para uma fonte real e diz quando foi capturada (RN-19). */
export function ListaEvidencias({
  evidencias,
  aoRemover,
}: {
  evidencias: EvidenciaForm[];
  aoRemover?: (i: number) => void;
}) {
  if (!evidencias.length)
    return (
      <p className={estilos.vazia}>
        Nenhuma evidência vinculada.
        <Dica
          texto="Use “Registrar avaliação” no mapa ou “Encaminhar para avaliação” nos cenários para trazer valores com fonte e horário."
          rotulo="Como vincular evidências"
        />
      </p>
    );
  return (
    <ul className={estilos.lista}>
      {evidencias.map((e, i) => {
        const t = TIPOS[e.tipo] ?? TIPOS.fonte;
        return (
          <li key={i} className={estilos.cartao}>
            <span className={estilos.disco} aria-hidden="true">
              {t.icone}
            </span>
            <div className={estilos.corpo}>
              <p className={estilos.tipo}>{t.rotulo}</p>
              <p className={estilos.descricao}>{e.descricao}</p>
              {e.valor && <p className={estilos.valor}>{e.valor}</p>}
              <p className={estilos.meta}>
                <span>Fonte {e.fonte_id}</span>
                <span>Capturada em {formatarDataHora(e.capturada_em)}</span>
              </p>
              {e.endereco && (
                <a className={estilos.abrir} href={e.endereco} target="_blank" rel="noreferrer">
                  Abrir o recorte
                  <ExternalLink aria-hidden="true" size={16} />
                </a>
              )}
            </div>
            {aoRemover && (
              <Botao variante="discreto" icone={<X />} onClick={() => aoRemover(i)}>
                Remover<span className="so-leitor"> evidência {i + 1}</span>
              </Botao>
            )}
          </li>
        );
      })}
    </ul>
  );
}
