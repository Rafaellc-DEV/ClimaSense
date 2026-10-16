import { useEffect, useMemo, useRef, useState } from "react";
import { Download, FileDown, Info, Maximize, RotateCcw, Search } from "lucide-react";
import { useLocation, useNavigate } from "react-router-dom";
import { CabecalhoTela } from "@/app/AppShell";
import { useTerritorios } from "@/app/FiltroFrase";
import { Botao, classesBotao } from "@/design-system/componentes/Botao";
import { Dialogo } from "@/design-system/componentes/Dialogo";
import { EstadoDados, LegendaFonte } from "@/design-system/componentes/EstadoDados";
import { Carregando, FalhaCarga } from "@/design-system/componentes/Painel";
import { Selecao } from "@/design-system/componentes/Selecao";
import { SeloNivel } from "@/design-system/componentes/SeloNivel";
import type { ChaveNivel } from "@/design-system/niveis";
import type { Esquemas } from "@/lib/api";
import { useConsulta } from "@/lib/consultas";
import { baixarCsv } from "@/lib/csv";
import { formatarNumero } from "@/lib/formatos";
import { useRecorte } from "@/lib/recorte";
import { useSessao } from "@/lib/sessao";
import { classIndex, makeScale, matches } from "@/map/model";
import {
  MapaTerritorio,
  type ColecaoDistritos,
  type ControleMapa,
  type FeatureDistrito,
} from "@/map/MapaTerritorio";
import { distritoPorExtenso, ROMANOS } from "@/textos/glossario";
import estilos from "./TelaMapa.module.css";

type Indicador = "quantidade_bairros" | "area_km2" | "vacinacao" | "prioridade" | "ocorrencias";

const INDICADORES: Record<
  Indicador,
  { rotulo: string; unidade: string; casas: number; ajuda: string; interpretar: string; fonte: string }
> = {
  quantidade_bairros: {
    rotulo: "Quantidade de bairros",
    unidade: "bairros",
    casas: 0,
    ajuda: "Quanto mais escuro, maior o número de bairros.",
    interpretar:
      "As cores mostram quantos bairros cada distrito tem. Não representam população, risco nem a qualidade dos serviços de saúde.",
    fonte: "territorio-oficial",
  },
  area_km2: {
    rotulo: "Área do distrito (km²)",
    unidade: "km²",
    casas: 1,
    ajuda: "Quanto mais escuro, maior a área do distrito.",
    interpretar:
      "As cores mostram a área geográfica, calculada a partir dos limites oficiais. A área não representa população nem demanda por serviços.",
    fonte: "territorio-oficial",
  },
  vacinacao: {
    rotulo: "Vacinação COVID-19 (doses, amostra)",
    unidade: "doses",
    casas: 0,
    ajuda: "Quanto mais escuro, mais doses na amostra carregada, no período escolhido.",
    interpretar:
      "As cores mostram doses registradas na amostra carregada da base, não o total de vacinados. O dado existe só por distrito: não diz nada sobre bairros.",
    fonte: "vacinacao",
  },
  prioridade: {
    rotulo: "Prioridade do cenário de 72 h (experimental)",
    unidade: "",
    casas: 0,
    ajuda: "A cor é o nível indicado pela regra experimental para as próximas 72 horas.",
    interpretar:
      "Prioridade é uma indicação para a equipe avaliar, nunca a chance de alagar. A regra é experimental e não foi validada.",
    fonte: "open-meteo-previsao",
  },
  ocorrencias: {
    rotulo: "Ocorrências de alagamento",
    unidade: "ocorrências",
    casas: 0,
    ajuda: "Contagem de ocorrências registradas pela Defesa Civil, quando a fonte estiver integrada.",
    interpretar: "Ocorrências registradas não são confirmadas por padrão e dependem de quem registrou.",
    fonte: "recife-alagamento",
  },
};
const NIVEL_PRIORIDADE: ChaveNivel[] = ["sem", "atencao", "alerta", "critico"];
const ROTULO_PRIORIDADE = ["Sem indicação", "Atenção", "Alerta", "Situação crítica"];
const COR_PRIORIDADE = ["#0b6f6c", "#c98a00", "#d2581f", "#a41f15"];

type RespostaIndicador = Esquemas["RespostaDados_list_ValorDistrito__"];

/** Mapa do território (design §9.5): preserva tudo do mapa da Aula 07 (RF-07.1–07.14), agora ligado à API. */
export function TelaMapa() {
  const { usuario } = useSessao();
  const { recorte, mudar } = useRecorte();
  const navegar = useNavigate();
  const local = useLocation();
  const territorios = useTerritorios();
  const geo = useConsulta<ColecaoDistritos>("/territorios/distritos.geojson", { staleTime: 30 * 60_000 });
  const agua = useConsulta<GeoJSON.FeatureCollection>("/territorios/hidrografia.geojson", {
    staleTime: 30 * 60_000,
  });
  const [indicador, setIndicador] = useState<Indicador>("quantidade_bairros");
  const doApi = indicador === "vacinacao" || indicador === "prioridade" || indicador === "ocorrencias";
  const valoresApi = useConsulta<RespostaIndicador>(
    doApi
      ? `/territorios/indicadores?indicador=${indicador}&inicio=${recorte.inicio}&fim=${recorte.fim}`
      : null,
  );
  const [busca, setBusca] = useState("");
  const [mostrarDistritos, setMostrarDistritos] = useState(true);
  const [mostrarFaixas, setMostrarFaixas] = useState(true);
  const [opacidade, setOpacidade] = useState(72);
  const [sobre, setSobre] = useState(false);
  const controle = useRef<ControleMapa>(null);

  useEffect(() => {
    document.title = "Mapa do território | ClimaSense";
  }, []);

  // o recorte global decide o distrito selecionado (um bairro seleciona o distrito dele: RN-07)
  const selecionado = useMemo(() => {
    const t = recorte.territorio;
    if (t.startsWith("ds-")) return Number(t.slice(3));
    if (t.startsWith("bairro-")) {
      const pai = territorios.data?.find((x) => x.id === t)?.pai_id;
      return pai ? Number(pai.slice(3)) : null;
    }
    return null;
  }, [recorte.territorio, territorios.data]);
  const bairroDoRecorte = recorte.territorio.startsWith("bairro-")
    ? territorios.data?.find((x) => x.id === recorte.territorio)?.nome_exibicao
    : undefined;

  const features = useMemo(
    () => [...(geo.data?.features ?? [])].sort((a, b) => a.properties.cdistscodi - b.properties.cdistscodi),
    [geo.data],
  );
  const valorDe = useMemo(() => {
    const porDs = new Map(
      (valoresApi.data?.dados ?? []).map((v) => [Number(v.territorio_id.slice(3)), v.valor]),
    );
    return (f: FeatureDistrito): number | null =>
      doApi ? porDs.get(f.properties.cdistscodi) ?? null : f.properties[indicador as "area_km2"];
  }, [valoresApi.data, doApi, indicador]);

  // escala sobre TODOS os distritos: busca e filtro não mudam os limites (RF-07.3)
  const escala = useMemo(() => makeScale(features.map(valorDe)), [features, valorDe]);
  const visiveis = useMemo(() => features.filter((f) => matches(f.properties, busca)), [features, busca]);
  const codigosVisiveis = useMemo(() => new Set(visiveis.map((f) => f.properties.cdistscodi)), [visiveis]);
  const info = INDICADORES[indicador];

  const cor = (f: FeatureDistrito): string => {
    const v = valorDe(f);
    if (v === null || v === undefined) return "hachura";
    if (indicador === "prioridade") return COR_PRIORIDADE[v] ?? "hachura";
    const i = classIndex(v, escala);
    return i < 0 ? "hachura" : escala.bins[i].color;
  };
  const textoValor = (f: FeatureDistrito) => {
    const v = valorDe(f);
    if (v === null || v === undefined) return "sem dado";
    if (indicador === "prioridade") return ROTULO_PRIORIDADE[v];
    return `${formatarNumero(v, info.casas)}${info.unidade ? ` ${info.unidade}` : ""}`;
  };
  const dica = (f: FeatureDistrito) =>
    `<strong>${distritoPorExtenso(`ds-${f.properties.cdistscodi}`)}</strong><br>${textoValor(
      f,
    )}<br><small>Clique para ver os bairros</small>`;

  const selecionar = (codigo: number) => {
    if (!mostrarDistritos) setMostrarDistritos(true);
    mudar({ territorio: `ds-${codigo}` });
  };
  const limpar = () => {
    setBusca("");
    setMostrarDistritos(true);
    mudar({ territorio: "recife" });
    requestAnimationFrame(() => controle.current?.enquadrar(features.map((f) => f.properties.cdistscodi)));
  };
  const escolhido = features.find((f) => f.properties.cdistscodi === selecionado);
  const fonteMeta = doApi ? valoresApi.data?.meta : undefined;

  function exportar() {
    baixarCsv("distritos-recife.csv", [
      ["codigo", "distrito", "quantidade_bairros", "area_km2", indicador, "bairros"],
      ...visiveis.map((f) => {
        const p = f.properties;
        return [
          p.cdistscodi,
          p.nome_distrito,
          p.quantidade_bairros,
          p.area_km2,
          valorDe(f),
          p.bairros.join(" | "),
        ];
      }),
    ]);
  }

  function registrarAvaliacao() {
    if (!escolhido) return;
    const ds = `ds-${escolhido.properties.cdistscodi}`;
    navegar(`/app/avaliacoes/nova${local.search}`, {
      state: {
        territorio_id: ds,
        evidencias: [
          {
            tipo: "mapa",
            descricao: `Mapa: ${info.rotulo} no ${distritoPorExtenso(ds)}`,
            fonte_id: info.fonte,
            capturada_em: new Date().toISOString(),
            valor: textoValor(escolhido),
            endereco: `/app/mapa${local.search}`,
          },
        ],
      },
    });
  }

  if (geo.isPending) return <Carregando texto="Carregando o mapa do território…" />;
  if (geo.isError)
    return (
      <>
        <CabecalhoTela
          titulo="Mapa do território"
          proposito="Distritos, bairros e faixas hídricas do Recife."
        />
        <FalhaCarga erro={geo.error} aoTentar={() => geo.refetch()} />
      </>
    );

  const totalBairros = features.reduce((s, f) => s + f.properties.quantidade_bairros, 0);
  return (
    <>
      <CabecalhoTela
        titulo="Mapa do território"
        proposito={`Os ${features.length} distritos sanitários, ${totalBairros} bairros e ${
          agua.data?.features.length ?? 81
        } faixas hídricas do Recife, coloridos pelo indicador que você escolher.`}
        acoes={
          <>
            <Botao variante="secundario" onClick={exportar} disabled={!visiveis.length} icone={<Download />}>
              Exportar CSV
            </Botao>
            <a href="/api/v1/territorios/mapa-portatil" className={classesBotao("secundario")} download>
              <FileDown aria-hidden="true" /> Baixar mapa offline
            </a>
          </>
        }
      />
      <div className={estilos.area}>
        {/* ------------------------------------------------ busca e camadas */}
        <aside className={estilos.controles} aria-label="Busca e camadas">
          <div className={estilos.campoBusca}>
            <label htmlFor="busca-mapa">Distrito ou bairro</label>
            <div>
              <Search aria-hidden="true" size={20} />
              <input
                id="busca-mapa"
                type="search"
                value={busca}
                placeholder="Ex.: Boa Viagem, DS II"
                autoComplete="off"
                onChange={(e) => setBusca(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && visiveis.length === 1)
                    selecionar(visiveis[0].properties.cdistscodi);
                }}
              />
            </div>
          </div>
          <Selecao
            rotulo="Colorir por"
            valor={indicador}
            aoMudar={(v) => setIndicador(v as Indicador)}
            opcoes={(Object.keys(INDICADORES) as Indicador[]).map((k) => ({
              valor: k,
              rotulo: INDICADORES[k].rotulo,
            }))}
            ajuda={info.ajuda}
          />
          <p className={estilos.nota}>
            Os vínculos dos Distritos Sanitários VII e VIII foram conferidos com a Secretaria de Saúde.{" "}
            <button type="button" className={estilos.linkBotao} onClick={() => setSobre(true)}>
              Ver nota
            </button>
          </p>
          <fieldset className={estilos.camadas}>
            <legend>Camadas</legend>
            <label>
              <input
                type="checkbox"
                role="switch"
                checked={mostrarDistritos}
                onChange={(e) => setMostrarDistritos(e.target.checked)}
              />
              Distritos sanitários
            </label>
            <label>
              <input
                type="checkbox"
                role="switch"
                checked={mostrarFaixas}
                onChange={(e) => setMostrarFaixas(e.target.checked)}
              />
              Faixas marginais dos recursos hídricos
            </label>
          </fieldset>
          <label className={estilos.intensidade}>
            <span>
              Intensidade do preenchimento <output>{opacidade}%</output>
            </span>
            <input
              type="range"
              min={20}
              max={95}
              value={opacidade}
              onChange={(e) => setOpacidade(Number(e.target.value))}
            />
          </label>
          <div className={estilos.listaTopo}>
            <h2>Distritos</h2>
            <span role="status">
              {visiveis.length} de {features.length}
            </span>
          </div>
          <ul className={estilos.lista}>
            {visiveis.map((f) => (
              <li key={f.properties.cdistscodi}>
                <button
                  type="button"
                  aria-pressed={f.properties.cdistscodi === selecionado}
                  onClick={() => selecionar(f.properties.cdistscodi)}
                >
                  <span
                    className={estilos.amostra}
                    data-sem-dado={cor(f) === "hachura"}
                    style={{ background: cor(f) === "hachura" ? undefined : cor(f) }}
                    aria-hidden="true"
                  />
                  <span>{distritoPorExtenso(`ds-${f.properties.cdistscodi}`)}</span>
                  <small>{textoValor(f)}</small>
                </button>
              </li>
            ))}
          </ul>
          {!visiveis.length && (
            <p className={estilos.vazio}>Nenhum distrito encontrado. Tente outro nome ou limpe a busca.</p>
          )}
          <Botao variante="discreto" onClick={limpar} icone={<RotateCcw />}>
            Limpar filtros e ver todos
          </Botao>
        </aside>

        {/* ------------------------------------------------ mapa */}
        <section className={estilos.colunaMapa} aria-label="Mapa">
          <div className={estilos.barraMapa}>
            <strong>Mapa dos distritos</strong>
            <Botao variante="secundario" onClick={() => controle.current?.enquadrar()} icone={<Maximize />}>
              Enquadrar
            </Botao>
          </div>
          <div className={estilos.canvas}>
            <MapaTerritorio
              ref={controle}
              distritos={geo.data}
              hidrografia={agua.data}
              tilesUrl={usuario?.mapa_tiles_url ?? ""}
              cor={cor}
              dica={dica}
              visiveis={codigosVisiveis}
              selecionado={selecionado}
              mostrarDistritos={mostrarDistritos}
              mostrarFaixas={mostrarFaixas}
              opacidade={opacidade / 100}
              aoSelecionar={selecionar}
            />
            <div className={estilos.legenda} aria-label="Legenda do mapa">
              <h3>{info.rotulo}</h3>
              {indicador === "prioridade"
                ? ROTULO_PRIORIDADE.map((r, i) => (
                    <div key={r} className={estilos.linhaLegenda}>
                      <i style={{ background: COR_PRIORIDADE[i] }} />
                      <span>{r}</span>
                    </div>
                  ))
                : escala.bins.map((b, i) => (
                    <div key={i} className={estilos.linhaLegenda}>
                      <i style={{ background: b.color }} />
                      <span>
                        {rotuloClasse(indicador, b.low, b.high, i === escala.bins.length - 1, info.casas)}
                      </span>
                    </div>
                  ))}
              {features.some((f) => valorDe(f) === null) && (
                <div className={estilos.linhaLegenda}>
                  <i className={estilos.hachura} />
                  <span>Sem dado</span>
                </div>
              )}
              <div className={estilos.linhaLegenda}>
                <i className={estilos.agua} />
                <span>Faixas hídricas</span>
              </div>
            </div>
          </div>
          <p className={estilos.status} role="status">
            {mostrarDistritos ? `${visiveis.length} distritos visíveis` : "Camada de distritos oculta"}.
            Arraste para mover; use + e − para aproximar.
          </p>
          {fonteMeta?.dados_insuficientes && (
            <EstadoDados tipo="insuficiente" titulo="Dados insuficientes para este indicador">
              {fonteMeta.avisos.join(" ")} Os distritos aparecem com hachura, nunca como zero.
            </EstadoDados>
          )}
          <LegendaFonte
            fontes={
              fonteMeta
                ? fonteMeta.fontes.map((f) => ({ nome: f.nome, atualizadoEm: f.atualizado_em }))
                : [
                    {
                      nome: "Prefeitura do Recife, distritos sanitários, bairros e faixas hídricas (Dados Abertos)",
                    },
                  ]
            }
          >
            {fonteMeta?.amostra && (
              <span>
                {" "}
                Amostra de {formatarNumero(fonteMeta.amostra.n)} registros, não representa o total.
              </span>
            )}
          </LegendaFonte>
        </section>

        {/* ------------------------------------------------ detalhe */}
        <aside className={estilos.detalhe} aria-label="Detalhes do distrito">
          {escolhido ? (
            <>
              <h2>{distritoPorExtenso(`ds-${escolhido.properties.cdistscodi}`, true)}</h2>
              <p className={estilos.apoio}>
                Recife, Pernambuco. Código oficial {String(escolhido.properties.cdistscodi).padStart(2, "0")}.
              </p>
              {bairroDoRecorte && (
                <p className={estilos.avisoBairro}>
                  Você escolheu o bairro {bairroDoRecorte}. Os dados deste mapa existem só por distrito, então
                  ele mostra o distrito inteiro.
                </p>
              )}
              <dl className={estilos.numeros}>
                <div>
                  <dt>Bairros</dt>
                  <dd>{escolhido.properties.quantidade_bairros}</dd>
                </div>
                <div>
                  <dt>Área</dt>
                  <dd>{formatarNumero(escolhido.properties.area_km2, 2)} km²</dd>
                </div>
                {indicador !== "quantidade_bairros" && indicador !== "area_km2" && (
                  <div>
                    <dt>{info.rotulo}</dt>
                    <dd>
                      {indicador === "prioridade" && valorDe(escolhido) !== null ? (
                        <SeloNivel
                          nivel={NIVEL_PRIORIDADE[valorDe(escolhido)!]}
                          rotulo={textoValor(escolhido)}
                        />
                      ) : (
                        textoValor(escolhido)
                      )}
                    </dd>
                  </div>
                )}
              </dl>
              <h3>Bairros do distrito</h3>
              <ul className={estilos.bairros}>
                {escolhido.properties.bairros.map((b) => (
                  <li key={b} data-recorte={b === bairroDoRecorte}>
                    {b}
                  </li>
                ))}
              </ul>
              <div className={estilos.acoesDetalhe}>
                {usuario?.permissoes.includes("editar") && (
                  <Botao onClick={registrarAvaliacao}>Registrar avaliação</Botao>
                )}
                <Botao variante="discreto" onClick={limpar}>
                  Voltar à visão geral
                </Botao>
              </div>
            </>
          ) : (
            <>
              <h2>Conheça o território</h2>
              <p className={estilos.apoio}>Escolha um distrito no mapa ou na lista para ver os bairros.</p>
              <h3>Compare os distritos</h3>
              <p className={estilos.apoio}>
                {info.rotulo}
                {busca ? ", só os do resultado da busca" : ""}.
              </p>
              <ul className={estilos.ranking}>
                {[...visiveis]
                  .sort((a, b) => (valorDe(b) ?? -Infinity) - (valorDe(a) ?? -Infinity))
                  .map((f) => {
                    const v = valorDe(f);
                    return (
                      <li key={f.properties.cdistscodi}>
                        <button
                          type="button"
                          onClick={() => selecionar(f.properties.cdistscodi)}
                          aria-label={`Selecionar ${distritoPorExtenso(
                            `ds-${f.properties.cdistscodi}`,
                          )}: ${textoValor(f)}`}
                        >
                          <span>DS {ROMANOS[f.properties.cdistscodi]}</span>
                          <i>
                            <b
                              data-sem-dado={v === null}
                              style={{
                                width: v === null ? "100%" : `${(v / (escala.max || 1)) * 100}%`,
                                background: v === null ? undefined : cor(f),
                              }}
                            />
                          </i>
                          <span>{textoValor(f)}</span>
                        </button>
                      </li>
                    );
                  })}
              </ul>
            </>
          )}
          <div className={estilos.interpretar}>
            <h3>Como interpretar</h3>
            <p>{info.interpretar}</p>
            <button type="button" className={estilos.linkBotao} onClick={() => setSobre(true)}>
              <Info aria-hidden="true" size={18} /> Sobre os dados
            </button>
          </div>
        </aside>
      </div>
      <SobreDados aberto={sobre} aoMudar={setSobre} />
    </>
  );
}

function rotuloClasse(indicador: Indicador, low: number, high: number, ultima: boolean, casas: number) {
  if (indicador === "quantidade_bairros" || indicador === "vacinacao" || indicador === "ocorrencias") {
    const lo = Math.ceil(low),
      hi = ultima ? Math.floor(high) : Math.ceil(high) - 1;
    return lo >= hi ? formatarNumero(lo) : `${formatarNumero(lo)} a ${formatarNumero(hi)}`;
  }
  return `${formatarNumero(low, casas + 2)} a ${ultima ? "" : "menos de "}${formatarNumero(high, casas + 2)}`;
}

function SobreDados({ aberto, aoMudar }: { aberto: boolean; aoMudar: (a: boolean) => void }) {
  return (
    <Dialogo aberto={aberto} aoMudar={aoMudar} titulo="Sobre os dados do mapa">
      <div className={estilos.sobre}>
        <p>
          Os limites oficiais dos distritos vêm dos Dados Abertos do Recife e são ligados ao arquivo de
          bairros pelo código do distrito. A carga fica no MongoDB Atlas (coleção Recife.DistritosSanitarios)
          e é lida pela API do ClimaSense.
        </p>
        <h3>O que as cores mostram</h3>
        <p>
          A escala tem cinco intervalos iguais entre o menor e o maior valor de todos os distritos. A busca e
          os filtros não mudam os limites. A área usa o elipsoide WGS84, em km², descontando os buracos dos
          polígonos.
        </p>
        <h3>Faixas hídricas</h3>
        <p>
          A camada azul mostra as faixas marginais dos recursos hídricos: polígonos de entorno, não só o leito
          dos rios. Passe o cursor para ver o nome e a bacia.
        </p>
        <h3>Correção documentada: Distritos Sanitários VII e VIII</h3>
        <p>
          O arquivo oficial de bairros traz vínculos divergentes para esses dois distritos. A relação da
          Secretaria de Saúde foi usada para atribuir 13 bairros ao Distrito Sanitário VII (incluindo
          Guabiraba e Brejo de Beberibe) e 3 ao VIII (Cohab, Ibura e Jordão). O arquivo original foi
          preservado, e os 15 ajustes estão registrados em data/territorio/correcoes-bairros.json.
        </p>
        <p>
          <a
            href="https://dados.recife.pe.gov.br/dataset/distritos-sanitarios"
            target="_blank"
            rel="noopener noreferrer"
          >
            Distritos e bairros nos Dados Abertos do Recife
          </a>
        </p>
      </div>
    </Dialogo>
  );
}
