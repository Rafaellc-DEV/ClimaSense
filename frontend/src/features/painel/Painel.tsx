import { Link, useSearchParams } from "react-router-dom";
import { CabecalhoTela } from "@/app/AppShell";
import { classesBotao } from "@/design-system/componentes/Botao";
import { Carregando, FalhaCarga, Painel as Bloco } from "@/design-system/componentes/Painel";
import { SeloNivel } from "@/design-system/componentes/SeloNivel";
import { VazioConvidativo } from "@/design-system/componentes/VazioConvidativo";
import type { ChaveNivel } from "@/design-system/niveis";
import type { Esquemas } from "@/lib/api";
import { useConsulta } from "@/lib/consultas";
import { quandoRelativo } from "@/lib/formatos";
import { buscaDoRecorte } from "@/lib/recorte";
import { useSessao } from "@/lib/sessao";
import { StatusFonte } from "@/features/fontes/StatusFonte";
import estilos from "./Painel.module.css";

/** Painel inicial (design §9.4): responde “o que precisa de mim agora?” em 4 blocos, sem gráfico protagonista. */
export function Painel() {
  const { usuario, pode } = useSessao();
  const [params] = useSearchParams();
  const busca = buscaDoRecorte(params);
  const r = useConsulta<Esquemas["ResumoPainel"]>("/painel/resumo");
  const primeiroNome = usuario?.nome.split(" ")[0];

  return (
    <>
      <CabecalhoTela
        titulo="Painel inicial"
        proposito={`Olá, ${primeiroNome}. O que está publicado, o que espera por você e como estão os dados.`}
      />
      {r.isPending && <Carregando />}
      {r.isError && <FalhaCarga erro={r.error} aoTentar={() => r.refetch()} />}
      {r.data && (
        <div className={estilos.grade}>
          <Bloco titulo="Avisos publicados agora" id="b-avisos">
            {r.data.avisos.length ? (
              <ul className={estilos.lista}>
                {r.data.avisos.map((a) => (
                  <li key={a.id}>
                    <SeloNivel nivel={a.nivel as ChaveNivel} />
                    <div>
                      <Link to={`/app/comunicados/${a.id}`} className={estilos.titulo}>
                        {a.titulo}
                      </Link>
                      <p className={estilos.apoio}>
                        {a.territorios.map((t) => t.nome_exibicao).join(", ")}. Vale até{" "}
                        {quandoRelativo(a.validade_fim)}.
                      </p>
                    </div>
                  </li>
                ))}
              </ul>
            ) : (
              <VazioConvidativo
                titulo="Nenhum aviso publicado agora."
                texto="Quando a coordenação publicar um comunicado, ele aparece aqui e na página inicial."
                acao={
                  pode("editar") && (
                    <Link to="/app/comunicados/novo" className={classesBotao("secundario")}>
                      Escrever comunicado
                    </Link>
                  )
                }
              />
            )}
          </Bloco>

          <Bloco titulo="Aguardando sua revisão" id="b-revisao">
            {!r.data.pode_revisar ? (
              <p className={estilos.apoio}>
                Quem revisa é outra pessoa da equipe, nunca quem escreveu. Acompanhe os seus envios em{" "}
                <Link to="/app/avaliacoes">Avaliações</Link> e <Link to="/app/comunicados">Comunicados</Link>.
              </p>
            ) : r.data.aguardando_revisao.length ? (
              <ul className={estilos.lista}>
                {r.data.aguardando_revisao.map((i) => (
                  <li key={i.id}>
                    <div>
                      <p className={estilos.titulo}>{i.titulo}</p>
                      <p className={estilos.apoio}>
                        {i.tipo === "comunicado" ? "Comunicado" : "Avaliação"} de {i.autor_nome}, enviado{" "}
                        {quandoRelativo(i.enviado_em)}.
                      </p>
                    </div>
                    <Link
                      to={`/app/${i.tipo === "comunicado" ? "comunicados" : "avaliacoes"}/${i.id}`}
                      className={classesBotao("secundario")}
                    >
                      Revisar
                    </Link>
                  </li>
                ))}
              </ul>
            ) : (
              <VazioConvidativo
                titulo="Nada esperando por você."
                texto="Quando alguém enviar uma avaliação ou um comunicado para revisão, ele aparece aqui."
              />
            )}
          </Bloco>

          <Bloco titulo="Territórios em atenção" id="b-territorios">
            {r.data.territorios_em_atencao.length ? (
              <ul className={estilos.lista}>
                {r.data.territorios_em_atencao.map((t) => (
                  <li key={t.territorio_id}>
                    <SeloNivel nivel={t.nivel as ChaveNivel} />
                    <div>
                      <p className={estilos.titulo}>{t.territorio_nome}</p>
                      <p className={estilos.apoio}>{t.motivo}</p>
                    </div>
                    <Link
                      to={`/app/mapa${mesclar(busca, { territorio: t.territorio_id })}`}
                      className={classesBotao("discreto")}
                    >
                      Abrir no mapa
                    </Link>
                  </li>
                ))}
              </ul>
            ) : (
              <VazioConvidativo
                titulo="Nenhum território em atenção agora."
                texto="Aparecem aqui os territórios com aviso publicado, avaliação que sugere atenção ou cenário experimental indicando cuidado."
                acao={
                  <Link to={`/app/cenarios${busca}`} className={classesBotao("secundario")}>
                    Ver cenários de alagamento
                  </Link>
                }
              />
            )}
          </Bloco>

          <Bloco
            titulo="Saúde das fontes"
            id="b-fontes"
            acoes={
              <Link to="/app/fontes" className={estilos.link}>
                Ver todas as fontes
              </Link>
            }
          >
            <ul className={estilos.fontes}>
              {r.data.fontes
                .filter((f) => f.status !== "planejada")
                .map((f) => (
                  <li key={f.id}>
                    <span>{f.nome}</span>
                    <StatusFonte status={f.status} />
                  </li>
                ))}
            </ul>
            <p className={estilos.apoio}>
              {r.data.fontes.filter((f) => f.status === "planejada").length} fontes planejadas ainda não geram
              dados.
            </p>
          </Bloco>
        </div>
      )}
    </>
  );
}

function mesclar(busca: string, extra: Record<string, string>) {
  const p = new URLSearchParams(busca);
  for (const [k, v] of Object.entries(extra)) p.set(k, v);
  return `?${p}`;
}
