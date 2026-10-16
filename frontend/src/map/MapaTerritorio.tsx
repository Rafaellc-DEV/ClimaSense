import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import estilos from "./MapaTerritorio.module.css";

export interface PropsDistrito {
  cdistscodi: number;
  nome_distrito: string;
  bairros: string[];
  quantidade_bairros: number;
  area_km2: number;
}
export type FeatureDistrito = GeoJSON.Feature<GeoJSON.Geometry, PropsDistrito>;
export type ColecaoDistritos = GeoJSON.FeatureCollection<GeoJSON.Geometry, PropsDistrito>;

export interface ControleMapa {
  enquadrar: (codigos?: number[]) => void;
}

interface Props {
  distritos: ColecaoDistritos;
  hidrografia?: GeoJSON.FeatureCollection | null;
  tilesUrl: string;
  /** Cor de preenchimento de cada distrito; "hachura" = sem dado (RN-01). */
  cor: (f: FeatureDistrito) => string | "hachura";
  dica: (f: FeatureDistrito) => string;
  visiveis: Set<number>;
  selecionado: number | null;
  mostrarDistritos: boolean;
  mostrarFaixas: boolean;
  opacidade: number;
  aoSelecionar: (codigo: number) => void;
}

const HACHURA = "cs-hachura-sem-dado";
const escapar = (v: unknown) =>
  String(v ?? "").replace(
    /[&<>"']/g,
    (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]!,
  );
const semMovimento = () => matchMedia("(prefers-reduced-motion: reduce)").matches;

/**
 * Mapa dos 8 distritos e das 81 faixas hídricas (RF-07). Porte do `app.js` da Aula 07: mesma lógica de estilo,
 * seleção, rótulos e aviso de falha dos tiles, agora alimentado pela API.
 */
export const MapaTerritorio = forwardRef<ControleMapa, Props>(function MapaTerritorio(props, ref) {
  const caixa = useRef<HTMLDivElement>(null);
  const mapa = useRef<L.Map>();
  const camadas = useRef(new Map<number, L.Path>());
  const grupoDistritos = useRef<L.GeoJSON>();
  const grupoFaixas = useRef<L.GeoJSON>();
  const rotulos = useRef<L.LayerGroup>();
  const marcadores = useRef(new Map<number, L.Marker>());
  const atuais = useRef(props);
  atuais.current = props;
  const [tilesFalharam, setTilesFalharam] = useState(false);

  function estilo(f: FeatureDistrito): L.PathOptions {
    const p = atuais.current;
    const sel = f.properties.cdistscodi === p.selecionado;
    const c = p.cor(f);
    return {
      fillColor: c === "hachura" ? `url(#${HACHURA})` : c,
      fillOpacity: c === "hachura" ? 1 : p.opacidade,
      color: sel ? "#0e2433" : "#ffffff",
      weight: sel ? 3.5 : 2,
      opacity: 0.95,
    };
  }

  function enquadrar(codigos?: number[]) {
    const m = mapa.current;
    const alvo = (codigos ?? [...atuais.current.visiveis]).map((c) => camadas.current.get(c)).filter(Boolean);
    if (m && alvo.length)
      m.fitBounds(L.featureGroup(alvo as L.Layer[]).getBounds(), {
        padding: [32, 32],
        animate: false,
        maxZoom: 14,
      });
  }
  useImperativeHandle(ref, () => ({ enquadrar }));

  // criação (uma vez)
  useEffect(() => {
    if (!caixa.current) return;
    const m = L.map(caixa.current, {
      zoomControl: true,
      keyboard: true,
      preferCanvas: false,
      attributionControl: true,
    });
    mapa.current = m;
    m.setView([-8.05, -34.92], 12); // o renderizador SVG só cria o contêiner depois que há uma vista
    m.zoomControl.setPosition("topright");
    L.control.scale({ imperial: false, position: "bottomright" }).addTo(m);
    m.createPane("hidrografia").style.zIndex = "420";
    const tiles = L.tileLayer(atuais.current.tilesUrl, {
      maxZoom: 18,
      attribution: "Mapa de fundo © Esri",
    });
    tiles.on("tileerror", () => setTilesFalharam(true));
    tiles.on("tileload", () => setTilesFalharam(false));
    tiles.addTo(m);
    m.getContainer().setAttribute(
      "aria-label",
      "Mapa dos distritos sanitários do Recife. Use as setas para mover e as teclas + e - para aproximar ou afastar.",
    );

    // padrão de hachura para “sem dado”, desenhado no próprio SVG do Leaflet
    const renderizador = L.svg();
    m.addLayer(renderizador as unknown as L.Layer);
    const svg = (renderizador as unknown as { _container: SVGSVGElement })._container;
    const ns = "http://www.w3.org/2000/svg";
    const defs = document.createElementNS(ns, "defs");
    defs.innerHTML = `<pattern id="${HACHURA}" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="8" height="8" fill="#eef1f3"/><line x1="0" y1="0" x2="0" y2="8" stroke="#8fa0ab" stroke-width="3"/></pattern>`;
    svg.prepend(defs);

    const grupo = L.geoJSON(atuais.current.distritos, {
      // o renderizador SVG compartilhado guarda o padrão de hachura
      ...({ renderer: renderizador } as L.GeoJSONOptions),
      style: (f) => estilo(f as FeatureDistrito),
      onEachFeature: (f, camada) => {
        const feature = f as FeatureDistrito;
        const codigo = feature.properties.cdistscodi;
        const caminho = camada as L.Path;
        camadas.current.set(codigo, caminho);
        caminho.on("click", () => atuais.current.aoSelecionar(codigo));
        caminho.on("mouseover", () =>
          caminho.setStyle({
            weight: 3,
            color: "#0e2433",
            fillOpacity: Math.min(1, atuais.current.opacidade + 0.13),
          }),
        );
        caminho.on("mouseout", () => caminho.setStyle(estilo(feature)));
        caminho.bindTooltip("", { sticky: true });
        const centro = (camada as L.Polygon).getBounds().getCenter();
        marcadores.current.set(
          codigo,
          L.marker(centro, {
            interactive: false,
            keyboard: false,
            icon: L.divIcon({
              className: estilos.rotulo,
              html: escapar(feature.properties.nome_distrito),
              iconSize: [52, 18],
              iconAnchor: [26, 9],
            }),
          }),
        );
      },
    });
    grupoDistritos.current = grupo;
    rotulos.current = L.layerGroup().addTo(m);
    grupo.addTo(m);
    enquadrar([...camadas.current.keys()]);

    const listaCamadas = camadas.current;
    const listaMarcadores = marcadores.current;
    const observador = new ResizeObserver(() => m.invalidateSize({ pan: false }));
    observador.observe(caixa.current);
    return () => {
      observador.disconnect();
      m.remove();
      listaCamadas.clear();
      listaMarcadores.clear();
    };
  }, []);

  // faixas hídricas (chegam depois: 430 KB)
  useEffect(() => {
    const m = mapa.current;
    if (!m || !props.hidrografia) return;
    const faixas = L.geoJSON(props.hidrografia, {
      pane: "hidrografia",
      style: { color: "#1f6fb2", weight: 1, fillColor: "#4f8cc2", fillOpacity: 0.45, opacity: 0.9 },
      onEachFeature: (f, camada) => {
        const p = (f.properties ?? {}) as { nome?: string; bacia?: string };
        camada.bindTooltip(
          `<strong>${escapar(p.nome || "Recurso hídrico")}</strong><br>Bacia: ${escapar(
            p.bacia || "não informada",
          )}<br><small>Faixa marginal do recurso hídrico</small>`,
          { sticky: true },
        );
      },
    });
    grupoFaixas.current = faixas;
    if (atuais.current.mostrarFaixas) faixas.addTo(m);
    return () => {
      faixas.remove();
    };
  }, [props.hidrografia]);

  // estado → mapa
  useEffect(() => {
    const m = mapa.current;
    const grupo = grupoDistritos.current;
    if (!m || !grupo) return;
    rotulos.current?.clearLayers();
    camadas.current.forEach((camada, codigo) => {
      const feature = (camada as unknown as { feature: FeatureDistrito }).feature;
      if (props.visiveis.has(codigo)) {
        grupo.addLayer(camada);
        if (props.mostrarDistritos) rotulos.current?.addLayer(marcadores.current.get(codigo)!);
      } else grupo.removeLayer(camada);
      camada.setStyle(estilo(feature));
      camada.setTooltipContent(props.dica(feature));
    });
    if (props.mostrarDistritos) grupo.addTo(m);
    else m.removeLayer(grupo);
    const faixas = grupoFaixas.current;
    if (faixas) {
      if (props.mostrarFaixas) faixas.addTo(m);
      else m.removeLayer(faixas);
    }
  });

  // enquadrar o distrito escolhido (RF-07.5)
  useEffect(() => {
    const m = mapa.current;
    const camada = props.selecionado ? camadas.current.get(props.selecionado) : null;
    if (m && camada)
      m.fitBounds((camada as L.Polygon).getBounds(), {
        padding: [45, 45],
        maxZoom: 14,
        animate: !semMovimento(),
      });
  }, [props.selecionado]);

  return (
    <div className={estilos.moldura}>
      <div ref={caixa} className={estilos.mapa} data-testid="mapa-leaflet" />
      {tilesFalharam && (
        <p className={estilos.avisoTiles} role="status">
          O mapa de ruas não carregou. Os distritos e as faixas hídricas continuam navegáveis.
        </p>
      )}
    </div>
  );
});
