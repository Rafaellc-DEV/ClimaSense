/**
 * Dica curta (ícone ⓘ): o texto longo sai da frente e aparece ao tocar (ou ao passar o mouse, pelo `title`).
 * Serve para explicações que a equipe lê uma vez e não precisa ver sempre (RF-20, RNF-08).
 */
import { useState } from "react";
import { Info } from "lucide-react";
import estilos from "./Mapa.module.css";

export function Dica({ texto, rotulo = "Saiba mais" }: { texto: string; rotulo?: string }) {
  const [aberta, setAberta] = useState(false);
  return (
    <>
      <button
        type="button"
        className={estilos.dica}
        title={texto}
        aria-label={rotulo}
        aria-expanded={aberta}
        onClick={() => setAberta((a) => !a)}
      >
        <Info aria-hidden="true" size={15} />
      </button>
      {aberta && (
        <span className={estilos.dicaTexto} role="note">
          {texto}
        </span>
      )}
    </>
  );
}
