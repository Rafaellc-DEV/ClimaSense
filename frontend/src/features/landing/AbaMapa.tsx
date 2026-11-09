import { MapaAvisos } from "./MapaAvisos";
import type { AvisoPublico } from "./useEstado";
import estilos from "./AbasLanding.module.css";

/**
 * Aba “Mapa”: onde há aviso (os 8 distritos). Tocar num bairro preenche a busca.
 */
export function AbaMapa({
  niveis,
  avisos,
  aoEscolherBairro,
}: {
  niveis: Record<string, string> | null;
  avisos?: AvisoPublico[];
  aoEscolherBairro: (nome: string) => void;
}) {
  return (
    <div className={estilos.painel}>
      <p className={estilos.lead}>
        O Recife é dividido em 8 distritos sanitários. Escolha um para ver os bairros e toque no seu para ver
        os avisos dele.
      </p>
      <MapaAvisos niveis={niveis} avisos={avisos} aoEscolherBairro={aoEscolherBairro} />
    </div>
  );
}
