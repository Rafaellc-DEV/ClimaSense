import { useQueries } from "@tanstack/react-query";
import { Painel } from "@/design-system/componentes/Painel";
import { EstadoConsulta } from "@/features/evento/Evento";
import { diaMes, nomeCurto } from "@/features/evento/textos";
import { desembrulhar, type Acao, type EventoAcao } from "@/features/evento/tipos";
import { api } from "@/lib/api";
import { useConsulta } from "@/lib/consultas";
import { formatarHora } from "@/lib/formatos";
import { useSessao } from "@/lib/sessao";
import estilos from "./Acoes.module.css";

const LIMITE_ACOES = 12;
const LIMITE_LINHAS = 10;

interface Linha {
  chave: string;
  em: string;
  texto: string;
}

interface RegistroAdmin {
  id: number | string;
  em: string;
  usuario_nome?: string | null;
  acao: string;
  detalhes?: Record<string, unknown>;
}

const hora = (iso: string) => `${diaMes(iso)} ${formatarHora(iso).replace("h", ":")}`;

/**
 * Trilha das ações: inclusões e mudanças de status vêm da linha do tempo de cada ação (só-inclusão, com autor e
 * hora). As exclusões ficam na auditoria do sistema, que só a administração consulta: quem administra as vê aqui.
 */
export function Auditoria({ acoes }: { acoes: Acao[] }) {
  const { pode } = useSessao();
  const admin = pode("administrar");
  const recentes = [...acoes]
    .sort((a, b) =>
      (b.atualizada_em ?? b.criada_em ?? "").localeCompare(a.atualizada_em ?? a.criada_em ?? ""),
    )
    .slice(0, LIMITE_ACOES);
  const linhasDoTempo = useQueries({
    queries: recentes.map((a) => ({
      queryKey: [`/acoes/${a.id}`],
      queryFn: () => api<unknown>(`/acoes/${encodeURIComponent(String(a.id))}`),
      staleTime: 60_000,
    })),
  });
  const exclusoes = useConsulta<{ itens?: RegistroAdmin[] }>(
    admin ? "/admin/auditoria?acao=acao_resposta_excluida&por_pagina=20" : null,
  );

  const linhas: Linha[] = [];
  linhasDoTempo.forEach((q, i) => {
    const a = recentes[i];
    const eventos = desembrulhar<{ linha_do_tempo?: EventoAcao[] }>(q.data)?.linha_do_tempo ?? [];
    for (const e of eventos)
      linhas.push({
        chave: `${a.id}-${e.id}`,
        em: e.em,
        texto: `${e.autor_nome}: “${a.descricao}” (${nomeCurto(a.territorio_nome ?? a.territorio_id)}). ${e.texto}`,
      });
  });
  for (const r of exclusoes.data?.itens ?? []) {
    const d = r.detalhes ?? {};
    const onde = typeof d.territorio_id === "string" ? d.territorio_id : "território não informado";
    linhas.push({
      chave: `ex-${r.id}`,
      em: r.em,
      texto: `${r.usuario_nome ?? "Alguém"} excluiu uma ação (${onde}, ${String(d.situacao ?? "situação não informada").replace("_", " ")}).`,
    });
  }
  linhas.sort((a, b) => b.em.localeCompare(a.em));
  const carregando = linhasDoTempo.some((q) => q.isPending);
  const erro = linhasDoTempo.find((q) => q.isError)?.error ?? null;

  return (
    <Painel
      id="ac-auditoria"
      titulo="Auditoria"
      dica="Inclusões, mudanças de status e exclusões, com quem e quando."
    >
      {carregando && linhas.length === 0 && <p className={estilos.meta}>Carregando a trilha…</p>}
      {erro && linhas.length === 0 && <EstadoConsulta erro={erro} oQue="a trilha das ações" />}
      {!carregando && !erro && linhas.length === 0 && (
        <p className={estilos.meta}>Nenhum registro ainda. Isso não quer dizer que nada foi feito.</p>
      )}
      {linhas.length > 0 && (
        <ol className={estilos.trilha}>
          {linhas.slice(0, LIMITE_LINHAS).map((l) => (
            <li key={l.chave}>
              <time dateTime={l.em}>{hora(l.em)}</time>
              <span>{l.texto}</span>
            </li>
          ))}
        </ol>
      )}
      <p className={estilos.meta}>
        Fonte: registro da equipe.
        {admin
          ? " As exclusões vêm da auditoria do sistema."
          : " As exclusões ficam na auditoria do sistema, que só a administração consulta."}
      </p>
    </Painel>
  );
}
