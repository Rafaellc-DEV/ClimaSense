import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { aoSessaoTerminar, api, clienteConsultas, enviar, type Esquemas } from "./api";

export type Usuario = Esquemas["UsuarioAtual"];

interface Ctx {
  usuario: Usuario | null | undefined; // undefined = verificando
  /** Motivo de a pessoa ter sido levada ao login (ex.: inatividade). */
  motivoSaida: string | null;
  entrar: (email: string, senha: string) => Promise<Usuario>;
  sair: (motivo?: string) => Promise<void>;
  renovar: () => Promise<void>;
  recarregar: () => Promise<void>;
  /** Verifica a sessão uma vez. Só a área da equipe e o login chamam: a landing nunca usa rota autenticada (RF-01.11). */
  garantir: () => void;
  pode: (permissao: string) => boolean;
}

const Contexto = createContext<Ctx | null>(null);
export const MOTIVO_INATIVIDADE = "Sua sessão terminou por inatividade. Entre novamente.";

export function ProvedorSessao({ children }: { children: ReactNode }) {
  const [usuario, setUsuario] = useState<Usuario | null | undefined>(undefined);
  const [motivoSaida, setMotivoSaida] = useState<string | null>(null);

  const recarregar = useCallback(async () => {
    try {
      setUsuario(await api<Usuario>("/auth/eu"));
    } catch {
      setUsuario(null);
    }
  }, []);

  const [verificada, setVerificada] = useState(false);
  const garantir = useCallback(() => {
    if (verificada) return;
    setVerificada(true);
    void recarregar();
  }, [verificada, recarregar]);

  useEffect(() => {
    return aoSessaoTerminar(() => {
      clienteConsultas.clear();
      setMotivoSaida(MOTIVO_INATIVIDADE);
      setUsuario(null);
    });
  }, []);

  const entrar = async (email: string, senha: string) => {
    const u = await enviar<Usuario>("/auth/entrar", { email, senha });
    setMotivoSaida(null);
    setUsuario(u);
    return u;
  };
  const sair = async (motivo?: string) => {
    await api("/auth/sair", { method: "POST" }).catch(() => undefined);
    clienteConsultas.clear();
    setMotivoSaida(motivo ?? null);
    setUsuario(null);
  };
  const renovar = async () => {
    setUsuario(await enviar<Usuario>("/auth/renovar"));
  };
  const pode = (permissao: string) => usuario?.permissoes.includes(permissao) ?? false;

  return (
    <Contexto.Provider value={{ usuario, motivoSaida, entrar, sair, renovar, recarregar, pode, garantir }}>
      {children}
    </Contexto.Provider>
  );
}

export function useSessao() {
  const c = useContext(Contexto);
  if (!c) throw new Error("useSessao fora do ProvedorSessao");
  return c;
}
