import { createContext, useCallback, useContext, useState, type ReactNode } from "react";
import * as Toast from "@radix-ui/react-toast";
import { CircleAlert, CircleCheck, X } from "lucide-react";
import estilos from "./Aviso.module.css";

/** Aviso (toast): retorno curto de uma ação, com o mesmo verbo do botão ("Enviado para revisão"). */
export interface DadosAviso {
  titulo: string;
  texto?: string;
  tipo?: "sucesso" | "erro";
}

const Contexto = createContext<(aviso: DadosAviso) => void>(() => undefined);

export function useAviso() {
  return useContext(Contexto);
}

export function ProvedorAvisos({ children }: { children: ReactNode }) {
  const [avisos, setAvisos] = useState<(DadosAviso & { id: number })[]>([]);
  const mostrar = useCallback(
    (a: DadosAviso) => setAvisos((lista) => [...lista, { ...a, id: Date.now() + Math.random() }]),
    [],
  );
  return (
    <Contexto.Provider value={mostrar}>
      <Toast.Provider swipeDirection="right" duration={7000} label="Notificação">
        {children}
        {avisos.map((a) => (
          <Toast.Root
            key={a.id}
            className={[estilos.aviso, a.tipo === "erro" && estilos.erro].filter(Boolean).join(" ")}
            type={a.tipo === "erro" ? "foreground" : "background"}
            onOpenChange={(aberto) => !aberto && setAvisos((lista) => lista.filter((x) => x.id !== a.id))}
          >
            {a.tipo === "erro" ? (
              <CircleAlert color="var(--n-critico)" aria-hidden="true" />
            ) : (
              <CircleCheck color="var(--cs-mangue)" aria-hidden="true" />
            )}
            <div>
              <Toast.Title className={estilos.titulo}>{a.titulo}</Toast.Title>
              {a.texto && <Toast.Description className={estilos.texto}>{a.texto}</Toast.Description>}
            </div>
            <Toast.Close className={estilos.fechar} aria-label="Fechar notificação">
              <X size={20} aria-hidden="true" />
            </Toast.Close>
          </Toast.Root>
        ))}
        <Toast.Viewport className={estilos.area} />
      </Toast.Provider>
    </Contexto.Provider>
  );
}
