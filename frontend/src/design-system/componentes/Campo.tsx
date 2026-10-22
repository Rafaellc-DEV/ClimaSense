import {
  useId,
  useState,
  type InputHTMLAttributes,
  type ReactNode,
  type TextareaHTMLAttributes,
} from "react";
import { CircleAlert, Info } from "lucide-react";
import estilos from "./Campo.module.css";

interface Base {
  rotulo: string;
  ajuda?: ReactNode;
  /** Explicação curta atrás de um ícone (i) ao lado do rótulo: aparece ao passar o mouse, tocar ou focar. */
  dica?: string;
  erro?: string;
}

function useIds(id?: string) {
  const gerado = useId();
  const base = id ?? gerado;
  return { campo: base, ajuda: `${base}-ajuda`, erro: `${base}-erro`, dica: `${base}-dica` };
}

/** Rótulo do campo, com o ícone de informação quando há dica. */
function Rotulo({ ids, rotulo, dica }: { ids: ReturnType<typeof useIds>; rotulo: string; dica?: string }) {
  const [aberta, setAberta] = useState(false);
  if (!dica)
    return (
      <label htmlFor={ids.campo} className={estilos.rotulo}>
        {rotulo}
      </label>
    );
  return (
    <div className={estilos.rotuloComDica}>
      <label htmlFor={ids.campo} className={estilos.rotulo}>
        {rotulo}
      </label>
      <span className={estilos.dica} data-aberta={aberta}>
        <button
          type="button"
          className={estilos.dicaBotao}
          aria-label="Mais informações"
          aria-expanded={aberta}
          onClick={() => setAberta((a) => !a)}
          onBlur={() => setAberta(false)}
          onKeyDown={(e) => e.key === "Escape" && setAberta(false)}
        >
          <Info aria-hidden="true" size={16} />
        </button>
        <span id={ids.dica} role="tooltip" className={estilos.dicaTexto}>
          {dica}
        </span>
      </span>
    </div>
  );
}

function Rodape({ ids, ajuda, erro }: { ids: ReturnType<typeof useIds>; ajuda?: ReactNode; erro?: string }) {
  return (
    <>
      {ajuda && (
        <p id={ids.ajuda} className={estilos.ajuda}>
          {ajuda}
        </p>
      )}
      {erro && (
        <p id={ids.erro} className={estilos.erro} role="alert">
          <CircleAlert size={18} aria-hidden="true" />
          {erro}
        </p>
      )}
    </>
  );
}

function descricao(ids: ReturnType<typeof useIds>, ajuda?: ReactNode, erro?: string, dica?: string) {
  return [dica && ids.dica, ajuda && ids.ajuda, erro && ids.erro].filter(Boolean).join(" ") || undefined;
}

export type CampoProps = Base & InputHTMLAttributes<HTMLInputElement>;

/** Campo de texto com rótulo visível acima (nunca só placeholder — RF-02.4). */
export function Campo({ rotulo, ajuda, dica, erro, id, className, ...resto }: CampoProps) {
  const ids = useIds(id);
  return (
    <div className={[estilos.campo, className].filter(Boolean).join(" ")}>
      <Rotulo ids={ids} rotulo={rotulo} dica={dica} />
      <input
        id={ids.campo}
        className={estilos.entrada}
        aria-invalid={erro ? true : undefined}
        aria-describedby={descricao(ids, ajuda, erro, dica)}
        {...resto}
      />
      <Rodape ids={ids} ajuda={ajuda} erro={erro} />
    </div>
  );
}

export type AreaTextoProps = Base & TextareaHTMLAttributes<HTMLTextAreaElement>;

export function AreaTexto({ rotulo, ajuda, erro, id, className, ...resto }: AreaTextoProps) {
  const ids = useIds(id);
  return (
    <div className={[estilos.campo, className].filter(Boolean).join(" ")}>
      <label htmlFor={ids.campo} className={estilos.rotulo}>
        {rotulo}
      </label>
      <textarea
        id={ids.campo}
        className={estilos.entrada}
        aria-invalid={erro ? true : undefined}
        aria-describedby={descricao(ids, ajuda, erro)}
        {...resto}
      />
      <Rodape ids={ids} ajuda={ajuda} erro={erro} />
    </div>
  );
}
