import { useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";
import { Link } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { CabecalhoTela } from "@/app/AppShell";
import { useAviso } from "@/design-system/componentes/Aviso";
import { Botao } from "@/design-system/componentes/Botao";
import { Carregando, FalhaCarga, Painel } from "@/design-system/componentes/Painel";
import { Tabela } from "@/design-system/componentes/Tabela";
import { api, enviar, type Esquemas } from "@/lib/api";
import { useConsulta } from "@/lib/consultas";
import { formatarDataHora, formatarNumero } from "@/lib/formatos";
import { useSessao } from "@/lib/sessao";
import { TIPOS_FONTE } from "@/textos/glossario";
import { StatusFonte } from "./StatusFonte";
import estilos from "./Fontes.module.css";

type Fonte = Esquemas["Fonte"];
type Execucao = Esquemas["Execucao"];

/** Fontes que não têm conector do ETL para disparar daqui (a carga territorial roda pelo módulo próprio). */
const SEM_CONECTOR_MANUAL = new Set(["territorio-oficial"]);

/** O que cada fonte planejada vai trazer quando o conector existir (resumo de docs/dicionario-dados). */
export const PLANOS: Record<string, string> = {
  "ana-telemetria":
    "Chuva e nível dos rios medidos nas estações telemétricas da ANA. Exige cadastro e credenciais.",
  "apac-chuva": "Chuva acumulada em 24 h nos pluviômetros da APAC, a agência estadual de águas e clima.",
  inmet: "Medições da estação automática do INMET no Recife (A301): chuva, temperatura e umidade.",
  cemaden: "Pluviômetros automáticos do Cemaden espalhados pelos bairros.",
  "mare-marinha":
    "Tábua de maré oficial da Marinha para o Porto do Recife, para comparar com o nível previsto.",
  "recife-alagamento":
    "Ocorrências de alagamento registradas pela Defesa Civil nos Dados Abertos do Recife, marcadas como não confirmadas.",
};

/**
 * “Buscar dados mais recentes”: quem pode executar o ETL dispara todas as fontes em uso de uma vez e acompanha
 * até terminarem; os demais papéis apenas verificam de novo o status (RF-16.2).
 */
function useBuscarRecentes(ativas: Fonte[], aoVerificar: () => Promise<unknown>) {
  const { pode } = useSessao();
  const aviso = useAviso();
  const cliente = useQueryClient();
  const [pendentes, setPendentes] = useState<string[]>([]);
  const [verificando, setVerificando] = useState(false);
  const podeExecutar = pode("executar_etl");

  useEffect(() => {
    if (!pendentes.length) return;
    const t = setInterval(async () => {
      const lista = await Promise.all(
        pendentes.map((id) => api<Execucao>(`/etl/execucoes/${id}`).catch(() => null)),
      );
      if (lista.some((e) => !e || e.status === "em_andamento")) return;
      setPendentes([]);
      const falhas = lista.filter((e) => e!.status === "falha").length;
      const gravados = lista.reduce((s, e) => s + e!.gravados, 0);
      aviso(
        falhas
          ? {
              tipo: "erro",
              titulo: `${falhas} de ${lista.length} fontes falharam.`,
              texto: "Abra a fonte para ver o motivo e tente de novo.",
            }
          : { titulo: "Dados atualizados.", texto: `${formatarNumero(gravados)} registros gravados.` },
      );
      void cliente.invalidateQueries();
    }, 3000);
    return () => clearInterval(t);
  }, [pendentes, aviso, cliente]);

  async function buscar() {
    if (!podeExecutar) {
      setVerificando(true);
      await aoVerificar();
      setVerificando(false);
      aviso({ titulo: "Status verificado agora.", texto: "Só a administração pode buscar dados novos." });
      return;
    }
    const alvos = ativas.filter((x) => !SEM_CONECTOR_MANUAL.has(x.id));
    const iniciadas = await Promise.all(
      alvos.map((x) => enviar<Execucao>("/etl/execucoes", { fonte_id: x.id }).catch(() => null)),
    );
    const ids = iniciadas.filter((e): e is Execucao => !!e).map((e) => e.id);
    if (!ids.length) {
      aviso({ tipo: "erro", titulo: "Não foi possível iniciar.", texto: "Tente de novo em instantes." });
      return;
    }
    setPendentes(ids);
    aviso({
      titulo: "Buscando os dados mais recentes.",
      texto: `${ids.length} fontes em atualização. Pode levar alguns minutos; avisamos quando terminar.`,
    });
    void aoVerificar();
  }

  const ocupado = pendentes.length > 0 || verificando;
  const botao = (
    <Botao onClick={buscar} disabled={ocupado} icone={<RefreshCw />}>
      {pendentes.length
        ? "Buscando dados…"
        : verificando
          ? "Verificando…"
          : podeExecutar
            ? "Buscar dados mais recentes"
            : "Verificar status agora"}
    </Botao>
  );
  return { botao };
}

export function TelaFontes() {
  const f = useConsulta<Fonte[]>("/fontes", { refetchInterval: false });
  const ativas = f.data?.filter((x) => x.status !== "planejada") ?? [];
  const planejadas = f.data?.filter((x) => x.status === "planejada") ?? [];
  const { botao } = useBuscarRecentes(ativas, () => f.refetch());
  return (
    <>
      <CabecalhoTela
        titulo="Fontes de dados"
        proposito="De onde vem cada dado do ClimaSense, quando foi atualizado e se está em dia. Todas as fontes são reais."
        acoes={f.data && botao}
      />
      {f.isPending && <Carregando />}
      {f.isError && <FalhaCarga erro={f.error} aoTentar={() => f.refetch()} />}
      {f.data && (
        <div className={estilos.pilha}>
          <Painel titulo="Em uso" id="f-uso">
            <Tabela
              legenda="Fontes em uso, com status e última atualização"
              legendaVisivel={false}
              linhas={ativas}
              chaveLinha={(x) => x.id}
              colunas={[
                {
                  chave: "nome",
                  titulo: "Fonte",
                  celula: (x) => (
                    <span className={estilos.nomeFonte}>
                      <Link to={`/app/fontes/${x.id}`}>{x.nome}</Link>
                      <span>{x.orgao}</span>
                    </span>
                  ),
                },
                { chave: "tipo", titulo: "Tipo", celula: (x) => TIPOS_FONTE[x.tipo] ?? x.tipo },
                { chave: "status", titulo: "Status", celula: (x) => <StatusFonte status={x.status} /> },
                {
                  chave: "quando",
                  titulo: "Última atualização",
                  celula: (x) =>
                    x.ultima_atualizacao ? formatarDataHora(x.ultima_atualizacao) : "Nunca carregada",
                },
                {
                  chave: "limite",
                  titulo: "Fica desatualizada após",
                  numerica: true,
                  celula: (x) => limiteTexto(x.limite_desatualizacao_h),
                },
              ]}
            />
          </Painel>
          <Painel titulo="Planejadas" id="f-planejadas">
            <p className={estilos.explicacao}>
              Estas fontes já foram escolhidas, mas ainda não têm conector. Enquanto isso, elas não geram
              nenhum dado, e as telas que dependem delas mostram “Dados insuficientes”.
            </p>
            <ul className={estilos.planejadas}>
              {planejadas.map((x) => (
                <li key={x.id}>
                  <div>
                    <h3>
                      <Link to={`/app/fontes/${x.id}`}>{x.nome}</Link>
                    </h3>
                    <p>{PLANOS[x.id] ?? x.orgao}</p>
                  </div>
                  <StatusFonte status="planejada" />
                </li>
              ))}
            </ul>
          </Painel>
        </div>
      )}
    </>
  );
}

export function limiteTexto(horas: number) {
  if (horas % (24 * 365) === 0) return `${horas / (24 * 365)} ano${horas > 24 * 365 ? "s" : ""}`;
  if (horas % 24 === 0) return `${horas / 24} dia${horas > 24 ? "s" : ""}`;
  return `${horas} h`;
}
