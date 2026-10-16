import { useId, useState, type InputHTMLAttributes } from "react";
import { Eye, EyeOff } from "lucide-react";
import campo from "@/design-system/componentes/Campo.module.css";
import estilos from "./Entrar.module.css";

/** Senha com botão “Mostrar senha” rotulado em texto (RF-02.4). */
export function CampoSenha({
  rotulo,
  ...resto
}: { rotulo: string } & Omit<InputHTMLAttributes<HTMLInputElement>, "type">) {
  const id = useId();
  const [visivel, setVisivel] = useState(false);
  return (
    <div className={campo.campo}>
      <label htmlFor={id} className={campo.rotulo}>
        {rotulo}
      </label>
      <div className={estilos.senha}>
        <input id={id} type={visivel ? "text" : "password"} className={campo.entrada} required {...resto} />
        <button
          type="button"
          className={estilos.mostrar}
          aria-pressed={visivel}
          aria-controls={id}
          onClick={() => setVisivel((v) => !v)}
        >
          {visivel ? <EyeOff aria-hidden="true" size={20} /> : <Eye aria-hidden="true" size={20} />}
          {visivel ? "Ocultar senha" : "Mostrar senha"}
        </button>
      </div>
    </div>
  );
}
