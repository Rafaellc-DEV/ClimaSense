import { useCallback, useMemo, useState } from "react";
import { token, useTemaAtual } from "@/charts/tema";
import { CarregandoLista } from "@/design-system/componentes/Esqueleto";
import { FalhaCarga } from "@/design-system/componentes/Painel";
import { Experimental } from "@/design-system/componentes/Pilula";
import { Segmentado } from "@/design-system/componentes/Segmentado";
import { SeloEstagio } from "@/features/evento/Evento";
import { TOKEN_ESTAGIO } from "@/features/territorio/indicadoresMapa";
import { impactoDe } from "@/features/mapa/modeloCamadas";
import { useConsulta } from "@/lib/consultas";
import { nomeDistrito } from "@/lib/distritos";
import { formatarNumero } from "@/lib/formatos";
import { useSessao } from "@/lib/sessao";
import { distritoPorExtenso } from "@/textos/glossario";
import { MapaBairros, type Aparencia, type ColecaoFeicoes } from "@/map/MapaBairros";
import type { ColecaoDistritos } from "@/map/MapaTerritorio";
import { ClasseAlagamento, PessoasExpostas } from "./EstagioPorDistrito";
import { ROTULO_CLASSE, VISOES, classeDoItem, type ItemSimulado, type Visao } from "./tipos";
import estilos from "./Simulador.module.css";

const ROTULO_MAPA =
  "Mapa dos bairros do Recife coloridos pelo risco simulado. Use as setas para mover e as teclas + e - para aproximar. Para escolher um bairro sem o mapa, use a lista Bairros mais afetados.";
const ROTULO_VISAO: Record<Visao, string> = {
  situacao: "Estágio",
  alagamento: "Alagamento",
  deslizamento: "Deslizamento",
};

const distritoDe = (i: ItemSimulado) =>
  i.distrito_id ? nomeDistrito(distritoPorExtenso(i.distrito_id)) : "Distrito não informado";

function pessoas(i: ItemSimulado): number {
  const p = impactoDe(i.impacto_pessoas);
  if (!p) return -1;
  return (p.idosos_60_mais ?? 0) + (p.criancas_0_14 ?? 0);
}

/** Os 10 primeiros por estágio sugerido e, no empate, por moradores idosos e crianças. Sem dado vai para o fim. */
export function maisAfetados(bairros: ItemSimulado[], limite = 10): ItemSimulado[] {
  return [...bairros]
    .sort(
      (a, b) =>
        (classeDoItem(b, "situacao") ?? -1) - (classeDoItem(a, "situacao") ?? -1) ||
        pessoas(b) - pessoas(a) ||
        a.nome.localeCompare(b.nome, "pt-BR"),
    )
    .slice(0, limite);
}

function Legenda({ visao }: { visao: Visao }) {
  useTemaAtual();
  return (
    <ul className={estilos.legendaMapa} aria-label={`Legenda: ${ROTULO_VISAO[visao]}`}>
      {[3, 2, 1, 0].map((o) => (
        <li key={o}>
          <i style={{ background: token(TOKEN_ESTAGIO[o]) }} aria-hidden="true" />
          {ROTULO_CLASSE[o]}
        </li>
      ))}
      <li>
        <i className={estilos.semDado} aria-hidden="true" />
        Dados insuficientes
      </li>
    </ul>
  );
}

function Escolhido({ item, aviso }: { item: ItemSimulado; aviso: string | null }) {
  const motivos = item.motivos ?? [];
  return (
    <div className={estilos.bairroEscolhido} data-testid="bairro-escolhido">
      <h3>
        {item.nome} <small>· {distritoDe(item)}</small>
      </h3>
      <p className={estilos.selosBairro}>
        <SeloEstagio estagio={item.estagio_sugerido} pequena />
        <span>Alagamento:</span> <ClasseAlagamento classe={item.classe_alagamento} />
        <span>Deslizamento:</span> <ClasseAlagamento classe={item.classe_deslizamento} />
      </p>
      <div className={estilos.detalheGrade}>
        <div>
          <h4>Por que</h4>
          {motivos.length > 0 ? (
            <ul className={estilos.motivos}>
              {motivos.map((m) => (
                <li key={m}>{nomeDistrito(m)}</li>
              ))}
            </ul>
          ) : (
            <p className={estilos.apoio}>
              <b>Dados insuficientes:</b> o cálculo não trouxe motivo para este bairro.
            </p>
          )}
        </div>
        <div>
          <h4>Pessoas expostas</h4>
          <PessoasExpostas impacto={impactoDe(item.impacto_pessoas)} aviso={aviso} unidade="bairro" />
        </div>
      </div>
    </div>
  );
}

/**
 * Mapa dos bairros colorido pelo risco simulado: é a resposta a "quais áreas serão afetadas". Crítico é a cor cheia
 * mais escura; sem dado é cinza listrado (nunca "baixo", RN-01). A lista "Bairros mais afetados" foca o bairro no mapa.
 */
export function MapaDoCenario({
  bairros,
  aviso,
  selecionado,
  aoSelecionar,
}: {
  bairros: ItemSimulado[];
  aviso: string | null;
  selecionado: string | null;
  aoSelecionar: (id: string | null) => void;
}) {
  const { usuario } = useSessao();
  const geoBairros = useConsulta<ColecaoFeicoes>("/territorios/bairros.geojson", { staleTime: 30 * 60_000 });
  const geoDistritos = useConsulta<ColecaoDistritos>("/territorios/distritos.geojson", {
    staleTime: 30 * 60_000,
  });
  const [visao, setVisao] = useState<Visao>("situacao");
  const porId = useMemo(() => new Map(bairros.map((i) => [i.territorio_id, i] as const)), [bairros]);
  const aparencia = useCallback(
    (id: string): Aparencia => {
      const ordem = classeDoItem(porId.get(id), visao);
      return { ordem, origem: ordem === null ? "sem_dados" : "declarado" };
    },
    [porId, visao],
  );
  const dica = useCallback(
    (id: string, nome: string) => {
      const o = classeDoItem(porId.get(id), visao);
      return `<strong>${nome.replace(/</g, "&lt;")}</strong><br>${o === null ? "Dados insuficientes" : ROTULO_CLASSE[o]}`;
    },
    [porId, visao],
  );
  const lista = useMemo(() => maisAfetados(bairros), [bairros]);
  const item = selecionado ? porId.get(selecionado) : undefined;

  return (
    <section className={estilos.painelBloco} aria-labelledby="sim-mapa">
      <div className={estilos.painelTopo}>
        <h2 id="sim-mapa">Quais áreas são afetadas</h2>
        <Experimental />
      </div>
      <Segmentado
        rotulo="Ver"
        opcoes={VISOES.map((v) => ({ valor: v.valor, rotulo: ROTULO_VISAO[v.valor] }))}
        valor={visao}
        aoMudar={setVisao}
      />
      <div className={estilos.mapaBairros}>
        {geoBairros.isPending && <CarregandoLista linhas={1} altura="12rem" texto="Carregando o mapa…" />}
        {geoBairros.isError && (
          <FalhaCarga erro={geoBairros.error} aoTentar={() => void geoBairros.refetch()} />
        )}
        {geoBairros.data && (
          <MapaBairros
            territorios={geoBairros.data}
            contorno={geoDistritos.data}
            tilesUrl={usuario?.mapa_tiles_url ?? ""}
            rotulo={ROTULO_MAPA}
            aparencia={aparencia}
            dica={dica}
            selecionado={selecionado}
            aoSelecionar={aoSelecionar}
            tokensEstagio={TOKEN_ESTAGIO}
          />
        )}
      </div>
      <Legenda visao={visao} />
      <p className={estilos.apoio}>
        Cor cheia é o risco simulado de cada bairro. Cinza listrado é falta de dado, não risco baixo.
      </p>

      {item ? (
        <Escolhido item={item} aviso={aviso} />
      ) : (
        <p className={estilos.apoio}>
          Toque num bairro, no mapa ou na lista, para ver por que e quem mora ali.
        </p>
      )}

      <div>
        <h3>Bairros mais afetados</h3>
        {lista.length === 0 ? (
          <p className={estilos.apoio}>Os bairros aparecem aqui quando o cenário for calculado.</p>
        ) : (
          <ol className={estilos.maisAfetados}>
            {lista.map((b) => {
              const p = impactoDe(b.impacto_pessoas);
              const n = (v: number | null | undefined) => (v == null ? "sem dado" : formatarNumero(v));
              return (
                <li key={b.territorio_id}>
                  <button
                    type="button"
                    aria-pressed={selecionado === b.territorio_id}
                    onClick={() => aoSelecionar(b.territorio_id)}
                  >
                    <span className={estilos.nomeBairro}>
                      <b>{b.nome}</b>
                      <small>{distritoDe(b)}</small>
                    </span>
                    <SeloEstagio estagio={b.estagio_sugerido} pequena />
                    <span className={estilos.pessoasBairro}>
                      {p
                        ? `Idosos ${n(p.idosos_60_mais)} · crianças ${n(p.criancas_0_14)}`
                        : "Pessoas expostas: dados insuficientes"}
                    </span>
                  </button>
                </li>
              );
            })}
          </ol>
        )}
      </div>
    </section>
  );
}
