import { useMemo, useState, type FormEvent } from "react";
import { GitCompare, Pencil, Plus, Save, X } from "lucide-react";
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
import { EtapasFluxo, LinhaDoTempo } from "@/design-system/componentes/Fluxo";
import { Carregando, FalhaCarga, Painel } from "@/design-system/componentes/Painel";
import { Selecao } from "@/design-system/componentes/Selecao";
import { api, enviar, type Esquemas } from "@/lib/api";
import { useConsulta } from "@/lib/consultas";
import { formatarDataHora, quandoRelativo } from "@/lib/formatos";
import { normalize } from "@/map/model";
import { PUBLICOS } from "@/textos/glossario";
import { RETORNO } from "@/textos/mensagens";
import { AcoesFluxo, ListaEvidencias, type EvidenciaForm } from "@/features/fluxo/AcoesFluxo";
import { SeloEstado } from "@/features/fluxo/Estado";
import fluxo from "@/features/fluxo/Fluxo.module.css";
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
          <Botao variante="discreto" icone={<Plus />} onClick={() => setAberto(true)}>
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
  rodapeExtra?: React.ReactNode;
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
    <form className={fluxo.form} onSubmit={salvar} noValidate>
      {avisoVersao && <p className={fluxo.dica}>{avisoVersao}</p>}
      <EscolhaTerritorios valor={v.territorios} aoMudar={(t) => mudar({ territorios: t })} />
      <Selecao
        rotulo="Público"
        valor={v.publico}
        aoMudar={(p) => mudar({ publico: p })}
        opcoes={Object.entries(PUBLICOS).map(([valor, rotulo]) => ({ valor, rotulo }))}
      />
      <BotoesNivel
        nome="nivel"
        legenda="Nível do aviso"
        opcoes={OPCOES_NIVEL_AVISO}
        valor={v.nivel}
        aoMudar={(n) => mudar({ nivel: n })}
      />
      <Campo
        rotulo="Título"
        value={v.titulo}
        maxLength={MAX_TITULO}
        onChange={(e) => mudar({ titulo: e.target.value })}
        ajuda={
          <span className={fluxo.contador} data-excedeu={v.titulo.length >= MAX_TITULO}>
            {v.titulo.length} de {MAX_TITULO} caracteres. Diga o quê e onde, em linguagem simples.
          </span>
        }
      />
      <AreaTexto
        rotulo="Texto"
        value={v.texto}
        maxLength={MAX_TEXTO}
        rows={6}
        onChange={(e) => mudar({ texto: e.target.value })}
        ajuda={
          <span className={fluxo.contador} data-excedeu={v.texto.length >= MAX_TEXTO}>
            {v.texto.length} de {MAX_TEXTO} caracteres.
          </span>
        }
      />
      {longas.length > 0 && (
        <p className={estilos.longa} role="status">
          {longas.map((l) => `A frase ${l.frase} tem ${l.palavras} palavras.`).join(" ")} Frases com mais de{" "}
          {PALAVRAS} palavras são difíceis para quem lê com dificuldade. Tente dividir.
        </p>
      )}
      <fieldset className={estilos.orientacoes}>
        <legend>O que fazer (até {MAX_ORIENTACOES} orientações)</legend>
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
              onClick={() => mudar({ orientacoes: v.orientacoes.filter((_, j) => j !== i) })}
            >
              Remover
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
      <div className={fluxo.linha}>
        <Campo
          rotulo="Vale a partir de"
          type="datetime-local"
          value={v.validade_inicio}
          onChange={(e) => mudar({ validade_inicio: e.target.value })}
          ajuda="Horário do Recife."
        />
        <Campo
          rotulo="Vale até"
          type="datetime-local"
          value={v.validade_fim}
          onChange={(e) => mudar({ validade_fim: e.target.value })}
          ajuda="Depois disso, o aviso sai sozinho da página inicial."
        />
      </div>
      <div>
        <h3 className={fluxo.dica}>Evidências vinculadas</h3>
        <ListaEvidencias
          evidencias={v.evidencias}
          aoRemover={(i) => mudar({ evidencias: v.evidencias.filter((_, j) => j !== i) })}
        />
      </div>
      {erro && (
        <p role="alert" className={estilos.erro}>
          {erro}
        </p>
      )}
      <div className={fluxo.rodape}>
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
      <p className={fluxo.voltar}>
        <Link to="/app/comunicados">Todos os comunicados</Link>
      </p>
      <CabecalhoTela
        titulo="Escrever comunicado"
        proposito="À direita, a prévia mostra exatamente o que a população verá na página inicial."
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

function Previa({ aviso, rodape }: { aviso: DadosAviso; rodape?: React.ReactNode }) {
  return (
    <aside className={estilos.previa} aria-labelledby="titulo-previa">
      <h2 id="titulo-previa">Prévia para a população</h2>
      <p className={fluxo.dica}>Exatamente como aparecerá na página inicial.</p>
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
            <span>
              <strong>Versão {v.numero}</strong>, de {v.autor_nome}, {formatarDataHora(v.criado_em)}
            </span>
            {v.numero > 1 && (
              <Botao
                variante="discreto"
                icone={<GitCompare />}
                onClick={() => comparar(v.numero - 1, v.numero)}
              >
                O que mudou
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
          <Carregando />
        ) : !d.alterados.length ? (
          <p>Nenhuma diferença no conteúdo.</p>
        ) : (
          <div className={estilos.diferenca}>
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
            <p className={fluxo.dica}>Trechos sublinhados entraram; riscados saíram.</p>
          </div>
        )}
      </Dialogo>
    </>
  );
}

function formatarMetadado(campo: string, valor: string) {
  return campo.startsWith("validade") ? formatarDataHora(valor) : valor;
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
    void cliente.invalidateQueries({ queryKey: ["/painel/resumo"] });
    void cliente.invalidateQueries({ queryKey: ["/comunicados"] });
    setEditando(false);
    setRascunho(null);
  };
  if (r.isPending) return <Carregando />;
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

  return (
    <>
      <p className={fluxo.voltar}>
        <Link to="/app/comunicados">Todos os comunicados</Link>
      </p>
      <CabecalhoTela
        titulo={p.titulo}
        proposito={`Versão ${c.versao_atual}, de ${c.autor_nome}.${
          c.versao_aprovada ? ` Versão aprovada: ${c.versao_aprovada}.` : ""
        }${c.publicado_em ? ` Publicado ${quandoRelativo(c.publicado_em)}.` : ""}`}
        acoes={<SeloEstado estado={c.estado} />}
      />
      <Painel titulo="Etapas do fluxo" id="co-etapas" className={estilos.etapas}>
        <EtapasFluxo estado={c.estado} />
      </Painel>
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
                c.estado === "rascunho" || c.estado === "devolvido" ? "Salvar rascunho" : "Salvar nova versão"
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
            <div className={fluxo.leitura}>
              {decide && (
                <p className={fluxo.dica}>
                  Você está revisando a versão {c.versao_atual}, de {c.autor_nome}. Confira a prévia ao lado:
                  é ela que vai para a população. Aprove ou devolva explicando o que ajustar.
                </p>
              )}
              {c.frases_longas.length > 0 && (
                <p className={estilos.longa}>
                  Atenção à leitura:{" "}
                  {c.frases_longas.map((f) => `a frase ${f.frase} tem ${f.palavras} palavras`).join("; ")}.
                </p>
              )}
              <div>
                <h3>Público</h3>
                <p>{PUBLICOS[c.publico] ?? c.publico}</p>
              </div>
              <div>
                <h3>Evidências</h3>
                <ListaEvidencias evidencias={c.evidencias as unknown as EvidenciaForm[]} />
              </div>
              {c.avaliacao_id && (
                <p>
                  <Link to={`/app/avaliacoes/${c.avaliacao_id}`}>
                    Ver a avaliação que originou este comunicado
                  </Link>
                </p>
              )}
            </div>
          )}
          <div className={estilos.acoesFluxo}>
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
            {formAberto && rascunho && c.acoes.includes("enviar") && (
              <p className={fluxo.dica}>Salve as mudanças antes de enviar para revisão.</p>
            )}
          </div>
        </Painel>
        <Previa
          aviso={previa}
          rodape={
            <>
              <p className={estilos.hash}>
                Identificador do conteúdo: <code>{c.hash_conteudo.slice(0, 12)}</code>. A publicação só
                acontece se ele for igual ao da versão aprovada.
              </p>
              <h3 className={estilos.subtitulo}>Histórico</h3>
              <LinhaDoTempo eventos={c.linha_do_tempo} />
              <h3 className={estilos.subtitulo}>Versões</h3>
              <Diferencas id={id} versoes={c.versoes} />
            </>
          }
        />
      </div>
    </>
  );
}
