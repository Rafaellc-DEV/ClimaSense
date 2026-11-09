/**
 * Controles acima do mapa (RF-20, RF-22): "Colorir por" e a legenda clicável dos distritos. Cada chip é um botão:
 * clicar escolhe o distrito (o mapa aproxima e esmaece os outros); clicar de novo volta ao Recife inteiro.
 */
import { Undo2 } from "lucide-react";
import { Botao } from "@/design-system/componentes/Botao";
import { Segmentado } from "@/design-system/componentes/Segmentado";
import { corDoDistrito, siglaDoDistrito, nomeDoDistrito } from "@/map/paleta";
import { OPCOES_COLORIR, type Colorir } from "./distritos";
import estilos from "./Mapa.module.css";

export function SeletorColorir({ valor, aoMudar }: { valor: Colorir; aoMudar: (v: Colorir) => void }) {
  return (
    <div className={estilos.colorir}>
      <span aria-hidden="true" className={estilos.colorirLongo}>
        Colorir por
      </span>
      <span aria-hidden="true" className={estilos.colorirCurto}>
        Colorir
      </span>
      <Segmentado rotulo="Colorir por" rotuloOculto opcoes={OPCOES_COLORIR} valor={valor} aoMudar={aoMudar} />
    </div>
  );
}

export function ChipsDistritos({
  ids,
  foco,
  aoEscolher,
  comCor,
}: {
  /** Ids `ds-N` na ordem a mostrar (mais vulnerável primeiro). */
  ids: string[];
  foco: string | null;
  aoEscolher: (id: string) => void;
  /** Só no modo "Distritos" a cor do chip é a cor do distrito no mapa. */
  comCor: boolean;
}) {
  return (
    <div className={estilos.chips} role="group" aria-label="Distritos sanitários">
      <ul>
        {ids.map((id) => {
          const ativo = foco === id;
          return (
            <li key={id}>
              <button
                type="button"
                className={estilos.chip}
                aria-pressed={ativo}
                aria-label={`${siglaDoDistrito(id)}, ${nomeDoDistrito(id)}`}
                data-esmaecido={foco !== null && !ativo}
                title={`${nomeDoDistrito(id)}${ativo ? ": toque de novo para ver o Recife inteiro" : ""}`}
                onClick={() => aoEscolher(id)}
              >
                <i
                  className={estilos.chipCor}
                  style={comCor ? { background: corDoDistrito(id) } : undefined}
                  aria-hidden="true"
                />
                {siglaDoDistrito(id)}
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

export function VoltarRecife({ aoClicar }: { aoClicar: () => void }) {
  return (
    <Botao variante="secundario" icone={<Undo2 />} onClick={aoClicar}>
      Voltar ao Recife inteiro
    </Botao>
  );
}
