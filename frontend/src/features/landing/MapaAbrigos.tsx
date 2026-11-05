import { useEffect, useRef, useState } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { token } from "@/charts/tema";
import { abertoConfirmado, temCoordenada, type AbrigoPublico } from "./abrigosPublicos";
import estilos from "./MapaAbrigos.module.css";

/** Mesmo fundo do mapa da equipe (backend `map_tiles_url`), já liberado no CSP. */
const TILES =
  "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}";

/**
 * Mapa dos locais de abrigo (Leaflet). É apoio visual: a lista ao lado diz tudo em texto, então o mapa pode falhar
 * sem esconder informação. Aberto confirmado = disco cheio e maior; os outros, anel fino.
 */
export default function MapaAbrigos({
  itens,
  aoEscolher,
  destaque,
}: {
  itens: AbrigoPublico[];
  aoEscolher: (id: AbrigoPublico["id"]) => void;
  destaque?: AbrigoPublico["id"] | null;
}) {
  const caixa = useRef<HTMLDivElement>(null);
  const mapa = useRef<L.Map | null>(null);
  const camada = useRef<L.LayerGroup | null>(null);
  const [fundoFalhou, setFundoFalhou] = useState(false);
  // no toque, o mapa não captura a rolagem da página: a pessoa o ativa quando quer mexer nele
  const toque = typeof matchMedia === "function" && matchMedia("(pointer: coarse)").matches;
  const [ativo, setAtivo] = useState(!toque);

  useEffect(() => {
    if (!caixa.current) return;
    const m = L.map(caixa.current, {
      zoomControl: true,
      keyboard: true,
      scrollWheelZoom: false,
      dragging: !toque,
      touchZoom: !toque,
    });
    m.setView([-8.05, -34.92], 12);
    m.zoomControl.setPosition("bottomright");
    const tiles = L.tileLayer(TILES, { maxZoom: 18, attribution: "Mapa de fundo © Esri" });
    tiles.on("tileerror", () => setFundoFalhou(true));
    tiles.on("tileload", () => setFundoFalhou(false));
    tiles.addTo(m);
    m.getContainer().setAttribute(
      "aria-label",
      "Mapa dos locais de abrigo do Recife. A mesma informação está na lista abaixo do mapa.",
    );
    camada.current = L.layerGroup().addTo(m);
    mapa.current = m;
    // a aba só mostra o mapa depois de aberta: recalcula o tamanho quando o contêiner ganha largura
    const observador =
      typeof ResizeObserver === "function" ? new ResizeObserver(() => m.invalidateSize()) : null;
    observador?.observe(caixa.current);
    return () => {
      observador?.disconnect();
      m.remove();
      mapa.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const m = mapa.current;
    if (!m || !toque) return;
    if (ativo) {
      m.dragging.enable();
      m.touchZoom.enable();
    } else {
      m.dragging.disable();
      m.touchZoom.disable();
    }
  }, [ativo, toque]);

  useEffect(() => {
    const m = mapa.current;
    const g = camada.current;
    if (!m || !g) return;
    g.clearLayers();
    const comPonto = itens.filter(temCoordenada);
    const corAberto = token("--n-sem");
    const corLocal = token("--cs-mare");
    const corFoco = token("--cs-foco");
    for (const a of comPonto) {
      const aberto = abertoConfirmado(a);
      const marcado = a.id === destaque;
      const marca = L.circleMarker([a.latitude, a.longitude], {
        radius: marcado ? 12 : aberto ? 10 : 6,
        color: marcado ? corFoco : "#ffffff",
        weight: marcado ? 4 : 2,
        fillColor: aberto ? corAberto : corLocal,
        fillOpacity: aberto ? 1 : 0.75,
      });
      marca.bindTooltip(`${a.nome}${aberto ? " (aberto agora)" : ""}`);
      marca.on("click", () => aoEscolher(a.id));
      marca.addTo(g);
    }
  }, [itens, aoEscolher, destaque]);

  // o enquadramento só muda quando a lista muda, não quando a pessoa toca num marcador
  useEffect(() => {
    const m = mapa.current;
    const comPonto = itens.filter(temCoordenada);
    if (m && comPonto.length > 0)
      m.fitBounds(L.latLngBounds(comPonto.map((a) => [a.latitude, a.longitude])), {
        padding: [24, 24],
        maxZoom: 15,
      });
  }, [itens]);

  return (
    <div className={estilos.mapaCaixa}>
      <div ref={caixa} className={estilos.mapa} />
      {toque && (
        <button
          type="button"
          className={estilos.ativar}
          aria-pressed={ativo}
          onClick={() => setAtivo((v) => !v)}
        >
          {ativo ? "Desativar o mapa e voltar a rolar a página" : "Ativar o mapa para mexer nele"}
        </button>
      )}
      {fundoFalhou && (
        <p className={estilos.mapaAviso} role="status">
          O fundo do mapa não carregou. Os pontos e a lista continuam valendo.
        </p>
      )}
    </div>
  );
}
