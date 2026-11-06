import { useEffect, useRef, useState } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { token, useTemaAtual } from "@/charts/tema";
import estilos from "./MapaTerritorio.module.css";

export interface PropsFeicao {
  id: string;
  nome: string;
}
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

export interface PontoAbrigo {
  id: string | number;
  nome: string;
  lat: number;
  lng: number;
  /** `true` = aberto (destaque); `false` = fechado; `null` = ninguém informou a situação. */
  aberto: boolean | null;
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
  abrigos?: PontoAbrigo[] | null;
}

const PREFIXO = "cs-mapa-";
const escapar = (v: unknown) =>
  String(v ?? "").replace(
    /[&<>"']/g,
    (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]!,
  );
const semMovimento = () => matchMedia("(prefers-reduced-motion: reduce)").matches;

/**
 * Mapa de territórios (94 bairros) colorido pelo estágio em vigor. Declarado = preenchimento cheio e borda contínua;
 * sugerido pelo sistema = listras e borda tracejada; sem dado = hachura cinza. Clicar (ou Enter, com o foco no
 * território) escolhe. A lista de bairros ao lado do mapa é o caminho para quem não usa o mapa.
 */
export function MapaBairros(props: Props) {
  const caixa = useRef<HTMLDivElement>(null);
  const mapa = useRef<L.Map>();
  const camadas = useRef(new Map<string, L.Path>());
  const grupo = useRef<L.GeoJSON>();
  const defs = useRef<SVGDefsElement>();
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

  function estilo(id: string): L.PathOptions {
    const p = atuais.current;
    const sel = id === p.selecionado;
    const base: L.PathOptions = {
      color: sel ? token("--cs-tinta") : token("--cs-papel"),
      weight: sel ? 3.5 : 1.2,
      opacity: 1,
    };
    if (p.modo === "nenhum")
      return { ...base, color: sel ? token("--cs-tinta") : token("--cs-linha-forte"), fillOpacity: 0 };
    if (p.modo === "populacao" && p.populacao) {
      const v = p.populacao(id);
      if (v.suprimido)
        return {
          ...base,
          fillColor: `url(#${PREFIXO}supr)`,
          fillOpacity: 1,
          dashArray: sel ? undefined : "2 3",
        };
      if (v.classe === null)
        return {
          ...base,
          fillColor: `url(#${PREFIXO}sem)`,
          fillOpacity: 1,
          dashArray: sel ? undefined : "3 3",
        };
      return { ...base, fillColor: token(p.tokensPopulacao?.[v.classe] ?? "--g-seq-4"), fillOpacity: 0.9 };
    }
    const a = p.aparencia(id);
    if (a.ordem === null)
      return {
        ...base,
        fillColor: `url(#${PREFIXO}sem)`,
        fillOpacity: 1,
        dashArray: sel ? undefined : "3 3",
      };
    if (a.origem === "sugerido")
      return {
        ...base,
        fillColor: `url(#${PREFIXO}sug-${a.ordem})`,
        fillOpacity: 1,
        dashArray: sel ? undefined : "5 3",
        color: sel ? token("--cs-tinta") : token(p.tokensEstagio[a.ordem]),
        weight: sel ? 3.5 : 1.8,
      };
    return { ...base, fillColor: token(p.tokensEstagio[a.ordem]), fillOpacity: 0.88 };
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
    const tiles = L.tileLayer(atuais.current.tilesUrl, { maxZoom: 18, attribution: "Mapa de fundo © Esri" });
    tiles.on("tileerror", () => setTilesFalharam(true));
    tiles.on("tileload", () => setTilesFalharam(false));
    tiles.addTo(m);
    m.getContainer().setAttribute("aria-label", atuais.current.rotulo);

    const renderizador = L.svg();
    m.addLayer(renderizador as unknown as L.Layer);
    const svg = (renderizador as unknown as { _container: SVGSVGElement })._container;
    const d = document.createElementNS("http://www.w3.org/2000/svg", "defs");
    svg.prepend(d);
    defs.current = d;
    desenharPadroes();

    const g = L.geoJSON(atuais.current.territorios, {
      ...({ renderer: renderizador } as L.GeoJSONOptions),
      style: (f) => estilo((f as GeoJSON.Feature<GeoJSON.Geometry, PropsFeicao>).properties.id),
      onEachFeature: (f, camada) => {
        const { id, nome } = (f as GeoJSON.Feature<GeoJSON.Geometry, PropsFeicao>).properties;
        const caminho = camada as L.Path;
        camadas.current.set(id, caminho);
        caminho.on("click", () => atuais.current.aoSelecionar(id));
        caminho.on("mouseover", () => caminho.setStyle({ weight: 3, color: token("--cs-tinta") }));
        caminho.on("mouseout", () => caminho.setStyle(estilo(id)));
        caminho.bindTooltip(escapar(nome), { sticky: true });
      },
    }).addTo(m);
    grupo.current = g;
    m.fitBounds(g.getBounds(), { padding: [16, 16], animate: false });

    const ro = new ResizeObserver(() => m.invalidateSize({ pan: false }));
    ro.observe(caixa.current);
    const lista = camadas.current;
    return () => {
      ro.disconnect();
      m.remove();
      lista.clear();
    };
  }, []);

  // contorno dos distritos, por cima
  useEffect(() => {
    const m = mapa.current;
    if (!m || !props.contorno) return;
    const c = L.geoJSON(props.contorno, {
      pane: "contorno",
      interactive: false,
      style: { color: token("--cs-tinta"), weight: 2.5, fill: false, opacity: 0.85 },
    }).addTo(m);
    return () => {
      c.remove();
    };
  }, [props.contorno]);

  // estado → mapa
  useEffect(() => {
    desenharPadroes();
    camadas.current.forEach((camada, id) => {
      camada.setStyle(estilo(id));
      const nome = (camada as unknown as { feature: GeoJSON.Feature<GeoJSON.Geometry, PropsFeicao> }).feature
        .properties.nome;
      camada.setTooltipContent(props.dica(id, nome));
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

  // abrigos: aberto em destaque (cheio e maior), fechado ou sem informação (vazado)
  useEffect(() => {
    const m = mapa.current;
    const lista = props.abrigos;
    if (!m || !lista) return;
    const g = L.layerGroup();
    for (const a of lista) {
      const sit = a.aberto === null ? "situação não informada" : a.aberto ? "aberto" : "fechado";
      const tam = a.aberto ? 30 : 24;
      L.marker([a.lat, a.lng], {
        title: `${a.nome} (${sit})`,
        alt: `${a.nome}, ${sit}`,
        zIndexOffset: a.aberto ? 500 : 0,
        icon: L.divIcon({
          className: `${estilos.pino} ${estilos.pinoAbrigo} ${a.aberto ? estilos.pinoAberto : ""}`,
          html: `<span aria-hidden="true">${a.aberto ? "A" : "a"}</span>`,
          iconSize: [tam, tam],
          iconAnchor: [tam / 2, tam / 2],
          popupAnchor: [0, -tam / 2],
        }),
      })
        .bindPopup(`<strong>${escapar(a.nome)}</strong><br>Abrigo, ${sit}`)
        .addTo(g);
    }
    g.addTo(m);
    return () => {
      g.remove();
    };
  }, [props.abrigos]);

  // foco no território escolhido
  useEffect(() => {
    const m = mapa.current;
    const camada = props.selecionado ? camadas.current.get(props.selecionado) : null;
    if (m && camada) {
      (camada as L.Path).bringToFront();
      m.fitBounds((camada as L.Polygon).getBounds(), {
        padding: [40, 40],
        maxZoom: 15,
        animate: !semMovimento(),
      });
    }
  }, [props.selecionado]);

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
