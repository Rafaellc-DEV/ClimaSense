import { useMemo, useState } from "react";
import { ArrowRight, ChevronDown, CircleOff, Megaphone, MessageCircle } from "lucide-react";
import { Link } from "react-router-dom";
import { CabecalhoTela } from "@/design-system/componentes/CabecalhoTela";
import { useAviso } from "@/design-system/componentes/Aviso";
import { Botao } from "@/design-system/componentes/Botao";
import { Dialogo } from "@/design-system/componentes/Dialogo";
import { CarregandoLista, Esqueleto } from "@/design-system/componentes/Esqueleto";
import { EstadoDados } from "@/design-system/componentes/EstadoDados";
import { FaixaMare } from "@/design-system/componentes/FaixaMare";
import { Painel } from "@/design-system/componentes/Painel";
import { consulta, enviar, ErroApi } from "@/lib/api";
import { useConsulta } from "@/lib/consultas";
import { formatarNumero } from "@/lib/formatos";
import { useSessao } from "@/lib/sessao";
import { ESTAGIOS, infoEstagio } from "@/features/evento/estagios";
import { ConfiraOficial, EstadoConsulta, MensagemPronta, SeloEstagio } from "@/features/evento/Evento";
import { atualizada, listaEmFrase, nomeCurto, quandoAs, useFontesResumo } from "@/features/evento/textos";
import {
  listaDe,
  totaisDe,
  type Abrigo,
  type ItemEstagio,
  type MensagemWhatsApp,
} from "@/features/evento/tipos";
import { MapaSituacao } from "@/features/territorio/MapaSituacao";
import { DialogoDeclarar, DialogoEncerrar, Parametros, pedeDecisao } from "./Declarar";
import estilos from "./Situacao.module.css";

const porNome = (a: ItemEstagio, b: ItemEstagio) =>
  a.territorio_nome.localeCompare(b.territorio_nome, "pt-BR", { numeric: true });

/** Motivos que aparecem em todos os distritos: ditos uma vez, acima da tabela, e não repetidos em cada linha. */
export function motivosComuns(itens: ItemEstagio[]): string[] {
  if (itens.length < 2) return [];
  const [primeiro, ...resto] = itens.map((i) => i.sugerido?.motivos ?? []);
  return primeiro.filter((m) => resto.every((r) => r.includes(m)));
}

/** Falta comum quando todos os distritos estão sem dados pela mesma razão; senão `null`. */
function faltaDeTodos(itens: ItemEstagio[]): string | null {
  if (itens.length === 0) return null;
  if (!itens.every((i) => infoEstagio(i.sugerido?.estagio) === ESTAGIOS.sem_dados)) return null;
  const faltas = new Set(itens.map((i) => (i.sugerido?.faltando ?? []).join(", ")));
  return faltas.size === 1 ? [...faltas][0] || "a previsão de chuva ou de maré" : null;
}

/** A frase do topo: o que fazer agora, em uma linha. Nunca diz “tudo seguro” (RN-01). */
export function fraseAgora(distritos: ItemEstagio[], bairros: ItemEstagio[]): string {
  const pedem = distritos.filter(pedeDecisao).map((d) => nomeCurto(d.territorio_nome));
  const bairrosPedem = bairros.filter(pedeDecisao).length;
  if (pedem.length > 0)
    return `${listaEmFrase(pedem)} ${
      pedem.length === 1 ? "pede" : "pedem"
    } a sua decisão: a sugestão está acima da situação declarada.`;
  if (bairrosPedem > 0)
    return bairrosPedem === 1
      ? "Um bairro pede a sua decisão: a sugestão está acima da situação declarada."
      : `${bairrosPedem} bairros pedem a sua decisão: a sugestão está acima da situação declarada.`;
  const falta = faltaDeTodos(distritos);
  if (falta !== null)
    return `O sistema não consegue sugerir agora: falta ${falta}. Declare pelo que a equipe sabe.`;
  const emVigor = distritos.filter((d) => infoEstagio(d.declarado?.estagio).ordem >= 1);
  if (emVigor.length > 0)
    return `Nada novo para decidir. ${listaEmFrase(
      emVigor.map((d) => `${nomeCurto(d.territorio_nome)} em ${infoEstagio(d.declarado?.estagio).rotulo}`),
    )}.`;
  return "Nada a decidir agora: nenhum distrito passou dos limites.";
}

/**
 * Situação (tela inicial): o que fazer agora, a tabela dos 8 distritos com declarada, sugerida, motivo e ação, os
 * bairros sob demanda, o mapa e os abrigos abertos. Responde à dor 1 (alerta da cidade, decisão por bairro) e à 2
 * (aviso aos distritos pelo WhatsApp).
 */
export function TelaSituacao() {
  const { pode } = useSessao();
  const podeDeclarar = pode("editar");
  const distritos = useConsulta<unknown>(`/estagios${consulta({ nivel: "distrito" })}`);
  const [abertos, setAbertos] = useState<Set<string>>(new Set());
  const bairros = useConsulta<unknown>(`/estagios${consulta({ nivel: "bairro" })}`, {
    enabled: abertos.size > 0,
  });
  const abrigos = useConsulta<unknown>(`/abrigos${consulta({ aberto: "true" })}`);
  const fontes = useFontesResumo();
  const avisar = useAviso();

  const itens = useMemo(() => listaDe<ItemEstagio>(distritos.data).sort(porNome), [distritos.data]);
  const itensBairro = useMemo(() => listaDe<ItemEstagio>(bairros.data).sort(porNome), [bairros.data]);
  const comuns = motivosComuns(itens);
  const falta = faltaDeTodos(itens);

  const [declarar, setDeclarar] = useState<ItemEstagio[] | null>(null);
  const [retirar, setRetirar] = useState<ItemEstagio | null>(null);
  const [mensagem, setMensagem] = useState<MensagemWhatsApp | null>(null);

  function alternar(id: string, abrir?: boolean) {
    setAbertos((s) => {
      const n = new Set(s);
      if (abrir ?? !n.has(id)) n.add(id);
      else n.delete(id);
      return n;
    });
  }

  async function whatsapp(i: ItemEstagio) {
    const corpo = { territorio_ids: [i.territorio_id], estagio: i.declarado?.estagio ?? i.sugerido?.estagio };
    try {
      setMensagem({ ...(await enviar<MensagemWhatsApp>("/estagios/mensagem", corpo)), uso: corpo });
    } catch (x) {
      avisar({
        titulo: "A mensagem para o WhatsApp não foi gerada.",
        texto: x instanceof ErroApi ? x.message : undefined,
        tipo: "erro",
      });
    }
  }

  const calculo = itens
    .map((i) => i.sugerido?.calculado_em)
    .filter((x): x is string => !!x)
    .sort()
    .pop();
  const horaPrevisao = fontes.hora("open-meteo-previsao");

  return (
    <>
      <CabecalhoTela
        titulo="Situação"
        proposito="Em que situação está cada distrito e o que pede a sua decisão."
        acoes={
          podeDeclarar &&
          itens.length > 0 && (
            <Botao variante="secundario" icone={<Megaphone />} onClick={() => setDeclarar(itens)}>
              Declarar para todos
            </Botao>
          )
        }
      />
      <div className={estilos.pagina}>
        <FaixaMare titulo="O que fazer agora" id="si-agora">
          {distritos.isPending && (
            <div role="status" aria-busy="true" className={estilos.esqueletoAzul}>
              <span className="so-leitor">Carregando a situação…</span>
              <Esqueleto largura="min(34rem, 90%)" altura="2.5rem" forma="bloco" />
            </div>
          )}
          {distritos.isSuccess && itens.length > 0 && (
            <p className={estilos.frase}>{fraseAgora(itens, itensBairro)}</p>
          )}
          {distritos.isSuccess && itens.length === 0 && (
            <p className={estilos.frase}>Nenhuma situação calculada ainda. Declare pelo que a equipe sabe.</p>
          )}
          {distritos.isError && (
            <p className={estilos.frase}>
              Não foi possível ver a situação agora. Confira a APAC e o Cemaden.
            </p>
          )}
          <ConfiraOficial sobreMare />
        </FaixaMare>

        <Painel id="si-distritos" titulo="Situação por distrito">
          {distritos.isPending && (
            <CarregandoLista linhas={4} altura="3.5rem" texto="Carregando os distritos…" />
          )}
          {distritos.isError && (
            <EstadoConsulta erro={distritos.error} oQue="as situações" aoTentar={() => distritos.refetch()} />
          )}
          {falta !== null && (
            <EstadoDados tipo="insuficiente" titulo="Nenhum distrito tem dados para sugerir agora.">
              Falta {falta}. Isso não quer dizer risco baixo.
            </EstadoDados>
          )}
          {falta === null && comuns.length > 0 && (
            <p className={estilos.comum}>
              <b>Motivo igual para os {itens.length} distritos:</b> {comuns.join(" ")}
            </p>
          )}
          {itens.length > 0 && (
            <table className={estilos.tabela}>
              <caption className="so-leitor">Situação declarada e sugerida em cada distrito</caption>
              <thead>
                <tr>
                  <th scope="col">Distrito</th>
                  <th scope="col">Declarada</th>
                  <th scope="col">Sugerida</th>
                  <th scope="col">Motivo</th>
                  <th scope="col">
                    <span className="so-leitor">Ações</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {itens.map((d) => {
                  const aberto = abertos.has(d.territorio_id);
                  const filhos = itensBairro.filter((b) => b.distrito_id === d.territorio_id);
                  return (
                    <LinhaDistrito
                      key={d.territorio_id}
                      item={d}
                      comuns={comuns}
                      faltaComum={falta !== null}
                      aberto={aberto}
                      aoAlternar={() => alternar(d.territorio_id)}
                      podeDeclarar={podeDeclarar}
                      aoDeclarar={(i) => setDeclarar([i])}
                      aoRetirar={setRetirar}
                      aoWhatsApp={whatsapp}
                      bairros={
                        bairros.isPending ? (
                          <CarregandoLista linhas={2} altura="2.5rem" texto="Carregando os bairros…" />
                        ) : bairros.isError ? (
                          <EstadoConsulta
                            erro={bairros.error}
                            oQue="as situações por bairro"
                            aoTentar={() => bairros.refetch()}
                          />
                        ) : (
                          <ListaBairros
                            distrito={d}
                            itens={filhos}
                            podeDeclarar={podeDeclarar}
                            aoDeclarar={(i) => setDeclarar([i])}
                          />
                        )
                      }
                    />
                  );
                })}
              </tbody>
            </table>
          )}
          <details className={estilos.comoSugere}>
            <summary>Como o sistema sugere</summary>
            <Parametros />
          </details>
        </Painel>

        <div className={estilos.duas}>
          <MapaSituacao
            distritos={itens}
            selecionado={null}
            aoEscolher={(id) => {
              alternar(id, true);
              requestAnimationFrame(
                () => document.getElementById(`linha-${id}`)?.scrollIntoView({ block: "center" }),
              );
            }}
          />
          <AbrigosAbertos r={abrigos} />
        </div>

        <p className={estilos.rodape}>
          {calculo ? `Sugestão calculada ${quandoAs(calculo)}. ` : ""}
          Previsão de chuva e maré: Open-Meteo, {atualizada(horaPrevisao)}.
        </p>
      </div>

      {declarar && (
        <DialogoDeclarar
          territorios={declarar}
          aoFechar={() => setDeclarar(null)}
          aoDeclarar={(m) => {
            setDeclarar(null);
            setMensagem(m);
          }}
        />
      )}
      {retirar && <DialogoEncerrar item={retirar} aoFechar={() => setRetirar(null)} />}
      {mensagem && (
        <Dialogo aberto aoMudar={(a) => !a && setMensagem(null)} titulo="Mensagem para os distritos">
          <MensagemPronta mensagem={mensagem} rotulo="Texto pronto para o WhatsApp" />
        </Dialogo>
      )}
    </>
  );
}

/* ------------------------------------------------------------------ uma linha da tabela */
function motivoDaLinha(i: ItemEstagio, comuns: string[], faltaComum: boolean): string | null {
  if (infoEstagio(i.sugerido?.estagio) === ESTAGIOS.sem_dados)
    return faltaComum ? null : `Falta ${(i.sugerido?.faltando ?? []).join(", ") || "insumo para sugerir"}.`;
  const proprios = (i.sugerido?.motivos ?? []).filter((m) => !comuns.includes(m));
  return proprios.length ? proprios.join(" ") : null;
}

function LinhaDistrito({
  item: d,
  comuns,
  faltaComum,
  aberto,
  aoAlternar,
  podeDeclarar,
  aoDeclarar,
  aoRetirar,
  aoWhatsApp,
  bairros,
}: {
  item: ItemEstagio;
  comuns: string[];
  faltaComum: boolean;
  aberto: boolean;
  aoAlternar: () => void;
  podeDeclarar: boolean;
  aoDeclarar: (i: ItemEstagio) => void;
  aoRetirar: (i: ItemEstagio) => void;
  aoWhatsApp: (i: ItemEstagio) => void;
  bairros: React.ReactNode;
}) {
  const nome = nomeCurto(d.territorio_nome);
  const pede = pedeDecisao(d);
  const motivo = motivoDaLinha(d, comuns, faltaComum);
  const idBairros = `bairros-${d.territorio_id}`;
  return (
    <>
      <tr id={`linha-${d.territorio_id}`} data-pede={pede} className={estilos.linha}>
        <th scope="row" className={estilos.celulaNome}>
          <span className={estilos.nome} title={d.territorio_nome}>
            {nome}
          </span>
          <button
            type="button"
            className={estilos.expandir}
            aria-expanded={aberto}
            aria-controls={idBairros}
            onClick={aoAlternar}
          >
            <ChevronDown aria-hidden="true" size={18} />
            Bairros<span className="so-leitor"> de {d.territorio_nome}</span>
          </button>
        </th>
        <td data-rotulo="Declarada">
          {d.declarado ? (
            <span className={estilos.celulaSelo}>
              <SeloEstagio estagio={d.declarado.estagio} pequena />
              <small>
                {d.declarado.autor_nome}, {quandoAs(d.declarado.declarado_em)}
              </small>
            </span>
          ) : (
            <span className={estilos.apagado}>sem declaração</span>
          )}
        </td>
        <td data-rotulo="Sugerida">
          <span className={estilos.celulaSelo}>
            <SeloEstagio estagio={d.sugerido?.estagio} pequena />
            {pede && <small className={estilos.acima}>acima da declarada</small>}
          </span>
        </td>
        <td data-rotulo="Motivo" className={estilos.motivo} data-vazio={motivo === null}>
          {motivo ?? <span className={estilos.apagado}>igual ao de cima</span>}
        </td>
        <td className={estilos.acoes}>
          {podeDeclarar && (
            <Botao variante={pede ? "principal" : "secundario"} onClick={() => aoDeclarar(d)}>
              Declarar<span className="so-leitor"> situação de {d.territorio_nome}</span>
            </Botao>
          )}
          {podeDeclarar && d.declarado && !d.declarado.herdado && (
            <Botao variante="discreto" icone={<CircleOff />} onClick={() => aoRetirar(d)}>
              Retirar<span className="so-leitor"> declaração de {d.territorio_nome}</span>
            </Botao>
          )}
          <Botao variante="discreto" icone={<MessageCircle />} onClick={() => aoWhatsApp(d)}>
            WhatsApp<span className="so-leitor"> para {d.territorio_nome}</span>
          </Botao>
        </td>
      </tr>
      {aberto && (
        <tr className={estilos.linhaBairros}>
          <td colSpan={5} id={idBairros}>
            {bairros}
          </td>
        </tr>
      )}
    </>
  );
}

/* ------------------------------------------------------------------ bairros de um distrito */
function ListaBairros({
  distrito,
  itens,
  podeDeclarar,
  aoDeclarar,
}: {
  distrito: ItemEstagio;
  itens: ItemEstagio[];
  podeDeclarar: boolean;
  aoDeclarar: (i: ItemEstagio) => void;
}) {
  if (itens.length === 0)
    return <EstadoDados tipo="insuficiente" titulo="Nenhum bairro com situação calculada." />;
  const ordenados = [...itens].sort(
    (a, b) =>
      Number(pedeDecisao(b)) - Number(pedeDecisao(a)) ||
      infoEstagio(b.sugerido?.estagio).ordem - infoEstagio(a.sugerido?.estagio).ordem ||
      porNome(a, b),
  );
  return (
    <div className={estilos.bairros}>
      <p className={estilos.detalhe}>
        A previsão é do distrito: os {itens.length} bairros do {nomeCurto(distrito.territorio_nome)} usam a
        mesma chuva. O que muda é o histórico de alagamento de cada um.
      </p>
      <ul className={estilos.gradeBairros} aria-label={`Bairros de ${distrito.territorio_nome}`}>
        {ordenados.map((b) => {
          const ocorr = b.sugerido?.insumos?.ocorrencias_historicas;
          return (
            <li key={b.territorio_id} data-pede={pedeDecisao(b)}>
              <span className={estilos.nomeBairro}>{b.territorio_nome}</span>
              <span className={estilos.celulaSelo}>
                <SeloEstagio estagio={b.declarado?.estagio ?? b.sugerido?.estagio} pequena />
                <small>
                  {b.declarado ? (b.declarado.herdado ? "do distrito" : "declarada") : "sugerida"}
                </small>
              </span>
              {typeof ocorr === "number" && ocorr > 0 && (
                <small className={estilos.apagado}>
                  {ocorr === 1
                    ? "1 alagamento registrado"
                    : `${formatarNumero(ocorr)} alagamentos registrados`}
                </small>
              )}
              {podeDeclarar && (
                <Botao variante="discreto" onClick={() => aoDeclarar(b)}>
                  Declarar<span className="so-leitor"> situação de {b.territorio_nome}</span>
                </Botao>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

/* ------------------------------------------------------------------ abrigos abertos */
function AbrigosAbertos({ r }: { r: ReturnType<typeof useConsulta<unknown>> }) {
  const lista = listaDe<Abrigo>(r.data).filter((a) => a.aberto);
  const totais = totaisDe(r.data);
  const semInformacao = totais?.abrigos_cadastrados === 0;
  const n = totais?.abrigos_abertos ?? lista.length;
  return (
    <Painel
      id="si-abrigos"
      titulo="Abrigos abertos agora"
      acoes={
        <Link to="/app/abrigos" className={estilos.verTodos}>
          Ver abrigos <ArrowRight aria-hidden="true" size={18} />
        </Link>
      }
    >
      {r.isPending && <CarregandoLista linhas={2} altura="2.5rem" texto="Carregando os abrigos…" />}
      {r.isError && <EstadoConsulta erro={r.error} oQue="os abrigos" aoTentar={() => r.refetch()} />}
      {r.isSuccess &&
        (semInformacao ? (
          <EstadoDados tipo="insuficiente" titulo="Sem informação de abrigos." />
        ) : (
          <>
            <p className={estilos.numeroAbrigos}>
              <b>{formatarNumero(n)}</b> {n === 1 ? "aberto" : "abertos"}
            </p>
            {lista.length > 0 && (
              <ul className={estilos.listaAbrigos}>
                {lista.slice(0, 5).map((a) => (
                  <li key={a.id}>
                    {a.nome}
                    {a.bairro_nome && <small>, {a.bairro_nome}</small>}
                  </li>
                ))}
                {lista.length > 5 && <li className={estilos.apagado}>e mais {lista.length - 5}</li>}
              </ul>
            )}
            <p className={estilos.detalhe}>
              Feed do COP e registro da equipe, {atualizada(totais?.atualizado_em, "o")}.
            </p>
          </>
        ))}
    </Painel>
  );
}
