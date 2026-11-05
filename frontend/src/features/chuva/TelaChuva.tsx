import { useSearchParams } from "react-router-dom";
import { Abas } from "@/design-system/componentes/Abas";
import { CabecalhoTela } from "@/design-system/componentes/CabecalhoTela";
import { Historico } from "./Historico";
import { ProximosDias } from "./ProximosDias";

type Aba = "proximos" | "historico";

/** Chuva: o que vem nos próximos 3 dias e o que já aconteceu. A aba fica no endereço (?aba=historico). */
export function TelaChuva() {
  const [params, setParams] = useSearchParams();
  const aba: Aba = params.get("aba") === "historico" ? "historico" : "proximos";
  return (
    <>
      <CabecalhoTela
        titulo="Chuva"
        proposito="Onde pode passar do limite nos próximos dias e como foi até agora."
      />
      <Abas
        rotulo="Chuva"
        valor={aba}
        aoMudar={(v) =>
          setParams(
            (atual) => {
              const p = new URLSearchParams(atual);
              if (v === "historico") p.set("aba", "historico");
              else p.delete("aba");
              return p;
            },
            { replace: true },
          )
        }
        itens={[
          { valor: "proximos", rotulo: "Próximos 3 dias", conteudo: <ProximosDias /> },
          { valor: "historico", rotulo: "Histórico", conteudo: <Historico /> },
        ]}
      />
    </>
  );
}
