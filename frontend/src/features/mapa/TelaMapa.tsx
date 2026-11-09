import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { CabecalhoTela } from "@/design-system/componentes/CabecalhoTela";
import { Dialogo } from "@/design-system/componentes/Dialogo";
import { Esqueleto } from "@/design-system/componentes/Esqueleto";
import {
  EstadoDados,
  LegendaFonte,
  SeloDesatualizado,
  fontesDado,
} from "@/design-system/componentes/EstadoDados";
import { FalhaCarga } from "@/design-system/componentes/Painel";
import { token, useTemaAtual } from "@/charts/tema";
import { consulta } from "@/lib/api";
import { useConsulta, useConsultaViva, ultimaAtualizacao } from "@/lib/consultas";
import { formatarHoraMinuto } from "@/lib/formatos";
import { fontesDe, juntarFontes } from "@/lib/frescor";
import { useSessao } from "@/lib/sessao";
import { MapaBairros, type Aparencia, type ColecaoFeicoes, type ModoCor } from "@/map/MapaBairros";
import type { ColecaoDistritos } from "@/map/MapaTerritorio";
import { siglaDoDistrito, nomeDoDistrito } from "@/map/paleta";
import { EstadoConsulta, MensagemPronta } from "@/features/evento/Evento";
import { listaDe, type ItemEstagio, type MensagemWhatsApp } from "@/features/evento/tipos";
import { DialogoDeclarar, DialogoEncerrar } from "@/features/situacao/Declarar";
import { ESTAGIOS } from "@/features/evento/estagios";
import { ROTULO_ESTAGIO, TOKEN_ESTAGIO } from "@/features/territorio/indicadoresMapa";
import { CoberturaNoMapa, ControleCamadas, LegendaCamadas } from "./PainelCamadas";
import { ChipsDistritos, SeletorColorir, VoltarRecife } from "./ControlesMapa";
import { PainelBairroPendente } from "./PainelBairroPendente";
import { PainelDistrito } from "./PainelDistrito";
import {
  CLASSES_PRIORIDADE,
  bairrosDoDistrito,
  classePrioridade,
  distritosPorPrioridade,
  rotulosPrioridade,
  type Colorir,
} from "./distritos";
import { useCamadas } from "./usarCamadas";
import { INDICADORES, textoPessoas, valorDe } from "./modeloCamadas";
import { FaixaOficial } from "./EstagioOficial";
import { ListaBairros, Prioritarios } from "./Listas";
import { PainelTerritorio } from "./PainelTerritorio";
import {
  contarPorEstagio,
  ehBairro,
  emVigor,
  ordenarPorGravidade,
  type ItemPrioridadeTerritorio,
} from "./tipos";
import estilos from "./Mapa.module.css";

const ROTULO_MAPA =
  "Mapa dos bairros do Recife, cada distrito sanitário em uma cor. Use as setas para mover e as teclas + e - para aproximar. " +
  "Para escolher um distrito ou bairro sem o mapa, use os botões dos distritos acima do mapa e a lista de bairros abaixo.";

const TOKENS_PRIORIDADE = ["--g-seq-2", "--g-seq-3", "--g-seq-4", "--g-seq-6", "--g-seq-7"];

/**
 * Mapa (tela principal da equipe): o mapa é o protagonista. Faixa compacta com o estágio oficial do COP, mapa dos 94
 * bairros colorido por distrito (padrão), estágio ou prioridade, e um painel em dois níveis: distrito e bairro
 * (RF-01, RF-05, RF-06, RF-07, RF-20, RF-22). A malha desenha assim que o GeoJSON chega; os dados lentos entram depois.
 */
export function TelaMapa() {
  const { pode, usuario } = useSessao();
  useTemaAtual(); // as cores do mapa vêm dos tokens: redesenha ao trocar claro/escuro
  const podeDeclarar = pode("editar");

  const camadas = useCamadas();
  const oficial = useConsultaViva<unknown>("/estagios/oficial");
  const distritos = useConsultaViva<unknown>(`/estagios${consulta({ nivel: "distrito" })}`);
  const bairros = useConsultaViva<unknown>(`/estagios${consulta({ nivel: "bairro" })}`);
  const prioridade = useConsultaViva<unknown>("/territorios/prioridade");
  const geoBairros = useConsulta<ColecaoFeicoes>("/territorios/bairros.geojson", { staleTime: 30 * 60_000 });
  const geoDistritos = useConsulta<ColecaoDistritos>("/territorios/distritos.geojson", {
    staleTime: 30 * 60_000,
  });

  const itensBairro = useMemo(() => listaDe<ItemEstagio>(bairros.data), [bairros.data]);
  const itensDistrito = useMemo(() => listaDe<ItemEstagio>(distritos.data), [distritos.data]);
  const listaPrioridade = useMemo(
    () => listaDe<ItemPrioridadeTerritorio>(prioridade.data),
    [prioridade.data],
  );
  const posicao = useMemo(
    () => new Map(listaPrioridade.map((p) => [p.territorio_id, p.posicao] as const)),
    [listaPrioridade],
  );
  const totalBairrosPrioridade = useMemo(
    () => listaPrioridade.filter((p) => p.nivel === "bairro").length,
    [listaPrioridade],
  );
  const porId = useMemo(
    () => new Map([...itensDistrito, ...itensBairro].map((i) => [i.territorio_id, i] as const)),
    [itensDistrito, itensBairro],
  );
  const itensBairroPorId = useMemo(
    () => new Map(itensBairro.map((i) => [i.territorio_id, i] as const)),
    [itensBairro],
  );
  const ordenados = useMemo(() => ordenarPorGravidade(itensBairro, posicao), [itensBairro, posicao]);
  const contagem = useMemo(() => contarPorEstagio(itensBairro), [itensBairro]);
  const ordemDistritos = useMemo(() => distritosPorPrioridade(listaPrioridade), [listaPrioridade]);

  /** Sem o arquivo de bairros (404), o mapa mostra os 8 distritos e diz isso. */
  const modoDistrito = geoBairros.isError && geoDistritos.isSuccess;
  const territorios: ColecaoFeicoes | undefined = useMemo(() => {
    if (!modoDistrito) return geoBairros.data;
    return {
      type: "FeatureCollection",
      features: (geoDistritos.data?.features ?? []).map((f) => ({
        type: "Feature",
        geometry: f.geometry,
        properties: {
          id: `ds-${f.properties.cdistscodi}`,
          nome: nomeDoDistrito(`ds-${f.properties.cdistscodi}`),
        },
      })),
    };
  }, [modoDistrito, geoBairros.data, geoDistritos.data]);
  const distritoDoBairro = useMemo(
    () =>
      new Map(
        (geoBairros.data?.features ?? []).map((f) => [f.properties.id, f.properties.distrito_id ?? null]),
      ),
    [geoBairros.data],
  );
  const nomeDoBairro = useMemo(
    () => new Map((geoBairros.data?.features ?? []).map((f) => [f.properties.id, f.properties.nome])),
    [geoBairros.data],
  );

  const secaoMapa = useRef<HTMLElement>(null);
  const [colorir, setColorir] = useState<Colorir>("distrito");
  const [distrito, setDistrito] = useState<string | null>(null);
  const [bairro, setBairro] = useState<string | null>(null);
  const [declarar, setDeclarar] = useState<ItemEstagio | null>(null);
  const [retirar, setRetirar] = useState<ItemEstagio | null>(null);
  const [mensagem, setMensagem] = useState<MensagemWhatsApp | null>(null);
  const sel = bairro ?? distrito;
  const item = sel ? porId.get(sel) : undefined;

  const voltarAoRecife = useCallback(() => {
    setDistrito(null);
    setBairro(null);
  }, []);
  /** Distrito ou bairro (de qualquer lista). O bairro leva junto o distrito dele. */
  const escolher = useCallback(
    (id: string) => {
      if (ehBairro(id)) {
        setBairro(id);
        setDistrito(distritoDoBairro.get(id) ?? porId.get(id)?.distrito_id ?? null);
      } else {
        setDistrito(id);
        setBairro(null);
      }
    },
    [distritoDoBairro, porId],
  );
  /** Clique no mapa: primeiro o distrito (aproxima); já dentro dele, o bairro. */
  const aoClicarNoMapa = useCallback(
    (id: string) => {
      if (!ehBairro(id)) return escolher(id);
      const ds = distritoDoBairro.get(id) ?? null;
      if (ds && ds !== distrito) return escolher(ds);
      escolher(id);
    },
    [distrito, distritoDoBairro, escolher],
  );
  const alternarDistrito = useCallback(
    (id: string) => (id === distrito && !bairro ? voltarAoRecife() : escolher(id)),
    [distrito, bairro, escolher, voltarAoRecife],
  );

  // no celular o painel é uma folha de baixo: leva o mapa para a parte de cima da tela, que fica à vista
  useEffect(() => {
    if (sel && typeof matchMedia === "function" && matchMedia("(max-width: 1100px)").matches)
      secaoMapa.current?.scrollIntoView?.({ block: "start", behavior: "smooth" });
  }, [distrito]); // eslint-disable-line react-hooks/exhaustive-deps

  const temDialogo = !!declarar || !!retirar;
  useEffect(() => {
    if (!sel) return;
    // Esc sobe um nível: bairro, depois distrito, depois o Recife inteiro
    const aoTeclar = (e: KeyboardEvent) => {
      if (e.key !== "Escape" || temDialogo) return;
      if (bairro) setBairro(null);
      else setDistrito(null);
    };
    document.addEventListener("keydown", aoTeclar);
    return () => document.removeEventListener("keydown", aoTeclar);
  }, [sel, bairro, temDialogo]);

  const aparencia = useCallback(
    (id: string): Aparencia => {
      const v = emVigor(porId.get(id));
      return { ordem: v.ordem, origem: v.origem };
    },
    [porId],
  );
  const valorPorBairro = useCallback(
    (id: string) => classePrioridade(posicao.get(id), totalBairrosPrioridade),
    [posicao, totalBairrosPrioridade],
  );
  const modoPopulacao = camadas.modo === "populacao";
  const porBairroPop = camadas.populacao.porBairro;
  const indicadorPop = camadas.indicador;
  const dica = useCallback(
    (id: string, nome: string) => {
      const n = nome.replace(/</g, "&lt;");
      const ds = distritoDoBairro.get(id) ?? (id.startsWith("ds-") ? id : null);
      const quem = `<strong>${n}</strong>${ds && ds !== id ? ` <small>${siglaDoDistrito(ds)}</small>` : ""}`;
      if (modoPopulacao) {
        const pop = valorDe(porBairroPop.get(id), indicadorPop);
        const rotulo = INDICADORES.find((i) => i.valor === indicadorPop)?.rotulo ?? "";
        return `${quem}<br>${rotulo}: ${textoPessoas(pop)}`;
      }
      if (colorir === "distrito") return quem;
      if (colorir === "prioridade") {
        const p = posicao.get(id);
        return `${quem}<br>${p ? `Prioridade ${p}º de ${totalBairrosPrioridade}` : "Prioridade: dados insuficientes"}`;
      }
      const v = emVigor(porId.get(id));
      const texto =
        v.ordem === null
          ? "Dados insuficientes"
          : `${ROTULO_ESTAGIO[v.ordem]} (${v.origem === "declarado" ? "declarado" : "sugerido pelo sistema"})`;
      return `${quem}<br>${texto}`;
    },
    [
      porId,
      modoPopulacao,
      porBairroPop,
      indicadorPop,
      colorir,
      posicao,
      totalBairrosPrioridade,
      distritoDoBairro,
    ],
  );

  const semBairros = bairros.isError
    ? "o servidor ainda não oferece os estágios por bairro."
    : bairros.isSuccess && itensBairro.length === 0
      ? "nenhum bairro tem estágio calculado ou declarado."
      : null;

  // "Estágio" só pinta diferente quando há estágios diferentes: senão, uma linha explica
  const estagiosPresentes = useMemo(() => new Set(itensBairro.map((i) => emVigor(i).estagio)), [itensBairro]);
  const avisoEstagio =
    colorir === "estagio" && bairros.isSuccess && itensBairro.length > 0 && estagiosPresentes.size === 1
      ? estagiosPresentes.has("sem_dados")
        ? "Dados insuficientes: nenhum bairro tem estágio, falta a previsão de chuva e de maré."
        : `Todos os bairros estão em ${ESTAGIOS[[...estagiosPresentes][0]].rotulo}. Não há diferença de estágio para mostrar; use Distritos ou Prioridade.`
      : null;

  const modoCor: ModoCor = modoPopulacao ? "populacao" : colorir === "prioridade" ? "valor" : colorir;
  const pronto =
    modoPopulacao ||
    colorir === "distrito" ||
    (colorir === "estagio" ? !bairros.isPending : !prioridade.isPending);
  const colorindoPorOutra = camadas.ligadas.populacao;

  const fontes = fontesDado(juntarFontes(bairros.data, distritos.data));
  const momento = ultimaAtualizacao(oficial, distritos, bairros, prioridade);
  const carregandoMapa = geoBairros.isPending && !modoDistrito;
  const bairrosDoDs = distrito && !modoDistrito ? bairrosDoDistrito(territorios, distrito) : [];

  return (
    <>
      <CabecalhoTela titulo="Mapa" proposito="Toque em um distrito." atualizadoEm={momento} />
      <div className={estilos.pagina}>
        <FaixaOficial
          oficial={oficial}
          contagem={contagem}
          totalBairros={itensBairro.length}
          semBairros={semBairros}
          carregandoBairros={bairros.isPending}
          podeInformar={podeDeclarar}
        />

        <div className={estilos.ferramentas}>
          <SeletorColorir valor={colorir} aoMudar={setColorir} />
          {!modoDistrito && (
            <ChipsDistritos
              ids={ordemDistritos}
              foco={distrito}
              aoEscolher={alternarDistrito}
              comCor={colorir === "distrito" && !colorindoPorOutra}
            />
          )}
        </div>
        {colorindoPorOutra && (
          <p className={estilos.avisoLinha}>
            A população está colorindo o mapa. Desligue-a em “Mais camadas” para voltar a colorir por{" "}
            {colorir === "distrito" ? "distritos" : colorir === "estagio" ? "estágio" : "prioridade"}.
          </p>
        )}
        {avisoEstagio && !colorindoPorOutra && (
          <p className={estilos.avisoLinha} role="status" data-aviso="estagio-igual">
            {avisoEstagio}
          </p>
        )}

        <div className={estilos.corpo} data-com-painel={!!sel}>
          <div className={estilos.colunaMapa}>
            <section ref={secaoMapa} className={estilos.mapa} aria-label="Mapa dos bairros do Recife">
              {carregandoMapa && (
                <div className={estilos.esqueletoMapa} aria-busy="true" role="status">
                  <Esqueleto forma="bloco" altura="100%" />
                  <span className={estilos.carregandoMapa}>Carregando o mapa…</span>
                </div>
              )}
              {geoBairros.isError && !modoDistrito && geoDistritos.isError && (
                <FalhaCarga erro={geoBairros.error} aoTentar={() => geoBairros.refetch()} />
              )}
              {territorios && (
                <MapaBairros
                  territorios={territorios}
                  contorno={modoDistrito ? null : geoDistritos.data}
                  tilesUrl={usuario?.mapa_tiles_url ?? ""}
                  rotulo={ROTULO_MAPA}
                  aparencia={aparencia}
                  dica={dica}
                  selecionado={modoDistrito ? distrito : bairro}
                  distritoEmFoco={distrito}
                  painelSobreposto={!!sel}
                  aoSelecionar={aoClicarNoMapa}
                  tokensEstagio={TOKEN_ESTAGIO}
                  valorPorBairro={valorPorBairro}
                  tokensValor={TOKENS_PRIORIDADE}
                  pronto={pronto}
                  {...camadas.propsMapa}
                  modoCor={modoCor}
                />
              )}
              {territorios && !pronto && (
                <p className={estilos.carregandoValores} role="status">
                  {colorir === "estagio" ? "Carregando os estágios…" : "Carregando as prioridades…"}
                </p>
              )}
              {sel && (
                <div className={estilos.voltarNoMapa}>
                  <VoltarRecife aoClicar={voltarAoRecife} />
                </div>
              )}
              <CoberturaNoMapa c={camadas} />
            </section>
            {modoDistrito && (
              <EstadoDados tipo="insuficiente" titulo="O mapa dos bairros ainda não está disponível.">
                Mostrando os 8 distritos, com o estágio de cada um. Os bairros continuam na lista.
              </EstadoDados>
            )}
            {colorir === "estagio" && !colorindoPorOutra && (
              <LegendaEstagios fontes={fontes} consultadoEm={bairros.dataUpdatedAt} />
            )}
            {colorir === "prioridade" && !colorindoPorOutra && (
              <LegendaPrioridade
                dados={prioridade.data}
                atualizadoEm={prioridade.dataUpdatedAt}
                total={totalBairrosPrioridade}
                carregando={prioridade.isPending}
              />
            )}
            <details className={estilos.camadasRecolhidas}>
              <summary>Mais camadas: unidades de saúde, idosos e crianças, áreas de risco</summary>
              <ControleCamadas c={camadas} rotuloBase="Cor dos bairros" semBase />
            </details>
            <LegendaCamadas c={camadas} />
            {bairros.isError && (
              <EstadoConsulta
                erro={bairros.error}
                oQue="os estágios por bairro"
                aoTentar={() => bairros.refetch()}
              />
            )}
          </div>

          <div className={estilos.colunaLateral}>
            {sel && (
              <div className={estilos.painelCaixa}>
                {distrito && !bairro && !modoDistrito && (
                  <PainelDistrito
                    id={distrito}
                    bairros={bairrosDoDs}
                    item={porId.get(distrito)}
                    itensBairro={itensBairroPorId}
                    posicaoBairro={posicao}
                    prioridade={listaPrioridade.find((p) => p.territorio_id === distrito)}
                    totalDistritos={listaPrioridade.filter((p) => p.nivel === "distrito").length || 8}
                    carregandoEstagios={bairros.isPending || distritos.isPending}
                    carregandoPrioridade={prioridade.isPending}
                    fontesPrioridade={fontesDado(fontesDe(prioridade.data))}
                    prioridadeEm={prioridade.dataUpdatedAt}
                    podeDeclarar={podeDeclarar}
                    aoDeclarar={setDeclarar}
                    aoRetirar={setRetirar}
                    aoEscolherBairro={escolher}
                    aoVoltar={voltarAoRecife}
                  />
                )}
                {(bairro || modoDistrito) && item && (
                  <PainelTerritorio
                    item={item}
                    podeDeclarar={podeDeclarar}
                    aoDeclarar={setDeclarar}
                    aoRetirar={setRetirar}
                    aoFechar={() => (bairro ? setBairro(null) : voltarAoRecife())}
                    voltarDistrito={
                      bairro && distrito
                        ? { rotulo: nomeDoDistrito(distrito), aoClicar: () => setBairro(null) }
                        : undefined
                    }
                  />
                )}
                {bairro && !item && (
                  <PainelBairroPendente
                    id={bairro}
                    nome={nomeDoBairro.get(bairro) ?? "Bairro"}
                    distritoId={distrito}
                    carregando={bairros.isPending}
                    aoVoltarDistrito={() => setBairro(null)}
                    aoFechar={() => setBairro(null)}
                  />
                )}
              </div>
            )}
            {!sel && (
              <p className={estilos.dicaClique}>
                Toque em um distrito, no mapa ou nos botões, para aproximar. Depois toque em um bairro para
                ver o estágio, os alertas e a população vulnerável.
              </p>
            )}
            <Prioritarios consulta={prioridade} selecionado={sel} aoEscolher={escolher} />
            <ListaBairros bairros={ordenados} selecionado={bairro} aoEscolher={escolher} />
          </div>
        </div>
      </div>

      {declarar && (
        <DialogoDeclarar
          territorios={[declarar]}
          aoFechar={() => setDeclarar(null)}
          aoDeclarar={(m) => {
            setDeclarar(null);
            setMensagem(m);
          }}
        />
      )}
      {retirar && <DialogoEncerrar item={retirar} aoFechar={() => setRetirar(null)} />}
      {mensagem && (
        <Dialogo aberto aoMudar={(a) => !a && setMensagem(null)} titulo="Mensagem para o território">
          <MensagemPronta mensagem={mensagem} rotulo="Texto pronto para o WhatsApp" />
        </Dialogo>
      )}
    </>
  );
}

/** Legenda da coloração por prioridade: escala de uma cor, da mais à menos prioritária (RF-22, RN-06). */
function LegendaPrioridade({
  dados,
  atualizadoEm,
  total,
  carregando,
}: {
  dados: unknown;
  atualizadoEm: number;
  total: number;
  carregando: boolean;
}) {
  useTemaAtual();
  const faixas = rotulosPrioridade(total);
  const fontesP = fontesDado(fontesDe(dados));
  return (
    <div className={estilos.legenda} role="group" aria-label="Legenda do mapa">
      {carregando ? (
        <p className={estilos.legendaNota} role="status">
          Carregando as prioridades…
        </p>
      ) : total === 0 ? (
        <EstadoDados tipo="insuficiente" titulo="Dados insuficientes.">
          Falta a fonte de ocorrências de alagamento e deslizamento para ordenar os bairros.
        </EstadoDados>
      ) : (
        <>
          <ul>
            {Array.from({ length: CLASSES_PRIORIDADE }, (_, i) => CLASSES_PRIORIDADE - 1 - i).map((c, i) => (
              <li key={c}>
                <i
                  className={estilos.cor}
                  style={{ background: token(TOKENS_PRIORIDADE[c]) }}
                  aria-hidden="true"
                />
                {i === 0 ? "Mais prioritários" : i === CLASSES_PRIORIDADE - 1 ? "Menos prioritários" : ""}
                <small>{faixas[i]}</small>
              </li>
            ))}
            <li>
              <i className={estilos.corSemDado} aria-hidden="true" />
              Dados insuficientes
            </li>
          </ul>
          <p className={estilos.legendaNota}>Prioridade não é a chance de acontecer: é onde agir primeiro.</p>
        </>
      )}
      <LegendaFonte fontes={fontesP}>
        {fontesP.length === 0 && (
          <span>
            Fonte: ocorrências registradas da Defesa Civil
            {atualizadoEm ? `, consultado às ${formatarHoraMinuto(atualizadoEm)}` : ""}.
          </span>
        )}
      </LegendaFonte>
    </div>
  );
}

function LegendaEstagios({
  fontes,
  consultadoEm,
}: {
  fontes: ReturnType<typeof fontesDado>;
  consultadoEm: number;
}) {
  useTemaAtual();
  return (
    <div className={estilos.legenda} role="group" aria-label="Legenda do mapa">
      <ul>
        {ROTULO_ESTAGIO.map((r, i) => (
          <li key={r}>
            <i className={estilos.cor} style={{ background: token(TOKEN_ESTAGIO[i]) }} aria-hidden="true" />
            {r}
          </li>
        ))}
        <li>
          <i className={estilos.corSemDado} aria-hidden="true" />
          Dados insuficientes
        </li>
      </ul>
      <ul>
        <li>
          <i className={estilos.corCheia} aria-hidden="true" />
          Cor cheia: declarado pela equipe
        </li>
        <li>
          <i className={estilos.corListrada} aria-hidden="true" />
          Listrado: sugerido pelo sistema
        </li>
        <li>
          <i className={estilos.contorno} aria-hidden="true" />
          Linha grossa: distritos
        </li>
      </ul>
      <p className={estilos.legendaNota}>Cinza tracejado não quer dizer risco baixo: falta dado.</p>
      <p className={estilos.legendaFonteTxt}>
        Fonte: estágios do ClimaSense (declaração da equipe e sugestão do sistema)
        {consultadoEm ? `, consultado às ${formatarHoraMinuto(consultadoEm)}` : ""}.
      </p>
      {fontes.some((f) => f.desatualizado === true) && (
        <p className={estilos.legendaNota} data-aviso="desatualizado">
          <SeloDesatualizado /> Alguma fonte da sugestão está vencida: confira antes de decidir.
        </p>
      )}
      {fontes.length > 0 && (
        <details className={estilos.fontesLegenda}>
          <summary>Fontes da sugestão e hora de cada uma ({fontes.length})</summary>
          <LegendaFonte fontes={fontes} />
        </details>
      )}
    </div>
  );
}
