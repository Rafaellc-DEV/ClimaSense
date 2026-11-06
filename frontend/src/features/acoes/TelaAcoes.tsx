import { useMemo, useState, type FormEvent } from "react";
import { FileText } from "lucide-react";
import { Link } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { CabecalhoTela } from "@/design-system/componentes/CabecalhoTela";
import { useAviso } from "@/design-system/componentes/Aviso";
import { Botao, classesBotao } from "@/design-system/componentes/Botao";
import { AreaTexto, Campo } from "@/design-system/componentes/Campo";
import { CarregandoLista } from "@/design-system/componentes/Esqueleto";
import { EstadoDados } from "@/design-system/componentes/EstadoDados";
import { Painel } from "@/design-system/componentes/Painel";
import { Pilula, type TomPilula } from "@/design-system/componentes/Pilula";
import { Segmentado } from "@/design-system/componentes/Segmentado";
import { enviar, ErroApi } from "@/lib/api";
import { useConsulta, useConsultaViva, ultimaAtualizacao } from "@/lib/consultas";
import { formatarDataHora } from "@/lib/formatos";
import { useSessao } from "@/lib/sessao";
import campo from "@/design-system/componentes/Campo.module.css";
import { EstadoConsulta, invalidarPrefixo, SelecaoTerritorio } from "@/features/evento/Evento";
import { nomeCurto, quandoAs } from "@/features/evento/textos";
import {
  desembrulhar,
  listaDe,
  type Acao,
  type EventoAcao,
  type SituacaoAcao,
} from "@/features/evento/tipos";
import type { ItemPrioridadeTerritorio } from "@/features/mapa/tipos";
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
const ABERTAS: SituacaoAcao[] = ["em_andamento", "planejada"];

/** Distritos mais vulneráveis primeiro (RF-22); dentro do distrito, a ação mais recente primeiro. */
export function ordenarAcoes(acoes: Acao[], prioridade: ItemPrioridadeTerritorio[]): Acao[] {
  const pos = new Map(
    prioridade.filter((p) => p.nivel === "distrito").map((p) => [p.territorio_id, p.posicao]),
  );
  const rank = (a: Acao) => pos.get(a.distrito_id ?? "") ?? Number.MAX_SAFE_INTEGER;
  const quando = (a: Acao) => a.inicio_em ?? a.criada_em ?? "";
  return [...acoes].sort((a, b) => rank(a) - rank(b) || quando(b).localeCompare(quando(a)));
}

function useGravar() {
  const cliente = useQueryClient();
  const avisar = useAviso();
  const [ocupado, setOcupado] = useState(false);
  async function gravar(caminho: string, corpo: unknown, metodo: string, confirmacao: string) {
    setOcupado(true);
    try {
      await enviar(caminho, corpo, metodo);
      void invalidarPrefixo(cliente, "/acoes");
      void invalidarPrefixo(cliente, "/boletim");
      avisar({ titulo: confirmacao });
      return true;
    } catch (x) {
      avisar({
        titulo: "Não foi possível salvar.",
        texto: x instanceof ErroApi ? x.message : "Tente de novo.",
        tipo: "erro",
      });
      return false;
    } finally {
      setOcupado(false);
    }
  }
  return { ocupado, gravar };
}

/**
 * Ações (RF-15, RF-16, RF-17): registrar o que a equipe fez em cada distrito, acompanhar o que está em andamento
 * (distritos mais vulneráveis primeiro) e abrir o relatório executivo. Registro manual, com hora e autor.
 */
export function TelaAcoes() {
  const { pode } = useSessao();
  const podeEditar = pode("editar");
  const r = useConsultaViva<unknown>("/acoes?ordem=prioridade");
  const prioridade = useConsultaViva<unknown>("/territorios/prioridade");
  const todas = useMemo(
    () => ordenarAcoes(listaDe<Acao>(r.data), listaDe<ItemPrioridadeTerritorio>(prioridade.data)),
    [r.data, prioridade.data],
  );
  const abertas = todas.filter((a) => ABERTAS.includes(a.situacao));
  const fechadas = todas.filter((a) => !ABERTAS.includes(a.situacao));
  const ultima = todas
    .map((a) => a.atualizada_em ?? a.criada_em ?? "")
    .sort()
    .pop();

  return (
    <>
      <CabecalhoTela
        titulo="Ações"
        proposito="O que a equipe está fazendo em cada distrito, quem cuida e desde quando."
        atualizadoEm={ultimaAtualizacao(r, prioridade)}
        acoes={
          <Link to="/app/acoes/relatorio" className={classesBotao("secundario")}>
            <FileText aria-hidden="true" size={20} /> Relatório executivo
          </Link>
        }
      />
      <div className={estilos.pagina}>
        {podeEditar && <FormularioAcao />}

        <Painel id="ac-andamento" titulo={`Em andamento${r.isSuccess ? ` (${abertas.length})` : ""}`}>
          {r.isPending && <CarregandoLista linhas={3} altura="5rem" texto="Carregando as ações…" />}
          {r.isError && <EstadoConsulta erro={r.error} oQue="as ações" aoTentar={() => r.refetch()} />}
          {r.isSuccess && todas.length === 0 && (
            <EstadoDados tipo="insuficiente" titulo="Nenhuma ação registrada.">
              Isso não quer dizer que nada esteja sendo feito: registre aqui o que a equipe faz em cada
              distrito.
            </EstadoDados>
          )}
          {r.isSuccess && todas.length > 0 && abertas.length === 0 && (
            <p className={estilos.vazio}>Nenhuma ação em andamento ou planejada.</p>
          )}
          {abertas.length > 0 && (
            <ul className={estilos.lista}>
              {abertas.map((a) => (
                <CartaoAcao key={a.id} acao={a} podeEditar={podeEditar} />
              ))}
            </ul>
          )}
          {fechadas.length > 0 && (
            <details className={estilos.recolhido}>
              <summary>Concluídas e canceladas ({fechadas.length})</summary>
              <ul className={estilos.lista}>
                {fechadas.map((a) => (
                  <CartaoAcao key={a.id} acao={a} podeEditar={podeEditar} />
                ))}
              </ul>
            </details>
          )}
          {r.isSuccess && (
            <p className={estilos.meta}>
              Fonte: registro da equipe
              {ultima ? `, última atualização ${quandoAs(ultima)}` : ", sem hora de atualização"}.
            </p>
          )}
        </Painel>
      </div>
    </>
  );
}

function CartaoAcao({ acao: a, podeEditar }: { acao: Acao; podeEditar: boolean }) {
  const { ocupado, gravar } = useGravar();
  const [historico, setHistorico] = useState(false);
  const quando = a.inicio_em ?? a.criada_em;
  const nome =
    a.territorio_id === "recife" ? "Recife inteiro" : nomeCurto(a.territorio_nome ?? a.territorio_id);
  const idSel = `st-${a.id}`;
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
    <li className={estilos.acao}>
      <div className={estilos.acaoTopo}>
        <span className={estilos.distrito}>{nome}</span>
        <Pilula tom={TOM[a.situacao]}>{ROTULO[a.situacao]}</Pilula>
      </div>
      <p className={estilos.texto}>{a.descricao}</p>
      <p className={estilos.meta}>
        {a.responsavel ? `Responsável: ${a.responsavel}. ` : "Sem responsável informado. "}
        {quando ? `${a.situacao === "planejada" ? "Para" : "Desde"} ${quandoAs(quando)}. ` : ""}
        {a.fim_em && a.situacao === "concluida" ? `Concluída ${quandoAs(a.fim_em)}. ` : ""}
        {a.autor_nome ? `Registrada por ${a.autor_nome}.` : ""}
      </p>
      {podeEditar && (
        <div className={estilos.status}>
          <label htmlFor={idSel}>Status</label>
          <select
            id={idSel}
            className={campo.entrada}
            value={a.situacao}
            disabled={ocupado}
            aria-label={`Mudar o status da ação em ${nome}`}
            onChange={(e) => mudar(e.target.value as SituacaoAcao)}
          >
            {(Object.keys(ROTULO) as SituacaoAcao[]).map((s) => (
              <option key={s} value={s}>
                {ROTULO[s]}
              </option>
            ))}
          </select>
        </div>
      )}
      <details className={estilos.recolhido} onToggle={(e) => setHistorico(e.currentTarget.open)}>
        <summary>Histórico</summary>
        {historico && <Historico id={String(a.id)} />}
      </details>
    </li>
  );
}

function Historico({ id }: { id: string }) {
  const r = useConsulta<unknown>(`/acoes/${encodeURIComponent(id)}`);
  const linha = (desembrulhar<{ linha_do_tempo?: EventoAcao[] }>(r.data)?.linha_do_tempo ??
    []) as EventoAcao[];
  if (r.isPending) return <p className={estilos.meta}>Carregando o histórico…</p>;
  if (r.isError) return <EstadoConsulta erro={r.error} oQue="o histórico" aoTentar={() => r.refetch()} />;
  if (linha.length === 0) return <p className={estilos.meta}>Sem histórico registrado.</p>;
  return (
    <ol className={estilos.historico}>
      {linha.map((e) => (
        <li key={e.id}>
          <b>{formatarDataHora(e.em)}</b>, {e.autor_nome}: {e.texto}
        </li>
      ))}
    </ol>
  );
}

function FormularioAcao() {
  const inicial = () => ({
    territorio: "",
    texto: "",
    responsavel: "",
    situacao: "em_andamento" as SituacaoAcao,
    ...agoraNoRecife(),
  });
  const [v, setV] = useState(inicial);
  const [erros, setErros] = useState<{ territorio?: string; texto?: string; quando?: string }>({});
  const { ocupado, gravar } = useGravar();

  async function registrar(e: FormEvent) {
    e.preventDefault();
    const quando = isoDeDiaHora(v.dia, v.hora);
    const f = {
      territorio: v.territorio ? undefined : "Escolha o distrito.",
      texto: v.texto.trim() ? undefined : "Escreva o que foi feito, em uma frase.",
      quando: !quando
        ? "Informe o dia e a hora."
        : v.situacao !== "planejada" && Date.parse(quando) > Date.now() + 60_000
          ? "Só ações planejadas podem ter dia e hora no futuro."
          : undefined,
    };
    setErros(f);
    if (f.territorio || f.texto || f.quando || !quando) return;
    const ok = await gravar(
      "/acoes",
      {
        territorio_id: v.territorio,
        tipo: "outro",
        descricao: v.texto.trim(),
        responsavel: v.responsavel.trim() || null,
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
      <SelecaoTerritorio
        rotulo="Distrito"
        vazio="Escolha o distrito"
        niveis={["municipio", "distrito"]}
        valor={v.territorio}
        aoMudar={(t) => setV((a) => ({ ...a, territorio: t }))}
        erro={erros.territorio}
        obrigatorio
      />
      <AreaTexto
        privacidade
        rotulo="O que foi feito"
        rows={2}
        maxLength={2000}
        value={v.texto}
        onChange={(e) => setV((a) => ({ ...a, texto: e.target.value }))}
        erro={erros.texto}
      />
      <Campo
        rotulo="Responsável (órgão ou pessoa)"
        value={v.responsavel}
        maxLength={160}
        onChange={(e) => setV((a) => ({ ...a, responsavel: e.target.value }))}
      />
      <Segmentado
        rotulo="Status"
        opcoes={[
          { valor: "planejada", rotulo: "Planejada" },
          { valor: "em_andamento", rotulo: "Em andamento" },
          { valor: "concluida", rotulo: "Concluída" },
        ]}
        valor={v.situacao}
        aoMudar={(s) => setV((a) => ({ ...a, situacao: s }))}
      />
      <div className={estilos.dupla}>
        <Campo
          rotulo="Dia"
          type="date"
          value={v.dia}
          onChange={(e) => setV((a) => ({ ...a, dia: e.target.value }))}
          erro={erros.quando}
        />
        <Campo
          rotulo="Hora"
          type="time"
          value={v.hora}
          onChange={(e) => setV((a) => ({ ...a, hora: e.target.value }))}
        />
      </div>
      <div>
        <Botao type="submit" disabled={ocupado}>
          {ocupado ? "Registrando…" : "Registrar ação"}
        </Botao>
      </div>
    </form>
  );
}
