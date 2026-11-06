import { useEffect, useState, type FormEvent } from "react";
import { ArrowLeft, CircleAlert } from "lucide-react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { Botao } from "@/design-system/componentes/Botao";
import { Campo } from "@/design-system/componentes/Campo";
import { Marca } from "@/design-system/componentes/Marca";
import { funcionalidadeLigada } from "@/lib/funcionalidades";
import { enviar } from "@/lib/api";
import { useSessao } from "@/lib/sessao";
import { CampoSenha } from "./CampoSenha";
import estilos from "./Entrar.module.css";

export function Entrar() {
  const { usuario, entrar, recarregar, motivoSaida, garantir } = useSessao();
  const navegar = useNavigate();
  const landing = funcionalidadeLigada("landingPublica");
  const local = useLocation();
  const destino = (local.state as { voltarPara?: string } | null)?.voltarPara ?? "/app";
  const [erro, setErro] = useState<string>();
  const [enviando, setEnviando] = useState(false);
  // A senha temporária digitada no login fica só em memória, para não pedir de novo (e não confundir com a senha nova).
  const [temporaria, setTemporaria] = useState<string>();

  useEffect(() => {
    document.title = "Entrar | ClimaSense";
    garantir();
  }, [garantir]);

  if (usuario && !usuario.troca_senha_obrigatoria) return <Navigate to={destino} replace />;
  const trocar = usuario?.troca_senha_obrigatoria;

  async function aoEnviar(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const dados = new FormData(e.currentTarget);
    setErro(undefined);
    setEnviando(true);
    try {
      if (trocar) {
        if (dados.get("nova") !== dados.get("confirmar"))
          throw new Error("As duas senhas novas não são iguais.");
        await enviar("/auth/trocar-senha", {
          senha_atual: temporaria ?? dados.get("atual"),
          nova_senha: dados.get("nova"),
        });
        setTemporaria(undefined);
        await recarregar();
        navegar(destino);
      } else {
        const senha = String(dados.get("senha"));
        const u = await entrar(String(dados.get("email")), senha);
        setTemporaria(u.troca_senha_obrigatoria ? senha : undefined);
        if (!u.troca_senha_obrigatoria) navegar(destino);
      }
    } catch (x) {
      setErro(x instanceof Error ? x.message : "Algo deu errado. Tente de novo.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className={estilos.tela}>
      {landing && (
        <Link to="/" className={estilos.voltar}>
          <ArrowLeft aria-hidden="true" size={16} strokeWidth={1.5} />
          <span className={estilos.voltarTexto}>Voltar à página inicial</span>
        </Link>
      )}
      <main className={estilos.principal}>
        {landing ? (
          <Link to="/" aria-label="ClimaSense, página inicial" className={estilos.logo}>
            <Marca decorativa />
          </Link>
        ) : (
          <span className={estilos.logo}>
            <Marca />
          </span>
        )}
        <h1>{trocar ? "Crie uma senha nova" : "Acesso da equipe"}</h1>
        {trocar && (
          <p className={estilos.apoio}>
            É o seu primeiro acesso. Escolha uma senha com pelo menos 10 caracteres; uma frase curta funciona
            bem.
          </p>
        )}
        {motivoSaida && !trocar && (
          <p className={estilos.motivo} role="status">
            {motivoSaida}
          </p>
        )}
        <form onSubmit={aoEnviar} className={estilos.form}>
          {trocar ? (
            <>
              <input
                type="text"
                name="username"
                value={usuario?.email ?? ""}
                autoComplete="username"
                readOnly
                hidden
              />
              {!temporaria && (
                <CampoSenha
                  rotulo="Senha atual (temporária)"
                  name="atual"
                  autoComplete="current-password"
                  autoFocus
                />
              )}
              <CampoSenha
                rotulo="Senha nova"
                name="nova"
                autoComplete="new-password"
                minLength={10}
                autoFocus={!!temporaria}
              />
              <CampoSenha rotulo="Repita a senha nova" name="confirmar" autoComplete="new-password" />
            </>
          ) : (
            <>
              <Campo
                rotulo="E-mail"
                dica="Use o e-mail e a senha que o administrador enviou para você."
                name="email"
                type="email"
                autoComplete="username"
                required
                autoFocus
              />
              <CampoSenha rotulo="Senha" name="senha" autoComplete="current-password" />
            </>
          )}
          {erro && (
            <p role="alert" className={estilos.erro}>
              <CircleAlert aria-hidden="true" size={20} />
              {erro}
            </p>
          )}
          <Botao type="submit" grande larguraTotal disabled={enviando}>
            {enviando ? "Aguarde…" : trocar ? "Salvar a senha nova" : "Entrar"}
          </Botao>
        </form>
        <p className={estilos.nota}>Esqueceu a senha? Fale com o administrador do ClimaSense.</p>
      </main>
    </div>
  );
}
