import { useId, useState, type ReactNode } from "react";
import { Info } from "lucide-react";
import { formatarDataHora } from "@/lib/formatos";
import estilos from "./Dica.module.css";
import type { FonteDado } from "./EstadoDados";

export interface DicaProps {
  /** O que o (i) revela. Uma ou duas frases; é aqui que moram as explicações que não cabem na tela. */
  texto: ReactNode;
  /** Nome do botão para leitores de tela. Diga sobre o quê: "Sobre este indicador". */
  rotulo?: string;
  /** Para onde o balão abre. Em cabeçalhos, "abaixo". */
  lado?: "acima" | "abaixo";
  /** De que borda do ícone o balão parte: "inicio" abre para a direita, "fim" para a esquerda. */
  alinhar?: "inicio" | "fim";
  /** Cor do ícone sobre fundo azul (menu, faixas de marca). */
  sobreMare?: boolean;
  className?: string;
}

/**
 * Ícone (i) que revela uma explicação: ao passar o mouse, focar ou tocar. É o padrão `dica` do Campo, solto.
 * Regra da plataforma: texto de apoio vive aqui, nunca solto na tela. Esc fecha.
 */
export function Dica({
  texto,
  rotulo = "Mais informações",
  lado = "acima",
  alinhar = "inicio",
  sobreMare,
  className,
}: DicaProps) {
  const [aberta, setAberta] = useState(false);
  const id = useId();
  return (
    <span
      className={[estilos.dica, sobreMare && estilos.sobreMare, className].filter(Boolean).join(" ")}
      data-aberta={aberta}
      data-lado={lado}
      data-alinhar={alinhar}
    >
      <button
        type="button"
        className={estilos.botao}
        aria-label={rotulo}
        aria-expanded={aberta}
        aria-describedby={id}
        onClick={() => setAberta((a) => !a)}
        onBlur={() => setAberta(false)}
        onKeyDown={(e) => e.key === "Escape" && setAberta(false)}
      >
        <Info aria-hidden="true" size={16} />
      </button>
      <span id={id} role="tooltip" className={estilos.texto}>
        {texto}
      </span>
    </span>
  );
}

/** “Fonte: … atualizada em …” atrás de um (i): a forma padrão de citar a origem de um valor (CA-02). */
export function DicaFonte({
  fontes,
  rotulo = "Fonte e atualização",
}: {
  fontes: FonteDado[];
  rotulo?: string;
}) {
  const frase = fontes
    .map((f) => (f.atualizadoEm ? `${f.nome}, atualizada em ${formatarDataHora(f.atualizadoEm)}` : f.nome))
    .join("; ");
  return <Dica rotulo={rotulo} texto={`Fonte: ${frase}.`} alinhar="fim" />;
}
