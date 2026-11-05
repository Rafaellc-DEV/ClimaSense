import { useState, type FormEvent } from "react";
import {
  Copy,
  Hourglass,
  KeyRound,
  Pencil,
  ShieldCheck,
  UserCheck,
  UserPlus,
  UserX,
  CircleCheck,
  Loader,
  TriangleAlert,
} from "lucide-react";
import { Navigate, NavLink, Route, Routes } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { CabecalhoTela } from "@/app/AppShell";
import { useAviso } from "@/design-system/componentes/Aviso";
import { Botao } from "@/design-system/componentes/Botao";
import { Campo } from "@/design-system/componentes/Campo";
import { Confirmacao, Dialogo } from "@/design-system/componentes/Dialogo";
import { Dica } from "@/design-system/componentes/Dica";
import { FalhaCarga, Painel } from "@/design-system/componentes/Painel";
import { Pilula, type TomPilula } from "@/design-system/componentes/Pilula";
import { Selecao } from "@/design-system/componentes/Selecao";
import { semDado } from "@/design-system/componentes/Tabela";
import { VazioConvidativo } from "@/design-system/componentes/VazioConvidativo";
import { ListaAdaptavel } from "@/features/fluxo/ListaAdaptavel";
import { consulta, enviar, type Esquemas } from "@/lib/api";
import { useConsulta } from "@/lib/consultas";
import { formatarDataHora, formatarNumero } from "@/lib/formatos";
import { useSessao } from "@/lib/sessao";
import { PAPEIS } from "@/textos/glossario";
import { ICONE_PAPEL, iniciais, PapelPilula } from "./Papeis";
import estilos from "./Admin.module.css";

type Conta = Esquemas["Conta"];

/** Administração (design §9.11): três abas. Só para quem tem o papel de administrador (RF-03.3; a API confere). */
export function TelaAdmin() {
  const { pode } = useSessao();
  if (!pode("administrar")) return <Navigate to="/app" replace />;
  return (
    <>
      <CabecalhoTela
        titulo="Administração"
        proposito="Contas da equipe, cargas de dados e o registro de tudo o que foi feito."
      />
      <nav className={estilos.abas} aria-label="Seções da administração">
        <NavLink to="/app/admin" end>
          Usuários
        </NavLink>
        <NavLink to="/app/admin/execucoes">Execuções do ETL</NavLink>
        <NavLink to="/app/admin/auditoria">Auditoria</NavLink>
      </nav>
      <Routes>
        <Route index element={<Usuarios />} />
        <Route path="execucoes" element={<Execucoes />} />
        <Route path="auditoria" element={<Auditoria />} />
      </Routes>
    </>
  );
}

function SenhaMostrada({
  senha,
  email,
  aoFechar,
}: {
  senha: string | null;
  email: string;
  aoFechar: () => void;
}) {
  const aviso = useAviso();
  async function copiar() {
    try {
      await navigator.clipboard.writeText(senha ?? "");
      aviso({ titulo: "Senha copiada." });
    } catch {
      aviso({ tipo: "erro", titulo: "Não foi possível copiar.", texto: "Selecione a senha e copie à mão." });
    }
  }
  return (
    <Dialogo
      aberto={!!senha}
      aoMudar={(a) => !a && aoFechar()}
      modalEstrito
      titulo="Senha temporária"
      descricao={`Entregue esta senha a ${email} por um canal seguro. Ela aparece só agora; no primeiro acesso a pessoa cria a própria.`}
      acoes={
        <>
          <Botao variante="secundario" icone={<Copy />} onClick={copiar}>
            Copiar senha
          </Botao>
          <Botao onClick={aoFechar}>Já anotei</Botao>
        </>
      }
    >
      <p className={estilos.senha}>
        <code>{senha}</code>
      </p>
    </Dialogo>
  );
}

/** Papéis em cartões marcáveis; cada um diz, em palavras simples, o que a pessoa pode fazer. */
function EscolhaPapeis({ valor, aoMudar }: { valor: string[]; aoMudar: (v: string[]) => void }) {
  const papeis = useConsulta<Esquemas["PapelDescrito"][]>("/admin/usuarios/papeis", { staleTime: Infinity });
  return (
    <fieldset className={estilos.papeis}>
      <legend>
        Papéis
        <Dica
          texto="Os papéis se somam: quem é revisor também faz tudo o que o analista faz."
          rotulo="Como os papéis se somam"
          lado="abaixo"
        />
      </legend>
      {papeis.data?.map((p) => (
        <label key={p.papel}>
          <input
            type="checkbox"
            checked={valor.includes(p.papel)}
            onChange={(e) =>
              aoMudar(e.target.checked ? [...valor, p.papel] : valor.filter((x) => x !== p.papel))
            }
          />
          <span className={estilos.papelIcone} aria-hidden="true">
            {ICONE_PAPEL[p.papel] ?? <ShieldCheck />}
          </span>
          <span className={estilos.papelTexto}>
            <strong>{PAPEIS[p.papel] ?? p.papel}</strong>
            <span>{p.descricao}</span>
          </span>
        </label>
      ))}
    </fieldset>
  );
}

function SituacaoConta({ conta }: { conta: Conta }) {
  if (!conta.ativo)
    return (
      <Pilula tom="neutro" icone={<UserX />}>
        Desativada
      </Pilula>
    );
  if (conta.troca_senha_obrigatoria)
    return (
      <Pilula tom="info" icone={<Hourglass />}>
        Ativa, aguardando o 1º acesso
      </Pilula>
    );
  return (
    <Pilula tom="sucesso" icone={<CircleCheck />}>
      Ativa
    </Pilula>
  );
}

function Usuarios() {
  const { usuario } = useSessao();
  const aviso = useAviso();
  const cliente = useQueryClient();
  const contas = useConsulta<Conta[]>("/admin/usuarios");
  const [nova, setNova] = useState(false);
  const [papeisNovos, setPapeisNovos] = useState<string[]>(["analista"]);
  const [erroNova, setErroNova] = useState<string>();
  const [senha, setSenha] = useState<{ senha: string; email: string } | null>(null);
  const [editar, setEditar] = useState<Conta | null>(null);
  const [papeisEdicao, setPapeisEdicao] = useState<string[]>([]);
  const [confirmar, setConfirmar] = useState<{
    conta: Conta;
    acao: "desativar" | "reativar" | "senha";
  } | null>(null);
  const recarregar = () => cliente.invalidateQueries({ queryKey: ["/admin/usuarios"] });

  async function criar(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const d = new FormData(e.currentTarget);
    if (!papeisNovos.length) return setErroNova("Escolha pelo menos um papel.");
    try {
      const r = await enviar<Esquemas["ContaComSenha"]>("/admin/usuarios", {
        nome: d.get("nome"),
        email: d.get("email"),
        papeis: papeisNovos,
      });
      setNova(false);
      setErroNova(undefined);
      setPapeisNovos(["analista"]);
      setSenha({ senha: r.senha_temporaria, email: r.conta.email });
      aviso({ titulo: "Conta criada." });
      void recarregar();
    } catch (x) {
      setErroNova((x as Error).message);
    }
  }

  async function aplicar() {
    if (!confirmar) return;
    const { conta, acao } = confirmar;
    setConfirmar(null);
    try {
      if (acao === "senha") {
        const r = await enviar<Esquemas["SenhaTemporaria"]>(`/admin/usuarios/${conta.id}/redefinir-senha`);
        setSenha({ senha: r.senha_temporaria, email: conta.email });
      } else {
        await enviar(`/admin/usuarios/${conta.id}`, { ativo: acao === "reativar" }, "PATCH");
        aviso({ titulo: acao === "desativar" ? "Conta desativada." : "Conta reativada." });
      }
      void recarregar();
    } catch (x) {
      aviso({ tipo: "erro", titulo: "Não foi possível concluir.", texto: (x as Error).message });
    }
  }

  return (
    <Painel
      titulo="Usuários"
      id="adm-usuarios"
      dica="Contas não são apagadas, só desativadas, para preservar a auditoria."
      acoes={
        <Botao icone={<UserPlus />} onClick={() => setNova(true)}>
          Criar conta
        </Botao>
      }
    >
      {contas.isError && <FalhaCarga erro={contas.error} aoTentar={() => contas.refetch()} />}
      {!contas.isError && (
        <ListaAdaptavel
          legenda="Contas da equipe. Contas não são apagadas, só desativadas, para preservar a auditoria."
          carregando={contas.isPending}
          linhas={contas.data ?? []}
          chaveLinha={(c) => c.id}
          vazio={<VazioConvidativo titulo="Nenhuma conta ainda." />}
          colunas={[
            {
              chave: "nome",
              titulo: "Pessoa",
              celula: (c) => (
                <span className={estilos.pessoa}>
                  <span className={estilos.avatar} aria-hidden="true">
                    {iniciais(c.nome)}
                  </span>
                  <span className={estilos.pessoaTexto}>
                    {c.nome}
                    <span>{c.email}</span>
                  </span>
                </span>
              ),
            },
            {
              chave: "papeis",
              titulo: "Papéis",
              celula: (c) => (
                <span className={estilos.chips}>
                  {c.papeis.map((p) => (
                    <PapelPilula key={p} papel={p} />
                  ))}
                </span>
              ),
            },
            {
              chave: "situacao",
              titulo: "Situação",
              celula: (c) => <SituacaoConta conta={c} />,
            },
            {
              chave: "acoes",
              semRotulo: true,
              titulo: "Ações",
              celula: (c) => (
                <span className={estilos.acoes}>
                  <Botao
                    variante="discreto"
                    aria-label={`Editar papéis de ${c.nome}`}
                    icone={<Pencil />}
                    onClick={() => {
                      setEditar(c);
                      setPapeisEdicao(c.papeis);
                    }}
                  >
                    Papéis
                  </Botao>
                  <Botao
                    variante="discreto"
                    aria-label={`Redefinir senha de ${c.nome}`}
                    icone={<KeyRound />}
                    onClick={() => setConfirmar({ conta: c, acao: "senha" })}
                  >
                    Senha
                  </Botao>
                  {c.id !== usuario?.id && (
                    <Botao
                      variante="discreto"
                      icone={c.ativo ? <UserX /> : <UserCheck />}
                      onClick={() => setConfirmar({ conta: c, acao: c.ativo ? "desativar" : "reativar" })}
                    >
                      {c.ativo ? "Desativar" : "Reativar"}
                      <span className="so-leitor"> {c.nome}</span>
                    </Botao>
                  )}
                </span>
              ),
            },
          ]}
        />
      )}

      <Dialogo
        aberto={nova}
        aoMudar={setNova}
        titulo="Criar conta"
        descricao="A pessoa recebe uma senha temporária e cria a própria no primeiro acesso."
      >
        <form className={estilos.form} onSubmit={criar}>
          <Campo rotulo="Nome" name="nome" required minLength={2} maxLength={120} autoComplete="off" />
          <Campo rotulo="E-mail" name="email" type="email" required autoComplete="off" spellCheck={false} />
          <EscolhaPapeis valor={papeisNovos} aoMudar={setPapeisNovos} />
          {erroNova && (
            <p role="alert" className={estilos.erro}>
              {erroNova}
            </p>
          )}
          <Botao type="submit">Criar conta</Botao>
        </form>
      </Dialogo>

      <Dialogo
        aberto={!!editar}
        aoMudar={(a) => !a && setEditar(null)}
        titulo={`Papéis de ${editar?.nome ?? ""}`}
        acoes={
          <>
            <Botao variante="secundario" onClick={() => setEditar(null)}>
              Cancelar
            </Botao>
            <Botao
              onClick={async () => {
                if (!editar) return;
                try {
                  await enviar(`/admin/usuarios/${editar.id}`, { papeis: papeisEdicao }, "PATCH");
                  aviso({ titulo: "Papéis salvos." });
                  setEditar(null);
                  void recarregar();
                } catch (x) {
                  aviso({ tipo: "erro", titulo: "Não foi possível salvar.", texto: (x as Error).message });
                }
              }}
            >
              Salvar papéis
            </Botao>
          </>
        }
      >
        <EscolhaPapeis valor={papeisEdicao} aoMudar={setPapeisEdicao} />
      </Dialogo>

      {confirmar && (
        <Confirmacao
          aberto
          aoMudar={(a) => !a && setConfirmar(null)}
          titulo={
            confirmar.acao === "senha"
              ? `Redefinir a senha de ${confirmar.conta.nome}?`
              : confirmar.acao === "desativar"
                ? `Desativar ${confirmar.conta.nome}?`
                : `Reativar ${confirmar.conta.nome}?`
          }
          consequencia={
            confirmar.acao === "senha"
              ? "A senha atual deixa de funcionar e as sessões abertas são encerradas. Uma senha temporária aparece em seguida."
              : confirmar.acao === "desativar"
                ? "A pessoa não consegue mais entrar, e as sessões abertas são encerradas. A conta e o histórico ficam guardados."
                : "A pessoa volta a entrar com a senha que já tinha."
          }
          rotuloConfirmar={
            confirmar.acao === "senha"
              ? "Redefinir senha"
              : confirmar.acao === "desativar"
                ? "Desativar"
                : "Reativar"
          }
          perigo={confirmar.acao === "desativar"}
          aoConfirmar={aplicar}
        />
      )}
      <SenhaMostrada
        senha={senha?.senha ?? null}
        email={senha?.email ?? ""}
        aoFechar={() => setSenha(null)}
      />
    </Painel>
  );
}

const STATUS: Record<string, { rotulo: string; tom: TomPilula; icone: JSX.Element }> = {
  em_andamento: { rotulo: "Em andamento", tom: "info", icone: <Loader /> },
  sucesso: { rotulo: "Concluída", tom: "sucesso", icone: <CircleCheck /> },
  falha: { rotulo: "Com falha", tom: "alerta", icone: <TriangleAlert /> },
};

function Execucoes() {
  const r = useConsulta<Esquemas["ExecucaoAdmin"][]>("/admin/etl/execucoes");
  return (
    <Painel
      titulo="Execuções do ETL"
      id="adm-execucoes"
      dica="As últimas 100 buscas de dados novas, de todas as fontes. Inicie uma carga na tela de cada fonte, em Fontes de dados."
    >
      {r.isError && <FalhaCarga erro={r.error} aoTentar={() => r.refetch()} />}
      {!r.isError && (
        <ListaAdaptavel
          legenda="Últimas 100 execuções, de todas as fontes"
          carregando={r.isPending}
          linhas={r.data ?? []}
          chaveLinha={(e) => e.id}
          vazio={<VazioConvidativo titulo="Nenhuma execução ainda." />}
          colunas={[
            { chave: "inicio", semQuebra: true, titulo: "Início", celula: (e) => formatarDataHora(e.inicio) },
            { chave: "fonte", titulo: "Fonte", celula: (e) => e.fonte_nome },
            {
              chave: "status",
              titulo: "Resultado",
              celula: (e) => {
                const s = STATUS[e.status] ?? STATUS.em_andamento;
                return (
                  <span className={estilos.execucao}>
                    <Pilula tom={s.tom} icone={s.icone}>
                      {STATUS[e.status]?.rotulo ?? e.status}
                    </Pilula>
                    {e.erro && <small>{e.erro}</small>}
                  </span>
                );
              },
            },
            {
              chave: "gravados",
              titulo: "Gravados",
              numerica: true,
              celula: (e) => semDado(e.gravados, formatarNumero),
            },
            {
              chave: "descartados",
              titulo: "Descartados",
              numerica: true,
              celula: (e) => semDado(e.descartados, formatarNumero),
            },
            {
              chave: "quem",
              semQuebra: true,
              titulo: "Disparada por",
              celula: (e) => e.disparado_por_nome ?? "Linha de comando",
            },
          ]}
        />
      )}
    </Painel>
  );
}

const ROTULOS_ACAO: Record<string, string> = {
  login_sucesso: "Entrou",
  login_falha: "Tentativa de entrada recusada",
  logout: "Saiu",
};

function Auditoria() {
  const [filtro, setFiltro] = useState({ acao: "", inicio: "", fim: "", usuario_id: "" });
  const [pagina, setPagina] = useState(1);
  const contas = useConsulta<Conta[]>("/admin/usuarios");
  const r = useConsulta<Esquemas["PaginaAuditoria"]>(
    `/admin/auditoria${consulta({ ...filtro, pagina, por_pagina: 50 })}`,
  );
  const mudar = (p: Partial<typeof filtro>) => {
    setFiltro((f) => ({ ...f, ...p }));
    setPagina(1);
  };
  const filtrando = Object.values(filtro).some(Boolean);
  return (
    <Painel
      titulo="Auditoria"
      id="adm-auditoria"
      dica="Registro somente de inclusão: nada aqui pode ser editado nem apagado, nem pelo administrador."
      acoes={
        filtrando && (
          <Botao
            variante="discreto"
            onClick={() => {
              setFiltro({ acao: "", inicio: "", fim: "", usuario_id: "" });
              setPagina(1);
            }}
          >
            Limpar filtros
          </Botao>
        )
      }
    >
      <div className={estilos.filtros}>
        <Selecao
          rotulo="Pessoa"
          valor={filtro.usuario_id || "todas"}
          aoMudar={(v) => mudar({ usuario_id: v === "todas" ? "" : v })}
          opcoes={[
            { valor: "todas", rotulo: "Todas" },
            ...(contas.data ?? []).map((c) => ({ valor: c.id, rotulo: c.nome })),
          ]}
        />
        <Selecao
          rotulo="Ação"
          valor={filtro.acao || "todas"}
          aoMudar={(v) => mudar({ acao: v === "todas" ? "" : v })}
          opcoes={[
            { valor: "todas", rotulo: "Todas" },
            ...(r.data?.acoes ?? []).map((a) => ({
              valor: a,
              rotulo: ROTULOS_ACAO[a] ?? a.replace(/_/g, " "),
            })),
          ]}
        />
        <Campo
          rotulo="De"
          type="date"
          value={filtro.inicio}
          onChange={(e) => mudar({ inicio: e.target.value })}
        />
        <Campo rotulo="Até" type="date" value={filtro.fim} onChange={(e) => mudar({ fim: e.target.value })} />
      </div>
      {r.isError && <FalhaCarga erro={r.error} aoTentar={() => r.refetch()} />}
      {!r.isError && (
        <>
          <ListaAdaptavel
            legenda="Registros de auditoria, do mais recente para o mais antigo"
            carregando={r.isPending}
            linhas={r.data?.itens ?? []}
            chaveLinha={(x) => String(x.id)}
            vazio={<VazioConvidativo titulo="Nenhum registro com esses filtros." />}
            colunas={[
              { chave: "em", semQuebra: true, titulo: "Quando", celula: (x) => formatarDataHora(x.em) },
              {
                chave: "quem",
                semQuebra: true,
                titulo: "Pessoa",
                celula: (x) => x.usuario_nome ?? "Sistema",
              },
              {
                chave: "acao",
                titulo: "Ação",
                celula: (x) => ROTULOS_ACAO[x.acao] ?? x.acao.replace(/_/g, " "),
              },
              {
                chave: "alvo",
                titulo: "Sobre",
                celula: (x) => (x.alvo_tipo ? `${x.alvo_tipo} ${x.alvo_id?.slice(0, 8) ?? ""}` : "—"),
              },
              {
                chave: "detalhes",
                titulo: "Detalhes",
                celula: (x) => <code className={estilos.detalhes}>{resumoDetalhes(x.detalhes)}</code>,
              },
            ]}
          />
          {r.data && r.data.itens.length > 0 && (
            <div className={estilos.paginas}>
              <Botao variante="secundario" disabled={pagina === 1} onClick={() => setPagina((p) => p - 1)}>
                Página anterior
              </Botao>
              <span>Página {pagina}</span>
              <Botao
                variante="secundario"
                disabled={r.data.itens.length < 50}
                onClick={() => setPagina((p) => p + 1)}
              >
                Próxima página
              </Botao>
            </div>
          )}
        </>
      )}
    </Painel>
  );
}

function resumoDetalhes(d: Record<string, unknown>) {
  const partes = Object.entries(d)
    .filter(([, v]) => v !== null && v !== undefined && v !== "")
    .map(([k, v]) => `${k}: ${typeof v === "object" ? JSON.stringify(v) : String(v)}`);
  const t = partes.join("; ");
  return t.length > 140 ? t.slice(0, 140) + "…" : t || "—";
}
