import { lazy, Suspense, useCallback, useMemo, useState } from "react";
import { Segmentado } from "@/design-system/componentes/Segmentado";
import { CartaoAbrigo } from "./CartaoAbrigo";
import { filtrar } from "./abrigosPublicos";
import { MapaAvisos } from "./MapaAvisos";
import type { Abrigos } from "./useAbrigos";
import type { AvisoPublico } from "./useEstado";
import type { AbrigoPublico } from "./abrigosPublicos";
import estilos from "./AbasLanding.module.css";

const MapaAbrigos = lazy(() => import("./MapaAbrigos"));

type Camada = "avisos" | "abrigos";

/**
 * Aba “Mapa” com duas camadas: onde há aviso (os 8 distritos) e onde ficam os abrigos. Tocar num bairro da camada de
 * avisos preenche a busca; tocar num marcador de abrigo mostra o cartão dele logo abaixo do mapa.
 */
export function AbaMapa({
  niveis,
  avisos,
  abrigos,
  aoEscolherBairro,
}: {
  niveis: Record<string, string> | null;
  avisos?: AvisoPublico[];
  abrigos: Abrigos;
  aoEscolherBairro: (nome: string) => void;
}) {
  const [camada, setCamada] = useState<Camada>("avisos");
  const [destaque, setDestaque] = useState<AbrigoPublico["id"] | null>(null);
  const locais = useMemo(() => filtrar(abrigos.itens, "abrigos", false), [abrigos.itens]);
  const escolhido = locais.find((a) => a.id === destaque);
  const escolher = useCallback((id: AbrigoPublico["id"]) => setDestaque(id), []);

  return (
    <div className={estilos.painel}>
      <Segmentado
        rotulo="Camada do mapa"
        valor={camada}
        aoMudar={setCamada}
        opcoes={[
          { valor: "avisos", rotulo: "Avisos" },
          { valor: "abrigos", rotulo: "Abrigos" },
        ]}
      />
      {camada === "avisos" ? (
        <>
          <p className={estilos.lead}>
            O Recife é dividido em 8 distritos sanitários. Escolha um para ver os bairros e toque no seu para
            ver os avisos dele.
          </p>
          <MapaAvisos niveis={niveis} avisos={avisos} aoEscolherBairro={aoEscolherBairro} />
        </>
      ) : abrigos.indisponivel || abrigos.erro ? (
        <p className={estilos.vazio}>
          {abrigos.indisponivel
            ? "A lista de abrigos ainda não está disponível. Ligue 0800 081 3400."
            : "Não foi possível carregar os abrigos agora. Ligue 0800 081 3400."}
        </p>
      ) : (
        <>
          <p className={estilos.lead}>
            Disco cheio e maior: aberto agora, informado pela Defesa Civil. Anel fino: local de apoio
            cadastrado, sem confirmação de abertura. Toque num ponto para ver o endereço.
          </p>
          <Suspense fallback={<div className={estilos.mapaEspera} aria-hidden="true" />}>
            <MapaAbrigos itens={locais} aoEscolher={escolher} destaque={destaque} />
          </Suspense>
          {escolhido && (
            <ul className={estilos.abrigos} aria-label="Abrigo escolhido no mapa">
              <CartaoAbrigo a={escolhido} destaque />
            </ul>
          )}
        </>
      )}
    </div>
  );
}
