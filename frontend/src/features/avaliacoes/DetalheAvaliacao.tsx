import { useState, type FormEvent } from "react";
import { Pencil, Save } from "lucide-react";
import { Link, useLocation, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { CabecalhoTela } from "@/app/AppShell";
import { useTerritorios } from "@/app/FiltroFrase";
import { useAviso } from "@/design-system/componentes/Aviso";
import { Botao } from "@/design-system/componentes/Botao";
import { BotoesNivel, OPCOES_PRIORIDADE } from "@/design-system/componentes/BotoesNivel";
import { AreaTexto, Campo } from "@/design-system/componentes/Campo";
import { EtapasFluxo, LinhaDoTempo } from "@/design-system/componentes/Fluxo";
import { Carregando, FalhaCarga, Painel } from "@/design-system/componentes/Painel";
import { Selecao } from "@/design-system/componentes/Selecao";
import { SeloNivel } from "@/design-system/componentes/SeloNivel";
import type { ChaveNivel } from "@/design-system/niveis";
import { enviar, type Esquemas } from "@/lib/api";
import { useConsulta } from "@/lib/consultas";
import { dataCurta } from "@/lib/formatos";
import { buscaDoRecorte, useRecorte } from "@/lib/recorte";
import { PRIORIDADES } from "@/textos/glossario";
import { RETORNO } from "@/textos/mensagens";
import { AcoesFluxo, ListaEvidencias, type EvidenciaForm } from "@/features/fluxo/AcoesFluxo";
import { SeloEstado } from "@/features/fluxo/Estado";
import estilos from "@/features/fluxo/Fluxo.module.css";

type Detalhe = Esquemas["DetalheAvaliacao"];
const NIVEL: Record<string, ChaveNivel> = {
  sem_indicacao: "sem",
  atencao: "atencao",
  alerta: "alerta",
  critico: "critico",
};

interface Valores {
  territorio_id: string;
  periodo_inicio: string;
  periodo_fim: string;
  prioridade: string;
  justificativa: string;
  limitacoes: string;
  evidencias: EvidenciaForm[];
}

function Formulario({
  inicial,
  novo,
  aoSalvar,
}: {
  inicial: Valores;
  novo: boolean;
  aoSalvar: (v: Valores) => Promise<void>;
}) {
  const territorios = useTerritorios();
  const [v, setV] = useState(inicial);
  const [erro, setErro] = useState<string>();
  const [ocupado, setOcupado] = useState(false);
  const mudar = (p: Partial<Valores>) => setV((x) => ({ ...x, ...p }));
  async function salvar(e: FormEvent) {
    e.preventDefault();
    if (!v.justificativa.trim())
      return setErro("Escreva a justificativa: por que este território precisa (ou não) de atenção.");
    setErro(undefined);
    setOcupado(true);
    try {
      await aoSalvar(v);
    } catch (x) {
      setErro((x as Error).message);
    } finally {
      setOcupado(false);
    }
  }
  return (
    <form className={estilos.form} onSubmit={salvar} noValidate>
      {novo && (
        <div className={estilos.linha}>
          <Selecao
            rotulo="Território"
            valor={v.territorio_id}
            aoMudar={(t) => mudar({ territorio_id: t })}
            opcoes={(territorios.data ?? []).map((t) => ({
              valor: t.id,
              rotulo: t.id === "recife" ? "Recife inteiro" : t.nome_exibicao,
            }))}
          />
          <Campo
            rotulo="Período: de"
            type="date"
            value={v.periodo_inicio}
            onChange={(e) => mudar({ periodo_inicio: e.target.value })}
          />
          <Campo
            rotulo="até"
            type="date"
            value={v.periodo_fim}
            onChange={(e) => mudar({ periodo_fim: e.target.value })}
          />
        </div>
      )}
      <BotoesNivel
        nome="prioridade"
        legenda="Prioridade sugerida"
        opcoes={OPCOES_PRIORIDADE}
        valor={v.prioridade}
        aoMudar={(p) => mudar({ prioridade: p })}
      />
      <AreaTexto
        rotulo="Justificativa"
        ajuda="Por que este território precisa (ou não) de atenção. Cite os valores e as fontes."
        value={v.justificativa}
        onChange={(e) => mudar({ justificativa: e.target.value })}
        maxLength={4000}
        erro={erro}
      />
      <AreaTexto
        rotulo="Limitações"
        ajuda="O que os dados não mostram: lacunas, granularidade, fontes que faltam."
        value={v.limitacoes}
        onChange={(e) => mudar({ limitacoes: e.target.value })}
        maxLength={2000}
      />
      <div>
        <h3 className={estilos.dica}>Evidências vinculadas</h3>
        <ListaEvidencias
          evidencias={v.evidencias}
          aoRemover={(i) => mudar({ evidencias: v.evidencias.filter((_, j) => j !== i) })}
        />
      </div>
      <div className={estilos.rodape}>
        <Botao type="submit" disabled={ocupado} icone={<Save />}>
          {novo ? "Salvar rascunho" : "Salvar nova versão"}
        </Botao>
      </div>
    </form>
  );
}

/** Nova avaliação: vem do mapa ou dos cenários já com território, prioridade e evidências (RF-09.7). */
export function NovaAvaliacao() {
  const { recorte } = useRecorte();
  const [params] = useSearchParams();
  const local = useLocation();
  const navegar = useNavigate();
  const aviso = useAviso();
  const pre = (local.state ?? {}) as Partial<Valores>;
  const inicial: Valores = {
    territorio_id: pre.territorio_id ?? recorte.territorio,
    periodo_inicio: recorte.inicio,
    periodo_fim: recorte.fim,
    prioridade: pre.prioridade ?? "sem_indicacao",
    justificativa: pre.justificativa ?? "",
    limitacoes: pre.limitacoes ?? "",
    evidencias: pre.evidencias ?? [],
  };
  return (
    <>
      <p className={estilos.voltar}>
        <Link to={`/app/avaliacoes${buscaDoRecorte(params)}`}>Todas as avaliações</Link>
      </p>
      <CabecalhoTela
        titulo="Registrar avaliação"
        proposito="Diga se o território precisa de atenção, por quê e com quais evidências. Outra pessoa vai revisar."
      />
      <Painel titulo="Avaliação" id="av-nova">
        <Formulario
          novo
          inicial={inicial}
          aoSalvar={async (v) => {
            const r = await enviar<Detalhe>("/avaliacoes", v);
            aviso({ titulo: RETORNO.salvar });
            navegar(`/app/avaliacoes/${r.id}${buscaDoRecorte(params)}`, { replace: true });
          }}
        />
      </Painel>
    </>
  );
}

/** Detalhe da avaliação: formulário (quando pode editar), linha do tempo e a área de decisão do revisor (RF-10). */
export function DetalheAvaliacao() {
  const { id = "" } = useParams();
  const [params] = useSearchParams();
  const navegar = useNavigate();
  const aviso = useAviso();
  const cliente = useQueryClient();
  const r = useConsulta<Detalhe>(`/avaliacoes/${id}`);
  const [editando, setEditando] = useState(false);
  const atualizar = (d: Detalhe) => {
    cliente.setQueryData([`/avaliacoes/${id}`], d);
    void cliente.invalidateQueries({ queryKey: ["/painel/resumo"] });
    setEditando(false);
  };
  if (r.isPending) return <Carregando />;
  if (r.isError) return <FalhaCarga erro={r.error} aoTentar={() => r.refetch()} />;
  const a = r.data;
  const v = a.versao;
  const podeEditar = a.acoes.includes("editar");
  const formAberto = podeEditar && (editando || a.estado === "rascunho" || a.estado === "devolvido");
  const decide = a.acoes.includes("aprovar");

  return (
    <>
      <p className={estilos.voltar}>
        <Link to={`/app/avaliacoes${buscaDoRecorte(params)}`}>Todas as avaliações</Link>
      </p>
      <CabecalhoTela
        titulo={`Avaliação: ${a.territorio_nome}`}
        proposito={`Período de ${dataCurta(a.periodo_inicio)} a ${dataCurta(a.periodo_fim)}. Versão ${
          v.numero
        }, escrita por ${v.autor_nome}.`}
        acoes={<SeloEstado estado={a.estado} avaliacao />}
      />
      <Painel titulo="Etapas" id="av-etapas" className={estilos.voltar}>
        <EtapasFluxo estado={a.estado} comPublicacao={false} />
      </Painel>
      <div className={estilos.grade}>
        <Painel
          titulo={formAberto ? "Editar avaliação" : "Conteúdo da versão atual"}
          id="av-conteudo"
          acoes={
            podeEditar &&
            !formAberto && (
              <Botao variante="secundario" icone={<Pencil />} onClick={() => setEditando(true)}>
                Editar (cria nova versão)
              </Botao>
            )
          }
        >
          {formAberto ? (
            <>
              {(a.estado === "em_revisao" || a.estado === "aprovado") && (
                <p className={estilos.dica}>
                  Salvar cria a versão {v.numero + 1}, que volta para revisão. A versão {v.numero} fica
                  guardada.
                </p>
              )}
              <Formulario
                novo={false}
                inicial={{
                  territorio_id: a.territorio_id,
                  periodo_inicio: a.periodo_inicio,
                  periodo_fim: a.periodo_fim,
                  prioridade: v.prioridade,
                  justificativa: v.justificativa,
                  limitacoes: v.limitacoes ?? "",
                  evidencias: v.evidencias as unknown as EvidenciaForm[],
                }}
                aoSalvar={async (x) => {
                  const d = await enviar<Detalhe>(
                    `/avaliacoes/${id}`,
                    {
                      prioridade: x.prioridade,
                      justificativa: x.justificativa,
                      limitacoes: x.limitacoes,
                      evidencias: x.evidencias,
                    },
                    "PUT",
                  );
                  aviso({ titulo: "Nova versão salva." });
                  atualizar(d);
                }}
              />
            </>
          ) : (
            <div className={estilos.leitura}>
              <div>
                <h3>Prioridade sugerida</h3>
                <SeloNivel nivel={NIVEL[v.prioridade] ?? "sem"} rotulo={PRIORIDADES[v.prioridade]} grande />
              </div>
              <div>
                <h3>Justificativa</h3>
                <p>{v.justificativa}</p>
              </div>
              {v.limitacoes && (
                <div>
                  <h3>Limitações</h3>
                  <p>{v.limitacoes}</p>
                </div>
              )}
              <div>
                <h3>Evidências</h3>
                <ListaEvidencias evidencias={v.evidencias as unknown as EvidenciaForm[]} />
              </div>
            </div>
          )}
        </Painel>
        <div className={estilos.lateral}>
          <Painel titulo={decide ? "Sua decisão" : "Próximo passo"} id="av-decisao">
            {decide && (
              <p className={estilos.dica}>
                Você está revisando a versão {v.numero}, de {v.autor_nome}. Aprove se as evidências sustentam
                a prioridade, ou devolva explicando o que ajustar.
              </p>
            )}
            {!a.acoes.some((x) => x !== "editar") && (
              <p className={estilos.dica}>
                {a.estado === "em_revisao"
                  ? "Aguardando a revisão de outra pessoa da equipe. Quem escreveu não aprova a própria versão."
                  : a.estado === "encerrado"
                    ? "Esta avaliação foi encerrada e fica no histórico."
                    : "Nenhuma ação disponível para você agora."}
              </p>
            )}
            <AcoesFluxo<Detalhe>
              base={`/avaliacoes/${id}`}
              acoes={a.acoes}
              aoConcluir={atualizar}
              consequencias={{
                encerrar:
                  "Encerrar tira a avaliação do fluxo. Ela fica no histórico e não pode mais ser editada.",
              }}
            />
            {a.estado === "aprovado" && (
              <Botao
                variante="secundario"
                onClick={() =>
                  navegar(`/app/comunicados/novo${buscaDoRecorte(params)}`, {
                    state: {
                      avaliacao_id: a.id,
                      territorios: [a.territorio_id],
                      evidencias: v.evidencias,
                      prioridade: v.prioridade,
                    },
                  })
                }
              >
                Escrever comunicado a partir desta avaliação
              </Botao>
            )}
          </Painel>
          <Painel titulo="Linha do tempo" id="av-tempo">
            <LinhaDoTempo eventos={a.linha_do_tempo} />
          </Painel>
        </div>
      </div>
    </>
  );
}
