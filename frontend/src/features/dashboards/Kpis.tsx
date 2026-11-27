/**
 * Fileira de quatro indicadores: situação agora (destacado, na cor da marca), decisões pendentes, quanto falta para o
 * próximo estágio e maior chuva. Cada cartão tem ícone, rótulo curto, número grande, um chip e um mini gráfico, e uma
 * linha de fonte e hora (RF-19). Sem dado: "Dados insuficientes" e a fonte que falta, nunca zero (RN-01).
 */
import type { CSSProperties, ReactNode } from "react";
import { ClipboardCheck, Clock, CloudRain, Gauge, Radio } from "lucide-react";
import { Esqueleto } from "@/design-system/componentes/Esqueleto";
import { infoEstagio } from "@/features/evento/estagios";
import { quandoAs } from "@/features/evento/textos";
import { desembrulhar } from "@/features/evento/tipos";
import { nomeDaFonte, type EstagioOficial } from "@/features/mapa/tipos";
import { ErroApi } from "@/lib/api";
import { formatarHoraMinuto, formatarNumero } from "@/lib/formatos";
import type { FonteMeta } from "@/lib/frescor";
import { GraficoPainel, SeloExp } from "./CartaoPainel";
import { graficoMini } from "./graficos";
import { LEITURA_GATILHO, ROTULO_INSUMO, maiorSugerido, serieHoraria, type Janela } from "./indicadores";
import type { DadosDecisao } from "./usarDadosDecisao";
import estilos from "./Painel.module.css";

const mm = (v: number) => formatarNumero(v, v < 10 && !Number.isInteger(v) ? 1 : 0);
const CURTO: Record<string, string> = {
  "apac-chuva": "APAC",
  "open-meteo-previsao": "Open-Meteo",
  "open-meteo-mare": "Open-Meteo",
  "ibge-censo-2022-bairro": "IBGE 2022",
  "cnes-equipamentos": "CNES",
};

export function curto(x: FonteMeta): string {
  if (CURTO[x.id]) return CURTO[x.id];
  if (x.id.includes("infodengue")) return "InfoDengue";
  if (x.id.includes("sinan")) return "SINAN";
  return x.nome;
}

/** "APAC 01:13": nome curto e hora da última atualização da fonte, com um relógio se estiver vencida (RF-19). */
export function RodapeFonte({
  ids,
  padrao,
  consultadoEm,
  fontes,
}: {
  ids: string[];
  /** Nome curto quando a resposta não traz a fonte (cálculo do próprio ClimaSense). */
  padrao: string;
  consultadoEm: number;
  fontes: FonteMeta[];
}) {
  const unicas = new Map<string, FonteMeta>();
  for (const f of fontes.filter((x) => ids.includes(x.id)))
    if (!unicas.has(curto(f))) unicas.set(curto(f), f);
  if (unicas.size === 0)
    return (
      <>
        {padrao}
        {consultadoEm ? ` ${formatarHoraMinuto(consultadoEm)}` : ""}
      </>
    );
  return (
    <>
      {[...unicas.values()].map((x, i) => (
        <span key={x.id}>
          {i > 0 && " · "}
          {curto(x)}
          {x.atualizado_em ? ` ${formatarHoraMinuto(x.atualizado_em)}` : " sem hora"}
          {x.desatualizado === true && (
            <span className={estilos.vencida} title="Desatualizado">
              <Clock aria-hidden="true" size={14} />
              <span className="so-leitor"> (desatualizado)</span>
            </span>
          )}
        </span>
      ))}
    </>
  );
}

function Kpi({
  icone,
  cor,
  rotulo,
  destaque,
  experimental,
  carregando,
  insuficiente,
  rodape,
  esmaecido,
  children,
}: {
  icone: ReactNode;
  /** Variável de cor do design system, ex.: "--n-alerta". */
  cor: string;
  rotulo: string;
  /** O primeiro cartão vai cheio, na cor da marca. */
  destaque?: boolean;
  experimental?: boolean;
  carregando: boolean;
  insuficiente: string | null;
  rodape: ReactNode;
  esmaecido?: boolean;
  children: ReactNode;
}) {
  return (
    <li
      className={estilos.kpi}
      data-destaque={destaque ? "true" : undefined}
      style={{ "--cor": `var(${cor})` } as CSSProperties}
      data-esmaecido={esmaecido ? "true" : undefined}
    >
      <div className={estilos.kpiTopo}>
        <span className={estilos.icone} aria-hidden="true">
          {icone}
        </span>
        <h3>{rotulo}</h3>
      </div>
      {carregando ? (
        <div role="status" aria-busy="true">
          <Esqueleto largura="6rem" altura="1.6rem" forma="bloco" />
          <span className="so-leitor">Carregando {rotulo}…</span>
        </div>
      ) : insuficiente ? (
        <div className={estilos.kpiCorpo}>
          <div>
            <p className={estilos.kpiSemDado}>Dados insuficientes</p>
            <p className={estilos.kpiApoio}>Falta: {insuficiente}</p>
          </div>
        </div>
      ) : (
        children
      )}
      <div className={estilos.kpiRodape}>
        <span>{rodape}</span>
        {experimental && <SeloExp />}
      </div>
    </li>
  );
}

export function KpisPainel({
  d,
  janela,
  agora,
  esmaecer,
  acaoCop,
  compacto,
}: {
  d: DadosDecisao;
  janela: Janela;
  agora: Date;
  /** Ids dos KPIs que o filtro "Foco" deixa em segundo plano. */
  esmaecer: Set<string>;
  /** Botão "Informar estágio" do COP, dentro do cartão Situação agora (no Mapa). */
  acaoCop?: ReactNode;
  /** Versão baixa, para o topo do Mapa: sem a leitura histórica nem os mini gráficos. */
  compacto?: boolean;
}) {
  const oficial = desembrulhar<EstagioOficial | null>(d.oficial.data) ?? null;
  const definido = oficial?.estagio ? oficial : null;
  const indisponivel =
    d.oficial.isError && d.oficial.error instanceof ErroApi && d.oficial.error.status === 404;
  const { pendencias: p, gatilhos: g, maior } = d;
  const topo = g?.itens[0];
  const semEstagios = !p || p.avaliados === 0 || p.semDados === p.avaliados;
  const serie = serieHoraria(d.chuva, janela, agora, null);
  const sugerido = maiorSugerido([...d.itensDistrito, ...d.itensBairro]);
  const porEstagio = ["critico", "alerta", "atencao"]
    .map((e) => ({ e, n: p?.itens.filter((x) => x.sugerido === e).length ?? 0 }))
    .filter((x) => x.n > 0);
  const maxBarra = Math.max(...porEstagio.map((x) => x.n), 1);

  return (
    <ul
      className={estilos.kpis}
      aria-label="Números principais"
      data-compacto={compacto ? "true" : undefined}
    >
      <Kpi
        destaque
        icone={<Radio />}
        cor="--cs-mare"
        rotulo="Situação agora"
        carregando={d.oficial.isPending}
        insuficiente={null}
        rodape={
          definido
            ? `${nomeDaFonte(definido.fonte).replace(/ \(.*\)/, "")}${definido.informado_em ? ` · ${quandoAs(definido.informado_em, agora)}` : ""}`
            : "Estágio do COP: registro da equipe"
        }
      >
        <div className={estilos.kpiCorpo}>
          <div>
            {definido ? (
              <p className={estilos.kpiValor}>{infoEstagio(definido.estagio).rotulo}</p>
            ) : (
              <>
                <p className={estilos.kpiSemDado}>Dados insuficientes</p>
                <p className={estilos.kpiApoio}>
                  Falta:{" "}
                  {indisponivel
                    ? "COP (ainda não disponível)"
                    : d.oficial.isError
                      ? "COP (falha ao carregar)"
                      : "estágio do COP"}
                </p>
              </>
            )}
            <p className={estilos.kpiChip}>
              {sugerido
                ? `Sistema sugere ${infoEstagio(sugerido).rotulo}`
                : "Sistema sem sugestão: dados insuficientes"}
            </p>
            {acaoCop}
          </div>
        </div>
      </Kpi>

      <Kpi
        icone={<ClipboardCheck />}
        cor="--n-alerta"
        rotulo="Decisões pendentes"
        experimental
        esmaecido={esmaecer.has("pendentes")}
        carregando={d.distritos.isPending && d.bairros.isPending}
        insuficiente={
          d.distritos.isError && d.bairros.isError
            ? "estágios sugeridos"
            : semEstagios
              ? "previsão de chuva e maré"
              : null
        }
        rodape={
          <RodapeFonte
            ids={[]}
            padrao="ClimaSense"
            consultadoEm={d.bairros.dataUpdatedAt || d.distritos.dataUpdatedAt}
            fontes={d.fontes}
          />
        }
      >
        {p && (
          <div className={estilos.kpiCorpo}>
            <div>
              <p className={estilos.kpiValor}>
                {p.total}
                <small>
                  {p.itens[0]?.nivel === "distrito"
                    ? p.total === 1
                      ? "distrito"
                      : "distritos"
                    : p.total === 1
                      ? "bairro"
                      : "bairros"}
                </small>
              </p>
              <p className={estilos.kpiChip} data-tom={p.total > 0 ? "alerta" : undefined}>
                {p.total === 0 ? "Nada acima do declarado" : "Sugestão acima do declarado"}
                {p.semDados > 0 ? ` · ${p.semDados} sem dados` : ""}
              </p>
            </div>
            {porEstagio.length > 0 && (
              <div
                className={estilos.miniBarras}
                role="img"
                aria-label={porEstagio.map((x) => `${x.n} em ${infoEstagio(x.e).rotulo}`).join(", ")}
              >
                {porEstagio.map((x) => (
                  <span
                    key={x.e}
                    data-estagio={x.e}
                    style={{ height: `${Math.max(25, (x.n / maxBarra) * 100)}%` }}
                  >
                    <b>{x.n}</b>
                  </span>
                ))}
              </div>
            )}
          </div>
        )}
      </Kpi>

      <Kpi
        icone={<Gauge />}
        cor="--n-atencao"
        rotulo={`Falta para ${topo ? infoEstagio(topo.proximo).rotulo : "Atenção"}`}
        experimental
        esmaecido={esmaecer.has("gatilho")}
        carregando={d.distritos.isPending}
        insuficiente={!g || (!topo && g.noTopo === 0) ? "previsão de chuva por distrito" : null}
        rodape={
          <RodapeFonte
            ids={topo?.insumo === "chuva_24h_mm" ? ["apac-chuva"] : ["open-meteo-previsao"]}
            padrao="Limiares"
            consultadoEm={d.distritos.dataUpdatedAt}
            fontes={d.fontes}
          />
        }
      >
        {topo ? (
          <div className={estilos.kpiCorpo} data-coluna="true">
            <div>
              <p className={estilos.kpiValor}>
                {mm(topo.falta)}
                <small>mm</small>
              </p>
              <p className={estilos.kpiChip} data-tom="atencao">
                {topo.nome} · {ROTULO_INSUMO[topo.insumo].replace("chuva ", "")}
              </p>
            </div>
            <div
              className={estilos.progresso}
              role="img"
              aria-label={`${mm(topo.atual)} de ${mm(topo.limiar)} mm do limiar de ${infoEstagio(topo.proximo).rotulo}`}
            >
              <i style={{ width: `${Math.max(2, Math.min(100, (topo.atual / topo.limiar) * 100))}%` }} />
            </div>
            <p className={estilos.kpiHistorico} title={`${LEITURA_GATILHO.curta} ${LEITURA_GATILHO.fonte}.`}>
              {LEITURA_GATILHO.curta} <small>Histórico {LEITURA_GATILHO.fonte}.</small>
            </p>
          </div>
        ) : (
          <p className={estilos.kpiApoio}>Todos já no estágio mais alto</p>
        )}
      </Kpi>

      <Kpi
        icone={<CloudRain />}
        cor="--g-1"
        rotulo={`Maior chuva em ${janela} h`}
        esmaecido={esmaecer.has("chuva")}
        carregando={d.situacao.isPending}
        insuficiente={maior ? null : "pluviômetros (APAC)"}
        rodape={
          <RodapeFonte
            ids={["apac-chuva"]}
            padrao="APAC"
            consultadoEm={d.situacao.dataUpdatedAt}
            fontes={d.fontes}
          />
        }
      >
        <div className={estilos.kpiCorpo}>
          <div>
            <p className={estilos.kpiValor}>
              {maior ? mm(maior.mm) : ""}
              <small>mm</small>
            </p>
            <p className={estilos.kpiChip} data-tom="info">
              {maior?.nome}
              {maior?.estacoes ? ` · ${maior.estacoes}` : ""}
            </p>
          </div>
          {serie && (
            <div className={estilos.kpiMini}>
              <GraficoPainel
                opcao={graficoMini(serie)}
                rotulo={`Chuva medida por hora nas últimas ${janela} h, maior pluviômetro`}
                resumo="uma barra por hora, hora sem leitura fica vazia"
              />
            </div>
          )}
        </div>
      </Kpi>
    </ul>
  );
}
