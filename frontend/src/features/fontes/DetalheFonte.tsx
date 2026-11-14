import { useEffect, useRef, useState } from "react";
import { CircleCheck, Loader, RefreshCw, TriangleAlert } from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { CabecalhoTela } from "@/app/AppShell";
import { useAviso } from "@/design-system/componentes/Aviso";
import { Botao } from "@/design-system/componentes/Botao";
import { CarregandoLista } from "@/design-system/componentes/Esqueleto";
import { FalhaCarga, Painel } from "@/design-system/componentes/Painel";
import { Pilula, type TomPilula } from "@/design-system/componentes/Pilula";
import { semDado } from "@/design-system/componentes/Tabela";
import { VazioConvidativo } from "@/design-system/componentes/VazioConvidativo";
import { type Esquemas } from "@/lib/api";
import { useConsulta } from "@/lib/consultas";
import { formatarDataHora, formatarNumero } from "@/lib/formatos";
import { useSessao } from "@/lib/sessao";
import { RETORNO } from "@/textos/mensagens";
import { GLOSSARIO, TIPOS_FONTE } from "@/textos/glossario";
import { Fato, Fatos } from "@/features/fluxo/Pecas";
import { ListaAdaptavel } from "@/features/fluxo/ListaAdaptavel";
import { Frescor, limiteTexto, StatusFonte } from "./StatusFonte";
import { PLANOS } from "./TelaFontes";
import estilos from "./Fontes.module.css";
import { acompanhar, apiComPrazo } from "./acompanhar";

type Execucao = Esquemas["Execucao"];
const STATUS_EXECUCAO: Record<string, { rotulo: string; tom: TomPilula; icone: JSX.Element }> = {
  em_andamento: { rotulo: "Em andamento", tom: "info", icone: <Loader /> },
  sucesso: { rotulo: "Concluída", tom: "sucesso", icone: <CircleCheck /> },
  falha: { rotulo: "Com falha", tom: "alerta", icone: <TriangleAlert /> },
};
const SEM_CONECTOR_MANUAL = new Set(["territorio-oficial"]);

/** Detalhe da fonte: metadados (RNF-CON-04), execuções do ETL e, para o administrador, “Atualizar agora” (RF-16.2). */
export function DetalheFonte() {
  const { id = "" } = useParams();
  const { pode } = useSessao();
  const aviso = useAviso();
  const cliente = useQueryClient();
  const [iniciando, setIniciando] = useState(false);
  const controle = useRef<AbortController | null>(null);
  const fonte = useConsulta<Esquemas["Fonte"]>(`/fontes/${id}`);
  const execucoes = useConsulta<Execucao[]>(`/fontes/${id}/execucoes`);
  useEffect(() => () => controle.current?.abort(), []);

  async function atualizar() {
    if (controle.current) return;
    const c = new AbortController();
    controle.current = c;
    setIniciando(true);
    try {
      const e = await apiComPrazo<Execucao>("/etl/execucoes", c.signal, {
        method: "POST",
        body: JSON.stringify({ fonte_id: id }),
      });
      aviso({ titulo: RETORNO.atualizarFonte, texto: "O status muda aqui quando terminar." });
      void execucoes.refetch();
      const fim = await acompanhar(e.id, c.signal);
      if (!c.signal.aborted)
        aviso(
          fim.status === "sucesso"
            ? {
                titulo: fim.gravados ? "Atualização concluída." : "Coleta concluída sem novos registros.",
                texto: `${formatarNumero(fim.gravados)} registros gravados. A validade dos dados continua indicada na fonte.`,
              }
            : { tipo: "erro", titulo: "A atualização falhou.", texto: fim.erro ?? undefined },
        );
    } catch (x) {
      if (!c.signal.aborted)
        aviso({ tipo: "erro", titulo: "Atualização com pendência.", texto: (x as Error).message });
    } finally {
      controle.current = null;
      if (!c.signal.aborted) {
        setIniciando(false);
        void cliente.invalidateQueries();
      }
    }
  }

  const voltar = <Link to="/app/fontes">Todas as fontes</Link>;
  if (fonte.isPending)
    return (
      <>
        <CabecalhoTela titulo="Fonte" voltar={voltar} />
        <CarregandoLista linhas={3} altura="5rem" />
      </>
    );
  if (fonte.isError) return <FalhaCarga erro={fonte.error} aoTentar={() => fonte.refetch()} />;
  const f = fonte.data;
  const podeAtualizar = pode("executar_etl") && f.status !== "planejada" && !SEM_CONECTOR_MANUAL.has(f.id);

  return (
    <>
      <CabecalhoTela
        titulo={f.nome}
        proposito={f.status === "planejada" ? (PLANOS[f.id] ?? f.orgao) : f.orgao}
        voltar={voltar}
        acoes={
          podeAtualizar && (
            <Botao onClick={atualizar} disabled={iniciando} icone={<RefreshCw />}>
              {iniciando ? "Atualizando…" : "Atualizar agora"}
            </Botao>
          )
        }
      />
      <div className={estilos.pilhaDetalhe}>
        <Painel titulo="Sobre a fonte" id="f-sobre">
          <Fatos colunas="duas">
            <Fato rotulo="Status">
              <StatusFonte status={f.status} />
            </Fato>
            <Fato rotulo="Frescor">
              <Frescor
                ultima={f.ultima_atualizacao}
                limiteH={f.limite_desatualizacao_h}
                status={f.status}
                grande
              />
            </Fato>
            <Fato rotulo="Tipo de dado" dica={GLOSSARIO[f.tipo as keyof typeof GLOSSARIO]}>
              {TIPOS_FONTE[f.tipo] ?? f.tipo}
            </Fato>
            <Fato rotulo="Órgão">{f.orgao}</Fato>
            <Fato rotulo="Licença">{f.licenca ?? "Não informada"}</Fato>
            <Fato rotulo="Última carga bem-sucedida">
              {f.ultima_atualizacao ? formatarDataHora(f.ultima_atualizacao) : "Nunca carregada"}
            </Fato>
            <Fato
              rotulo="Fica desatualizada após"
              dica="Tempo sem carga nova a partir do qual a fonte passa a aparecer como desatualizada."
            >
              {limiteTexto(f.limite_desatualizacao_h)}
            </Fato>
            <Fato rotulo="Endereço">
              <a className={estilos.endereco} href={f.url} target="_blank" rel="noopener noreferrer">
                {f.url.replace(/^https?:\/\//, "")}
              </a>
            </Fato>
          </Fatos>
        </Painel>
        <Painel
          titulo="Execuções do ETL"
          id="f-execucoes"
          dica="Cada vez que o sistema busca dados novos desta fonte. Lidos são os registros recebidos; gravados, os aceitos; descartados, os recusados por não passarem nas regras."
        >
          <ListaAdaptavel
            legenda="Últimas execuções desta fonte"
            carregando={execucoes.isPending}
            linhas={execucoes.data ?? []}
            chaveLinha={(e) => e.id}
            vazio={
              <VazioConvidativo
                titulo={
                  f.status === "planejada"
                    ? "Nenhuma execução: o conector ainda está em preparo."
                    : "Nenhuma execução registrada."
                }
              />
            }
            colunas={[
              {
                chave: "inicio",
                semQuebra: true,
                titulo: "Início",
                celula: (e) => formatarDataHora(e.inicio),
              },
              {
                chave: "status",
                titulo: "Resultado",
                celula: (e) => {
                  const s = STATUS_EXECUCAO[e.status] ?? STATUS_EXECUCAO.em_andamento;
                  return (
                    <span className={estilos.execucao}>
                      <Pilula tom={s.tom} icone={s.icone}>
                        {STATUS_EXECUCAO[e.status]?.rotulo ?? e.status}
                      </Pilula>
                      {e.erro && <small>{e.erro}</small>}
                    </span>
                  );
                },
              },
              {
                chave: "lidos",
                titulo: "Lidos",
                numerica: true,
                celula: (e) => semDado(e.lidos, formatarNumero),
              },
              {
                chave: "gravados",
                titulo: "Gravados",
                numerica: true,
                celula: (e) => semDado(e.gravados, formatarNumero),
              },
              {
                chave: "descartados",
                titulo: "Descartados",
                numerica: true,
                celula: (e) => semDado(e.descartados, formatarNumero),
              },
            ]}
          />
        </Painel>
      </div>
    </>
  );
}
