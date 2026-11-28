import { useEffect, useRef, useState } from "react";
import { RefreshCw } from "lucide-react";
import { Link } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { CabecalhoTela } from "@/app/AppShell";
import { useAviso } from "@/design-system/componentes/Aviso";
import { Botao } from "@/design-system/componentes/Botao";
import { Indicador } from "@/design-system/componentes/Indicador";
import { FalhaCarga, Painel } from "@/design-system/componentes/Painel";
import { Pilula } from "@/design-system/componentes/Pilula";
import { VazioConvidativo } from "@/design-system/componentes/VazioConvidativo";
import { ListaAdaptavel } from "@/features/fluxo/ListaAdaptavel";
import { ErroApi, type Esquemas } from "@/lib/api";
import { useConsulta } from "@/lib/consultas";
import { noProduto } from "@/lib/fontes";
import { formatarDataHora, formatarNumero } from "@/lib/formatos";
import { useSessao } from "@/lib/sessao";
import { TIPOS_FONTE } from "@/textos/glossario";
import { Frescor, StatusFonte } from "./StatusFonte";
import estilos from "./Fontes.module.css";
import { acompanhar, apiComPrazo } from "./acompanhar";

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
 * Atualiza uma fonte por vez; os demais papéis apenas verificam o status (RF-16.2).
 */
function useBuscarRecentes(ativas: Fonte[], aoVerificar: () => Promise<unknown>) {
  const { pode } = useSessao();
  const aviso = useAviso();
  const cliente = useQueryClient();
  const [verificando, setVerificando] = useState(false);
  const [buscando, setBuscando] = useState(false);
  const controle = useRef<AbortController | null>(null);
  const podeExecutar = pode("executar_etl");

  useEffect(() => () => controle.current?.abort(), []);

  async function buscar() {
    if (controle.current) return;
    const c = new AbortController();
    controle.current = c;
    try {
      if (!podeExecutar) {
        setVerificando(true);
        await aoVerificar();
        aviso({ titulo: "Status verificado agora.", texto: "Só a administração pode buscar dados novos." });
        return;
      }
      setBuscando(true);
      // rápido: só o que não está em dia e as fontes que vencem em poucas horas (chuva, rios, alertas, previsão)
      const alvos = ativas.filter(
        (x) =>
          !SEM_CONECTOR_MANUAL.has(x.id) &&
          (x.status !== "atualizada" || (x.limite_desatualizacao_h ?? Infinity) <= 6),
      );
      aviso({
        titulo: "Buscando os dados mais recentes.",
        texto: `${alvos.length} fontes, uma por vez. Pode levar alguns minutos.`,
      });
      let falhas = 0,
        gravados = 0,
        semNovos = 0,
        concluidas = 0;
      for (const alvo of alvos) {
        if (c.signal.aborted) return;
        try {
          const e = await apiComPrazo<Execucao>("/etl/execucoes", c.signal, {
            method: "POST",
            body: JSON.stringify({
              fonte_id: alvo.id,
              ...(alvo.id === "open-meteo-historico" ? { limite: 45 } : {}),
            }),
          });
          const fim = await acompanhar(e.id, c.signal);
          concluidas++;
          if (fim.status === "falha") falhas++;
          else {
            gravados += fim.gravados;
            if (!fim.gravados) semNovos++;
          }
        } catch (erro) {
          if (c.signal.aborted) return;
          // já em coleta (ex.: pelo agendamento): segue para a próxima fonte
          if (erro instanceof ErroApi && erro.status === 409) continue;
          falhas++;
          aviso({
            tipo: "erro",
            titulo: `Coleta de ${alvo.nome} não concluída.`,
            texto: (erro as Error).message,
          });
          // Não inicia outra carga enquanto a situação desta permanece desconhecida.
          break;
        }
        void cliente.invalidateQueries();
      }
      if (!c.signal.aborted)
        aviso({
          tipo: falhas ? "erro" : undefined,
          titulo: falhas ? "Atualização terminou com pendências." : "Coletas concluídas.",
          texto: `${concluidas} de ${alvos.length} fontes concluídas; ${formatarNumero(gravados)} registros gravados; ${semNovos} cargas sem novos registros; ${falhas} falhas. Consulte o histórico das fontes.`,
        });
    } catch (erro) {
      if (!c.signal.aborted)
        aviso({ tipo: "erro", titulo: "Não foi possível verificar.", texto: (erro as Error).message });
    } finally {
      controle.current = null;
      if (!c.signal.aborted) {
        setBuscando(false);
        setVerificando(false);
        void cliente.invalidateQueries();
      }
    }
  }

  const ocupado = buscando || verificando;
  const botao = (
    <Botao onClick={buscar} disabled={ocupado} icone={<RefreshCw />}>
      {buscando
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
  // a tela mostra só o que está atualizado; o botão continua tentando atualizar todas as fontes em uso
  const atualizadas = ativas.filter((x) => x.status === "atualizada" && x.ultima_atualizacao);
  const { botao } = useBuscarRecentes(ativas, () => f.refetch());
  return (
    <>
      <CabecalhoTela
        titulo="Fontes de dados"
        proposito="De onde vem cada dado e quando foi atualizado pela última vez."
        acoes={f.data && botao}
      />
      {f.isError && <FalhaCarga erro={f.error} aoTentar={() => f.refetch()} />}
      {!f.isError && (
        <div className={estilos.pilha}>
          <div className={estilos.resumo}>
            <Indicador
              rotulo="Atualizadas"
              valor={f.data ? atualizadas.length : null}
              unidade="fontes"
              carregando={f.isPending}
            />
          </div>
          <Painel titulo="Em uso" id="f-uso">
            <ListaAdaptavel
              legenda="Fontes em uso, com status e última atualização"
              carregando={f.isPending}
              linhas={atualizadas}
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
                {
                  chave: "status",
                  titulo: "Status",
                  celula: (x) => (
                    <div className={estilos.estadoFonte}>
                      <StatusFonte status={x.status} />
                      {x.ultima_execucao_status === "em_andamento" && (
                        <small>
                          Coleta em andamento desde{" "}
                          {x.ultima_execucao_em
                            ? formatarDataHora(x.ultima_execucao_em)
                            : "horário indisponível"}
                        </small>
                      )}
                      {x.ultima_execucao_status === "sucesso" && x.ultima_execucao_gravados === 0 && (
                        <small>Última carga sem novos registros.</small>
                      )}
                    </div>
                  ),
                },
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
        </div>
      )}
    </>
  );
}
