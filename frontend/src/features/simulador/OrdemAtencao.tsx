import { EstadoDados } from "@/design-system/componentes/EstadoDados";
import { SeloEstagio } from "@/features/evento/Evento";
import { ListaAdaptavel } from "@/features/fluxo/ListaAdaptavel";
import { nomeDistrito } from "@/lib/distritos";
import { NotaArboviroses, textoArboviroses } from "./DistritosArboviroses";
import { ClasseAlagamento, textoConfianca } from "./EstagioPorDistrito";
import type { ItemSimulado, ResultadoSimulacao } from "./tipos";
import estilos from "./Simulador.module.css";

/**
 * Ordem de atenção dos distritos com a chuva simulada. É uma ordem, não uma probabilidade (RN-06). As arboviroses
 * entram como contexto, não como previsão causal.
 */
export function OrdemAtencao({
  resultado,
  distritos,
  aoEscolher,
}: {
  resultado: ResultadoSimulacao | undefined;
  distritos: ItemSimulado[];
  aoEscolher: (id: string) => void;
}) {
  if (!resultado) return null;
  const ordem = resultado.resumo?.ordem_de_atencao_distritos ?? [];
  const porId = new Map(distritos.map((d) => [d.territorio_id, d] as const));
  return (
    <section className={estilos.painelBloco} aria-labelledby="sim-ordem">
      <h2 id="sim-ordem">Ordem de atenção dos distritos</h2>
      <p className={estilos.apoio}>
        Do mais para o menos afetado pela chuva simulada; no empate, pela classe de arboviroses. É ordem de
        atenção, não probabilidade.
      </p>
      <ListaAdaptavel
        legenda="Ordem de atenção dos distritos"
        linhas={ordem}
        chaveLinha={(o) => o.distrito_id}
        vazio={
          <EstadoDados tipo="insuficiente" titulo="Dados insuficientes.">
            O cálculo não trouxe a ordem dos distritos. Falta a fonte da chuva ou das arboviroses.
          </EstadoDados>
        }
        colunas={[
          {
            chave: "pos",
            titulo: "#",
            numerica: true,
            celula: (o) => ordem.indexOf(o) + 1,
          },
          {
            chave: "distrito",
            titulo: "Distrito",
            celula: (o) => (
              <button
                type="button"
                className={estilos.linkDistrito}
                onClick={() => aoEscolher(o.distrito_id)}
              >
                {nomeDistrito(o.nome)}
              </button>
            ),
          },
          {
            chave: "estagio",
            titulo: "Estágio sugerido",
            celula: (o) => <SeloEstagio estagio={o.estagio_sugerido} pequena />,
          },
          {
            chave: "alag",
            titulo: "Alagamento",
            celula: (o) => <ClasseAlagamento classe={porId.get(o.distrito_id)?.classe_alagamento} />,
          },
          {
            chave: "desl",
            titulo: "Deslizamento",
            celula: (o) => <ClasseAlagamento classe={porId.get(o.distrito_id)?.classe_deslizamento} />,
          },
          {
            chave: "arbo",
            titulo: "Arboviroses em destaque",
            celula: (o) => textoArboviroses(porId.get(o.distrito_id)?.arboviroses),
          },
          {
            chave: "conf",
            titulo: "Confiança",
            celula: (o) => textoConfianca(porId.get(o.distrito_id)?.confianca),
          },
        ]}
      />
      <NotaArboviroses resumo={resultado.resumo?.arboviroses} />
    </section>
  );
}
