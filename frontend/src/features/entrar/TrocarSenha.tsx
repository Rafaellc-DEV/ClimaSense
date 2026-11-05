import { useState, type FormEvent } from "react";
import { CabecalhoTela } from "@/app/AppShell";
import { useAviso } from "@/design-system/componentes/Aviso";
import { CircleAlert, KeyRound } from "lucide-react";
import { Botao } from "@/design-system/componentes/Botao";
import { Painel } from "@/design-system/componentes/Painel";
import { enviar } from "@/lib/api";
import { useSessao } from "@/lib/sessao";
import { Fato } from "@/features/fluxo/Pecas";
import { iniciais, PapelPilula } from "@/features/admin/Papeis";
import { CampoSenha } from "./CampoSenha";
import estilos from "./TrocarSenha.module.css";

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
      <div className={estilos.grade}>
        <Painel titulo="Conta" id="conta-dados">
          <div className={estilos.perfil}>
            <span className={estilos.avatar} aria-hidden="true">
              {iniciais(usuario?.nome ?? "")}
            </span>
            <dl className={estilos.dados}>
              <Fato rotulo="Nome">{usuario?.nome}</Fato>
              <Fato rotulo="E-mail">{usuario?.email}</Fato>
              <Fato rotulo="Papéis">
                <span className={estilos.chips}>
                  {usuario?.papeis.map((p) => <PapelPilula key={p} papel={p} />)}
                </span>
              </Fato>
            </dl>
          </div>
        </Painel>
        <Painel
          titulo="Trocar a senha"
          id="conta-senha"
          dica="A senha nova precisa de pelo menos 10 caracteres. Os três campos são obrigatórios."
        >
          <form className={estilos.form} onSubmit={trocar}>
            <CampoSenha rotulo="Senha atual" name="atual" autoComplete="current-password" />
            <CampoSenha rotulo="Senha nova" name="nova" autoComplete="new-password" minLength={10} />
            <CampoSenha rotulo="Repita a senha nova" name="confirmar" autoComplete="new-password" />
            {erro && (
              <p role="alert" className={estilos.erro}>
                <CircleAlert aria-hidden="true" size={20} />
                {erro}
              </p>
            )}
            <Botao type="submit" icone={<KeyRound />}>
              Trocar a senha
            </Botao>
          </form>
        </Painel>
      </div>
    </>
  );
}
