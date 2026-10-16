import { Check, CircleDot, MessageSquareWarning, Pencil } from "lucide-react";
import { formatarDataHora } from "@/lib/formatos";
import estilos from "./Fluxo.module.css";

const ETAPAS = [
  { chave: "rascunho", rotulo: "Rascunho" },
  { chave: "em_revisao", rotulo: "Em revisão" },
  { chave: "aprovado", rotulo: "Aprovado" },
  { chave: "publicado", rotulo: "Publicado" },
];

/** Etapas do fluxo (sequência real → numeração justificada). “Devolvido” volta para o rascunho. */
export function EtapasFluxo({ estado, comPublicacao = true }: { estado: string; comPublicacao?: boolean }) {
  const etapas = comPublicacao
    ? ETAPAS
    : ETAPAS.slice(0, 3).concat({ chave: "encerrado", rotulo: "Encerrada" });
  const efetivo = estado === "devolvido" ? "rascunho" : estado;
  const atual = estado === "encerrado" ? etapas.length : etapas.findIndex((e) => e.chave === efetivo);
  return (
    <ol className={estilos.etapas} aria-label="Etapas do fluxo">
      {etapas.map((e, i) => {
        const situacao = i < atual ? "feita" : i === atual ? "atual" : "futura";
        return (
          <li key={e.chave} data-situacao={situacao} aria-current={situacao === "atual" ? "step" : undefined}>
            <span className={estilos.marca} aria-hidden="true">
              {situacao === "feita" ? <Check size={16} /> : i + 1}
            </span>
            <span>
              {e.rotulo}
              {situacao === "atual" && estado === "devolvido" && " (devolvido para ajuste)"}
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
      {estado === "encerrado" && <li data-situacao="encerrado">Encerrado</li>}
    </ol>
  );
}

export interface Evento {
  tipo: string;
  numero: number;
  em: string;
  por: string;
  texto?: string | null;
}

const ICONES: Record<string, JSX.Element> = {
  versao: <Pencil size={16} />,
  aprovar: <Check size={16} />,
  devolver: <MessageSquareWarning size={16} />,
};
const VERBOS: Record<string, string> = {
  versao: "escreveu a versão",
  aprovar: "aprovou a versão",
  devolver: "devolveu a versão",
};

/** Histórico de versões e decisões (RF-10.3, RF-11.7), do mais antigo ao mais recente. */
export function LinhaDoTempo({ eventos }: { eventos: Evento[] }) {
  return (
    <ol className={estilos.tempo}>
      {eventos.map((e, i) => (
        <li key={i} data-tipo={e.tipo}>
          <span className={estilos.ponto} aria-hidden="true">
            {ICONES[e.tipo] ?? <CircleDot size={16} />}
          </span>
          <div>
            <p>
              <strong>{e.por}</strong> {VERBOS[e.tipo] ?? e.tipo} {e.numero}.
            </p>
            {e.texto && <p className={estilos.motivo}>“{e.texto}”</p>}
            <p className={estilos.quando}>{formatarDataHora(e.em)}</p>
          </div>
        </li>
      ))}
    </ol>
  );
}
