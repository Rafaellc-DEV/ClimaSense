import { useRef } from "react";
import * as Tabs from "@radix-ui/react-tabs";
import { AbaAbrigos } from "./AbaAbrigos";
import { AbaComunicados } from "./AbaComunicados";
import { AbaMapa } from "./AbaMapa";
import { useRevelar } from "./efeitos";
import type { Abrigos } from "./useAbrigos";
import type { Busca } from "./useBusca";
import type { useAvisos } from "./useEstado";
import estilos from "./AbasLanding.module.css";

export type AbaLanding = "comunicados" | "abrigos" | "mapa";
export const ABAS: AbaLanding[] = ["comunicados", "abrigos", "mapa"];

/**
 * As três visões da página, em abas (controle segmentado): Comunicados, Abrigos e Mapa. A primeira é a mais urgente
 * e mostra quantos comunicados estão em vigor. Setas do teclado trocam de aba (Radix Tabs).
 */
export function AbasLanding({
  aba,
  aoMudar,
  avisos,
  niveis,
  abrigos,
  busca,
}: {
  aba: AbaLanding;
  aoMudar: (a: AbaLanding) => void;
  avisos: ReturnType<typeof useAvisos>;
  niveis: Record<string, string> | null;
  abrigos: Abrigos;
  busca: Busca;
}) {
  const n = avisos.data?.length;
  const secao = useRef<HTMLElement>(null);
  useRevelar(secao);
  return (
    <section ref={secao} id="avisos-e-abrigos" className={estilos.abas} aria-labelledby="abas-h">
      <h2 id="abas-h" className="so-leitor">
        Comunicados, abrigos e mapa
      </h2>
      <Tabs.Root value={aba} onValueChange={(v) => aoMudar(v as AbaLanding)}>
        <Tabs.List className={estilos.lista} data-aba={aba} aria-label="Comunicados, abrigos e mapa">
          <span className={estilos.pilula} aria-hidden="true" />
          <Tabs.Trigger value="comunicados" className={estilos.aba}>
            Comunicados
            {n !== undefined && n > 0 && (
              <>
                <span className={estilos.contagem} aria-hidden="true">
                  {n}
                </span>
                <span className="so-leitor"> ({n} em vigor)</span>
              </>
            )}
          </Tabs.Trigger>
          <Tabs.Trigger value="abrigos" className={estilos.aba}>
            Abrigos
          </Tabs.Trigger>
          <Tabs.Trigger value="mapa" className={estilos.aba}>
            Mapa
          </Tabs.Trigger>
        </Tabs.List>
        <Tabs.Content value="comunicados" className={estilos.conteudo}>
          <AbaComunicados avisos={avisos} />
        </Tabs.Content>
        <Tabs.Content value="abrigos" className={estilos.conteudo}>
          <AbaAbrigos abrigos={abrigos} busca={busca} />
        </Tabs.Content>
        <Tabs.Content value="mapa" className={estilos.conteudo}>
          <AbaMapa
            niveis={niveis}
            avisos={avisos.data}
            abrigos={abrigos}
            aoEscolherBairro={(nome) => {
              busca.buscar(nome);
              document.getElementById("pergunta")?.scrollIntoView?.({ block: "start" });
            }}
          />
        </Tabs.Content>
      </Tabs.Root>
    </section>
  );
}
