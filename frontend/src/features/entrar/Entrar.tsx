import { useEffect, useState, type FormEvent } from "react";
import { CircleAlert } from "lucide-react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { Botao } from "@/design-system/componentes/Botao";
import { Campo } from "@/design-system/componentes/Campo";
import { enviar } from "@/lib/api";
import { useSessao } from "@/lib/sessao";
import rios from "@/assets/tracos/rios.svg?raw";
import { CampoSenha } from "./CampoSenha";
import estilos from "./Entrar.module.css";

export function Entrar() {
  const { usuario, entrar, recarregar, motivoSaida, garantir } = useSessao();
  const navegar = useNavigate();
  const local = useLocation();
  const destino = (local.state as { voltarPara?: string } | null)?.voltarPara ?? "/app";
  const [erro, setErro] = useState<string>();
  const [enviando, setEnviando] = useState(false);

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
          senha_atual: dados.get("atual"),
          nova_senha: dados.get("nova"),
        });
        await recarregar();
        navegar(destino);
      } else {
        const u = await entrar(String(dados.get("email")), String(dados.get("senha")));
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
      <aside className={estilos.lado} aria-hidden="true">
        <div className={estilos.rios} dangerouslySetInnerHTML={{ __html: rios }} />
        <img src="/brand/logo-negativo.png" srcSet="/brand/logo-negativo@2x.png 2x" alt="" />
        <p>Antecipar riscos. Orientar decisões. Cuidar do território.</p>
      </aside>
      <main className={estilos.principal}>
        <Link to="/" className={estilos.voltar}>
          Voltar à página inicial
        </Link>
        <img src="/brand/logo.png" alt="ClimaSense" className={estilos.logoMovel} />
        <h1>{trocar ? "Crie uma senha nova" : "Acesso da equipe"}</h1>
        <p className={estilos.apoio}>
          {trocar
            ? "É o seu primeiro acesso. Escolha uma senha com pelo menos 10 caracteres; uma frase curta funciona bem."
            : "Use o e-mail e a senha que o administrador enviou para você."}
        </p>
        {motivoSaida && !trocar && (
          <p className={estilos.motivo} role="status">
            {motivoSaida}
          </p>
        )}
        <form onSubmit={aoEnviar} className={estilos.form}>
          {trocar ? (
            <>
              <CampoSenha
                rotulo="Senha atual (temporária)"
                name="atual"
                autoComplete="current-password"
                autoFocus
              />
              <CampoSenha rotulo="Senha nova" name="nova" autoComplete="new-password" minLength={10} />
              <CampoSenha rotulo="Repita a senha nova" name="confirmar" autoComplete="new-password" />
            </>
          ) : (
            <>
              <Campo rotulo="E-mail" name="email" type="email" autoComplete="username" required autoFocus />
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
