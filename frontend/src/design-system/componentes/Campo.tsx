import { useId, type InputHTMLAttributes, type ReactNode, type TextareaHTMLAttributes } from "react";
import { CircleAlert } from "lucide-react";
import estilos from "./Campo.module.css";

interface Base {
  rotulo: string;
  ajuda?: ReactNode;
  erro?: string;
}

function useIds(id?: string) {
  const gerado = useId();
  const base = id ?? gerado;
  return { campo: base, ajuda: `${base}-ajuda`, erro: `${base}-erro` };
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

function descricao(ids: ReturnType<typeof useIds>, ajuda?: ReactNode, erro?: string) {
  return [ajuda && ids.ajuda, erro && ids.erro].filter(Boolean).join(" ") || undefined;
}

export type CampoProps = Base & InputHTMLAttributes<HTMLInputElement>;

/** Campo de texto com rótulo visível acima (nunca só placeholder — RF-02.4). */
export function Campo({ rotulo, ajuda, erro, id, className, ...resto }: CampoProps) {
  const ids = useIds(id);
  return (
    <div className={[estilos.campo, className].filter(Boolean).join(" ")}>
      <label htmlFor={ids.campo} className={estilos.rotulo}>
        {rotulo}
      </label>
      <input
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
