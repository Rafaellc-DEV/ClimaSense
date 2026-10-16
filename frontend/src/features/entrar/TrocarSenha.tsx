import { useState, type FormEvent } from "react";
import { CabecalhoTela } from "@/app/AppShell";
import { useAviso } from "@/design-system/componentes/Aviso";
import { Botao } from "@/design-system/componentes/Botao";
import { Painel } from "@/design-system/componentes/Painel";
import { enviar } from "@/lib/api";
import { useSessao } from "@/lib/sessao";
import { PAPEIS } from "@/textos/glossario";
import { CampoSenha } from "./CampoSenha";
import estilos from "./Entrar.module.css";

/** Minha conta: dados da conta e troca de senha a qualquer momento. */
export function TelaConta() {
  const { usuario } = useSessao();
  const aviso = useAviso();
  const [erro, setErro] = useState<string>();
  async function trocar(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const d = new FormData(form);
    setErro(undefined);
    if (d.get("nova") !== d.get("confirmar")) return setErro("As duas senhas novas não são iguais.");
    try {
      await enviar("/auth/trocar-senha", { senha_atual: d.get("atual"), nova_senha: d.get("nova") });
      form.reset();
      aviso({ titulo: "Senha trocada.", texto: "Use a senha nova no próximo acesso." });
    } catch (x) {
      setErro((x as Error).message);
    }
  }
  return (
    <>
      <CabecalhoTela titulo="Minha conta" proposito="Seus dados de acesso e a troca de senha." />
      <div className={estilos.contaGrade}>
        <Painel titulo="Conta" id="conta-dados">
          <dl className={estilos.dados}>
            <dt>Nome</dt>
            <dd>{usuario?.nome}</dd>
            <dt>E-mail</dt>
            <dd>{usuario?.email}</dd>
            <dt>Papéis</dt>
            <dd>{usuario?.papeis.map((p) => PAPEIS[p] ?? p).join(", ")}</dd>
          </dl>
        </Painel>
        <Painel titulo="Trocar a senha" id="conta-senha">
          <form className={estilos.form} onSubmit={trocar}>
            <CampoSenha rotulo="Senha atual" name="atual" autoComplete="current-password" />
            <CampoSenha rotulo="Senha nova" name="nova" autoComplete="new-password" minLength={10} />
            <CampoSenha rotulo="Repita a senha nova" name="confirmar" autoComplete="new-password" />
            {erro && (
              <p role="alert" className={estilos.erro}>
                {erro}
              </p>
            )}
            <Botao type="submit">Trocar a senha</Botao>
          </form>
        </Painel>
      </div>
    </>
  );
}
