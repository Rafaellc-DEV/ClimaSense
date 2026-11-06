import { useMemo, useState, type FormEvent, type ReactNode } from "react";
import { GitCompare, Pencil, Plus, Save, TriangleAlert, X } from "lucide-react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { CabecalhoTela } from "@/app/AppShell";
import { useTerritorios } from "@/app/FiltroFrase";
import { useAviso } from "@/design-system/componentes/Aviso";
import { Botao } from "@/design-system/componentes/Botao";
import { BotoesNivel, OPCOES_NIVEL_AVISO } from "@/design-system/componentes/BotoesNivel";
import { CartaoAviso, type DadosAviso } from "@/design-system/componentes/CartaoAviso";
import { AreaTexto, Campo } from "@/design-system/componentes/Campo";
import { Dialogo } from "@/design-system/componentes/Dialogo";
import { Dica } from "@/design-system/componentes/Dica";
import { CarregandoLista } from "@/design-system/componentes/Esqueleto";
import { LinhaDoTempo } from "@/design-system/componentes/Fluxo";
import { FalhaCarga, Painel } from "@/design-system/componentes/Painel";
import { Pilula } from "@/design-system/componentes/Pilula";
import { Selecao } from "@/design-system/componentes/Selecao";
import { api, enviar, type Esquemas } from "@/lib/api";
import { useConsulta } from "@/lib/consultas";
import { formatarDataHora, quandoRelativo } from "@/lib/formatos";
import { normalize } from "@/map/model";
import { PUBLICOS } from "@/textos/glossario";
import { funcionalidadeLigada } from "@/lib/funcionalidades";
import { RETORNO } from "@/textos/mensagens";
import { AcoesFluxo, ListaEvidencias, type EvidenciaForm } from "@/features/fluxo/AcoesFluxo";
import { EtapasFinas, SeloEstado } from "@/features/fluxo/Estado";
import { Bloco, CartaoDecisao, Contador, Fato, Fatos, Recolher, SecaoForm } from "@/features/fluxo/Pecas";
import estilos from "./Editor.module.css";

type Detalhe = Esquemas["DetalheComunicado"];
const MAX_TITULO = 120,
  MAX_TEXTO = 1200,
  MAX_ORIENTACOES = 5,
  PALAVRAS = 25;
const NIVEL_DA_PRIORIDADE: Record<string, string> = {
  atencao: "atencao",
  alerta: "alerta",
  critico: "critico",
};

interface Valores {
  territorios: string[];
  publico: string;
  nivel: string;
  titulo: string;
  texto: string;
  orientacoes: string[];
  validade_inicio: string; // datetime-local, horário do Recife
  validade_fim: string;
  evidencias: EvidenciaForm[];
  avaliacao_id?: string | null;
}

/** "2026-10-16T18:00" (horário do Recife, sem horário de verão desde 2019) ↔ ISO em UTC. */
const paraIso = (local: string) => new Date(`${local}:00-03:00`).toISOString();
function paraLocal(iso: string) {
  const d = new Date(new Date(iso).getTime() - 3 * 3_600_000);
  return d.toISOString().slice(0, 16);
}

/** Frases com mais de 25 palavras: difíceis para quem lê com dificuldade (RF-11.8). Mesma regra da API. */
export function frasesLongas(texto: string) {
  return texto
    .split(/(?<=[.!?])\s+|\n+/)
    .filter((f) => f.trim())
    .map((f, i) => ({ frase: i + 1, palavras: f.trim().split(/\s+/).length }))
    .filter((f) => f.palavras > PALAVRAS);
}

/** Aviso de leitura difícil: uma frase curta, com ícone e texto. */
function AvisoLeitura({
  frases,
  papel,
}: {
  frases: { frase: number; palavras: number }[];
  papel?: "status";
}) {
  return (
    <p className={estilos.longa} role={papel}>
      <TriangleAlert aria-hidden="true" size={20} />
      <span>
        {frases.map((l) => `A frase ${l.frase} tem ${l.palavras} palavras`).join("; ")}. Divida em frases de
        até {PALAVRAS}.
      </span>
    </p>
  );
}

function EscolhaTerritorios({ valor, aoMudar }: { valor: string[]; aoMudar: (v: string[]) => void }) {
  const territorios = useTerritorios();
  const [aberto, setAberto] = useState(false);
  const [q, setQ] = useState("");
  const nomes = new Map(
    (territorios.data ?? []).map((t) => [t.id, t.id === "recife" ? "Recife inteiro" : t.nome_exibicao]),
  );
  const filtrados = (territorios.data ?? []).filter(
    (t) => !q || normalize(t.nome_exibicao).includes(normalize(q)),
  );
  return (
    <div className={estilos.territorios}>
      <p className={estilos.rotulo} id="rotulo-territorios">
        Territórios
      </p>
      <ul aria-labelledby="rotulo-territorios">
        {valor.map((t) => (
          <li key={t}>
            {nomes.get(t) ?? t}
            <button
              type="button"
              aria-label={`Remover ${nomes.get(t) ?? t}`}
              onClick={() => aoMudar(valor.filter((x) => x !== t))}
            >
              <X aria-hidden="true" size={16} />
            </button>
          </li>
        ))}
        <li>
          <Botao variante="secundario" icone={<Plus />} onClick={() => setAberto(true)}>
            Adicionar território
          </Botao>
        </li>
      </ul>
      <Dialogo
        aberto={aberto}
        aoMudar={setAberto}
        titulo="Adicionar território"
        descricao="Bairros, distritos ou Recife inteiro."
      >
        <Campo
          rotulo="Procurar"
          type="search"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          autoComplete="off"
        />
        <ul className={estilos.opcoes}>
          {filtrados.slice(0, 40).map((t) => (
            <li key={t.id}>
              <label>
                <input
                  type="checkbox"
                  checked={valor.includes(t.id)}
                  onChange={(e) =>
                    aoMudar(e.target.checked ? [...valor, t.id] : valor.filter((x) => x !== t.id))
                  }
                />
                {nomes.get(t.id)}
              </label>
            </li>
          ))}
        </ul>
        <Botao onClick={() => setAberto(false)}>Pronto</Botao>
      </Dialogo>
    </div>
  );
}

function Formulario({
  inicial,
  rotuloSalvar,
  aviso: avisoVersao,
  aoSalvar,
  rodapeExtra,
  aoMudar,
}: {
  inicial: Valores;
  rotuloSalvar: string;
  aviso?: string;
  aoSalvar: (v: Valores) => Promise<void>;
  rodapeExtra?: ReactNode;
  aoMudar: (v: Valores) => void;
}) {
  const [v, setV] = useState(inicial);
  const [erro, setErro] = useState<string>();
  const [ocupado, setOcupado] = useState(false);
  const mudar = (p: Partial<Valores>) =>
    setV((x) => {
      const n = { ...x, ...p };
      aoMudar(n);
      return n;
    });
  const longas = useMemo(() => frasesLongas(v.texto), [v.texto]);

  async function salvar(e: FormEvent) {
    e.preventDefault();
    const problemas = [
      !v.territorios.length && "Escolha pelo menos um território.",
      !v.titulo.trim() && "Escreva um título.",
      v.validade_inicio >= v.validade_fim && "O fim da validade precisa ser depois do início.",
    ].filter(Boolean);
    if (problemas.length) return setErro(problemas.join(" "));
    setErro(undefined);
    setOcupado(true);
    try {
      await aoSalvar(v);
    } catch (x) {
      setErro((x as Error).message);
    } finally {
      setOcupado(false);
    }
  }

  return (
    <form className={estilos.form} onSubmit={salvar} noValidate>
      {avisoVersao && <p className={estilos.versao}>{avisoVersao}</p>}
      <SecaoForm titulo="Onde e para quem">
        <EscolhaTerritorios valor={v.territorios} aoMudar={(t) => mudar({ territorios: t })} />
        <Selecao
          rotulo="Público"
          valor={v.publico}
          aoMudar={(p) => mudar({ publico: p })}
          opcoes={Object.entries(PUBLICOS).map(([valor, rotulo]) => ({ valor, rotulo }))}
        />
      </SecaoForm>
      <SecaoForm titulo="Nível do aviso">
        <BotoesNivel
          nome="nivel"
          legenda="Nível do aviso"
          opcoes={OPCOES_NIVEL_AVISO}
          valor={v.nivel}
          aoMudar={(n) => mudar({ nivel: n })}
        />
      </SecaoForm>
      <SecaoForm
        titulo="Mensagem"
        dica="Diga o quê e onde, em linguagem simples. Frases curtas são mais fáceis de ler."
      >
        <Campo
          rotulo="Título"
          value={v.titulo}
          maxLength={MAX_TITULO}
          onChange={(e) => mudar({ titulo: e.target.value })}
          ajuda={<Contador atual={v.titulo.length} max={MAX_TITULO} />}
        />
        <AreaTexto
          rotulo="Texto"
          value={v.texto}
          maxLength={MAX_TEXTO}
          rows={6}
          onChange={(e) => mudar({ texto: e.target.value })}
          ajuda={<Contador atual={v.texto.length} max={MAX_TEXTO} />}
        />
        {longas.length > 0 && <AvisoLeitura frases={longas} papel="status" />}
      </SecaoForm>
      <SecaoForm titulo="O que fazer">
        <fieldset className={estilos.orientacoes}>
          <legend>
            Orientações
            <span className={estilos.limite}>
              {v.orientacoes.length} de {MAX_ORIENTACOES}
            </span>
          </legend>
          {v.orientacoes.map((o, i) => (
            <div key={i} className={estilos.orientacao}>
              <Campo
                rotulo={`Orientação ${i + 1}`}
                value={o}
                maxLength={300}
                onChange={(e) =>
                  mudar({ orientacoes: v.orientacoes.map((x, j) => (j === i ? e.target.value : x)) })
                }
              />
              <Botao
                variante="discreto"
                icone={<X />}
                onClick={() => mudar({ orientacoes: v.orientacoes.filter((_, j) => j !== i) })}
              >
                Remover<span className="so-leitor"> orientação {i + 1}</span>
              </Botao>
            </div>
          ))}
          {v.orientacoes.length < MAX_ORIENTACOES && (
            <Botao
              variante="secundario"
              icone={<Plus />}
              onClick={() => mudar({ orientacoes: [...v.orientacoes, ""] })}
            >
              Adicionar orientação
            </Botao>
          )}
        </fieldset>
      </SecaoForm>
      <SecaoForm titulo="Validade">
        <div className={estilos.linha}>
          <Campo
            rotulo="Vale a partir de"
            type="datetime-local"
            value={v.validade_inicio}
            onChange={(e) => mudar({ validade_inicio: e.target.value })}
            dica="Horário do Recife."
          />
          <Campo
            rotulo="Vale até"
            type="datetime-local"
            value={v.validade_fim}
            onChange={(e) => mudar({ validade_fim: e.target.value })}
            dica="Depois disso, o aviso sai sozinho da página inicial."
          />
        </div>
      </SecaoForm>
      <SecaoForm titulo="Evidências vinculadas">
        <ListaEvidencias
          evidencias={v.evidencias}
          aoRemover={(i) => mudar({ evidencias: v.evidencias.filter((_, j) => j !== i) })}
        />
      </SecaoForm>
      {erro && (
        <p role="alert" className={estilos.erro}>
          {erro}
        </p>
      )}
      <div className={estilos.rodape}>
        <Botao type="submit" disabled={ocupado} icone={<Save />}>
          {rotuloSalvar}
        </Botao>
        {rodapeExtra}
      </div>
    </form>
  );
}

function comoAviso(v: Valores, nomes: Map<string, string>, id = "previa"): DadosAviso {
  return {
    id,
    titulo: v.titulo,
    nivel: v.nivel,
    territorios: v.territorios.map((t) => ({ id: t, nome_exibicao: nomes.get(t) ?? t })),
    texto: v.texto,
    orientacoes: v.orientacoes.filter((o) => o.trim()),
    validade_inicio: v.validade_inicio ? paraIso(v.validade_inicio) : new Date().toISOString(),
    validade_fim: v.validade_fim ? paraIso(v.validade_fim) : new Date().toISOString(),
    emitido_por: "Vigilância em Saúde do Recife",
    publicado_em: null,
  };
}

function corpo(v: Valores) {
  return {
    ...v,
    orientacoes: v.orientacoes.filter((o) => o.trim()),
    validade_inicio: paraIso(v.validade_inicio),
    validade_fim: paraIso(v.validade_fim),
  };
}

function useNomes() {
  const territorios = useTerritorios();
  return useMemo(
    () =>
      new Map(
        (territorios.data ?? []).map((t) => [t.id, t.id === "recife" ? "Recife inteiro" : t.nome_exibicao]),
      ),
    [territorios.data],
  );
}

/** Novo comunicado: pode vir de uma avaliação aprovada (território, nível e evidências preenchidos). */
export function NovoComunicado() {
  const local = useLocation();
  const navegar = useNavigate();
  const aviso = useAviso();
  const nomes = useNomes();
  const pre = (local.state ?? {}) as {
    avaliacao_id?: string;
    territorios?: string[];
    evidencias?: EvidenciaForm[];
    prioridade?: string;
  };
  const agora = new Date();
  const inicial: Valores = {
    territorios: pre.territorios ?? [],
    publico: "populacao",
    nivel: NIVEL_DA_PRIORIDADE[pre.prioridade ?? ""] ?? "informativo",
    titulo: "",
    texto: "",
    orientacoes: [""],
    validade_inicio: paraLocal(agora.toISOString()),
    validade_fim: paraLocal(new Date(agora.getTime() + 24 * 3_600_000).toISOString()),
    evidencias: pre.evidencias ?? [],
    avaliacao_id: pre.avaliacao_id ?? null,
  };
  const [atual, setAtual] = useState(inicial);
  return (
    <>
      <CabecalhoTela
        titulo="Escrever comunicado"
        proposito="À direita, a prévia mostra exatamente o que a população verá na página inicial."
        voltar={<Link to="/app/comunicados">Todos os comunicados</Link>}
      />
      <div className={estilos.editor}>
        <Painel titulo="Comunicado" id="co-form">
          <Formulario
            inicial={inicial}
            rotuloSalvar="Salvar rascunho"
            aoMudar={setAtual}
            aoSalvar={async (v) => {
              const d = await enviar<Detalhe>("/comunicados", corpo(v));
              aviso({ titulo: RETORNO.salvar });
              navegar(`/app/comunicados/${d.id}`, { replace: true });
            }}
          />
        </Painel>
        <Previa aviso={comoAviso(atual, nomes)} />
      </div>
    </>
  );
}

/** Prévia ao vivo: o MESMO cartão da página inicial (design §9.9, RF-11.3). */
function Previa({ aviso, rodape }: { aviso: DadosAviso; rodape?: ReactNode }) {
  return (
    <aside className={estilos.previa} aria-labelledby="titulo-previa">
      <h2 id="titulo-previa">
        Prévia para a população
        <Dica
          texto="Exatamente como aparecerá na página inicial."
          rotulo="Sobre a prévia"
          alinhar="fim"
          lado="abaixo"
        />
      </h2>
      <CartaoAviso aviso={aviso} previa />
      {rodape}
    </aside>
  );
}

function Diferencas({ id, versoes }: { id: string; versoes: Esquemas["VersaoResumo"][] }) {
  const [par, setPar] = useState<[number, number] | null>(null);
  const [d, setD] = useState<Esquemas["Diferenca"]>();
  async function comparar(a: number, b: number) {
    setPar([a, b]);
    setD(await api<Esquemas["Diferenca"]>(`/comunicados/${id}/versoes/${a}/diferenca/${b}`));
  }
  const NOMES: Record<string, string> = {
    titulo: "Título",
    texto: "Texto",
    orientacoes: "O que fazer",
    nivel: "Nível",
    territorios: "Territórios",
    publico: "Público",
    validade_inicio: "Início da validade",
    validade_fim: "Fim da validade",
  };
  return (
    <>
      <ol className={estilos.versoes}>
        {[...versoes].reverse().map((v) => (
          <li key={v.numero}>
            <span className={estilos.versaoNumero}>{v.numero}</span>
            <span className={estilos.versaoTexto}>
              <strong>Versão {v.numero}</strong>
              <small>
                {v.autor_nome}, {formatarDataHora(v.criado_em)}
              </small>
            </span>
            {v.numero > 1 && (
              <Botao
                variante="discreto"
                icone={<GitCompare />}
                onClick={() => comparar(v.numero - 1, v.numero)}
              >
                O que mudou<span className="so-leitor"> na versão {v.numero}</span>
              </Botao>
            )}
          </li>
        ))}
      </ol>
      <Dialogo
        aberto={!!par}
        aoMudar={(a) => !a && (setPar(null), setD(undefined))}
        titulo={par ? `O que mudou da versão ${par[0]} para a ${par[1]}` : ""}
      >
        {!d ? (
          <CarregandoLista linhas={2} altura="3rem" />
        ) : !d.alterados.length ? (
          <p>Nenhuma diferença no conteúdo.</p>
        ) : (
          <div className={estilos.diferenca}>
            <p className={estilos.legenda}>
              <ins>Entrou</ins>
              <del>Saiu</del>
            </p>
            {d.alterados.map((campo) =>
              d.campos[campo] ? (
                <div key={campo}>
                  <h3>{NOMES[campo]}</h3>
                  <p>
                    {d.campos[campo].map((t, i) =>
                      t.tipo === "inserido" ? (
                        <ins key={i}>{t.texto}</ins>
                      ) : t.tipo === "removido" ? (
                        <del key={i}>{t.texto}</del>
                      ) : (
                        <span key={i}>{t.texto}</span>
                      ),
                    )}
                  </p>
                </div>
              ) : (
                <div key={campo}>
                  <h3>{NOMES[campo]}</h3>
                  <p>
                    <del>{formatarMetadado(campo, d.metadados[campo].antes)}</del> →{" "}
                    <ins>{formatarMetadado(campo, d.metadados[campo].depois)}</ins>
                  </p>
                </div>
              ),
            )}
          </div>
        )}
      </Dialogo>
    </>
  );
}

function formatarMetadado(campo: string, valor: string) {
  return campo.startsWith("validade") ? formatarDataHora(valor) : valor;
}

/** O que a pessoa deve fazer agora, em uma frase. */
function passo(c: Detalhe, salvarAntes: boolean) {
  if (c.acoes.includes("aprovar"))
    return `Você revisa a versão ${c.versao_atual}, de ${c.autor_nome}. Confira a prévia: é ela que vai para a população.`;
  if (c.acoes.includes("publicar")) return "Aprovado. Publique para o aviso aparecer na página inicial.";
  if (c.acoes.includes("enviar"))
    return salvarAntes
      ? "Salve as mudanças antes de enviar para revisão."
      : c.estado === "devolvido"
        ? "Ajuste o que foi pedido e envie de novo para revisão."
        : "Quando estiver pronto, envie para revisão.";
  if (c.estado === "publicado") return `No ar até ${quandoRelativo(c.previa.validade_fim)}.`;
  if (c.estado === "aprovado") return "Aprovado. Aguardando a coordenação publicar.";
  if (c.estado === "em_revisao") return "Aguardando a revisão de outra pessoa. Quem escreveu não aprova.";
  if (c.estado === "encerrado") return "Encerrado. Fica no histórico.";
  return "Nada a fazer agora.";
}

/** Editor do comunicado (design §9.9): edição, prévia ao vivo, decisão do revisor, publicação e histórico. */
export function EditorComunicado() {
  const { id = "" } = useParams();
  const cliente = useQueryClient();
  const aviso = useAviso();
  const nomes = useNomes();
  const r = useConsulta<Detalhe>(`/comunicados/${id}`);
  const [editando, setEditando] = useState(false);
  const [rascunho, setRascunho] = useState<Valores | null>(null);
  const atualizar = (d: Detalhe) => {
    cliente.setQueryData([`/comunicados/${id}`], d);
    void cliente.invalidateQueries({ queryKey: ["/comunicados"] });
    setEditando(false);
    setRascunho(null);
  };
  const voltar = <Link to="/app/comunicados">Todos os comunicados</Link>;
  if (r.isPending)
    return (
      <>
        <CabecalhoTela titulo="Comunicado" voltar={voltar} />
        <CarregandoLista linhas={3} altura="6rem" />
      </>
    );
  if (r.isError) return <FalhaCarga erro={r.error} aoTentar={() => r.refetch()} />;
  const c = r.data;
  const p = c.previa;
  const podeEditar = c.acoes.includes("editar");
  const formAberto = podeEditar && (editando || c.estado === "rascunho" || c.estado === "devolvido");
  const inicial: Valores = {
    territorios: c.territorios,
    publico: c.publico,
    nivel: p.nivel,
    titulo: p.titulo,
    texto: p.texto,
    orientacoes: p.orientacoes.length ? p.orientacoes : [""],
    validade_inicio: paraLocal(p.validade_inicio),
    validade_fim: paraLocal(p.validade_fim),
    evidencias: c.evidencias as unknown as EvidenciaForm[],
    avaliacao_id: c.avaliacao_id,
  };
  const previa: DadosAviso = rascunho ? comoAviso(rascunho, nomes, c.id) : p;
  const decide = c.acoes.includes("aprovar");
  const salvarAntes = formAberto && !!rascunho && c.acoes.includes("enviar");
  const temAcao = c.acoes.some((x) => x !== "editar");

  return (
    <>
      <CabecalhoTela titulo={p.titulo} acoes={<SeloEstado estado={c.estado} />} voltar={voltar} />
      <div className={estilos.pilha}>
        <Fatos>
          <Fato rotulo="Versão atual">{c.versao_atual}</Fato>
          {c.versao_aprovada && <Fato rotulo="Versão aprovada">{c.versao_aprovada}</Fato>}
          <Fato rotulo="Autor">{c.autor_nome}</Fato>
          <Fato rotulo="Vale até">{quandoRelativo(p.validade_fim)}</Fato>
          {c.publicado_em && <Fato rotulo="Publicado">{quandoRelativo(c.publicado_em)}</Fato>}
        </Fatos>
        <div className={estilos.etapas}>
          <EtapasFinas estado={c.estado} />
        </div>
        <CartaoDecisao
          titulo={decide ? "Sua decisão" : "Próximo passo"}
          tom={temAcao ? "agir" : "espera"}
          acoes={
            <AcoesFluxo<Detalhe>
              base={`/comunicados/${id}`}
              acoes={c.acoes}
              aoConcluir={atualizar}
              bloqueadas={formAberto && rascunho ? ["enviar"] : []}
              consequencias={{
                publicar: (
                  <>
                    Publicar torna o aviso visível para qualquer pessoa na página inicial até{" "}
                    <strong>{quandoRelativo(p.validade_fim)}</strong>. Depois disso ele sai sozinho.
                  </>
                ),
                encerrar:
                  c.estado === "publicado"
                    ? "Encerrar tira o aviso da página inicial agora. Ele fica no histórico e não pode ser publicado de novo."
                    : "Encerrar arquiva este comunicado. Ele fica no histórico e não pode mais ser editado.",
              }}
            />
          }
        >
          {passo(c, salvarAntes)}
        </CartaoDecisao>
        <div className={estilos.editor}>
          <Painel
            titulo={formAberto ? "Editar comunicado" : decide ? "Revisar esta versão" : "Conteúdo"}
            id="co-conteudo"
            acoes={
              podeEditar &&
              !formAberto && (
                <Botao variante="secundario" icone={<Pencil />} onClick={() => setEditando(true)}>
                  Editar (cria nova versão)
                </Botao>
              )
            }
          >
            {formAberto ? (
              <Formulario
                key={c.versao_atual}
                inicial={inicial}
                rotuloSalvar={
                  c.estado === "rascunho" || c.estado === "devolvido"
                    ? "Salvar rascunho"
                    : "Salvar nova versão"
                }
                aviso={
                  c.estado === "aprovado" || c.estado === "publicado" || c.estado === "em_revisao"
                    ? `Salvar cria a versão ${c.versao_atual + 1}, que volta para revisão${
                        c.estado === "publicado" ? " e sai da página inicial até ser aprovada de novo" : ""
                      }. A versão ${c.versao_atual} fica guardada.`
                    : undefined
                }
                aoMudar={setRascunho}
                aoSalvar={async (v) => {
                  const d = await enviar<Detalhe>(`/comunicados/${id}`, corpo(v), "PUT");
                  aviso({ titulo: c.estado === "rascunho" ? RETORNO.salvar : "Nova versão salva." });
                  atualizar(d);
                }}
                rodapeExtra={
                  editando && (
                    <Botao variante="discreto" onClick={() => (setEditando(false), setRascunho(null))}>
                      Cancelar edição
                    </Botao>
                  )
                }
              />
            ) : (
              <div className={estilos.leitura}>
                {c.frases_longas.length > 0 && <AvisoLeitura frases={c.frases_longas} />}
                <Bloco titulo="Público">
                  <p>{PUBLICOS[c.publico] ?? c.publico}</p>
                </Bloco>
                <Bloco titulo="Evidências">
                  <ListaEvidencias evidencias={c.evidencias as unknown as EvidenciaForm[]} />
                </Bloco>
                {c.avaliacao_id && funcionalidadeLigada("avaliacoes") && (
                  <p>
                    <Link to={`/app/avaliacoes/${c.avaliacao_id}`}>
                      Ver a avaliação que originou este comunicado
                    </Link>
                  </p>
                )}
              </div>
            )}
          </Painel>
          <Previa
            aviso={previa}
            rodape={
              <>
                <p className={estilos.hash}>
                  <Pilula tom="neutro" pequena semMarca>
                    Conteúdo {c.hash_conteudo.slice(0, 12)}
                  </Pilula>
                  <Dica
                    texto="Identificador do conteúdo. A publicação só acontece se ele for igual ao da versão aprovada."
                    rotulo="Sobre o identificador do conteúdo"
                    alinhar="fim"
                  />
                </p>
                <Recolher
                  titulo="Histórico"
                  contagem={c.linha_do_tempo.length}
                  aberto={c.estado === "devolvido"}
                >
                  <LinhaDoTempo eventos={c.linha_do_tempo} />
                </Recolher>
                <Recolher titulo="Versões" contagem={c.versoes.length}>
                  <Diferencas id={id} versoes={c.versoes} />
                </Recolher>
              </>
            }
          />
        </div>
      </div>
    </>
  );
}
