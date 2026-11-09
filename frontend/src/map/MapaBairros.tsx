import { useEffect, useRef, useState } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { token, useTemaAtual } from "@/charts/tema";
import { siglaDistrito } from "@/lib/distritos";
import { corDoDistrito } from "./paleta";
import estilos from "./MapaTerritorio.module.css";

/**
 * MapaBairros: mapa Leaflet dos 94 bairros, reutilizável (Mapa e Simulador).
 *
 * Cores (`modoCor`; sem ele vale `modo`, que o Simulador já usa):
 *  - "distrito": um matiz por distrito sanitário (`CORES_DISTRITO` em `./paleta`, a mesma paleta em todas as telas).
 *    Só precisa do GeoJSON (`distrito_id` de cada bairro), então desenha antes de qualquer dado lento.
 *  - "estagio": estágio 0 a 3 vindo de `aparencia(id)`; é também o modo de risco do Simulador (classe do cenário).
 *    Declarado = cor cheia, sugerido = listras, sem dado = hachura cinza (nunca "baixo", RN-01).
 *  - "valor": escala sequencial de uma cor. `valorPorBairro(id)` devolve a classe 0..n-1 (maior = mais intenso)
 *    ou `null` (sem dado, hachura). `tokensValor` traz os tokens, do mais claro ao mais escuro. Usado na prioridade.
 *  - "populacao": faixas de população (`populacao`, `tokensPopulacao`). "nenhum": só contorno.
 *
 * Interação: `aoSelecionar(id)` recebe o id do bairro (ou do distrito, se o mapa tem só distritos). `selecionado`
 * destaca e aproxima o bairro. `distritoEmFoco` ("ds-N") aproxima o distrito e esmaece os demais; `null` volta ao
 * Recife inteiro. `pronto={false}` pinta tudo de cinza liso (ainda carregando; não é "sem dado").
 * Teclado: com um distrito em foco, os bairros dele entram na ordem do Tab (Enter escolhe, o nome aparece).
 */
export interface PropsFeicao {
  id: string;
  nome: string;
  /** Distrito do bairro (`ds-N`). Sem ele, o bairro não recebe cor de distrito (hachura). */
  distrito_id?: string | null;
}

export type ModoCor = "distrito" | "estagio" | "valor" | "populacao" | "nenhum";

/** Tokens padrão da escala "valor" (sequencial azul), do mais claro ao mais escuro. */
export const TOKENS_VALOR = ["--g-seq-2", "--g-seq-3", "--g-seq-4", "--g-seq-6", "--g-seq-7"];
export type ColecaoFeicoes = GeoJSON.FeatureCollection<GeoJSON.Geometry, PropsFeicao>;

/** Valor de um bairro na camada de população: faixa 0..n, ou `null` (sem dado). `suprimido` = "< 5", ocultado. */
export interface AparenciaPopulacao {
  classe: number | null;
  suprimido: boolean;
}

export interface TipoPino {
  chave: string;
  glifo: string;
  rotulo: string;
}

/** Como pintar um território: `ordem` 0 a 3 (observação a crítico) ou `null` (sem dado, hachura cinza, nunca verde). */
export interface Aparencia {
  ordem: number | null;
  origem: "declarado" | "sugerido" | "sem_dados";
}

interface Props {
  territorios: ColecaoFeicoes;
  /** Contorno dos distritos por cima dos bairros (só linha). */
  contorno?: GeoJSON.FeatureCollection | null;
  tilesUrl: string;
  rotulo: string;
  aparencia: (id: string) => Aparencia;
  dica: (id: string, nome: string) => string;
  selecionado: string | null;
  /** Ids a enquadrar quando a escolha é um distrito (não há camada própria para ele). */
  enquadrar?: string[] | null;
  aoSelecionar: (id: string) => void;
  /** Cores dos 4 estágios (tokens), lidas na hora de desenhar para valerem nos dois temas. */
  tokensEstagio: string[];
  /** O que pinta os bairros: o estágio/classe (padrão), a população vulnerável ou nada (só contorno). */
  modo?: "estagio" | "populacao" | "nenhum";
  /** Modo de cor completo; tem prioridade sobre `modo`. Veja o topo do arquivo. */
  modoCor?: ModoCor;
  /** Modo "valor": classe 0..n-1 do bairro (maior = mais intenso) ou `null` = sem dado. */
  valorPorBairro?: (id: string) => number | null;
  tokensValor?: string[];
  /** Distrito (`ds-N`) em foco: o mapa aproxima e esmaece os outros. `null`/ausente = Recife inteiro. */
  distritoEmFoco?: string | null;
  /** Os valores do modo atual ainda carregam: pinta cinza liso em vez de "sem dado". */
  pronto?: boolean;
  /** Há um painel fixo cobrindo a parte de baixo do mapa (celular): reserva essa faixa ao aproximar. */
  painelSobreposto?: boolean;
  populacao?: (id: string) => AparenciaPopulacao;
  /** Tokens das faixas da população, da menor para a maior. */
  tokensPopulacao?: string[];
  /** Camadas por cima (RF-02, RF-26). `null` ou ausente = desligada. */
  areasRisco?: {
    colecao: GeoJSON.FeatureCollection;
    /** Token de cor para o tipo da área. */
    cor: (tipo: string) => string;
  } | null;
  equipamentos?: {
    colecao: GeoJSON.FeatureCollection;
    tipo: (props: Record<string, unknown>) => TipoPino;
  } | null;
}

const PREFIXO = "cs-mapa-";
const escapar = (v: unknown) =>
  String(v ?? "").replace(
    /[&<>"']/g,
    (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]!,
  );
const semMovimento = () => matchMedia("(prefers-reduced-motion: reduce)").matches;
/** Fração da altura da tela que o painel fixo do celular cobre (igual ao `.painelCaixa` do Mapa). */
const ALTURA_PAINEL_CELULAR = 0.5;
/** Do zoom 14 em diante os rótulos dos distritos somem: já se enxergam os bairros. */
const ZOOM_SEM_ROTULOS = 14;

type Feicao = GeoJSON.Feature<GeoJSON.Geometry, PropsFeicao>;

function modoDe(p: Props): ModoCor {
  return p.modoCor ?? p.modo ?? "estagio";
}

/** Centroide (pela área) do maior polígono: lugar do rótulo do distrito. */
function centroide(g: GeoJSON.Geometry): L.LatLngExpression | null {
  const aneis: number[][][] =
    g.type === "Polygon"
      ? [g.coordinates[0]]
      : g.type === "MultiPolygon"
        ? g.coordinates.map((p) => p[0])
        : [];
  let melhor: { area: number; cx: number; cy: number } | null = null;
  for (const anel of aneis) {
    let a = 0,
      cx = 0,
      cy = 0;
    for (let i = 0; i < anel.length - 1; i++) {
      const [x0, y0] = anel[i];
      const [x1, y1] = anel[i + 1];
      const f = x0 * y1 - x1 * y0;
      a += f;
      cx += (x0 + x1) * f;
      cy += (y0 + y1) * f;
    }
    if (a === 0) continue;
    const area = Math.abs(a) / 2;
    if (!melhor || area > melhor.area) melhor = { area, cx: cx / (3 * a), cy: cy / (3 * a) };
  }
  return melhor ? [melhor.cy, melhor.cx] : null;
}

/**
 * Mapa de territórios (94 bairros). Veja o topo do arquivo para os modos de cor e as props de interação.
 * A lista de bairros ao lado do mapa é o caminho para quem não usa o mapa.
 */
export function MapaBairros(props: Props) {
  const caixa = useRef<HTMLDivElement>(null);
  const mapa = useRef<L.Map>();
  const camadas = useRef(new Map<string, L.Path>());
  const feicoes = useRef(new Map<string, PropsFeicao>());
  const grupo = useRef<L.GeoJSON>();
  const defs = useRef<SVGDefsElement>();
  const ligados = useRef(new WeakSet<Element>());
  const focoAnterior = useRef<string | null>(null);
  const atuais = useRef(props);
  atuais.current = props;
  const [tilesFalharam, setTilesFalharam] = useState(false);
  const tema = useTemaAtual();

  function desenharPadroes() {
    const d = defs.current;
    if (!d) return;
    const cinza = token("--n-insuf-bg");
    const traco = token("--g-eixo");
    const papel = token("--cs-papel");
    const cores = atuais.current.tokensEstagio.map((t) => token(t));
    d.innerHTML =
      `<pattern id="${PREFIXO}sem" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="8" height="8" fill="${cinza}"/><line x1="0" y1="0" x2="0" y2="8" stroke="${traco}" stroke-width="3"/></pattern>` +
      `<pattern id="${PREFIXO}supr" width="6" height="6" patternUnits="userSpaceOnUse"><rect width="6" height="6" fill="${token("--g-seq-1")}"/><circle cx="3" cy="3" r="1.3" fill="${token("--g-seq-6")}"/></pattern>` +
      cores
        .map(
          (c, i) =>
            `<pattern id="${PREFIXO}sug-${i}" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(-45)"><rect width="8" height="8" fill="${c}" fill-opacity="0.9"/><line x1="0" y1="0" x2="0" y2="8" stroke="${papel}" stroke-opacity="0.65" stroke-width="2.5"/></pattern>`,
        )
        .join("");
  }

  function distritoDe(id: string): string | null {
    return feicoes.current.get(id)?.distrito_id ?? (id.startsWith("ds-") ? id : null);
  }

  function estilo(id: string): L.PathOptions {
    const p = atuais.current;
    const sel = id === p.selecionado;
    const foco = p.distritoEmFoco ?? null;
    const fora = foco !== null && distritoDe(id) !== foco;
    const modo = modoDe(p);
    const base: L.PathOptions = {
      color: sel ? token("--cs-tinta") : token("--cs-papel"),
      weight: sel ? 3.5 : 0.9,
      opacity: fora ? 0.45 : 1,
    };
    // fora do distrito em foco: o preenchimento fica bem fraco, mas continua clicável
    const forca = (o: number) => (fora ? Math.min(o, 0.14) : o);
    const sem = (tracejado: string): L.PathOptions => ({
      ...base,
      fillColor: `url(#${PREFIXO}sem)`,
      fillOpacity: forca(1),
      dashArray: sel ? undefined : tracejado,
    });

    if (modo === "nenhum")
      return { ...base, color: sel ? token("--cs-tinta") : token("--cs-linha-forte"), fillOpacity: 0 };
    if (p.pronto === false) return { ...base, fillColor: token("--n-insuf-bg"), fillOpacity: forca(0.75) };
    if (modo === "distrito") {
      const ds = distritoDe(id);
      if (!ds) return sem("3 3");
      return { ...base, fillColor: corDoDistrito(ds), fillOpacity: forca(0.62) };
    }
    if (modo === "valor") {
      const v = p.valorPorBairro?.(id) ?? null;
      const tokens = p.tokensValor ?? TOKENS_VALOR;
      if (v === null || !tokens[v]) return sem("3 3");
      return { ...base, fillColor: token(tokens[v]), fillOpacity: forca(0.9) };
    }
    if (modo === "populacao" && p.populacao) {
      const v = p.populacao(id);
      if (v.suprimido)
        return {
          ...base,
          fillColor: `url(#${PREFIXO}supr)`,
          fillOpacity: forca(1),
          dashArray: sel ? undefined : "2 3",
        };
      if (v.classe === null) return sem("3 3");
      return {
        ...base,
        fillColor: token(p.tokensPopulacao?.[v.classe] ?? "--g-seq-4"),
        fillOpacity: forca(0.9),
      };
    }
    const a = p.aparencia(id);
    if (a.ordem === null) return sem("3 3");
    if (a.origem === "sugerido")
      return {
        ...base,
        fillColor: `url(#${PREFIXO}sug-${a.ordem})`,
        fillOpacity: forca(1),
        dashArray: sel ? undefined : "5 3",
        color: sel ? token("--cs-tinta") : token(p.tokensEstagio[a.ordem]),
        weight: sel ? 3.5 : 1.8,
      };
    return { ...base, fillColor: token(p.tokensEstagio[a.ordem]), fillOpacity: forca(0.88) };
  }

  /** Margem de baixo para o painel fixo do celular não esconder o que acabou de ser aproximado. */
  function margemInferior(): number {
    const m = mapa.current;
    if (!m || !atuais.current.painelSobreposto || !matchMedia("(max-width: 1100px)").matches) return 0;
    const r = m.getContainer().getBoundingClientRect();
    const visivelAte = window.innerHeight * (1 - ALTURA_PAINEL_CELULAR);
    return Math.max(0, Math.min(r.height * 0.6, r.bottom - visivelAte));
  }

  // criação (uma vez)
  useEffect(() => {
    if (!caixa.current) return;
    const m = L.map(caixa.current, { zoomControl: true, keyboard: true, attributionControl: true });
    mapa.current = m;
    m.setView([-8.05, -34.92], 12);
    m.zoomControl.setPosition("bottomright");
    L.control.scale({ imperial: false, position: "bottomright" }).addTo(m);
    m.createPane("areas").style.zIndex = "430";
    m.createPane("contorno").style.zIndex = "450";
    m.createPane("rotulos").style.zIndex = "460";
    const tiles = L.tileLayer(atuais.current.tilesUrl, { maxZoom: 18, attribution: "Mapa de fundo © Esri" });
    tiles.on("tileerror", () => setTilesFalharam(true));
    tiles.on("tileload", () => setTilesFalharam(false));
    tiles.addTo(m);
    m.getContainer().setAttribute("aria-label", atuais.current.rotulo);
    const marcarZoom = () => {
      m.getContainer().dataset.zoomAlto = String(m.getZoom() >= ZOOM_SEM_ROTULOS);
    };
    m.on("zoomend", marcarZoom);
    marcarZoom();

    const renderizador = L.svg();
    m.addLayer(renderizador as unknown as L.Layer);
    const svg = (renderizador as unknown as { _container: SVGSVGElement })._container;
    const d = document.createElementNS("http://www.w3.org/2000/svg", "defs");
    svg.prepend(d);
    defs.current = d;
    desenharPadroes();

    const g = L.geoJSON(atuais.current.territorios, {
      ...({ renderer: renderizador } as L.GeoJSONOptions),
      style: (f) => estilo((f as Feicao).properties.id),
      onEachFeature: (f, camada) => {
        const { id, nome } = (f as Feicao).properties;
        feicoes.current.set(id, (f as Feicao).properties);
        const caminho = camada as L.Path;
        camadas.current.set(id, caminho);
        caminho.on("click", () => atuais.current.aoSelecionar(id));
        caminho.on("mouseover", () => caminho.setStyle({ weight: 2.6, color: token("--cs-tinta") }));
        caminho.on("mouseout", () => caminho.setStyle(estilo(id)));
        caminho.bindTooltip(escapar(nome), { sticky: true });
      },
    }).addTo(m);
    grupo.current = g;
    m.fitBounds(g.getBounds(), { padding: [16, 16], animate: false });

    const ro = new ResizeObserver(() => m.invalidateSize({ pan: false }));
    ro.observe(caixa.current);
    const lista = camadas.current;
    const nomes = feicoes.current;
    return () => {
      ro.disconnect();
      m.remove();
      lista.clear();
      nomes.clear();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // contorno dos distritos (linha forte com halo) e rótulos "D1"
  useEffect(() => {
    const m = mapa.current;
    if (!m || !props.contorno) return;
    const foco = props.distritoEmFoco ?? null;
    const codigo = (f?: GeoJSON.Feature) =>
      `ds-${(f?.properties as { cdistscodi?: number } | null)?.cdistscodi}`;
    const halo = L.geoJSON(props.contorno, {
      pane: "contorno",
      interactive: false,
      style: { color: token("--cs-papel"), weight: 6, fill: false, opacity: 0.85 },
    }).addTo(m);
    const linha = L.geoJSON(props.contorno, {
      pane: "contorno",
      interactive: false,
      style: (f) => ({
        color: token("--cs-tinta"),
        weight: foco && codigo(f) === foco ? 4 : 2.6,
        fill: false,
        opacity: foco && codigo(f) !== foco ? 0.5 : 0.95,
      }),
    }).addTo(m);
    const rotulos = L.layerGroup();
    for (const f of props.contorno.features) {
      const ponto = centroide(f.geometry);
      const nome = String((f.properties as { nome_distrito?: string } | null)?.nome_distrito ?? "");
      const rotulo = siglaDistrito(nome);
      if (!ponto || !nome) continue;
      const ds = codigo(f);
      L.marker(ponto, {
        pane: "rotulos",
        interactive: false,
        keyboard: false,
        icon: L.divIcon({
          className: `${estilos.rotuloDistrito} ${foco && ds !== foco ? estilos.rotuloDistritoFraco : ""}`,
          html: `<span style="border-color:${corDoDistrito(ds)}">${escapar(rotulo)}</span>`,
          iconSize: [64, 24],
          iconAnchor: [32, 12],
        }),
      }).addTo(rotulos);
    }
    rotulos.addTo(m);
    return () => {
      halo.remove();
      linha.remove();
      rotulos.remove();
    };
  }, [props.contorno, props.distritoEmFoco, tema]);

  // estado → mapa
  useEffect(() => {
    desenharPadroes();
    const foco = props.distritoEmFoco ?? null;
    camadas.current.forEach((camada, id) => {
      camada.setStyle(estilo(id));
      const nome = feicoes.current.get(id)?.nome ?? "";
      camada.setTooltipContent(props.dica(id, nome));
      // teclado: os bairros do distrito em foco entram no Tab; Enter escolhe e o nome aparece
      const el = camada.getElement();
      if (!el) return;
      const navegavel = foco !== null && distritoDe(id) === foco;
      if (navegavel) {
        el.setAttribute("tabindex", "0");
        el.setAttribute("role", "button");
        el.setAttribute("aria-label", nome);
      } else {
        el.removeAttribute("tabindex");
        el.removeAttribute("role");
        el.removeAttribute("aria-label");
      }
      if (!ligados.current.has(el)) {
        ligados.current.add(el);
        el.addEventListener("focus", () => {
          camada.setStyle({ weight: 2.6, color: token("--cs-tinta") });
          camada.openTooltip();
        });
        el.addEventListener("blur", () => {
          camada.setStyle(estilo(id));
          camada.closeTooltip();
        });
        el.addEventListener("keydown", (e) => {
          const k = (e as KeyboardEvent).key;
          if (k === "Enter" || k === " ") {
            e.preventDefault();
            atuais.current.aoSelecionar(id);
          }
        });
      }
    });
  });

  // áreas de risco (polígonos por tipo; sem clique, para não tapar o bairro)
  useEffect(() => {
    const m = mapa.current;
    const cfg = props.areasRisco;
    if (!m || !cfg) return;
    const g = L.geoJSON(cfg.colecao, {
      pane: "areas",
      interactive: false,
      style: (f) => {
        const cor = token(cfg.cor(String((f?.properties as { tipo?: unknown } | null)?.tipo ?? "")));
        return { color: cor, weight: 1.5, dashArray: "4 2", fillColor: cor, fillOpacity: 0.35, opacity: 1 };
      },
    }).addTo(m);
    return () => {
      g.remove();
    };
  }, [props.areasRisco, tema]);

  // equipamentos de saúde (pino com letra por tipo; clique mostra nome e tipo)
  useEffect(() => {
    const m = mapa.current;
    const cfg = props.equipamentos;
    if (!m || !cfg) return;
    const g = L.layerGroup();
    for (const f of cfg.colecao.features) {
      if (f.geometry?.type !== "Point") continue;
      const [lng, lat] = f.geometry.coordinates;
      const p = (f.properties ?? {}) as Record<string, unknown>;
      const t = cfg.tipo(p);
      const nome = String(p.nome ?? "Equipamento de saúde");
      L.marker([lat, lng], {
        title: `${nome} (${t.rotulo})`,
        alt: `${nome}, ${t.rotulo}`,
        // centenas de pontos: sem parada de Tab em cada um; a lista do bairro traz os mesmos nomes em texto
        keyboard: false,
        icon: L.divIcon({
          className: `${estilos.pino} ${estilos.pinoSaude}`,
          html: `<span aria-hidden="true">${escapar(t.glifo)}</span>`,
          iconSize: [24, 24],
          iconAnchor: [12, 12],
          popupAnchor: [0, -12],
        }),
      })
        .bindPopup(`<strong>${escapar(nome)}</strong><br>${escapar(String(p.tipo ?? t.rotulo))}`)
        .addTo(g);
    }
    g.addTo(m);
    return () => {
      g.remove();
    };
  }, [props.equipamentos]);

  // aproximação: bairro escolhido > distrito em foco > Recife inteiro (só ao sair de um distrito)
  useEffect(() => {
    const m = mapa.current;
    if (!m) return;
    const foco = props.distritoEmFoco ?? null;
    const camada = props.selecionado ? camadas.current.get(props.selecionado) : null;
    const animar = !semMovimento();
    const baixo = margemInferior();
    if (camada) {
      (camada as L.Path).bringToFront();
      m.fitBounds((camada as L.Polygon).getBounds(), {
        paddingTopLeft: [40, 40],
        paddingBottomRight: [40, 40 + baixo],
        maxZoom: 15,
        animate: animar,
      });
    } else if (foco) {
      const alvo = [...camadas.current.entries()].filter(([id]) => distritoDe(id) === foco).map(([, c]) => c);
      if (alvo.length)
        m.fitBounds(L.featureGroup(alvo).getBounds(), {
          paddingTopLeft: [30, 30],
          paddingBottomRight: [30, 30 + baixo],
          maxZoom: 14,
          animate: animar,
        });
    } else if (focoAnterior.current !== null && grupo.current) {
      m.fitBounds(grupo.current.getBounds(), { padding: [16, 16], animate: animar });
    }
    focoAnterior.current = foco;
  }, [props.selecionado, props.distritoEmFoco]);

  const chaveEnquadrar = props.enquadrar?.join("|") ?? "";
  useEffect(() => {
    const m = mapa.current;
    const alvo = (atuais.current.enquadrar ?? []).map((i) => camadas.current.get(i)).filter(Boolean);
    if (m && alvo.length)
      m.fitBounds(L.featureGroup(alvo as L.Layer[]).getBounds(), {
        padding: [30, 30],
        maxZoom: 14,
        animate: !semMovimento(),
      });
  }, [chaveEnquadrar]);

  return (
    <div className={estilos.moldura}>
      <div ref={caixa} className={estilos.mapa} data-testid="mapa-leaflet" />
      {tilesFalharam && (
        <p className={estilos.avisoTiles} role="status">
          O mapa de ruas não carregou. Os bairros continuam navegáveis pela lista.
        </p>
      )}
    </div>
  );
}
