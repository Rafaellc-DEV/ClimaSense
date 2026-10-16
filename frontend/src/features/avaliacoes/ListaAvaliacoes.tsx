import { useState } from "react";
import { Plus } from "lucide-react";
import { Link, useSearchParams } from "react-router-dom";
import { CabecalhoTela } from "@/app/AppShell";
import { nomeTerritorio, useTerritorios } from "@/app/FiltroFrase";
import { classesBotao } from "@/design-system/componentes/Botao";
import { Carregando, FalhaCarga, Painel } from "@/design-system/componentes/Painel";
import { SeloNivel } from "@/design-system/componentes/SeloNivel";
import { Tabela } from "@/design-system/componentes/Tabela";
import { VazioConvidativo } from "@/design-system/componentes/VazioConvidativo";
import type { ChaveNivel } from "@/design-system/niveis";
import { consulta, type Esquemas } from "@/lib/api";
import { useConsulta } from "@/lib/consultas";
import { dataCurta, formatarDataHora } from "@/lib/formatos";
import { buscaDoRecorte, useRecorte } from "@/lib/recorte";
import { useSessao } from "@/lib/sessao";
import { ESTADOS_AVALIACAO, PRIORIDADES } from "@/textos/glossario";
import { AbasEstado, SeloEstado } from "@/features/fluxo/Estado";

const NIVEL: Record<string, ChaveNivel> = {
  sem_indicacao: "sem",
  atencao: "atencao",
  alerta: "alerta",
  critico: "critico",
};

/** Avaliações (design §9.8, RF-10.4): abas por estado com contagem; território e período vêm do recorte global. */
export function ListaAvaliacoes() {
  const { recorte } = useRecorte();
  const [params] = useSearchParams();
  const { pode } = useSessao();
  const territorios = useTerritorios();
  const [estado, setEstado] = useState("todos");
  const r = useConsulta<Esquemas["ListaAvaliacoes"]>(
    `/avaliacoes${consulta({
      territorio_id: recorte.territorio === "recife" ? null : recorte.territorio,
      inicio: recorte.inicio,
      fim: recorte.fim,
    })}`,
  );
  const itens = r.data?.itens.filter((a) => estado === "todos" || a.estado === estado) ?? [];
  return (
    <>
      <CabecalhoTela
        titulo="Avaliações"
        proposito={`Registros de por que um território precisa (ou não) de atenção, em ${nomeTerritorio(
          territorios.data,
          recorte.territorio,
        )} e no período escolhido.`}
        acoes={
          pode("editar") && (
            <Link to={`/app/avaliacoes/nova${buscaDoRecorte(params)}`} className={classesBotao()}>
              <Plus aria-hidden="true" /> Registrar avaliação
            </Link>
          )
        }
      />
      {r.isPending && <Carregando />}
      {r.isError && <FalhaCarga erro={r.error} aoTentar={() => r.refetch()} />}
      {r.data && (
        <Painel titulo="Avaliações do recorte" id="av-lista">
          <AbasEstado
            estados={Object.keys(ESTADOS_AVALIACAO)}
            contagens={r.data.contagens}
            atual={estado}
            aoMudar={setEstado}
            rotulos={ESTADOS_AVALIACAO}
          />
          {itens.length ? (
            <Tabela
              legenda="Avaliações, da mais recente para a mais antiga"
              legendaVisivel={false}
              linhas={itens}
              chaveLinha={(a) => a.id}
              colunas={[
                {
                  chave: "territorio",
                  titulo: "Território",
                  celula: (a) => (
                    <Link to={`/app/avaliacoes/${a.id}${buscaDoRecorte(params)}`}>
                      {a.territorio_nome}
                      <span className="so-leitor">, abrir avaliação</span>
                    </Link>
                  ),
                },
                {
                  chave: "prioridade",
                  titulo: "Prioridade",
                  celula: (a) => (
                    <SeloNivel nivel={NIVEL[a.prioridade] ?? "sem"} rotulo={PRIORIDADES[a.prioridade]} />
                  ),
                },
                {
                  chave: "estado",
                  titulo: "Estado",
                  celula: (a) => <SeloEstado estado={a.estado} avaliacao />,
                },
                {
                  chave: "periodo",
                  titulo: "Período",
                  celula: (a) => `${dataCurta(a.periodo_inicio)} a ${dataCurta(a.periodo_fim)}`,
                },
                { chave: "autor", titulo: "Autor", celula: (a) => a.autor_nome },
                {
                  chave: "quando",
                  titulo: "Atualizada em",
                  celula: (a) => formatarDataHora(a.atualizado_em),
                },
              ]}
            />
          ) : (
            <VazioConvidativo
              titulo={
                estado === "todos"
                  ? "Nenhuma avaliação ainda."
                  : `Nenhuma avaliação ${ESTADOS_AVALIACAO[estado].toLowerCase()}.`
              }
              texto="Comece pelo mapa ou pelos cenários e registre a primeira, com as evidências."
              acao={
                pode("editar") && (
                  <Link to={`/app/mapa${buscaDoRecorte(params)}`} className={classesBotao("secundario")}>
                    Abrir o mapa
                  </Link>
                )
              }
            />
          )}
        </Painel>
      )}
    </>
  );
}
