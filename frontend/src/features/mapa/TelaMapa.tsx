import { useCallback, useEffect, useMemo, useState } from "react";
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
import { juntarFontes } from "@/lib/frescor";
import { useSessao } from "@/lib/sessao";
import { MapaBairros, type Aparencia, type ColecaoFeicoes } from "@/map/MapaBairros";
import type { ColecaoDistritos } from "@/map/MapaTerritorio";
import { distritoPorExtenso } from "@/textos/glossario";
import { EstadoConsulta, MensagemPronta } from "@/features/evento/Evento";
import { listaDe, type Abrigo, type ItemEstagio, type MensagemWhatsApp } from "@/features/evento/tipos";
import { DialogoDeclarar, DialogoEncerrar } from "@/features/situacao/Declarar";
import { ROTULO_ESTAGIO, TOKEN_ESTAGIO } from "@/features/territorio/indicadoresMapa";
import { CoberturaNoMapa, ControleCamadas, LegendaCamadas } from "./PainelCamadas";
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
  "Mapa dos bairros do Recife coloridos pelo estágio. Use as setas para mover e as teclas + e - para aproximar. " +
  "Para escolher um bairro sem o mapa, use a lista de bairros logo abaixo.";

/**
 * Mapa (tela principal da equipe): estágio oficial do COP no topo, os 94 bairros coloridos pelo estágio em vigor,
 * painel do território escolhido e a lista dos territórios mais vulneráveis (RF-01, RF-05, RF-06, RF-07, RF-22).
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
  const abrigos = useConsultaViva<unknown>("/abrigos");
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
  const porId = useMemo(
    () => new Map([...itensDistrito, ...itensBairro].map((i) => [i.territorio_id, i] as const)),
    [itensDistrito, itensBairro],
  );
  const ordenados = useMemo(() => ordenarPorGravidade(itensBairro, posicao), [itensBairro, posicao]);
  const contagem = useMemo(() => contarPorEstagio(itensBairro), [itensBairro]);

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
          nome: distritoPorExtenso(`ds-${f.properties.cdistscodi}`),
        },
      })),
    };
  }, [modoDistrito, geoBairros.data, geoDistritos.data]);

  const [sel, setSel] = useState<string | null>(null);
  const [declarar, setDeclarar] = useState<ItemEstagio | null>(null);
  const [retirar, setRetirar] = useState<ItemEstagio | null>(null);
  const [mensagem, setMensagem] = useState<MensagemWhatsApp | null>(null);
  const item = sel ? porId.get(sel) : undefined;

  useEffect(() => {
    if (!sel) return;
    const aoTeclar = (e: KeyboardEvent) => e.key === "Escape" && !declarar && !retirar && setSel(null);
    document.addEventListener("keydown", aoTeclar);
    return () => document.removeEventListener("keydown", aoTeclar);
  }, [sel, declarar, retirar]);

  const aparencia = useCallback(
    (id: string): Aparencia => {
      const v = emVigor(porId.get(id));
      return { ordem: v.ordem, origem: v.origem };
    },
    [porId],
  );
  const modoPopulacao = camadas.modo === "populacao";
  const porBairroPop = camadas.populacao.porBairro;
  const indicadorPop = camadas.indicador;
  const dica = useCallback(
    (id: string, nome: string) => {
      if (modoPopulacao) {
        const pop = valorDe(porBairroPop.get(id), indicadorPop);
        const rotulo = INDICADORES.find((i) => i.valor === indicadorPop)?.rotulo ?? "";
        return `<strong>${nome.replace(/</g, "&lt;")}</strong><br>${rotulo}: ${textoPessoas(pop)}`;
      }
      const v = emVigor(porId.get(id));
      const texto =
        v.ordem === null
          ? "Dados insuficientes"
          : `${ROTULO_ESTAGIO[v.ordem]} (${v.origem === "declarado" ? "declarado" : "sugerido pelo sistema"})`;
      return `<strong>${nome.replace(/</g, "&lt;")}</strong><br>${texto}`;
    },
    [porId, modoPopulacao, porBairroPop, indicadorPop],
  );

  const enquadrar = useMemo(() => {
    if (!sel || ehBairro(sel) || modoDistrito) return null;
    return itensBairro.filter((b) => b.distrito_id === sel).map((b) => b.territorio_id);
  }, [sel, itensBairro, modoDistrito]);

  const semBairros = bairros.isError
    ? "o servidor ainda não oferece os estágios por bairro."
    : bairros.isSuccess && itensBairro.length === 0
      ? "nenhum bairro tem estágio calculado ou declarado."
      : null;

  const fontes = fontesDado(juntarFontes(bairros.data, distritos.data));
  const momento = ultimaAtualizacao(oficial, distritos, bairros, prioridade, abrigos);

  return (
    <>
      <CabecalhoTela
        titulo="Mapa"
        proposito="Onde agir primeiro: escolha um bairro para ver o estágio, os alertas oficiais, a população vulnerável e os abrigos."
        atualizadoEm={momento}
      />
      <div className={estilos.pagina}>
        <FaixaOficial
          oficial={oficial}
          contagem={contagem}
          totalBairros={itensBairro.length}
          semBairros={semBairros}
          carregandoBairros={bairros.isPending}
          podeInformar={podeDeclarar}
        />

        <div className={estilos.corpo} data-com-painel={!!item}>
          <div className={estilos.colunaMapa}>
            <section className={estilos.mapa} aria-label="Mapa dos bairros por estágio">
              {geoBairros.isPending && !modoDistrito && (
                <div className={estilos.esqueletoMapa} aria-busy="true">
                  <Esqueleto forma="bloco" altura="100%" />
                  <span className="so-leitor" role="status">
                    Carregando o mapa…
                  </span>
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
                  selecionado={sel && (modoDistrito ? !ehBairro(sel) : ehBairro(sel)) ? sel : null}
                  enquadrar={enquadrar}
                  aoSelecionar={setSel}
                  tokensEstagio={TOKEN_ESTAGIO}
                  {...camadas.propsMapa}
                />
              )}
              <CoberturaNoMapa c={camadas} />
            </section>
            {modoDistrito && (
              <EstadoDados tipo="insuficiente" titulo="O mapa dos bairros ainda não está disponível.">
                Mostrando os 8 distritos, com o estágio de cada um. Os bairros continuam na lista.
              </EstadoDados>
            )}
            <ControleCamadas c={camadas} rotuloBase="Estágio dos bairros" />
            {camadas.modo === "estagio" && (
              <LegendaEstagios fontes={fontes} consultadoEm={bairros.dataUpdatedAt} />
            )}
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
            {item && (
              <div className={estilos.painelCaixa}>
                <PainelTerritorio
                  item={item}
                  abrigos={{
                    lista: listaDe<Abrigo>(abrigos.data),
                    carregando: abrigos.isPending,
                    erro: abrigos.error,
                    aoTentar: () => void abrigos.refetch(),
                  }}
                  podeDeclarar={podeDeclarar}
                  aoDeclarar={setDeclarar}
                  aoRetirar={setRetirar}
                  aoFechar={() => setSel(null)}
                />
              </div>
            )}
            {!item && (
              <p className={estilos.dicaClique}>
                Toque em um bairro no mapa, ou escolha na lista, para ver o estágio, os alertas e os abrigos.
              </p>
            )}
            <Prioritarios consulta={prioridade} selecionado={sel} aoEscolher={setSel} />
            <ListaBairros bairros={ordenados} selecionado={sel} aoEscolher={setSel} />
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
