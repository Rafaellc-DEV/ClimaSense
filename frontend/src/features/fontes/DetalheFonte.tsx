import { useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { CabecalhoTela } from "@/app/AppShell";
import { useAviso } from "@/design-system/componentes/Aviso";
import { Botao } from "@/design-system/componentes/Botao";
import { Carregando, FalhaCarga, Painel } from "@/design-system/componentes/Painel";
import { semDado, Tabela } from "@/design-system/componentes/Tabela";
import { VazioConvidativo } from "@/design-system/componentes/VazioConvidativo";
import { enviar, type Esquemas } from "@/lib/api";
import { useConsulta } from "@/lib/consultas";
import { formatarDataHora, formatarNumero } from "@/lib/formatos";
import { useSessao } from "@/lib/sessao";
import { RETORNO } from "@/textos/mensagens";
import { GLOSSARIO, TIPOS_FONTE } from "@/textos/glossario";
import { StatusFonte } from "./StatusFonte";
import { limiteTexto, PLANOS } from "./TelaFontes";
import estilos from "./Fontes.module.css";

type Execucao = Esquemas["Execucao"];
const STATUS_EXECUCAO: Record<string, string> = {
  em_andamento: "Em andamento",
  sucesso: "Concluída",
  falha: "Com falha",
};
const SEM_CONECTOR_MANUAL = new Set(["territorio-oficial"]);

/** Detalhe da fonte: metadados (RNF-CON-04), execuções do ETL e, para o administrador, “Atualizar agora” (RF-16.2). */
export function DetalheFonte() {
  const { id = "" } = useParams();
  const { pode } = useSessao();
  const aviso = useAviso();
  const cliente = useQueryClient();
  const [acompanhando, setAcompanhando] = useState<string | null>(null);
  const fonte = useConsulta<Esquemas["Fonte"]>(`/fontes/${id}`, {
    refetchInterval: acompanhando ? 2000 : false,
  });
  const execucoes = useConsulta<Execucao[]>(`/fontes/${id}/execucoes`, {
    refetchInterval: acompanhando ? 2000 : false,
  });
  const andamento = execucoes.data?.find((e) => e.id === acompanhando);
  useEffect(() => {
    if (!acompanhando || !andamento || andamento.status === "em_andamento") return;
    setAcompanhando(null);
    aviso(
      andamento.status === "sucesso"
        ? {
            titulo: "Atualização concluída.",
            texto: `${formatarNumero(andamento.gravados)} registros gravados.`,
          }
        : { tipo: "erro", titulo: "A atualização falhou.", texto: andamento.erro ?? undefined },
    );
    void cliente.invalidateQueries({ queryKey: ["/fontes"] });
  }, [acompanhando, andamento, aviso, cliente]);

  async function atualizar() {
    try {
      const e = await enviar<Execucao>("/etl/execucoes", { fonte_id: id });
      setAcompanhando(e.id);
      aviso({ titulo: RETORNO.atualizarFonte, texto: "O status muda aqui quando terminar." });
      void execucoes.refetch();
    } catch (x) {
      aviso({ tipo: "erro", titulo: "Não foi possível iniciar.", texto: (x as Error).message });
    }
  }

  if (fonte.isPending) return <Carregando />;
  if (fonte.isError) return <FalhaCarga erro={fonte.error} />;
  const f = fonte.data;
  const podeAtualizar = pode("executar_etl") && f.status !== "planejada" && !SEM_CONECTOR_MANUAL.has(f.id);

  return (
    <>
      <p className={estilos.voltar}>
        <Link to="/app/fontes">Todas as fontes</Link>
      </p>
      <CabecalhoTela
        titulo={f.nome}
        proposito={f.status === "planejada" ? PLANOS[f.id] ?? f.orgao : f.orgao}
        acoes={
          podeAtualizar && (
            <Botao onClick={atualizar} disabled={!!acompanhando} icone={<RefreshCw />}>
              {acompanhando ? "Atualizando…" : "Atualizar agora"}
            </Botao>
          )
        }
      />
      <div className={estilos.detalhe}>
        <Painel titulo="Sobre a fonte" id="f-sobre">
          <dl className={estilos.metadados}>
            <dt>Status</dt>
            <dd>
              <StatusFonte status={f.status} />
            </dd>
            <dt>Tipo de dado</dt>
            <dd>
              {TIPOS_FONTE[f.tipo] ?? f.tipo}. {GLOSSARIO[f.tipo as keyof typeof GLOSSARIO] ?? ""}
            </dd>
            <dt>Órgão</dt>
            <dd>{f.orgao}</dd>
            <dt>Licença</dt>
            <dd>{f.licenca ?? "Não informada"}</dd>
            <dt>Última carga bem-sucedida</dt>
            <dd>{f.ultima_atualizacao ? formatarDataHora(f.ultima_atualizacao) : "Nunca carregada"}</dd>
            <dt>Fica desatualizada após</dt>
            <dd>{limiteTexto(f.limite_desatualizacao_h)} sem carga nova</dd>
            <dt>Endereço</dt>
            <dd>
              <a href={f.url} target="_blank" rel="noopener noreferrer">
                {f.url.replace(/^https?:\/\//, "")}
              </a>
            </dd>
          </dl>
        </Painel>
        <Painel titulo="Execuções do ETL" id="f-execucoes">
          {execucoes.data?.length ? (
            <Tabela
              legenda="Últimas execuções desta fonte"
              legendaVisivel={false}
              linhas={execucoes.data}
              chaveLinha={(e) => e.id}
              colunas={[
                { chave: "inicio", titulo: "Início", celula: (e) => formatarDataHora(e.inicio) },
                {
                  chave: "status",
                  titulo: "Resultado",
                  celula: (e) => (
                    <span className={estilos.execucao} data-status={e.status}>
                      {STATUS_EXECUCAO[e.status] ?? e.status}
                      {e.erro && <small>{e.erro}</small>}
                    </span>
                  ),
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
          ) : (
            <VazioConvidativo
              titulo="Nenhuma execução registrada."
              texto={
                f.status === "planejada"
                  ? "O conector desta fonte ainda está em preparo."
                  : "Esta fonte ainda não foi carregada. O administrador pode iniciar a primeira carga."
              }
            />
          )}
        </Painel>
      </div>
    </>
  );
}
