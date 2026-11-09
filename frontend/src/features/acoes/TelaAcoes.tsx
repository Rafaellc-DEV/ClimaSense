import { useMemo, useState, type FormEvent } from "react";
import { Trash2 } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { CabecalhoTela } from "@/design-system/componentes/CabecalhoTela";
import { useAviso } from "@/design-system/componentes/Aviso";
import { Botao } from "@/design-system/componentes/Botao";
import { AreaTexto, Campo } from "@/design-system/componentes/Campo";
import { Confirmacao } from "@/design-system/componentes/Dialogo";
import { CarregandoLista } from "@/design-system/componentes/Esqueleto";
import { EstadoDados } from "@/design-system/componentes/EstadoDados";
import { Indicador } from "@/design-system/componentes/Indicador";
import { Painel } from "@/design-system/componentes/Painel";
import { Pilula, type TomPilula } from "@/design-system/componentes/Pilula";
import { Segmentado } from "@/design-system/componentes/Segmentado";
import { consulta, enviar, ErroApi } from "@/lib/api";
import { useConsultaViva, ultimaAtualizacao } from "@/lib/consultas";
import { diaNoRecife, formatarHora, somarDias } from "@/lib/formatos";
import { useSessao } from "@/lib/sessao";
import campo from "@/design-system/componentes/Campo.module.css";
import { EstadoConsulta, invalidarPrefixo } from "@/features/evento/Evento";
import { diaMes, nomeCurto, quandoAs } from "@/features/evento/textos";
import { listaDe, type Acao, type SituacaoAcao } from "@/features/evento/tipos";
import { DocumentoRelatorio } from "@/features/boletim/DocumentoRelatorio";
import type { ItemPrioridadeTerritorio } from "@/features/mapa/tipos";
import { SeletorTerritorio } from "./SeletorTerritorio";
import { agoraNoRecife, isoDeDiaHora } from "./tempo";
import estilos from "./Acoes.module.css";

const ROTULO: Record<SituacaoAcao, string> = {
  planejada: "Planejada",
  em_andamento: "Em andamento",
  concluida: "Concluída",
  cancelada: "Cancelada",
};
const TOM: Record<SituacaoAcao, TomPilula> = {
  planejada: "neutro",
  em_andamento: "info",
  concluida: "sucesso",
  cancelada: "neutro",
};

type Periodo = "todo" | "hoje" | "7d" | "30d";
const PERIODOS: { valor: Periodo; rotulo: string }[] = [
  { valor: "todo", rotulo: "Todo o período" },
  { valor: "hoje", rotulo: "Hoje" },
  { valor: "7d", rotulo: "Últimos 7 dias" },
  { valor: "30d", rotulo: "Últimos 30 dias" },
];
const DIAS: Record<Exclude<Periodo, "todo">, number> = { hoje: 0, "7d": 7, "30d": 30 };

/** Distritos mais vulneráveis primeiro (RF-22); dentro do distrito, a ação mais recente primeiro. */
export function ordenarAcoes(acoes: Acao[], prioridade: ItemPrioridadeTerritorio[]): Acao[] {
  const pos = new Map(
    prioridade.filter((p) => p.nivel === "distrito").map((p) => [p.territorio_id, p.posicao]),
  );
  const rank = (a: Acao) => pos.get(a.distrito_id ?? "") ?? Number.MAX_SAFE_INTEGER;
  const quando = (a: Acao) => a.inicio_em ?? a.criada_em ?? "";
  return [...acoes].sort((a, b) => rank(a) - rank(b) || quando(b).localeCompare(quando(a)));
}

const horario = (iso: string) => `${diaMes(iso)} ${formatarHora(iso).replace("h", ":")}`;
const horarioDe = (a: Acao) => {
  const q = a.inicio_em ?? a.criada_em;
  return q ? horario(q) : "Sem horário";
};

function useGravar() {
  const cliente = useQueryClient();
  const avisar = useAviso();
  const [ocupado, setOcupado] = useState(false);
  async function executar(
    chamada: () => Promise<unknown>,
    confirmacao: string,
    falha: string,
  ): Promise<boolean> {
    setOcupado(true);
    try {
      await chamada();
      void invalidarPrefixo(cliente, "/acoes");
      void invalidarPrefixo(cliente, "/boletim");
      avisar({ titulo: confirmacao });
      return true;
    } catch (x) {
      avisar({ titulo: falha, texto: x instanceof ErroApi ? x.message : "Tente de novo.", tipo: "erro" });
      return false;
    } finally {
      setOcupado(false);
    }
  }
  const gravar = (caminho: string, corpo: unknown, metodo: string, confirmacao: string) =>
    executar(() => enviar(caminho, corpo, metodo), confirmacao, "Não foi possível salvar.");
  const excluir = (id: string) =>
    executar(
      () => enviar(`/acoes/${encodeURIComponent(id)}`, undefined, "DELETE"),
      "Ação excluída.",
      "Não foi possível excluir a ação.",
    );
  return { ocupado, gravar, excluir };
}

/**
 * Ações (RF-15, RF-16, RF-17): o que a equipe fez na cidade, em cada distrito e em cada bairro. Filtros por território
 * e período, três totais derivados do registro, a lista das ações (com exclusão), o formulário de registro e o
 * relatório executivo para a Secretaria de Saúde, editável, na mesma página.
 */
export function TelaAcoes() {
  const { pode } = useSessao();
  const podeEditar = pode("editar");
  const [territorio, setTerritorio] = useState("");
  const [periodo, setPeriodo] = useState<Periodo>("todo");
  const hoje = diaNoRecife();
  const caminho = `/acoes${consulta({
    ordem: "prioridade",
    territorio_id: territorio,
    desde: periodo === "todo" ? "" : somarDias(hoje, -DIAS[periodo]),
  })}`;
  const r = useConsultaViva<unknown>(caminho);
  const prioridade = useConsultaViva<unknown>("/territorios/prioridade");
  const todas = useMemo(
    () => ordenarAcoes(listaDe<Acao>(r.data), listaDe<ItemPrioridadeTerritorio>(prioridade.data)),
    [r.data, prioridade.data],
  );
  const conta = (s: SituacaoAcao) => todas.filter((a) => a.situacao === s).length;
  const ultima = todas
    .map((a) => a.atualizada_em ?? a.criada_em ?? "")
    .sort()
    .pop();
  const fonte = [{ nome: "Registro da equipe", atualizadoEm: ultima || null }];
  const cartao = (rotulo: string, n: number, unidade: string) => (
    <Indicador
      rotulo={rotulo}
      valor={String(n)}
      unidade={unidade}
      carregando={r.isPending}
      selo={<Pilula>Derivado</Pilula>}
      explicacao="Contagem das ações do registro da equipe, no território e período escolhidos."
      fonte={fonte}
    />
  );

  return (
    <>
      <div className={estilos.naoImprimir}>
        <CabecalhoTela
          titulo="Ações"
          proposito="O que a equipe fez na cidade, em cada distrito e em cada bairro, e o relatório para a Secretaria de Saúde."
          atualizadoEm={ultimaAtualizacao(r, prioridade)}
          acoes={
            <div className={estilos.filtros}>
              <SeletorTerritorio
                rotulo="Território"
                niveis={["municipio", "distrito", "bairro"]}
                vazio="Recife — todos os distritos"
                valor={territorio}
                aoMudar={setTerritorio}
              />
              <div className={campo.campo}>
                <label htmlFor="ac-periodo" className={campo.rotulo}>
                  Período
                </label>
                <select
                  id="ac-periodo"
                  className={campo.entrada}
                  value={periodo}
                  onChange={(e) => setPeriodo(e.target.value as Periodo)}
                >
                  {PERIODOS.map((p) => (
                    <option key={p.valor} value={p.valor}>
                      {p.rotulo}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          }
        />
      </div>
      <div className={estilos.pagina}>
        <div className={`${estilos.naoImprimir} ${estilos.pagina}`}>
          {r.isError ? (
            <EstadoConsulta erro={r.error} oQue="as ações" aoTentar={() => r.refetch()} />
          ) : (
            <section className={estilos.cartoes} aria-label="Totais das ações">
              {cartao("Em andamento", conta("em_andamento"), "ações abertas agora")}
              {cartao("Planejadas", conta("planejada"), "ainda não iniciadas")}
              {cartao("Concluídas", conta("concluida"), "no período")}
            </section>
          )}

          <div className={`${estilos.principal} ${podeEditar ? estilos.comFormulario : ""}`}>
            {podeEditar && <FormularioAcao />}
            <Painel id="ac-tabela" titulo="Ações do evento">
              {r.isSuccess && todas.length === 0 ? (
                <EstadoDados tipo="insuficiente" titulo="Nenhuma ação registrada.">
                  Isso não quer dizer que nada esteja sendo feito: registre aqui o que a equipe faz.
                </EstadoDados>
              ) : r.isPending ? (
                <CarregandoLista linhas={4} altura="5rem" />
              ) : (
                <ul className={estilos.lista} aria-label="Ações do evento">
                  {todas.map((a) => (
                    <li key={String(a.id)} className={estilos.acao}>
                      <div className={estilos.acaoTopo}>
                        <Onde acao={a} />
                        <span className={estilos.meta}>{horarioDe(a)}</span>
                      </div>
                      <p className={estilos.texto}>
                        <b>{a.descricao}</b>
                      </p>
                      <div className={estilos.acaoRodape}>
                        <span className={estilos.meta}>Responsável: {a.responsavel ?? "não informado"}</span>
                        <div className={estilos.acaoControles}>
                          <Status acao={a} podeEditar={podeEditar} />
                          {podeEditar && <Excluir acao={a} />}
                        </div>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
              {r.isSuccess && (
                <p className={estilos.meta}>
                  Fonte: registro da equipe
                  {ultima ? `, última atualização ${quandoAs(ultima)}` : ", sem hora de atualização"}.
                </p>
              )}
            </Painel>
          </div>
        </div>

        <DocumentoRelatorio />
      </div>
    </>
  );
}

function nomeOnde(a: Acao): string {
  return a.territorio_id === "recife" || a.territorio_nivel === "municipio"
    ? "Cidade"
    : nomeCurto(a.territorio_nome ?? a.territorio_id);
}

function Onde({ acao: a }: { acao: Acao }) {
  const distrito =
    a.territorio_nivel === "bairro" && (a.distrito_nome ?? a.distrito_id)
      ? nomeCurto(a.distrito_nome ?? String(a.distrito_id))
      : null;
  return (
    <span className={estilos.distrito}>
      {nomeOnde(a)}
      {distrito && <small className={estilos.doDistrito}> · {distrito}</small>}
    </span>
  );
}

function Status({ acao: a, podeEditar }: { acao: Acao; podeEditar: boolean }) {
  const { ocupado, gravar } = useGravar();
  function mudar(nova: SituacaoAcao) {
    if (nova === a.situacao) return;
    void gravar(
      `/acoes/${encodeURIComponent(String(a.id))}`,
      nova === "concluida" ? { situacao: nova, fim_em: new Date().toISOString() } : { situacao: nova },
      "PATCH",
      "Status atualizado.",
    );
  }
  return (
    <span className={estilos.status}>
      <Pilula tom={TOM[a.situacao]}>{ROTULO[a.situacao]}</Pilula>
      {podeEditar && (
        <select
          className={`${campo.entrada} ${estilos.statusSelect}`}
          value={a.situacao}
          disabled={ocupado}
          aria-label={`Mudar o status da ação em ${nomeOnde(a)}`}
          onChange={(e) => mudar(e.target.value as SituacaoAcao)}
        >
          {(Object.keys(ROTULO) as SituacaoAcao[]).map((s) => (
            <option key={s} value={s}>
              {ROTULO[s]}
            </option>
          ))}
        </select>
      )}
    </span>
  );
}

function Excluir({ acao: a }: { acao: Acao }) {
  const { ocupado, excluir } = useGravar();
  const [confirmando, setConfirmando] = useState(false);
  return (
    <>
      <Botao
        variante="perigo"
        icone={<Trash2 />}
        disabled={ocupado}
        aria-label={`Excluir a ação em ${nomeOnde(a)}`}
        onClick={() => setConfirmando(true)}
      >
        Excluir
      </Botao>
      <Confirmacao
        aberto={confirmando}
        aoMudar={setConfirmando}
        titulo="Excluir esta ação?"
        consequencia="Isso não pode ser desfeito."
        rotuloConfirmar="Excluir"
        perigo
        aoConfirmar={() => {
          setConfirmando(false);
          void excluir(String(a.id));
        }}
      />
    </>
  );
}

type Escopo = "cidade" | "distrito" | "bairro";

function FormularioAcao() {
  const inicial = () => ({
    escopo: "distrito" as Escopo,
    territorio: "",
    texto: "",
    responsavel: "",
    situacao: "em_andamento" as SituacaoAcao,
    ...agoraNoRecife(),
  });
  const [v, setV] = useState(inicial);
  const [erros, setErros] = useState<{
    territorio?: string;
    texto?: string;
    responsavel?: string;
    quando?: string;
  }>({});
  const { ocupado, gravar } = useGravar();
  const territorioId = v.escopo === "cidade" ? "recife" : v.territorio;

  async function registrar(e: FormEvent) {
    e.preventDefault();
    const quando = isoDeDiaHora(v.dia, v.hora);
    const f = {
      territorio: territorioId
        ? undefined
        : v.escopo === "bairro"
          ? "Escolha o bairro."
          : "Escolha o distrito.",
      texto: v.texto.trim() ? undefined : "Escreva o que foi feito, em uma frase.",
      responsavel: v.responsavel.trim() ? undefined : "Informe quem é o responsável.",
      quando: !quando
        ? "Informe o dia e a hora."
        : v.situacao !== "planejada" && Date.parse(quando) > Date.now() + 60_000
          ? "Só ações planejadas podem ter dia e hora no futuro."
          : undefined,
    };
    setErros(f);
    if (f.territorio || f.texto || f.responsavel || f.quando || !quando) return;
    const ok = await gravar(
      "/acoes",
      {
        territorio_id: territorioId,
        tipo: "outro",
        descricao: v.texto.trim(),
        responsavel: v.responsavel.trim(),
        situacao: v.situacao,
        inicio_em: quando,
        ...(v.situacao === "concluida" ? { fim_em: new Date().toISOString() } : {}),
      },
      "POST",
      "Ação registrada.",
    );
    if (ok) setV(inicial());
  }

  return (
    <form className={estilos.caixa} onSubmit={registrar} noValidate aria-label="Registrar ação">
      <h2>Registrar ação</h2>
      <p className={estilos.meta}>Responsável, status e horário são obrigatórios.</p>
      <Segmentado
        rotulo="Onde foi a ação"
        opcoes={[
          { valor: "cidade", rotulo: "Cidade" },
          { valor: "distrito", rotulo: "Distrito" },
          { valor: "bairro", rotulo: "Bairro" },
        ]}
        valor={v.escopo}
        aoMudar={(escopo: Escopo) => setV((a) => ({ ...a, escopo, territorio: "" }))}
      />
      {v.escopo === "distrito" && (
        <SeletorTerritorio
          rotulo="Distrito"
          niveis={["distrito"]}
          vazio="Escolha o distrito"
          valor={v.territorio}
          aoMudar={(t) => setV((a) => ({ ...a, territorio: t }))}
          erro={erros.territorio}
          obrigatorio
        />
      )}
      {v.escopo === "bairro" && (
        <SeletorTerritorio
          rotulo="Bairro"
          niveis={["bairro"]}
          vazio="Escolha o bairro"
          valor={v.territorio}
          aoMudar={(t) => setV((a) => ({ ...a, territorio: t }))}
          erro={erros.territorio}
          obrigatorio
        />
      )}
      <AreaTexto
        privacidade
        rotulo="Descrição"
        rows={3}
        maxLength={2000}
        placeholder="Ex.: visita das equipes de saúde às famílias da encosta"
        value={v.texto}
        onChange={(e) => setV((a) => ({ ...a, texto: e.target.value }))}
        erro={erros.texto}
      />
      <div className={estilos.dupla}>
        <Campo
          rotulo="Responsável"
          value={v.responsavel}
          maxLength={160}
          onChange={(e) => setV((a) => ({ ...a, responsavel: e.target.value }))}
          erro={erros.responsavel}
        />
        <Campo
          rotulo="Horário"
          type="datetime-local"
          value={`${v.dia}T${v.hora}`}
          onChange={(e) => {
            const [dia = "", hora = ""] = e.target.value.split("T");
            setV((a) => ({ ...a, dia, hora }));
          }}
          erro={erros.quando}
        />
      </div>
      <div className={campo.campo}>
        <label htmlFor="ac-status" className={campo.rotulo}>
          Status
        </label>
        <select
          id="ac-status"
          className={campo.entrada}
          value={v.situacao}
          onChange={(e) => setV((a) => ({ ...a, situacao: e.target.value as SituacaoAcao }))}
        >
          <option value="planejada">Planejada</option>
          <option value="em_andamento">Em andamento</option>
          <option value="concluida">Concluída</option>
        </select>
      </div>
      <div>
        <Botao type="submit" disabled={ocupado}>
          {ocupado ? "Registrando…" : "Registrar ação"}
        </Botao>
      </div>
    </form>
  );
}
