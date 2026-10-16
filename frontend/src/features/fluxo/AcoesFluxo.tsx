import { useState, type ReactNode } from "react";
import { Ban, Check, Send, Undo2, Upload } from "lucide-react";
import { useAviso } from "@/design-system/componentes/Aviso";
import { Botao } from "@/design-system/componentes/Botao";
import { AreaTexto } from "@/design-system/componentes/Campo";
import { Confirmacao, Dialogo } from "@/design-system/componentes/Dialogo";
import { enviar } from "@/lib/api";
import { RETORNO, ROTULOS_ACAO } from "@/textos/mensagens";
import estilos from "./Fluxo.module.css";

const ICONES: Record<string, ReactNode> = {
  enviar: <Send />,
  aprovar: <Check />,
  devolver: <Undo2 />,
  publicar: <Upload />,
  encerrar: <Ban />,
};

/**
 * Botões do fluxo de revisão: só aparecem as ações que a API diz que esta pessoa pode fazer agora
 * (e a API confere de novo ao receber). Publicar e encerrar pedem confirmação com a consequência (RNF-ACE-11);
 * devolver exige a justificativa (RF-10.3).
 */
export function AcoesFluxo<T>({
  base,
  acoes,
  aoConcluir,
  consequencias,
  bloqueadas = [],
}: {
  base: string;
  acoes: string[];
  aoConcluir: (resposta: T) => void;
  consequencias: Partial<Record<"publicar" | "encerrar", ReactNode>>;
  bloqueadas?: string[];
}) {
  const aviso = useAviso();
  const [confirmar, setConfirmar] = useState<"publicar" | "encerrar" | null>(null);
  const [devolver, setDevolver] = useState(false);
  const [justificativa, setJustificativa] = useState("");
  const [erroJustificativa, setErroJustificativa] = useState<string>();
  const [ocupado, setOcupado] = useState(false);

  async function executar(acao: string, corpo?: { justificativa: string }) {
    setOcupado(true);
    try {
      const r = await enviar<T>(`${base}/${acao}`, corpo);
      aviso({ titulo: RETORNO[acao as keyof typeof RETORNO] ?? "Feito." });
      aoConcluir(r);
      return true;
    } catch (e) {
      aviso({ tipo: "erro", titulo: "Não foi possível concluir.", texto: (e as Error).message });
      return false;
    } finally {
      setOcupado(false);
    }
  }

  const visiveis = ["enviar", "aprovar", "devolver", "publicar", "encerrar"].filter(
    (a) => acoes.includes(a) && !bloqueadas.includes(a),
  );
  if (!visiveis.length) return null;
  return (
    <div className={estilos.acoes}>
      {visiveis.map((a) => (
        <Botao
          key={a}
          variante={a === "encerrar" ? "secundario" : a === "devolver" ? "secundario" : "principal"}
          icone={ICONES[a]}
          disabled={ocupado}
          onClick={() => {
            if (a === "publicar" || a === "encerrar") setConfirmar(a);
            else if (a === "devolver") setDevolver(true);
            else void executar(a);
          }}
        >
          {ROTULOS_ACAO[a]}
        </Botao>
      ))}
      {confirmar && (
        <Confirmacao
          aberto
          aoMudar={(v) => !v && setConfirmar(null)}
          titulo={confirmar === "publicar" ? "Publicar na página inicial?" : "Encerrar?"}
          consequencia={consequencias[confirmar]}
          rotuloConfirmar={confirmar === "publicar" ? "Publicar" : "Encerrar"}
          perigo={confirmar === "encerrar"}
          aoConfirmar={async () => {
            const a = confirmar;
            setConfirmar(null);
            await executar(a);
          }}
        />
      )}
      <Dialogo
        aberto={devolver}
        aoMudar={setDevolver}
        titulo="Devolver com justificativa"
        descricao="Explique o que precisa mudar. Quem escreveu vê o motivo na linha do tempo."
        acoes={
          <>
            <Botao variante="secundario" onClick={() => setDevolver(false)}>
              Cancelar
            </Botao>
            <Botao
              disabled={ocupado}
              onClick={async () => {
                if (!justificativa.trim()) return setErroJustificativa("Escreva o motivo da devolução.");
                if (await executar("devolver", { justificativa })) {
                  setDevolver(false);
                  setJustificativa("");
                }
              }}
            >
              Devolver
            </Botao>
          </>
        }
      >
        <AreaTexto
          rotulo="Motivo"
          value={justificativa}
          onChange={(e) => {
            setJustificativa(e.target.value);
            setErroJustificativa(undefined);
          }}
          erro={erroJustificativa}
          maxLength={2000}
        />
      </Dialogo>
    </div>
  );
}

export interface EvidenciaForm {
  tipo: string;
  descricao: string;
  fonte_id: string;
  capturada_em: string;
  valor?: string | null;
  endereco?: string | null;
}

/** Evidências vinculadas: cada uma aponta para uma fonte real e diz quando foi capturada (RN-19). */
export function ListaEvidencias({
  evidencias,
  aoRemover,
}: {
  evidencias: EvidenciaForm[];
  aoRemover?: (i: number) => void;
}) {
  if (!evidencias.length)
    return (
      <p className={estilos.semEvidencia}>
        Nenhuma evidência vinculada. Use “Registrar avaliação” no mapa ou “Encaminhar para avaliação” nos
        cenários para trazer valores com fonte e horário.
      </p>
    );
  return (
    <ul className={estilos.evidencias}>
      {evidencias.map((e, i) => (
        <li key={i}>
          <div>
            <strong>{e.descricao}</strong>
            {e.valor && <span>{e.valor}</span>}
            <small>
              Fonte {e.fonte_id}, capturada em{" "}
              {new Intl.DateTimeFormat("pt-BR", {
                dateStyle: "short",
                timeStyle: "short",
                timeZone: "America/Recife",
              }).format(new Date(e.capturada_em))}
              .{" "}
              {e.endereco && (
                <a href={e.endereco} target="_blank" rel="noreferrer">
                  Abrir o recorte
                </a>
              )}
            </small>
          </div>
          {aoRemover && (
            <Botao variante="discreto" onClick={() => aoRemover(i)}>
              Remover
            </Botao>
          )}
        </li>
      ))}
    </ul>
  );
}
