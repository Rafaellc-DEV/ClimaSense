import { Phone } from "lucide-react";
import { DEFESA_CIVIL_RECIFE } from "./telefones";
import estilos from "./BarraEmergencia.module.css";

/**
 * Barra fixa no rodapé da tela, só no celular (no computador os telefones ficam no topo). Ligar para a Defesa Civil
 * do Recife, e ligar 199 ficam sempre a um toque, em qualquer ponto da página.
 */
export function BarraEmergencia() {
  return (
    <nav className={estilos.barra} aria-label="Emergência">
      <a
        href={DEFESA_CIVIL_RECIFE.href}
        className={estilos.principal}
        aria-label={`Ligar para a Defesa Civil do Recife, ${DEFESA_CIVIL_RECIFE.texto}, 24 horas, grátis`}
      >
        <Phone aria-hidden="true" size={20} />
        <span>
          Ligar <b className={estilos.numero}>{DEFESA_CIVIL_RECIFE.texto}</b>
        </span>
      </a>
      <a href="tel:199" className={estilos.link} aria-label="Ligar para a Defesa Civil, 199">
        <b>199</b>
      </a>
    </nav>
  );
}
