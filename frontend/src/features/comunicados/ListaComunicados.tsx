import { useState } from "react";
import { Plus } from "lucide-react";
import { Link } from "react-router-dom";
import { CabecalhoTela } from "@/app/AppShell";
import { classesBotao } from "@/design-system/componentes/Botao";
import { FalhaCarga, Painel } from "@/design-system/componentes/Painel";
import { Pilula } from "@/design-system/componentes/Pilula";
import { SeloNivel } from "@/design-system/componentes/SeloNivel";
import { VazioConvidativo } from "@/design-system/componentes/VazioConvidativo";
import type { ChaveNivel } from "@/design-system/niveis";
import type { Esquemas } from "@/lib/api";
import { useConsulta } from "@/lib/consultas";
import { formatarDataHora, quandoRelativo } from "@/lib/formatos";
import { useSessao } from "@/lib/sessao";
import {
  EstadoEPasso,
  FiltrosFluxo,
  noFiltro,
  proximoPasso,
  ROTULOS_FILTRO,
  type FiltroFluxo,
} from "@/features/fluxo/Estado";
import { ListaAdaptavel } from "@/features/fluxo/ListaAdaptavel";
import estilos from "./Lista.module.css";

const FILTROS: FiltroFluxo[] = ["comigo", "andamento", "no_ar", "encerrados", "todos"];

/** Comunicados (design §9.9, RF-11): o texto que a equipe escreve, revisa e publica como aviso. */
export function ListaComunicados() {
  const { pode, usuario } = useSessao();
  const r = useConsulta<Esquemas["ListaComunicados"]>("/comunicados");
  const comPasso = (r.data?.itens ?? []).map((c) => ({
    ...c,
    passo: proximoPasso({ ...c, tipo: "comunicado" }, usuario?.id, pode, quandoRelativo),
  }));
  const contagens = Object.fromEntries(
    FILTROS.map((f) => [f, comPasso.filter((c) => noFiltro(f, c.estado, c.passo)).length]),
  ) as Record<FiltroFluxo, number>;
  // abre no que depende da pessoa, quando houver; senão, em tudo
  const [escolha, setFiltro] = useState<FiltroFluxo | null>(null);
  const filtro = escolha ?? (contagens.comigo > 0 ? "comigo" : "todos");
  const itens = comPasso.filter((c) => noFiltro(filtro, c.estado, c.passo));
  return (
    <>
      <CabecalhoTela
        titulo="Comunicados"
        proposito="O que a população vê na página inicial. Cada aviso passa pela revisão de outra pessoa antes de ser publicado."
        estado={
          r.data &&
          (contagens.comigo > 0 ? (
            <Pilula tom="alerta">
              {contagens.comigo === 1
                ? "1 comunicado precisa de você"
                : `${contagens.comigo} comunicados precisam de você`}
            </Pilula>
          ) : (
            <Pilula tom="neutro">Nenhum comunicado esperando por você</Pilula>
          ))
        }
        acoes={
          pode("editar") && (
            <Link to="/app/comunicados/novo" className={classesBotao()}>
              <Plus aria-hidden="true" /> Escrever comunicado
            </Link>
          )
        }
      />
      {r.isError && <FalhaCarga erro={r.error} aoTentar={() => r.refetch()} />}
      {!r.isError && (
        <Painel titulo={ROTULOS_FILTRO[filtro]} id="co-lista">
          {r.data && r.data.itens.length > 0 && (
            <FiltrosFluxo filtros={FILTROS} contagens={contagens} atual={filtro} aoMudar={setFiltro} />
          )}
          <ListaAdaptavel
            legenda="Comunicados, do mais recente para o mais antigo"
            carregando={r.isPending}
            linhas={itens}
            chaveLinha={(c) => c.id}
            vazio={
              <VazioConvidativo
                titulo={
                  filtro === "todos"
                    ? "Nenhum comunicado ainda."
                    : filtro === "comigo"
                      ? "Nada esperando por você."
                      : `Nenhum comunicado em “${ROTULOS_FILTRO[filtro]}”.`
                }
                acao={
                  pode("editar") && (
                    <Link to="/app/comunicados/novo" className={classesBotao("secundario")}>
                      Escrever comunicado
                    </Link>
                  )
                }
              />
            }
            colunas={[
              {
                chave: "titulo",
                titulo: "Título",
                celula: (c) => <Link to={`/app/comunicados/${c.id}`}>{c.titulo}</Link>,
              },
              {
                chave: "estado",
                titulo: "Situação e próximo passo",
                celula: (c) => <EstadoEPasso estado={c.estado} passo={c.passo} />,
              },
              {
                chave: "nivel",
                titulo: "Nível do aviso",
                celula: (c) => <SeloNivel nivel={c.nivel as ChaveNivel} />,
              },
              {
                chave: "validade",
                semQuebra: true,
                titulo: "Vale até",
                celula: (c) => quandoRelativo(c.validade_fim),
              },
              {
                chave: "autor",
                titulo: "Quem escreveu",
                celula: (c) => (
                  <span className={estilos.autor}>
                    {c.autor_nome}
                    <small>
                      Versão {c.versao_atual}, {formatarDataHora(c.atualizado_em)}
                    </small>
                  </span>
                ),
              },
            ]}
          />
        </Painel>
      )}
    </>
  );
}
