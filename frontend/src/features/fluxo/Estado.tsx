import type { ReactNode } from "react";
import { Archive, Check, CircleCheck, Hourglass, Megaphone, Pencil, Undo2 } from "lucide-react";
import { Pilula, type TomPilula } from "@/design-system/componentes/Pilula";
import { ESTADOS, ESTADOS_AVALIACAO } from "@/textos/glossario";
import estilos from "./Estado.module.css";

const VISUAL: Record<string, { tom: TomPilula; icone: ReactNode }> = {
  rascunho: { tom: "neutro", icone: <Pencil /> },
  em_revisao: { tom: "info", icone: <Hourglass /> },
  aprovado: { tom: "sucesso", icone: <CircleCheck /> },
  devolvido: { tom: "atencao", icone: <Undo2 /> },
  publicado: { tom: "marca", icone: <Megaphone /> },
  encerrado: { tom: "neutro", icone: <Archive /> },
};

/** Estado do fluxo como pílula com ícone e texto: a cor nunca fala sozinha (RN-17). */
export function SeloEstado({ estado, avaliacao }: { estado: string; avaliacao?: boolean }) {
  const v = VISUAL[estado] ?? VISUAL.rascunho;
  return (
    <Pilula tom={v.tom} icone={v.icone}>
      {(avaliacao ? ESTADOS_AVALIACAO : ESTADOS)[estado] ?? estado}
    </Pilula>
  );
}

/** Abas por estado com contagem (filtro da lista): pílulas com o número em um disco. */
export function AbasEstado({
  estados,
  contagens,
  atual,
  aoMudar,
  rotulos,
}: {
  estados: string[];
  contagens: Record<string, number>;
  atual: string;
  aoMudar: (e: string) => void;
  rotulos: Record<string, string>;
}) {
  const total = Object.values(contagens).reduce((s, n) => s + n, 0);
  return (
    <div className={estilos.abas} role="group" aria-label="Filtrar por estado">
      {["todos", ...estados].map((e) => {
        const n = e === "todos" ? total : (contagens[e] ?? 0);
        return (
          <button
            key={e}
            type="button"
            className={estilos.aba}
            aria-pressed={atual === e}
            data-vazia={n === 0}
            onClick={() => aoMudar(e)}
          >
            {e === "todos" ? "Todos" : rotulos[e]}
            <span aria-label={`${n} itens`}>{n}</span>
          </button>
        );
      })}
    </div>
  );
}

interface Etapa {
  chave: string;
  rotulo: string;
}
const ETAPAS: Etapa[] = [
  { chave: "rascunho", rotulo: "Rascunho" },
  { chave: "em_revisao", rotulo: "Em revisão" },
  { chave: "aprovado", rotulo: "Aprovado" },
  { chave: "publicado", rotulo: "Publicado" },
];
const ETAPAS_AVALIACAO: Etapa[] = [
  { chave: "rascunho", rotulo: "Rascunho" },
  { chave: "em_revisao", rotulo: "Em revisão" },
  { chave: "aprovado", rotulo: "Aprovada" },
  { chave: "encerrado", rotulo: "Encerrada" },
];

/** Etapas e posição atual. “Devolvido” volta para o rascunho; comunicado encerrado ganha uma etapa final. */
function etapasDe(estado: string, comPublicacao: boolean) {
  let etapas = comPublicacao ? ETAPAS : ETAPAS_AVALIACAO;
  if (comPublicacao && estado === "encerrado")
    etapas = [...ETAPAS, { chave: "encerrado", rotulo: "Encerrado" }];
  const efetivo = estado === "devolvido" ? "rascunho" : estado;
  const atual = Math.max(
    0,
    etapas.findIndex((e) => e.chave === efetivo),
  );
  return { etapas, atual };
}

/** Quatro segmentos para linhas de lista. Decorativo: o texto vem da pílula de estado ao lado. */
export function MiniEtapas({ estado, comPublicacao = true }: { estado: string; comPublicacao?: boolean }) {
  const { etapas, atual } = etapasDe(estado, comPublicacao);
  return (
    <span className={estilos.mini} aria-hidden="true">
      {etapas.map((e, i) => (
        <i key={e.chave} data-situacao={i < atual ? "feita" : i === atual ? "atual" : "futura"} />
      ))}
    </span>
  );
}

/** Régua fina de etapas do fluxo (a sequência é real: rascunho, revisão, aprovação, publicação). */
export function EtapasFinas({ estado, comPublicacao = true }: { estado: string; comPublicacao?: boolean }) {
  const { etapas, atual } = etapasDe(estado, comPublicacao);
  return (
    <ol className={estilos.etapas} aria-label="Etapas do fluxo">
      {etapas.map((e, i) => {
        const situacao = i < atual ? "feita" : i === atual ? "atual" : "futura";
        return (
          <li key={e.chave} data-situacao={situacao} aria-current={situacao === "atual" ? "step" : undefined}>
            <span className={estilos.ponto} aria-hidden="true">
              {situacao === "feita" && <Check size={14} strokeWidth={3} />}
            </span>
            <span className={estilos.nome}>
              {e.rotulo}
              {situacao === "atual" && estado === "devolvido" && (
                <small className={estilos.nota}> devolvido</small>
              )}
              <span className="so-leitor">
                {situacao === "feita"
                  ? ", concluída"
                  : situacao === "atual"
                    ? ", etapa atual"
                    : ", ainda não"}
              </span>
            </span>
          </li>
        );
      })}
    </ol>
  );
}

/* ------------------------------------------------------------------ próximo passo e filtros simples */
export interface ItemFluxo {
  tipo: "comunicado" | "avaliacao";
  estado: string;
  autor_id?: string | null;
  autor_nome?: string | null;
  /** Só comunicado: até quando o aviso fica no ar. */
  validade_fim?: string | null;
}

export interface PassoFluxo {
  /** “Aguarda a sua revisão”, “Pronto para publicar”, “Publicado até amanhã, 18h00”. */
  texto: string;
  /** true quando quem age agora é a pessoa que está vendo a lista. */
  comVoce: boolean;
}

/**
 * O próximo passo de um item, em uma frase e do ponto de vista de quem olha. Quem escreveu não revisa a própria
 * versão; publicar é da coordenação. `quando` formata a validade (ex.: `quandoRelativo`).
 */
export function proximoPasso(
  item: ItemFluxo,
  euId: string | null | undefined,
  pode: (p: string) => boolean,
  quando: (iso: string) => string,
  agora: Date = new Date(),
): PassoFluxo {
  const meu = !!euId && item.autor_id === euId;
  const de = item.autor_nome ? ` de ${item.autor_nome}` : "";
  switch (item.estado) {
    case "rascunho":
      return meu
        ? { texto: "Rascunho seu: termine e envie para revisão", comVoce: true }
        : { texto: `Rascunho${de}, ainda não enviado`, comVoce: false };
    case "devolvido":
      return meu
        ? { texto: "Devolvido para você ajustar e reenviar", comVoce: true }
        : { texto: `Devolvido${de} para ajustes`, comVoce: false };
    case "em_revisao":
      return !meu && pode("revisar")
        ? { texto: "Aguarda a sua revisão", comVoce: true }
        : { texto: "Aguarda a revisão de outra pessoa", comVoce: false };
    case "aprovado":
      if (item.tipo === "avaliacao")
        return { texto: "Aprovada; encerre quando o evento passar", comVoce: pode("revisar") };
      return pode("publicar")
        ? { texto: "Pronto para publicar", comVoce: true }
        : { texto: "Aprovado; aguarda a coordenação publicar", comVoce: false };
    case "publicado":
      if (item.validade_fim && new Date(item.validade_fim) < agora)
        return { texto: `Venceu ${quando(item.validade_fim)}: encerre o aviso`, comVoce: pode("publicar") };
      return {
        texto: item.validade_fim ? `Publicado, no ar até ${quando(item.validade_fim)}` : "Publicado",
        comVoce: false,
      };
    case "encerrado":
      return { texto: "Encerrado, fica no histórico", comVoce: false };
    default:
      return { texto: "Nada a fazer agora", comVoce: false };
  }
}

/** Pílula de estado com o próximo passo escrito ao lado. O que depende de você ganha destaque. */
export function EstadoEPasso({
  estado,
  passo,
  avaliacao,
}: {
  estado: string;
  passo: PassoFluxo;
  avaliacao?: boolean;
}) {
  return (
    <span className={estilos.passo} data-com-voce={passo.comVoce}>
      <SeloEstado estado={estado} avaliacao={avaliacao} />
      <span className={estilos.passoTexto}>{passo.texto}</span>
    </span>
  );
}

/** Filtros simples da lista, por o que a pessoa precisa fazer, e não pelos seis estados técnicos. */
export type FiltroFluxo = "comigo" | "andamento" | "no_ar" | "encerrados" | "todos";
export const ROTULOS_FILTRO: Record<FiltroFluxo, string> = {
  comigo: "Precisam de você",
  andamento: "Em andamento",
  no_ar: "Publicados",
  encerrados: "Encerrados",
  todos: "Todos",
};

export function noFiltro(f: FiltroFluxo, estado: string, passo: PassoFluxo) {
  if (f === "todos") return true;
  if (f === "comigo") return passo.comVoce;
  if (f === "no_ar") return estado === "publicado";
  if (f === "encerrados") return estado === "encerrado";
  return ["rascunho", "devolvido", "em_revisao", "aprovado"].includes(estado);
}

/** Linha de filtros com contagem. Filtros sem itens ficam visíveis (a pessoa vê que está zerado), mas discretos. */
export function FiltrosFluxo({
  filtros,
  contagens,
  atual,
  aoMudar,
}: {
  filtros: FiltroFluxo[];
  contagens: Record<FiltroFluxo, number>;
  atual: FiltroFluxo;
  aoMudar: (f: FiltroFluxo) => void;
}) {
  return (
    <div className={estilos.abas} role="group" aria-label="Filtrar">
      {filtros.map((f) => (
        <button
          key={f}
          type="button"
          className={estilos.aba}
          aria-pressed={atual === f}
          data-vazia={contagens[f] === 0}
          onClick={() => aoMudar(f)}
        >
          {ROTULOS_FILTRO[f]}
          <span aria-label={`${contagens[f]} itens`}>{contagens[f]}</span>
        </button>
      ))}
    </div>
  );
}
