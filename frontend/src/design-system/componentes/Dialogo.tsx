import type { ReactNode } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import { Botao } from "./Botao";
import estilos from "./Dialogo.module.css";

export interface DialogoProps {
  aberto: boolean;
  aoMudar: (aberto: boolean) => void;
  titulo: string;
  descricao?: ReactNode;
  children?: ReactNode;
  acoes?: ReactNode;
  /** Diálogos de sessão e confirmação não fecham por clique fora. */
  modalEstrito?: boolean;
}

export function Dialogo({ aberto, aoMudar, titulo, descricao, children, acoes, modalEstrito }: DialogoProps) {
  return (
    <Dialog.Root open={aberto} onOpenChange={aoMudar}>
      <Dialog.Portal>
        <Dialog.Overlay className={estilos.fundo} />
        <Dialog.Content
          className={estilos.janela}
          onPointerDownOutside={modalEstrito ? (e) => e.preventDefault() : undefined}
        >
          <Dialog.Title className={estilos.titulo}>{titulo}</Dialog.Title>
          {descricao ? (
            <Dialog.Description className={estilos.descricao}>{descricao}</Dialog.Description>
          ) : (
            <Dialog.Description className="so-leitor">{titulo}</Dialog.Description>
          )}
          {children}
          {acoes && <div className={estilos.acoes}>{acoes}</div>}
          {!modalEstrito && (
            <Dialog.Close className={estilos.fechar} aria-label="Fechar">
              <X size={24} aria-hidden="true" />
            </Dialog.Close>
          )}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

export interface ConfirmacaoProps {
  aberto: boolean;
  aoMudar: (aberto: boolean) => void;
  titulo: string;
  /** Texto da consequência (RNF-ACE-11), ex.: "Publicar torna o aviso visível para qualquer pessoa…" */
  consequencia: ReactNode;
  rotuloConfirmar: string;
  aoConfirmar: () => void;
  perigo?: boolean;
}

export function Confirmacao({
  aberto,
  aoMudar,
  titulo,
  consequencia,
  rotuloConfirmar,
  aoConfirmar,
  perigo,
}: ConfirmacaoProps) {
  return (
    <Dialogo
      aberto={aberto}
      aoMudar={aoMudar}
      titulo={titulo}
      descricao={consequencia}
      modalEstrito
      acoes={
        <>
          <Botao variante="secundario" onClick={() => aoMudar(false)}>
            Cancelar
          </Botao>
          <Botao variante={perigo ? "perigo" : "principal"} onClick={aoConfirmar}>
            {rotuloConfirmar}
          </Botao>
        </>
      }
    />
  );
}
