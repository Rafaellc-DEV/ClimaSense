import { useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";
import { Link } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { CabecalhoTela } from "@/app/AppShell";
import { useAviso } from "@/design-system/componentes/Aviso";
import { Botao } from "@/design-system/componentes/Botao";
import { CarregandoLista } from "@/design-system/componentes/Esqueleto";
import { Dica } from "@/design-system/componentes/Dica";
import { Indicador } from "@/design-system/componentes/Indicador";
import { FalhaCarga, Painel } from "@/design-system/componentes/Painel";
import { Pilula } from "@/design-system/componentes/Pilula";
import { VazioConvidativo } from "@/design-system/componentes/VazioConvidativo";
import { ListaAdaptavel } from "@/features/fluxo/ListaAdaptavel";
import { api, enviar, type Esquemas } from "@/lib/api";
import { useConsulta } from "@/lib/consultas";
import { noProduto } from "@/lib/fontes";
import { formatarDataHora, formatarNumero } from "@/lib/formatos";
import { useSessao } from "@/lib/sessao";
import { TIPOS_FONTE } from "@/textos/glossario";
import { Frescor, StatusFonte } from "./StatusFonte";
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
  const todas = f.data?.filter(noProduto) ?? [];
  const ativas = todas.filter((x) => x.status !== "planejada");
  const planejadas = todas.filter((x) => x.status === "planejada");
  const { botao } = useBuscarRecentes(ativas, () => f.refetch());
  const conta = (s: string) => ativas.filter((x) => x.status === s).length;
  return (
    <>
      <CabecalhoTela
        titulo="Fontes de dados"
        proposito="De onde vem cada dado e se está em dia. Dado atrasado aparece como atrasado, nunca como zero."
        acoes={f.data && botao}
      />
      {f.isError && <FalhaCarga erro={f.error} aoTentar={() => f.refetch()} />}
      {!f.isError && (
        <div className={estilos.pilha}>
          <div className={estilos.resumo}>
            <Indicador
              rotulo="Atualizadas"
              valor={f.data ? conta("atualizada") : null}
              unidade="fontes"
              carregando={f.isPending}
            />
            <Indicador
              rotulo="Desatualizadas"
              valor={f.data ? conta("desatualizada") : null}
              unidade="fontes"
              carregando={f.isPending}
            />
            <Indicador
              rotulo="Com falha"
              valor={f.data ? conta("com_falha") : null}
              unidade="fontes"
              carregando={f.isPending}
            />
            <Indicador
              rotulo="Planejadas"
              valor={f.data ? planejadas.length : null}
              unidade="fontes"
              carregando={f.isPending}
            />
          </div>
          <Painel titulo="Em uso" id="f-uso">
            <ListaAdaptavel
              legenda="Fontes em uso, com status e última atualização"
              carregando={f.isPending}
              linhas={ativas}
              chaveLinha={(x) => x.id}
              vazio={<VazioConvidativo titulo="Nenhuma fonte em uso." />}
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
                { chave: "status", titulo: "Status", celula: (x) => <StatusFonte status={x.status} /> },
                {
                  chave: "frescor",
                  titulo: "Frescor",
                  celula: (x) => (
                    <Frescor
                      ultima={x.ultima_atualizacao}
                      limiteH={x.limite_desatualizacao_h}
                      status={x.status}
                    />
                  ),
                },
                {
                  chave: "quando",
                  semQuebra: true,
                  titulo: "Última atualização",
                  celula: (x) =>
                    x.ultima_atualizacao ? formatarDataHora(x.ultima_atualizacao) : "Nunca carregada",
                },
                {
                  chave: "tipo",
                  titulo: "Tipo",
                  celula: (x) => (
                    <Pilula tom="neutro" semMarca pequena>
                      {TIPOS_FONTE[x.tipo] ?? x.tipo}
                    </Pilula>
                  ),
                },
              ]}
            />
          </Painel>
          <Painel
            titulo="Planejadas"
            id="f-planejadas"
            className={estilos.planejadasPainel}
            dica="Estas fontes já foram escolhidas, mas ainda não têm conector. Enquanto isso, elas não geram nenhum dado, e as telas que dependem delas mostram “Dados insuficientes”."
          >
            {f.isPending ? (
              <CarregandoLista linhas={2} altura="5rem" />
            ) : (
              <ul className={estilos.planejadas}>
                {planejadas.map((x) => (
                  <li key={x.id}>
                    <div className={estilos.planejadaTopo}>
                      <h3>
                        <Link to={`/app/fontes/${x.id}`}>{x.nome}</Link>
                      </h3>
                      <StatusFonte status="planejada" />
                    </div>
                    <p className={estilos.plano}>
                      <span>{PLANOS[x.id] ?? x.orgao}</span>
                      <Dica
                        texto={PLANOS[x.id] ?? x.orgao}
                        rotulo={`O que traz: ${x.nome}`}
                        lado="acima"
                        alinhar="fim"
                      />
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </Painel>
        </div>
      )}
    </>
  );
}
