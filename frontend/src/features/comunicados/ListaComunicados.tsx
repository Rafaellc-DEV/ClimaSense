import { useState } from "react";
import { Plus } from "lucide-react";
import { Link } from "react-router-dom";
import { CabecalhoTela } from "@/app/AppShell";
import { classesBotao } from "@/design-system/componentes/Botao";
import { Carregando, FalhaCarga, Painel } from "@/design-system/componentes/Painel";
import { SeloNivel } from "@/design-system/componentes/SeloNivel";
import { Tabela } from "@/design-system/componentes/Tabela";
import { VazioConvidativo } from "@/design-system/componentes/VazioConvidativo";
import type { ChaveNivel } from "@/design-system/niveis";
import type { Esquemas } from "@/lib/api";
import { useConsulta } from "@/lib/consultas";
import { formatarDataHora, quandoRelativo } from "@/lib/formatos";
import { useSessao } from "@/lib/sessao";
import { ESTADOS } from "@/textos/glossario";
import { AbasEstado, SeloEstado } from "@/features/fluxo/Estado";

/** Comunicados (design §9.9, RF-11): o texto que a equipe escreve, revisa e publica como aviso. */
export function ListaComunicados() {
  const { pode } = useSessao();
  const [estado, setEstado] = useState("todos");
  const r = useConsulta<Esquemas["ListaComunicados"]>("/comunicados");
  const itens = r.data?.itens.filter((c) => estado === "todos" || c.estado === estado) ?? [];
  return (
    <>
      <CabecalhoTela
        titulo="Comunicados"
        proposito="O que a equipe escreve para a população. Só chega à página inicial depois de revisado por outra pessoa e publicado pela coordenação."
        acoes={
          pode("editar") && (
            <Link to="/app/comunicados/novo" className={classesBotao()}>
              <Plus aria-hidden="true" /> Escrever comunicado
            </Link>
          )
        }
      />
      {r.isPending && <Carregando />}
      {r.isError && <FalhaCarga erro={r.error} aoTentar={() => r.refetch()} />}
      {r.data && (
        <Painel titulo="Todos os comunicados" id="co-lista">
          <AbasEstado
            estados={Object.keys(ESTADOS)}
            contagens={r.data.contagens}
            atual={estado}
            aoMudar={setEstado}
            rotulos={ESTADOS}
          />
          {itens.length ? (
            <Tabela
              legenda="Comunicados, do mais recente para o mais antigo"
              legendaVisivel={false}
              linhas={itens}
              chaveLinha={(c) => c.id}
              colunas={[
                {
                  chave: "titulo",
                  titulo: "Título",
                  celula: (c) => <Link to={`/app/comunicados/${c.id}`}>{c.titulo}</Link>,
                },
                {
                  chave: "nivel",
                  titulo: "Nível",
                  celula: (c) => <SeloNivel nivel={c.nivel as ChaveNivel} />,
                },
                { chave: "estado", titulo: "Etapa", celula: (c) => <SeloEstado estado={c.estado} /> },
                {
                  chave: "validade",
                  titulo: "Vale até",
                  celula: (c) => quandoRelativo(c.validade_fim),
                },
                {
                  chave: "autor",
                  titulo: "Versão atual",
                  celula: (c) => `${c.versao_atual}, de ${c.autor_nome}`,
                },
                {
                  chave: "quando",
                  titulo: "Atualizado em",
                  celula: (c) => formatarDataHora(c.atualizado_em),
                },
              ]}
            />
          ) : (
            <VazioConvidativo
              titulo={
                estado === "todos"
                  ? "Nenhum comunicado ainda."
                  : `Nenhum comunicado ${ESTADOS[estado].toLowerCase()}.`
              }
              texto="Comece por uma avaliação aprovada ou escreva direto. A prévia mostra exatamente o que a população verá."
              acao={
                pode("editar") && (
                  <Link to="/app/comunicados/novo" className={classesBotao("secundario")}>
                    Escrever comunicado
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
