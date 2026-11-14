import { useCallback, useEffect, useMemo, useState } from "react";
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
import { EvidenciasImpacto } from "./EvidenciasImpacto";
import {
  ROTULO_CLASSE,
  ROTULOS_ML,
  TOKENS_ML,
  VISOES,
  classeDoItem,
  ordemMlAlagamento,
  ordemDaClasse,
  type ItemSimulado,
  type ResultadoSimulacao,
  type Visao,
} from "./tipos";
import estilos from "./Simulador.module.css";

const ROTULO_MAPA =
  "Mapa dos bairros do Recife coloridos pelo risco simulado. Use as setas para mover e as teclas + e - para aproximar. Para escolher um bairro sem o mapa, use a lista Bairros mais afetados.";
type VisaoMapa = Visao | "ml" | "preventiva";
const ROTULO_VISAO: Record<VisaoMapa, string> = {
  situacao: "Estágio",
  alagamento: "Alagamento",
  deslizamento: "Deslizamento",
  ml: "ML de alagamento",
  preventiva: "Atenção preventiva",
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

function Legenda({ visao }: { visao: VisaoMapa }) {
  useTemaAtual();
  return (
    <ul className={estilos.legendaMapa} aria-label={`Legenda: ${ROTULO_VISAO[visao]}`}>
      {visao === "ml"
        ? [2, 1, 0].map((o) => (
            <li key={o}>
              <i style={{ background: token(TOKENS_ML[o]) }} aria-hidden="true" />
              {ROTULOS_ML[o]} (ML)
            </li>
          ))
        : [3, 2, 1, 0].map((o) => (
            <li key={o}>
              <i style={{ background: token(TOKEN_ESTAGIO[o]) }} aria-hidden="true" />
              {visao === "preventiva" && o === 0 ? "Limite não atingido no período" : ROTULO_CLASSE[o]}
            </li>
          ))}
      <li>
        <i className={estilos.semDado} aria-hidden="true" />
        Dados insuficientes
      </li>
    </ul>
  );
}

function Escolhido({ item, aviso, ml }: { item: ItemSimulado; aviso: string | null; ml: boolean }) {
  const motivos = item.motivos ?? [];
  return (
    <div className={estilos.bairroEscolhido} data-testid="bairro-escolhido">
      <h3>
        {item.nome} <small>· {distritoDe(item)}</small>
      </h3>
      {item.sinalizacao_preventiva && (
        <p>
          Sinalização interna de chuva:{" "}
          {item.sinalizacao_preventiva === "observacao"
            ? "limite não atingido no período disponível"
            : item.sinalizacao_preventiva.replace("sem_dados", "dados insuficientes")}
          . Não é alerta oficial nem confirmação de impacto.
        </p>
      )}
      {ml && (
        <p role="status">
          <b>Classificação do ML:</b>{" "}
          {ordemMlAlagamento(item) === null
            ? "Dados insuficientes para este bairro"
            : ROTULOS_ML[ordemMlAlagamento(item)!]}
          {ordemMlAlagamento(item) !== null &&
            `. Confiança: ${item.ml_alagamento?.confianca ?? "não informada"}.`}{" "}
          Estimativa experimental, não é estágio oficial.
        </p>
      )}
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
      <EvidenciasImpacto item={item} />
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
  contexto = "manual",
  mlAlagamento,
  previaLocal = false,
  preventiva = false,
}: {
  bairros: ItemSimulado[];
  aviso: string | null;
  selecionado: string | null;
  aoSelecionar: (id: string | null) => void;
  contexto?: "manual" | "atual";
  mlAlagamento?: ResultadoSimulacao["ml_alagamento"];
  previaLocal?: boolean;
  preventiva?: boolean;
}) {
  const { usuario } = useSessao();
  const geoBairros = useConsulta<ColecaoFeicoes>("/territorios/bairros.geojson", { staleTime: 30 * 60_000 });
  const geoDistritos = useConsulta<ColecaoDistritos>("/territorios/distritos.geojson", {
    staleTime: 30 * 60_000,
  });
  const [visao, setVisao] = useState<VisaoMapa>("situacao");
  useEffect(() => {
    if (preventiva) setVisao("preventiva");
  }, [preventiva]);
  useEffect(() => {
    if (previaLocal && !preventiva) setVisao("ml");
  }, [previaLocal, preventiva]);
  useEffect(() => {
    if ((contexto === "manual" && visao === "ml") || (!preventiva && visao === "preventiva"))
      setVisao("situacao");
  }, [contexto, visao, preventiva]);
  const visaoAtual: VisaoMapa =
    (contexto === "manual" && visao === "ml") || (!preventiva && visao === "preventiva") ? "situacao" : visao;
  const mapaMl = contexto === "atual" && visaoAtual === "ml";
  const ordem = useCallback(
    (item: ItemSimulado | undefined) =>
      visaoAtual === "preventiva"
        ? ordemDaClasse(item?.sinalizacao_preventiva)
        : classeDoItem(item, visaoAtual as Visao),
    [visaoAtual],
  );
  const mlDisponivel = mlAlagamento?.disponivel === true;

  const porId = useMemo(() => new Map(bairros.map((i) => [i.territorio_id, i] as const)), [bairros]);
  const aparencia = useCallback(
    (id: string): Aparencia => {
      const valor = mapaMl ? null : ordem(porId.get(id));
      return { ordem: valor, origem: valor === null ? "sem_dados" : "declarado" };
    },
    [porId, ordem, mapaMl],
  );
  const dica = useCallback(
    (id: string, nome: string) => {
      const o = mapaMl ? ordemMlAlagamento(porId.get(id)) : ordem(porId.get(id));
      const rotulo = mapaMl
        ? !mlDisponivel
          ? "ML indisponível"
          : o === null
            ? "Dados insuficientes (ML)"
            : `${ROTULOS_ML[o]} (ML experimental)`
        : o === null
          ? "Dados insuficientes"
          : visaoAtual === "preventiva" && o === 0
            ? "Limite não atingido no período"
            : ROTULO_CLASSE[o];
      return `<strong>${nome.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]!)}</strong><br>${rotulo}`;
    },
    [porId, visaoAtual, ordem, mapaMl, mlDisponivel],
  );
  const lista = useMemo(() => {
    if (visaoAtual === "preventiva")
      return [...bairros]
        .filter((b) => (ordem(b) ?? -1) >= 1)
        .sort(
          (a, b) =>
            (ordem(b) ?? -1) - (ordem(a) ?? -1) ||
            pessoas(b) - pessoas(a) ||
            a.nome.localeCompare(b.nome, "pt-BR"),
        );
    if (!mapaMl) return maisAfetados(bairros);
    if (!mlDisponivel) return [];
    return bairros
      .filter((b) => ordemMlAlagamento(b) !== null)
      .sort(
        (a, b) =>
          (ordemMlAlagamento(b) ?? -1) - (ordemMlAlagamento(a) ?? -1) ||
          pessoas(b) - pessoas(a) ||
          a.nome.localeCompare(b.nome, "pt-BR"),
      )
      .slice(0, 10);
  }, [bairros, mapaMl, mlDisponivel, ordem, visaoAtual]);
  const item = selecionado ? porId.get(selecionado) : undefined;

  return (
    <section className={estilos.painelBloco} aria-labelledby="sim-mapa">
      <div className={estilos.painelTopo}>
        <h2 id="sim-mapa">
          {mapaMl
            ? "Bairros classificados pelo ML"
            : visaoAtual === "preventiva"
              ? "Territórios em atenção preventiva"
              : "Quais áreas são afetadas"}
        </h2>
        <Experimental />
      </div>
      <Segmentado
        rotulo="Ver"
        opcoes={[
          ...VISOES.map((v) => ({ valor: v.valor as VisaoMapa, rotulo: ROTULO_VISAO[v.valor] })),
          ...(contexto === "atual" ? [{ valor: "ml" as VisaoMapa, rotulo: ROTULO_VISAO.ml }] : []),
          ...(preventiva ? [{ valor: "preventiva" as VisaoMapa, rotulo: ROTULO_VISAO.preventiva }] : []),
        ]}
        valor={visaoAtual}
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
            rotulo={
              mapaMl
                ? "Mapa experimental dos bairros do Recife classificados pelo modelo de alagamento. Sem dados não significa risco baixo."
                : visaoAtual === "preventiva"
                  ? "Mapa da sinalização interna de chuva no dia selecionado, com bairros herdando os limites do distrito. Não é alerta oficial; dados ausentes não significam segurança."
                  : contexto === "atual"
                    ? ROTULO_MAPA.replace("risco simulado", "avaliação experimental da previsão atual")
                    : ROTULO_MAPA
            }
            aparencia={aparencia}
            dica={dica}
            modoCor={mapaMl ? "valor" : undefined}
            valorPorBairro={
              mapaMl ? (id) => (mlDisponivel ? ordemMlAlagamento(porId.get(id)) : null) : undefined
            }
            tokensValor={mapaMl ? [...TOKENS_ML] : undefined}
            selecionado={selecionado}
            aoSelecionar={aoSelecionar}
            tokensEstagio={TOKEN_ESTAGIO}
          />
        )}
      </div>
      <Legenda visao={visaoAtual} />
      <p className={estilos.apoio} role={mapaMl ? "status" : undefined}>
        {mapaMl
          ? mlDisponivel
            ? `Camada experimental do modelo ${mlAlagamento?.modelo?.versao ?? "sem versão"}. ${previaLocal ? "PRÉVIA ACADÊMICA NÃO VALIDADA PARA USO OPERACIONAL. " : ""}Os resultados não são alertas oficiais e não substituem a avaliação por regras.`
            : `Não há previsão de ML validada para mapear. ${mlAlagamento?.motivo ?? "Aguardando modelo e validação."} Consulte as camadas por regras.`
          : visaoAtual === "preventiva"
            ? "Sinalização interna para o dia selecionado: os bairros herdam o limiar meteorológico do distrito. Não é alerta oficial; a avaliação territorial por regras pode ter dados insuficientes."
            : contexto === "atual"
              ? "Cor cheia é a avaliação experimental da previsão de cada distrito."
              : "Cor cheia é o risco simulado de cada bairro."}{" "}
        Cinza listrado é falta de dado, não risco baixo.
      </p>

      {item ? (
        <Escolhido item={item} aviso={aviso} ml={mapaMl && mlDisponivel} />
      ) : (
        <p className={estilos.apoio}>
          Toque num bairro, no mapa ou na lista, para ver por que e quem mora ali.
        </p>
      )}

      <div>
        <h3>
          {mapaMl
            ? "Bairros sinalizados pelo ML"
            : visaoAtual === "preventiva"
              ? "Bairros em atenção preventiva"
              : "Bairros mais afetados"}
        </h3>
        {lista.length === 0 ? (
          <p className={estilos.apoio}>
            {mapaMl
              ? mlDisponivel
                ? "O modelo não retornou classes válidas para os bairros. Verifique os insumos de cada distrito."
                : "Ainda não há resultados de ML liberados pela validação para esta camada."
              : visaoAtual === "preventiva"
                ? "Nenhuma ultrapassagem confirmada nos dados disponíveis. Confira cobertura e dados ausentes; isso não significa ausência de risco."
                : "Os bairros aparecem aqui quando o cenário for calculado."}
          </p>
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
                    {mapaMl ? (
                      <b>{ROTULOS_ML[ordemMlAlagamento(b)!]} (ML)</b>
                    ) : visaoAtual === "preventiva" ? (
                      <b>{ROTULO_CLASSE[ordem(b)!]} (preventiva)</b>
                    ) : (
                      <SeloEstagio estagio={b.estagio_sugerido} pequena />
                    )}
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
