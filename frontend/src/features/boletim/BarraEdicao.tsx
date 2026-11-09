import type { ReactNode } from "react";
import {
  AlignCenter,
  AlignLeft,
  AlignRight,
  Bold,
  Italic,
  List,
  ListOrdered,
  Redo2,
  RemoveFormatting,
  Underline,
  Undo2,
} from "lucide-react";
import estilos from "./Boletim.module.css";

/** Tamanhos do editor: o valor é a escala 1 a 7 do navegador, o rótulo é o tamanho em pontos, como no Word. */
const TAMANHOS = [
  { valor: "2", rotulo: "10" },
  { valor: "3", rotulo: "12" },
  { valor: "4", rotulo: "14" },
  { valor: "5", rotulo: "18" },
  { valor: "6", rotulo: "24" },
];

const CORES = [
  { valor: "#0b1f33", rotulo: "Preto" },
  { valor: "#0d4f8b", rotulo: "Azul" },
  { valor: "#1f7a4d", rotulo: "Verde" },
  { valor: "#b45309", rotulo: "Laranja" },
  { valor: "#b42318", rotulo: "Vermelho" },
];

/** Aplica o comando na seleção da folha em edição. */
function aplicar(comando: string, valor?: string) {
  document.execCommand("styleWithCSS", false, "true");
  document.execCommand(comando, false, valor);
}

function BotaoFormato({
  rotulo,
  comando,
  children,
}: {
  rotulo: string;
  comando: string;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      className={estilos.ferramenta}
      aria-label={rotulo}
      title={rotulo}
      // mousedown sem foco: a seleção do texto continua na folha
      onMouseDown={(e) => e.preventDefault()}
      onClick={() => aplicar(comando)}
    >
      {children}
    </button>
  );
}

/**
 * Barra de formatação do relatório, no alto da folha, como num editor de documentos: desfazer e refazer, tamanho e
 * cor da fonte, negrito, itálico, sublinhado, alinhamento, listas e limpar formatação.
 */
export function BarraEdicao() {
  return (
    <div className={estilos.barraEdicao} role="toolbar" aria-label="Formatação do texto">
      <div className={estilos.grupo}>
        <BotaoFormato rotulo="Desfazer" comando="undo">
          <Undo2 aria-hidden="true" size={18} />
        </BotaoFormato>
        <BotaoFormato rotulo="Refazer" comando="redo">
          <Redo2 aria-hidden="true" size={18} />
        </BotaoFormato>
      </div>
      <div className={estilos.grupo}>
        <label className={estilos.seletor}>
          <span className="so-leitor">Tamanho da fonte</span>
          <select
            defaultValue=""
            aria-label="Tamanho da fonte"
            onChange={(e) => {
              if (e.target.value) aplicar("fontSize", e.target.value);
              e.target.value = "";
            }}
          >
            <option value="" disabled>
              Tamanho
            </option>
            {TAMANHOS.map((t) => (
              <option key={t.valor} value={t.valor}>
                {t.rotulo}
              </option>
            ))}
          </select>
        </label>
        <div className={estilos.cores} role="group" aria-label="Cor da fonte">
          {CORES.map((c) => (
            <button
              key={c.valor}
              type="button"
              className={estilos.cor}
              style={{ background: c.valor }}
              aria-label={`Cor da fonte: ${c.rotulo}`}
              title={c.rotulo}
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => aplicar("foreColor", c.valor)}
            />
          ))}
        </div>
      </div>
      <div className={estilos.grupo}>
        <BotaoFormato rotulo="Negrito" comando="bold">
          <Bold aria-hidden="true" size={18} />
        </BotaoFormato>
        <BotaoFormato rotulo="Itálico" comando="italic">
          <Italic aria-hidden="true" size={18} />
        </BotaoFormato>
        <BotaoFormato rotulo="Sublinhado" comando="underline">
          <Underline aria-hidden="true" size={18} />
        </BotaoFormato>
      </div>
      <div className={estilos.grupo}>
        <BotaoFormato rotulo="Alinhar à esquerda" comando="justifyLeft">
          <AlignLeft aria-hidden="true" size={18} />
        </BotaoFormato>
        <BotaoFormato rotulo="Centralizar" comando="justifyCenter">
          <AlignCenter aria-hidden="true" size={18} />
        </BotaoFormato>
        <BotaoFormato rotulo="Alinhar à direita" comando="justifyRight">
          <AlignRight aria-hidden="true" size={18} />
        </BotaoFormato>
      </div>
      <div className={estilos.grupo}>
        <BotaoFormato rotulo="Lista com marcadores" comando="insertUnorderedList">
          <List aria-hidden="true" size={18} />
        </BotaoFormato>
        <BotaoFormato rotulo="Lista numerada" comando="insertOrderedList">
          <ListOrdered aria-hidden="true" size={18} />
        </BotaoFormato>
        <BotaoFormato rotulo="Limpar formatação" comando="removeFormat">
          <RemoveFormatting aria-hidden="true" size={18} />
        </BotaoFormato>
      </div>
    </div>
  );
}
