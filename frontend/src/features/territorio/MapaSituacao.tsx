import { useMemo, useState } from "react";
import { token, useTemaAtual } from "@/charts/tema";
import { Dialogo } from "@/design-system/componentes/Dialogo";
import { Esqueleto } from "@/design-system/componentes/Esqueleto";
import { FalhaCarga } from "@/design-system/componentes/Painel";
import { useConsulta } from "@/lib/consultas";
import { useSessao } from "@/lib/sessao";
import { makeScale } from "@/map/model";
import { MapaTerritorio, type ColecaoDistritos, type FeatureDistrito } from "@/map/MapaTerritorio";
import { distritoPorExtenso } from "@/textos/glossario";
import { infoEstagio } from "@/features/evento/estagios";
import type { ItemEstagio } from "@/features/evento/tipos";
import { ROTULO_ESTAGIO, TOKEN_ESTAGIO } from "./indicadoresMapa";
import { LegendaMapa } from "./LegendaMapa";
import estilos from "./Mapa.module.css";

/** Ordem 0 a 3 da situação em vigor no distrito (declarada; sem declaração, a sugerida). `null` = sem dado. */
function ordemEmVigor(i: ItemEstagio | undefined): number | null {
  if (!i) return null;
  const o = infoEstagio(i.declarado?.estagio ?? i.sugerido?.estagio).ordem;
  return o < 0 ? null : o;
}

/**
 * Mapa dos 8 distritos colorido pela situação, em tamanho moderado, para a tela Situação. Clicar num distrito chama
 * `aoEscolher` com o id (`ds-5`): a tela abre os bairros dele na tabela.
 */
export function MapaSituacao({
  distritos,
  selecionado,
  aoEscolher,
}: {
  distritos: ItemEstagio[];
  selecionado: string | null;
  aoEscolher: (id: string) => void;
}) {
  const { usuario } = useSessao();
  useTemaAtual(); // as cores vêm dos tokens: redesenha ao trocar claro/escuro
  const geo = useConsulta<ColecaoDistritos>("/territorios/distritos.geojson", { staleTime: 30 * 60_000 });
  const agua = useConsulta<GeoJSON.FeatureCollection>("/territorios/hidrografia.geojson", {
    staleTime: 30 * 60_000,
  });
  const [sobre, setSobre] = useState(false);
  const porCodigo = useMemo(
    () => new Map(distritos.map((d) => [Number(d.territorio_id.replace(/\D/g, "")), d] as const)),
    [distritos],
  );
  const codigos = useMemo(
    () => new Set((geo.data?.features ?? []).map((f) => f.properties.cdistscodi)),
    [geo.data],
  );
  const valor = (f: FeatureDistrito) => ordemEmVigor(porCodigo.get(f.properties.cdistscodi));
  const escala = useMemo(() => makeScale([]), []);

  if (geo.isPending)
    return (
      <div className={estilos.cartao} aria-busy="true">
        <Esqueleto forma="bloco" altura="100%" className={estilos.esqueleto} />
        <span className="so-leitor" role="status">
          Carregando o mapa…
        </span>
      </div>
    );
  if (geo.isError) return <FalhaCarga erro={geo.error} aoTentar={() => geo.refetch()} />;

  const features = geo.data.features ?? [];
  return (
    <section className={estilos.cartao} aria-label="Mapa da situação por distrito">
      <MapaTerritorio
        distritos={geo.data}
        hidrografia={agua.data}
        tilesUrl={usuario?.mapa_tiles_url ?? ""}
        cor={(f) => {
          const v = valor(f);
          return v === null ? "hachura" : token(TOKEN_ESTAGIO[v]);
        }}
        dica={(f) => {
          const v = valor(f);
          return `<strong>${distritoPorExtenso(`ds-${f.properties.cdistscodi}`)}</strong><br>${
            v === null ? "sem dado" : ROTULO_ESTAGIO[v]
          }<br><small>Clique para ver os bairros</small>`;
        }}
        visiveis={codigos}
        selecionado={selecionado ? Number(selecionado.replace(/\D/g, "")) || null : null}
        mostrarDistritos
        mostrarFaixas
        opacidade={0.85}
        aoSelecionar={(c) => aoEscolher(`ds-${c}`)}
      />
      <LegendaMapa
        indicador="estagio"
        escala={escala}
        temSemDado={features.some((f) => valor(f) === null)}
        mostrarFaixas
        fontes={[{ nome: "Situações do ClimaSense (declaração da equipe e sugestão do sistema)" }]}
        aoAbrirSobre={() => setSobre(true)}
      />
      <SobreDados aberto={sobre} aoMudar={setSobre} />
    </section>
  );
}

function SobreDados({ aberto, aoMudar }: { aberto: boolean; aoMudar: (a: boolean) => void }) {
  return (
    <Dialogo aberto={aberto} aoMudar={aoMudar} titulo="Sobre os dados do mapa">
      <div className={estilos.sobre}>
        <p>
          A cor é a situação declarada pela equipe. Sem declaração, o mapa mostra a situação sugerida pelo
          sistema. Distrito riscado está sem dados para sugerir: não quer dizer risco baixo.
        </p>
        <h3>Faixas hídricas</h3>
        <p>A camada azul mostra as faixas marginais dos rios e canais, não só o leito.</p>
        <h3>Distritos VII e VIII</h3>
        <p>
          O arquivo oficial de bairros traz vínculos divergentes para esses dois distritos. Foi usada a
          relação da Secretaria de Saúde: 13 bairros no Distrito Sanitário VII e 3 no VIII (Cohab, Ibura e
          Jordão).
        </p>
        <p>
          <a
            href="https://dados.recife.pe.gov.br/dataset/distritos-sanitarios"
            target="_blank"
            rel="noopener noreferrer"
          >
            Distritos e bairros nos Dados Abertos do Recife
            <span className="so-leitor"> (abre em nova aba)</span>
          </a>
        </p>
      </div>
    </Dialogo>
  );
}
