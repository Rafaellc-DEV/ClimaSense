import { useId, useMemo, useState, type FormEvent } from "react";
import { History, Pencil, Plus, RefreshCw } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { useAviso } from "@/design-system/componentes/Aviso";
import { Botao } from "@/design-system/componentes/Botao";
import { AreaTexto, Campo } from "@/design-system/componentes/Campo";
import { Dialogo } from "@/design-system/componentes/Dialogo";
import { CarregandoLista } from "@/design-system/componentes/Esqueleto";
import { Painel } from "@/design-system/componentes/Painel";
import { Pilula } from "@/design-system/componentes/Pilula";
import { Segmentado } from "@/design-system/componentes/Segmentado";
import { VazioConvidativo } from "@/design-system/componentes/VazioConvidativo";
import { ListaAdaptavel } from "@/features/fluxo/ListaAdaptavel";
import {
  EstadoConsulta,
  invalidarPrefixo,
  SelecaoTerritorio,
  useNomeTerritorio,
} from "@/features/evento/Evento";
import { listaDe, type Abrigo, type HistoricoAbrigo } from "@/features/evento/tipos";
import { consulta, enviar, ErroApi } from "@/lib/api";
import { useConsulta, useConsultaViva } from "@/lib/consultas";
import { fontesDe } from "@/lib/frescor";
import { fontesDado, LegendaFonte } from "@/design-system/componentes/EstadoDados";
import { formatarDataHora, formatarNumero, quandoRelativo } from "@/lib/formatos";
import { useSessao } from "@/lib/sessao";
import { normalizar } from "@/features/landing/abrigosPublicos";
import campo from "@/design-system/componentes/Campo.module.css";
import estilos from "./Abrigos.module.css";

/** Texto do campo numérico → número inteiro, `null` se vazio, `NaN` se inválido. */
function inteiro(v: string): number | null {
  if (v.trim() === "") return null;
  const n = Number(v);
  return Number.isInteger(n) && n >= 0 ? n : Number.NaN;
}

const POR_PAGINA = 20;

type Mudanca = { de?: unknown; para?: unknown };
type HistoricoComMudancas = HistoricoAbrigo & {
  capacidade?: number | null;
  alteracoes?: Record<string, Mudanca> | null;
};

/** “Capacidade: de 80 para 120 pessoas”: só o que a API diz que mudou. */
function frasesDeMudanca(h: HistoricoComMudancas): string[] {
  const alt = h.alteracoes ?? {};
  const valor = (v: unknown, unidade = "") =>
    v === null || v === undefined || v === "" ? "sem dado" : `${v}${unidade}`;
  const frases: string[] = [];
  if (alt.capacidade)
    frases.push(
      `Capacidade: de ${valor(alt.capacidade.de)} para ${valor(alt.capacidade.para)}${
        alt.capacidade.para ? " pessoas" : ""
      }`,
    );
  if (alt.endereco) frases.push(`Endereço: de ${valor(alt.endereco.de)} para ${valor(alt.endereco.para)}`);
  return frases;
}

/**
 * Lista de abrigos da Situação do evento (RF-08, RF-09): abertos primeiro, com “Atualizar” (aberto ou fechado, pessoas
 * abrigadas, desabrigados atendidos e observação), “Editar dados” (capacidade e endereço) e histórico. É registro
 * manual da equipe, com hora e autor (PRD §9). Os totais ficam no topo da tela, calculados pela API.
 */
export function ListaAbrigos() {
  const { pode } = useSessao();
  const podeEditar = pode("editar");
  const [filtro, setFiltro] = useState<"todos" | "abertos">("todos");
  const r = useConsultaViva<unknown>(`/abrigos${consulta({ aberto: filtro === "abertos" ? "true" : null })}`);
  const nome = useNomeTerritorio();
  const todos = listaDe<Abrigo>(r.data);
  // com ~200 locais cadastrados, a lista precisa de busca, distrito e páginas; os abertos vêm sempre primeiro
  const [busca, setBusca] = useState("");
  const [distrito, setDistrito] = useState("");
  const [quantos, setQuantos] = useState(POR_PAGINA);
  const idBusca = useId();
  const idDistrito = useId();
  const distritos = useMemo(
    () =>
      [...new Set(todos.map((a) => a.distrito_nome).filter((d): d is string => !!d))].sort((a, b) =>
        a.localeCompare(b, "pt-BR", { numeric: true }),
      ),
    [todos],
  );
  const itens = useMemo(() => {
    const q = normalizar(busca);
    return todos
      .filter((a) => !distrito || a.distrito_nome === distrito)
      .filter((a) => !q || [a.nome, a.bairro_nome, a.endereco].some((c) => c && normalizar(c).includes(q)))
      .sort((a, b) => Number(b.aberto) - Number(a.aberto));
  }, [todos, busca, distrito]);
  const filtrando = !!busca || !!distrito;
  const [atualizar, setAtualizar] = useState<Abrigo | null>(null);
  const [cadastrar, setCadastrar] = useState(false);
  const [historico, setHistorico] = useState<Abrigo | null>(null);
  const [editar, setEditar] = useState<Abrigo | null>(null);

  return (
    <>
      <div className={estilos.pagina}>
        {r.isError && (
          <EstadoConsulta erro={r.error} oQue="o registro de abrigos" aoTentar={() => r.refetch()} />
        )}

        {!r.isError && (
          <Painel
            id="ab-lista"
            titulo={filtro === "abertos" ? "Abrigos abertos" : "Abrigos e locais cadastrados"}
            acoes={
              <span className={estilos.acoesLista}>
                {podeEditar && (
                  <Botao variante="secundario" icone={<Plus />} onClick={() => setCadastrar(true)}>
                    Cadastrar abrigo
                  </Botao>
                )}
                <Segmentado
                  rotulo="Mostrar"
                  rotuloOculto
                  opcoes={[
                    { valor: "todos", rotulo: "Todos" },
                    { valor: "abertos", rotulo: "Só abertos" },
                  ]}
                  valor={filtro}
                  aoMudar={setFiltro}
                />
              </span>
            }
          >
            {todos.length > 0 && (
              <div className={estilos.filtros}>
                <div className={campo.campo}>
                  <label htmlFor={idBusca} className={campo.rotulo}>
                    Buscar por nome, bairro ou rua
                  </label>
                  <input
                    id={idBusca}
                    type="search"
                    name="busca-abrigo"
                    autoComplete="off"
                    className={campo.entrada}
                    placeholder="Ex.: Cohab, escola…"
                    value={busca}
                    onChange={(e) => {
                      setBusca(e.target.value);
                      setQuantos(POR_PAGINA);
                    }}
                  />
                </div>
                {distritos.length > 1 && (
                  <div className={campo.campo}>
                    <label htmlFor={idDistrito} className={campo.rotulo}>
                      Distrito
                    </label>
                    <select
                      id={idDistrito}
                      className={campo.entrada}
                      value={distrito}
                      onChange={(e) => {
                        setDistrito(e.target.value);
                        setQuantos(POR_PAGINA);
                      }}
                    >
                      <option value="">Todos os distritos</option>
                      {distritos.map((d) => (
                        <option key={d} value={d}>
                          {d}
                        </option>
                      ))}
                    </select>
                  </div>
                )}
              </div>
            )}
            {todos.length > 0 && (
              <p className={estilos.contagem} role="status">
                {itens.length === 0
                  ? ""
                  : `${formatarNumero(Math.min(quantos, itens.length))} de ${formatarNumero(itens.length)} ${
                      filtrando ? "encontrados" : itens.length === 1 ? "local" : "locais"
                    }${
                      itens.some((a) => a.aberto)
                        ? ", abertos primeiro."
                        : ". Nenhum está marcado como aberto: use Atualizar na linha do abrigo quando ele abrir."
                    }`}
              </p>
            )}
            <ListaAdaptavel
              legenda="Abrigos cadastrados"
              carregando={r.isPending}
              linhas={itens.slice(0, quantos)}
              chaveLinha={(a) => String(a.id)}
              vazio={
                <VazioConvidativo
                  titulo={
                    filtrando && todos.length > 0
                      ? "Nenhum local com essa busca."
                      : filtro === "abertos"
                        ? "Nenhum abrigo aberto registrado."
                        : "Nenhum abrigo cadastrado ainda."
                  }
                  texto={
                    filtrando && todos.length > 0
                      ? "Tente outro nome, bairro ou distrito."
                      : filtro === "abertos"
                        ? "Nenhum dos locais cadastrados está marcado como aberto. Quando um abrir, escolha “Todos”, ache o local e use Atualizar para marcar como aberto."
                        : "Cadastre o abrigo assim que ele for aberto; a contagem do painel vem daqui."
                  }
                  acao={
                    filtro === "abertos" ? (
                      <Botao variante="secundario" onClick={() => setFiltro("todos")}>
                        Ver todos os locais
                      </Botao>
                    ) : (
                      podeEditar && (
                        <Botao variante="secundario" onClick={() => setCadastrar(true)}>
                          Cadastrar abrigo
                        </Botao>
                      )
                    )
                  }
                />
              }
              colunas={[
                {
                  chave: "nome",
                  titulo: "Abrigo",
                  celula: (a) => (
                    <span className={estilos.abrigo}>
                      <b>{a.nome}</b>
                      <small>
                        {nome(a.bairro_id ?? a.territorio_id, a.bairro_nome ?? a.territorio_nome)}
                        {a.endereco ? ` · ${a.endereco}` : ""}
                        {!a.endereco && podeEditar && (
                          <>
                            {" · "}
                            <span className={estilos.semDado}>sem endereço </span>
                            <button type="button" className={estilos.informar} onClick={() => setEditar(a)}>
                              Informar<span className="so-leitor"> endereço de {a.nome}</span>
                            </button>
                          </>
                        )}
                      </small>
                    </span>
                  ),
                },
                {
                  chave: "aberto",
                  titulo: "Situação",
                  celula: (a) => {
                    const quando = a.status_fonte === undefined ? a.atualizado_em : a.status_informado_em;
                    const autor = a.atualizado_por_nome ?? a.atualizado_por;
                    return (
                      <span className={estilos.abrigo}>
                        {a.aberto ? (
                          <Pilula tom="info">Aberto</Pilula>
                        ) : a.status_fonte === null ? (
                          // ninguém informou ainda: não é “fechado” (RN-01)
                          <Pilula tom="neutro">Sem informação</Pilula>
                        ) : (
                          <Pilula tom="neutro">Fechado</Pilula>
                        )}
                        <small>{quando ? quandoRelativo(quando) : "sem hora"}</small>
                        {autor && <small>por {autor}</small>}
                      </span>
                    );
                  },
                },
                {
                  chave: "abrigadas",
                  titulo: "Pessoas abrigadas",
                  numerica: true,
                  celula: (a) => (
                    <span className={estilos.abrigo}>
                      {a.pessoas_abrigadas !== null && a.pessoas_abrigadas !== undefined ? (
                        formatarNumero(a.pessoas_abrigadas)
                      ) : (
                        <span className={estilos.semDado}>sem dado</span>
                      )}
                      <small>
                        {a.capacidade !== null && a.capacidade !== undefined ? (
                          `de ${formatarNumero(a.capacidade)} vagas`
                        ) : (
                          <span className={estilos.semDado}>
                            vagas sem dado
                            {podeEditar && (
                              <button type="button" className={estilos.informar} onClick={() => setEditar(a)}>
                                Informar<span className="so-leitor"> capacidade de {a.nome}</span>
                              </button>
                            )}
                          </span>
                        )}
                      </small>
                    </span>
                  ),
                },
                {
                  chave: "desabrigados",
                  titulo: "Desabrigados",
                  numerica: true,
                  celula: (a) =>
                    a.desabrigados !== null && a.desabrigados !== undefined ? (
                      formatarNumero(a.desabrigados)
                    ) : (
                      <span className={estilos.semDado}>sem dado</span>
                    ),
                },
                {
                  chave: "acoes",
                  titulo: "Ações",
                  semRotulo: true,
                  celula: (a) => (
                    <span className={estilos.botoes}>
                      {podeEditar && (
                        <Botao icone={<RefreshCw />} onClick={() => setAtualizar(a)}>
                          Atualizar<span className="so-leitor"> {a.nome}</span>
                        </Botao>
                      )}
                      {podeEditar && (
                        <Botao variante="secundario" icone={<Pencil />} onClick={() => setEditar(a)}>
                          Editar dados<span className="so-leitor"> de {a.nome}</span>
                        </Botao>
                      )}
                      <Botao variante="discreto" icone={<History />} onClick={() => setHistorico(a)}>
                        Histórico<span className="so-leitor"> de {a.nome}</span>
                      </Botao>
                    </span>
                  ),
                },
              ]}
            />
            {itens.length > quantos && (
              <Botao variante="secundario" onClick={() => setQuantos((q) => q + POR_PAGINA)}>
                Mostrar mais {Math.min(POR_PAGINA, itens.length - quantos)}
              </Botao>
            )}
            <LegendaFonte fontes={fontesDado(fontesDe(r.data))}>
              {fontesDe(r.data).length === 0 && (
                <span>Fonte: feed do COP (abertura) e registro da equipe (pessoas, com hora e autor).</span>
              )}
            </LegendaFonte>
          </Painel>
        )}
      </div>

      {atualizar && <DialogoAtualizar abrigo={atualizar} aoFechar={() => setAtualizar(null)} />}
      {editar && <DialogoEditarDados abrigo={editar} aoFechar={() => setEditar(null)} />}
      {cadastrar && <DialogoCadastrar aoFechar={() => setCadastrar(false)} />}
      {historico && <DialogoHistorico abrigo={historico} aoFechar={() => setHistorico(null)} />}
    </>
  );
}

function useSalvar(aoFechar: () => void) {
  const cliente = useQueryClient();
  const avisar = useAviso();
  const [erro, setErro] = useState<string>();
  const [ocupado, setOcupado] = useState(false);
  async function salvar(caminho: string, corpo: unknown, metodo: string, confirmacao: string) {
    setOcupado(true);
    try {
      await enviar(caminho, corpo, metodo);
      void invalidarPrefixo(cliente, "/abrigos");
      void invalidarPrefixo(cliente, "/boletim");
      avisar({ titulo: confirmacao });
      aoFechar();
    } catch (x) {
      setErro(x instanceof ErroApi ? x.message : "Não foi possível salvar. Tente de novo.");
      setOcupado(false);
    }
  }
  return { erro, setErro, ocupado, salvar };
}

/**
 * Atualização rápida (registro manual da equipe, PRD §9): aberto ou fechado, pessoas abrigadas, desabrigados
 * atendidos e uma observação. Campo em branco quer dizer “sem informação”, não zero (RN-01, RN-02).
 */
function DialogoAtualizar({ abrigo, aoFechar }: { abrigo: Abrigo; aoFechar: () => void }) {
  const [aberto, setAberto] = useState(abrigo.aberto ? "sim" : "nao");
  const [abrigadas, setAbrigadas] = useState(abrigo.pessoas_abrigadas?.toString() ?? "");
  const [desabrigados, setDesabrigados] = useState(abrigo.desabrigados?.toString() ?? "");
  const [obs, setObs] = useState(abrigo.observacao ?? "");
  const [faltas, setFaltas] = useState<{ abrigadas?: string; desabrigados?: string }>({});
  const { erro, ocupado, salvar } = useSalvar(aoFechar);

  function enviarForm(e: FormEvent) {
    e.preventDefault();
    const pessoas = inteiro(abrigadas);
    const sem = inteiro(desabrigados);
    const invalido = "Use um número inteiro, sem pontos nem letras.";
    const f = {
      abrigadas: Number.isNaN(pessoas) ? invalido : undefined,
      desabrigados: Number.isNaN(sem) ? invalido : undefined,
    };
    setFaltas(f);
    if (f.abrigadas || f.desabrigados) return;
    void salvar(
      `/abrigos/${encodeURIComponent(String(abrigo.id))}`,
      {
        aberto: aberto === "sim",
        pessoas_abrigadas: pessoas,
        desabrigados: sem,
        observacao: obs.trim() || null,
      },
      "PATCH",
      "Abrigo atualizado.",
    );
  }

  return (
    <Dialogo
      aberto
      aoMudar={(a) => !a && aoFechar()}
      titulo={`Atualizar ${abrigo.nome}`}
      descricao="A atualização fica no histórico com a hora e o seu nome."
      acoes={
        <>
          <Botao variante="secundario" onClick={aoFechar}>
            Cancelar
          </Botao>
          <Botao type="submit" form="form-atualizar-abrigo" disabled={ocupado} grande>
            {ocupado ? "Salvando…" : "Salvar"}
          </Botao>
        </>
      }
    >
      <form id="form-atualizar-abrigo" className={estilos.form} onSubmit={enviarForm} noValidate>
        <Segmentado
          rotulo="O abrigo está"
          opcoes={[
            { valor: "sim", rotulo: "Aberto" },
            { valor: "nao", rotulo: "Fechado" },
          ]}
          valor={aberto}
          aoMudar={setAberto}
        />
        <div className={estilos.duplaCampos}>
          <Campo
            rotulo="Pessoas abrigadas"
            type="number"
            inputMode="numeric"
            min={0}
            value={abrigadas}
            onChange={(e) => setAbrigadas(e.target.value)}
            erro={faltas.abrigadas}
            ajuda="Deixe em branco se não souber."
          />
          <Campo
            rotulo="Desabrigados atendidos"
            type="number"
            inputMode="numeric"
            min={0}
            value={desabrigados}
            onChange={(e) => setDesabrigados(e.target.value)}
            erro={faltas.desabrigados}
            ajuda="Deixe em branco se não souber."
          />
        </div>
        <AreaTexto
          privacidade
          rotulo="Observação (opcional)"
          rows={2}
          value={obs}
          onChange={(e) => setObs(e.target.value)}
        />
        {erro && (
          <p className={estilos.erro} role="alert">
            {erro}
          </p>
        )}
      </form>
    </Dialogo>
  );
}

/** Dados que não vêm de API: a equipe liga ou vai ao local e informa aqui. Não mexe em aberto/fechado. */
function DialogoEditarDados({ abrigo, aoFechar }: { abrigo: Abrigo; aoFechar: () => void }) {
  const [cap, setCap] = useState(abrigo.capacidade?.toString() ?? "");
  const [endereco, setEndereco] = useState(abrigo.endereco ?? "");
  const [obs, setObs] = useState(abrigo.observacao ?? "");
  const [erroCap, setErroCap] = useState<string>();
  const { erro, ocupado, salvar } = useSalvar(aoFechar);

  function enviarForm(e: FormEvent) {
    e.preventDefault();
    const capacidade = inteiro(cap);
    if (Number.isNaN(capacidade)) {
      setErroCap("Use um número inteiro, sem pontos nem letras.");
      return;
    }
    setErroCap(undefined);
    void salvar(
      `/abrigos/${encodeURIComponent(String(abrigo.id))}`,
      { capacidade, endereco: endereco.trim() || null, observacao: obs.trim() || null },
      "PATCH",
      "Dados do abrigo salvos.",
    );
  }

  return (
    <Dialogo
      aberto
      aoMudar={(a) => !a && aoFechar()}
      titulo={`Editar dados de ${abrigo.nome}`}
      descricao="Capacidade e endereço vêm de ligação ou visita ao local. A mudança fica no histórico, com a hora e o seu nome."
      acoes={
        <>
          <Botao variante="secundario" onClick={aoFechar}>
            Cancelar
          </Botao>
          <Botao type="submit" form="form-editar-abrigo" disabled={ocupado}>
            {ocupado ? "Salvando…" : "Salvar"}
          </Botao>
        </>
      }
    >
      <form id="form-editar-abrigo" className={estilos.form} onSubmit={enviarForm} noValidate>
        <Campo
          rotulo="Capacidade em pessoas"
          type="number"
          inputMode="numeric"
          min={0}
          value={cap}
          onChange={(e) => setCap(e.target.value)}
          erro={erroCap}
          autoFocus
        />
        <Campo rotulo="Endereço" value={endereco} onChange={(e) => setEndereco(e.target.value)} />
        <AreaTexto
          privacidade
          rotulo="Observação"
          ajuda="Ex.: acesso pelo portão lateral, confirmado por ligação em 04/11."
          rows={3}
          value={obs}
          onChange={(e) => setObs(e.target.value)}
        />
        {erro && (
          <p className={estilos.erro} role="alert">
            {erro}
          </p>
        )}
      </form>
    </Dialogo>
  );
}

function DialogoCadastrar({ aoFechar }: { aoFechar: () => void }) {
  const [v, setV] = useState({
    nome: "",
    bairro: "",
    endereco: "",
    capacidade: "",
    aberto: "sim",
    observacao: "",
  });
  const [faltas, setFaltas] = useState<{ nome?: string; bairro?: string }>({});
  const { erro, setErro, ocupado, salvar } = useSalvar(aoFechar);
  const mudar = (k: keyof typeof v) => (x: string) => setV((a) => ({ ...a, [k]: x }));

  function enviarForm(e: FormEvent) {
    e.preventDefault();
    const f = {
      nome: v.nome.trim() ? undefined : "Escreva o nome do abrigo.",
      bairro: v.bairro ? undefined : "Escolha o bairro.",
    };
    setFaltas(f);
    if (f.nome || f.bairro) return;
    const capacidade = inteiro(v.capacidade);
    if (Number.isNaN(capacidade)) {
      setErro("Capacidade: use um número inteiro, sem pontos nem letras.");
      return;
    }
    void salvar(
      "/abrigos",
      {
        nome: v.nome.trim(),
        bairro_id: v.bairro,
        endereco: v.endereco.trim() || null,
        capacidade,
        aberto: v.aberto === "sim",
        observacao: v.observacao.trim() || null,
      },
      "POST",
      "Abrigo cadastrado.",
    );
  }

  return (
    <Dialogo
      aberto
      aoMudar={(a) => !a && aoFechar()}
      titulo="Cadastrar abrigo"
      acoes={
        <>
          <Botao variante="secundario" onClick={aoFechar}>
            Cancelar
          </Botao>
          <Botao type="submit" form="form-cadastrar-abrigo" disabled={ocupado}>
            {ocupado ? "Cadastrando…" : "Cadastrar abrigo"}
          </Botao>
        </>
      }
    >
      <form id="form-cadastrar-abrigo" className={estilos.form} onSubmit={enviarForm} noValidate>
        <Campo
          rotulo="Nome do abrigo"
          value={v.nome}
          onChange={(e) => mudar("nome")(e.target.value)}
          erro={faltas.nome}
          autoFocus
        />
        <SelecaoTerritorio
          rotulo="Bairro"
          niveis={["bairro"]}
          valor={v.bairro}
          aoMudar={mudar("bairro")}
          erro={faltas.bairro}
          obrigatorio
        />
        <Campo
          rotulo="Endereço (opcional)"
          value={v.endereco}
          onChange={(e) => mudar("endereco")(e.target.value)}
        />
        <Campo
          rotulo="Capacidade em pessoas (opcional)"
          type="number"
          inputMode="numeric"
          min={0}
          value={v.capacidade}
          onChange={(e) => mudar("capacidade")(e.target.value)}
        />
        <Segmentado
          rotulo="O abrigo está"
          opcoes={[
            { valor: "sim", rotulo: "Aberto" },
            { valor: "nao", rotulo: "Fechado" },
          ]}
          valor={v.aberto}
          aoMudar={mudar("aberto")}
        />
        <AreaTexto
          privacidade
          rotulo="Observação (opcional)"
          rows={2}
          value={v.observacao}
          onChange={(e) => mudar("observacao")(e.target.value)}
        />
        {erro && (
          <p className={estilos.erro} role="alert">
            {erro}
          </p>
        )}
      </form>
    </Dialogo>
  );
}

function DialogoHistorico({ abrigo, aoFechar }: { abrigo: Abrigo; aoFechar: () => void }) {
  const r = useConsulta<unknown>(`/abrigos/${encodeURIComponent(String(abrigo.id))}/historico`);
  const itens = listaDe<HistoricoComMudancas>(r.data);
  return (
    <Dialogo aberto aoMudar={(a) => !a && aoFechar()} titulo={`Histórico de ${abrigo.nome}`}>
      {r.isPending && <CarregandoLista linhas={3} altura="3rem" texto="Carregando o histórico…" />}
      {r.isError && (
        <EstadoConsulta erro={r.error} oQue="o histórico do abrigo" aoTentar={() => r.refetch()} />
      )}
      {r.isSuccess && itens.length === 0 && <p>Nenhuma atualização registrada.</p>}
      {itens.length > 0 && (
        <ol className={estilos.historico}>
          {itens.map((h, k) => {
            const quando = h.atualizado_em ?? h.em;
            return (
              <li key={h.id ?? `${quando}-${k}`}>
                <b>{quando ? formatarDataHora(quando) : "sem hora"}</b>
                {(h.autor_nome ?? h.atualizado_por_nome) && (
                  <span> · {h.autor_nome ?? h.atualizado_por_nome}</span>
                )}
                <span className={estilos.mudancas}>
                  {h.aberto !== undefined && h.aberto !== null && (
                    <span>{h.aberto ? "Aberto" : "Fechado"}</span>
                  )}
                  {h.pessoas_abrigadas !== undefined && h.pessoas_abrigadas !== null && (
                    <span>Pessoas abrigadas: {h.pessoas_abrigadas}</span>
                  )}
                  {h.desabrigados !== undefined && h.desabrigados !== null && (
                    <span>Desabrigados atendidos: {h.desabrigados}</span>
                  )}
                  {frasesDeMudanca(h).map((f) => (
                    <span key={f}>{f}</span>
                  ))}
                </span>
                {h.observacao && <q>{h.observacao}</q>}
              </li>
            );
          })}
        </ol>
      )}
    </Dialogo>
  );
}
