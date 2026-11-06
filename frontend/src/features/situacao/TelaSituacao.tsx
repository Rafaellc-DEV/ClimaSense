import { useMemo, useState } from "react";
import { ArrowRight, Megaphone } from "lucide-react";
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
import { ConfiraOficial, EstadoConsulta, MensagemPronta } from "@/features/evento/Evento";
import { atualizada, listaEmFrase, nomeCurto, quandoAs, useFontesResumo } from "@/features/evento/textos";
import {
  listaDe,
  totaisDe,
  type Abrigo,
  type ItemEstagio,
  type MensagemWhatsApp,
} from "@/features/evento/tipos";
import { MapaSituacao } from "@/features/territorio/MapaSituacao";
import { CartaoDistrito, type EstadoBairros } from "./CartaoDistrito";
import { DialogoDeclarar, DialogoEncerrar, Parametros, pedeDecisao } from "./Declarar";
import { ResumoTopo } from "./ResumoTopo";
import { ordenarDistritos } from "./resumo";
import estilos from "./Situacao.module.css";

const porNome = (a: ItemEstagio, b: ItemEstagio) =>
  a.territorio_nome.localeCompare(b.territorio_nome, "pt-BR", { numeric: true });

/** Motivos que aparecem em todos os distritos: ditos uma vez, e não repetidos em cada cartão. */
export function motivosComuns(itens: ItemEstagio[]): string[] {
  if (itens.length < 2) return [];
  const [primeiro, ...resto] = itens.map((i) => i.sugerido?.motivos ?? []);
  return primeiro.filter((m) => resto.every((r) => r.includes(m)));
}

/** Falta comum quando todos os distritos estão sem dados pela mesma razão; senão `null`. */
export function faltaDeTodos(itens: ItemEstagio[]): string | null {
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
 * Situação (tela inicial): responde “onde eu preciso agir agora?”. Resumo no topo (distritos por situação, chuva e
 * maré), os distritos que pedem decisão em destaque com os bairros que passam do distrito, os demais em cartões
 * discretos, o mapa ligado aos cartões e os abrigos abertos.
 */
export function TelaSituacao() {
  const { pode } = useSessao();
  const podeDeclarar = pode("editar");
  const distritos = useConsulta<unknown>(`/estagios${consulta({ nivel: "distrito" })}`);
  const bairros = useConsulta<unknown>(`/estagios${consulta({ nivel: "bairro" })}`);
  const abrigos = useConsulta<unknown>(`/abrigos${consulta({ aberto: "true" })}`);
  const fontes = useFontesResumo();
  const avisar = useAviso();

  const itens = useMemo(() => listaDe<ItemEstagio>(distritos.data).sort(porNome), [distritos.data]);
  const itensBairro = useMemo(() => listaDe<ItemEstagio>(bairros.data).sort(porNome), [bairros.data]);
  const ordenados = useMemo(() => ordenarDistritos(itens), [itens]);
  const pedem = ordenados.filter(pedeDecisao);
  const demais = ordenados.filter((d) => !pedeDecisao(d));
  const comuns = motivosComuns(itens);
  const falta = faltaDeTodos(itens);
  const semAvisos =
    itens.length > 0 &&
    itens.every((i) => Array.isArray(i.alertas_oficiais) && i.alertas_oficiais.length === 0);

  const [declarar, setDeclarar] = useState<ItemEstagio[] | null>(null);
  const [retirar, setRetirar] = useState<ItemEstagio | null>(null);
  const [mensagem, setMensagem] = useState<MensagemWhatsApp | null>(null);
  const [selecionado, setSelecionado] = useState<string | null>(null);

  const estadoBairros: EstadoBairros = {
    carregando: bairros.isPending,
    erro: bairros.isError ? bairros.error : null,
    aoTentar: () => bairros.refetch(),
    lista: itensBairro,
  };

  /** Do mapa para o cartão: destaca, rola até ele e leva o foco para o nome. */
  function irParaCartao(id: string) {
    setSelecionado(id);
    requestAnimationFrame(() => {
      const el = document.getElementById(`distrito-${id}`);
      const reduz = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
      el?.scrollIntoView?.({ block: "center", behavior: reduz ? "auto" : "smooth" });
      el?.querySelector<HTMLElement>("[data-nome]")?.focus({ preventScroll: true });
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

  const cartao = (d: ItemEstagio, grande: boolean) => (
    <CartaoDistrito
      key={d.territorio_id}
      item={d}
      grande={grande}
      comuns={comuns}
      faltaComum={falta !== null}
      selecionado={selecionado === d.territorio_id}
      aoSelecionar={() => setSelecionado((s) => (s === d.territorio_id ? null : d.territorio_id))}
      bairros={estadoBairros}
      podeDeclarar={podeDeclarar}
      aoDeclarar={(i) => setDeclarar([i])}
      aoRetirar={setRetirar}
      aoWhatsApp={whatsapp}
    />
  );

  return (
    <>
      <CabecalhoTela
        titulo="Situação"
        proposito="Onde agir agora: a situação de cada distrito e dos bairros."
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

        {distritos.isSuccess && itens.length > 0 && <ResumoTopo itens={itens} horaFonte={horaPrevisao} />}

        <div className={estilos.corpo}>
          <section className={estilos.distritos} aria-labelledby="si-distritos">
            <h2 id="si-distritos" className={estilos.tituloSecao}>
              Distritos
            </h2>
            {distritos.isPending && (
              <CarregandoLista linhas={4} altura="7rem" texto="Carregando os distritos…" />
            )}
            {distritos.isError && (
              <EstadoConsulta
                erro={distritos.error}
                oQue="as situações"
                aoTentar={() => distritos.refetch()}
              />
            )}
            {distritos.isSuccess && itens.length === 0 && (
              <EstadoDados tipo="insuficiente" titulo="Nenhum distrito com situação calculada.">
                Isso não quer dizer risco baixo. Confira a APAC e o Cemaden e declare pelo que a equipe sabe.
              </EstadoDados>
            )}
            {falta !== null && (
              <EstadoDados tipo="insuficiente" titulo="Nenhum distrito tem dados para sugerir agora.">
                Falta {falta}. Isso não quer dizer risco baixo.
              </EstadoDados>
            )}

            {itens.length > 0 && (
              <div className={estilos.blocos}>
                {pedem.length > 0 ? (
                  <>
                    <h3 className={estilos.subtitulo} data-pede="true">
                      Pedem a sua decisão ({pedem.length})
                    </h3>
                    <div className={estilos.gradeGrande}>{pedem.map((d) => cartao(d, true))}</div>
                    {demais.length > 0 && <h3 className={estilos.subtitulo}>Demais distritos</h3>}
                  </>
                ) : (
                  falta === null && (
                    <p className={estilos.nadaPede}>
                      <b>Nenhum distrito pede decisão agora.</b> A sugestão do sistema não passa da situação
                      em vigor.{semAvisos ? " Nenhum aviso oficial ativo." : ""}
                    </p>
                  )
                )}
                {demais.length > 0 && (
                  <div className={estilos.grade}>{demais.map((d) => cartao(d, false))}</div>
                )}
                {falta === null && comuns.length > 0 && (
                  <p className={estilos.comum}>
                    <b>Vale para todos os {itens.length} distritos:</b> {comuns.join(" ")}
                  </p>
                )}
              </div>
            )}
            <details className={estilos.comoSugere}>
              <summary>Como o sistema sugere</summary>
              <Parametros />
            </details>
          </section>

          <div className={estilos.lateral}>
            <MapaSituacao distritos={itens} selecionado={selecionado} aoEscolher={irParaCartao} />
            <AbrigosAbertos r={abrigos} />
          </div>
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
