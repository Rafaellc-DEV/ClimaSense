import { useEffect, useMemo, useState } from "react";
import type { EChartsOption } from "echarts";
import { Download } from "lucide-react";
import { CabecalhoTela } from "@/app/AppShell";
import { QuadroGrafico } from "@/charts/QuadroGrafico";
import { areaSemDado, estiloReferencia, token } from "@/charts/tema";
import { Botao } from "@/design-system/componentes/Botao";
import { EstadoDados, LegendaFonte } from "@/design-system/componentes/EstadoDados";
import { Carregando, FalhaCarga, Painel } from "@/design-system/componentes/Painel";
import { Selecao } from "@/design-system/componentes/Selecao";
import { consulta, type Esquemas } from "@/lib/api";
import { useConsulta } from "@/lib/consultas";
import { baixarCsv } from "@/lib/csv";
import { dataCurta, formatarMm, nomeMes } from "@/lib/formatos";
import { useRecorte } from "@/lib/recorte";
import { TIPOS_FONTE } from "@/textos/glossario";
import { Calendario } from "./Calendario";
import estilos from "./TelaSeries.module.css";

type Frequencia = "diaria" | "semanal" | "mensal";
const FREQUENCIAS: { valor: Frequencia; rotulo: string }[] = [
  { valor: "diaria", rotulo: "Diária" },
  { valor: "semanal", rotulo: "Semanal" },
  { valor: "mensal", rotulo: "Mensal" },
];
const VARIAVEIS = [
  { valor: "chuva_mm", rotulo: "Chuva" },
  { valor: "mare_m", rotulo: "Maré" },
  { valor: "nivel_m", rotulo: "Nível dos rios" },
  { valor: "temp_c", rotulo: "Temperatura" },
];

function rotuloPonto(t: string, f: Frequencia) {
  if (f === "mensal") return `${nomeMes(Number(t.slice(5, 7)), true)} ${t.slice(0, 4)}`;
  if (f === "semanal") return `sem. de ${dataCurta(t).slice(0, 5)}`;
  return dataCurta(t).slice(0, 5) + "/" + t.slice(2, 4);
}

/** Trechos consecutivos sem dado, para a faixa hachurada (RF-06.5, RN-02). */
function lacunas(rotulos: string[], valores: (number | null)[]) {
  const trechos: [string, string][] = [];
  let inicio: number | null = null;
  valores.forEach((v, i) => {
    if (v === null && inicio === null) inicio = i;
    if (v !== null && inicio !== null) {
      trechos.push([rotulos[inicio], rotulos[i - 1]]);
      inicio = null;
    }
  });
  if (inicio !== null) trechos.push([rotulos[inicio], rotulos[rotulos.length - 1]]);
  return trechos;
}

/** Séries e sazonalidade (design §9.6, RF-08). */
export function TelaSeries() {
  const { recorte } = useRecorte();
  const [variavel, setVariavel] = useState("chuva_mm");
  const [frequencia, setFrequencia] = useState<Frequencia>("diaria");
  const [comparar, setComparar] = useState("media");
  const filtro = { territorio_id: recorte.territorio, inicio: recorte.inicio, fim: recorte.fim };
  const serie = useConsulta<Esquemas["RespostaDados_SerieTemporal_"]>(
    `/series${consulta({ ...filtro, variavel, frequencia })}`,
  );
  const sazonal = useConsulta<Esquemas["RespostaDados_Sazonalidade_"]>(
    `/series/sazonalidade${consulta({ territorio_id: recorte.territorio })}`,
  );
  const estat = useConsulta<Esquemas["RespostaDados_Estatisticas_"]>(
    `/series/estatisticas${consulta({ ...filtro, frequencia })}`,
  );
  const referencia = useConsulta<Esquemas["RespostaDados_Referencia_"]>(
    `/series/referencia${consulta({ territorio_id: recorte.territorio })}`,
  );

  useEffect(() => {
    document.title = "Séries e sazonalidade | ClimaSense";
  }, []);

  const dados = serie.data?.dados;
  const meta = serie.data?.meta;
  const fonte = meta?.fontes[0];
  const comReferencia = frequencia === "mensal" && comparar === "media";

  const grafico = useMemo(() => {
    if (!dados) return null;
    const rotulos = dados.pontos.map((p) => rotuloPonto(p.t, frequencia));
    const valores = dados.pontos.map((p) => p.valor);
    const opcao: EChartsOption = {
      grid: { left: 56, right: 24, top: 40, bottom: 48, containLabel: true },
      tooltip: {
        trigger: "axis",
        valueFormatter: (v) => formatarMm(v as number | null),
      },
      legend: comReferencia ? { top: 0, left: 0 } : undefined,
      xAxis: {
        type: "category",
        data: rotulos,
        // no máximo uns 8 rótulos no eixo, para as datas não se sobreporem
        axisLabel: { interval: Math.max(0, Math.ceil(rotulos.length / 8) - 1), hideOverlap: true },
      },
      yAxis: { type: "value", name: "mm", nameLocation: "end", min: 0 },
      dataZoom:
        rotulos.length > 120 ? [{ type: "inside" }, { type: "slider", height: 24, bottom: 4 }] : undefined,
      series: [
        {
          name: "Chuva acumulada",
          type: "bar",
          data: valores,
          itemStyle: { color: token("--g-1"), borderRadius: [4, 4, 0, 0] },
          barMaxWidth: frequencia === "diaria" ? 10 : 28,
          markArea: lacunas(rotulos, valores).length
            ? {
                ...areaSemDado(lacunas(rotulos, valores)[0][0], lacunas(rotulos, valores)[0][1]),
                data: lacunas(rotulos, valores).map(([a, b]) => [{ xAxis: a }, { xAxis: b }]),
              }
            : undefined,
        },
        ...(comReferencia
          ? [
              {
                name: "Média histórica do mês",
                type: "line" as const,
                data: dados.referencia,
                symbol: "circle",
                symbolSize: 8,
                connectNulls: false,
                ...estiloReferencia(),
              },
            ]
          : []),
      ],
    };
    const tabela = {
      colunas: comReferencia ? ["Período", "Chuva (mm)", "Média histórica (mm)"] : ["Período", "Chuva (mm)"],
      linhas: dados.pontos.map((p, i) =>
        comReferencia ? [rotulos[i], p.valor, dados.referencia[i] ?? null] : [rotulos[i], p.valor],
      ),
    };
    return { opcao, tabela, rotulos };
  }, [dados, frequencia, comReferencia]);

  function exportar() {
    if (!dados || !grafico) return;
    baixarCsv(`chuva-${dados.territorio_id}-${recorte.inicio}-a-${recorte.fim}-${frequencia}.csv`, [
      ["periodo_inicio", "territorio", "chuva_mm", "dias_no_periodo", "dias_com_dado", "media_historica_mm"],
      ...dados.pontos.map((p, i) => [
        p.t,
        dados.territorio_nome,
        p.valor,
        p.dias,
        p.dias_com_dado,
        dados.referencia[i],
      ]),
    ]);
  }

  return (
    <>
      <CabecalhoTela
        titulo="Séries e sazonalidade"
        proposito="Como a chuva se comportou no território e no período escolhidos, comparada com os anos anteriores."
      />
      <div className={estilos.controles} role="group" aria-label="Opções da série">
        <Selecao rotulo="Variável" valor={variavel} aoMudar={setVariavel} opcoes={VARIAVEIS} />
        <fieldset className={estilos.segmentado}>
          <legend>Frequência</legend>
          <div>
            {FREQUENCIAS.map((f) => (
              <label key={f.valor} data-marcado={frequencia === f.valor}>
                <input
                  type="radio"
                  name="frequencia"
                  value={f.valor}
                  checked={frequencia === f.valor}
                  onChange={() => setFrequencia(f.valor)}
                />
                {f.rotulo}
              </label>
            ))}
          </div>
        </fieldset>
        <Selecao
          rotulo="Comparar com"
          valor={comparar}
          aoMudar={setComparar}
          opcoes={[
            { valor: "media", rotulo: "Média histórica (mensal)" },
            { valor: "nenhum", rotulo: "Sem comparação" },
          ]}
          ajuda={
            frequencia !== "mensal" && comparar === "media"
              ? "A média aparece na frequência mensal."
              : undefined
          }
        />
      </div>

      {serie.isPending && <Carregando texto="Carregando a série…" />}
      {serie.isError && <FalhaCarga erro={serie.error} aoTentar={() => serie.refetch()} />}
      {dados && meta && grafico && (
        <div className={estilos.pilha}>
          {meta.avisos.length > 0 && (
            <ul className={estilos.avisos}>
              {meta.avisos.map((a) => (
                <li key={a}>{a}</li>
              ))}
            </ul>
          )}
          {meta.dados_insuficientes ? (
            <EstadoDados tipo="insuficiente" titulo="Dados insuficientes para esta série">
              {variavel === "chuva_mm"
                ? "Nenhum dia do recorte tem dado de chuva. Escolha outro período ou peça ao administrador para atualizar a fonte."
                : meta.avisos[0]}
            </EstadoDados>
          ) : (
            <QuadroGrafico
              titulo={`Chuva ao longo do tempo: ${dados.territorio_nome}`}
              resumo={dados.resumo}
              opcao={grafico.opcao}
              tabela={grafico.tabela}
              fontes={(meta.fontes ?? []).map((f) => ({
                nome: `${f.nome} (${TIPOS_FONTE[f.tipo]?.toLowerCase() ?? f.tipo})`,
                atualizadoEm: f.atualizado_em,
              }))}
              altura={360}
              extra={
                <Botao variante="discreto" onClick={exportar} icone={<Download />}>
                  Exportar CSV
                </Botao>
              }
            />
          )}
          {fonte && (
            <p className={estilos.cobertura}>
              Cobertura do recorte: {meta.cobertura_pct?.toLocaleString("pt-BR") ?? "sem dado"}% dos dias.{" "}
              {dados.lacunas_dias > 0 && `${dados.lacunas_dias} dias sem dado aparecem como faixa hachurada.`}
            </p>
          )}

          <div className={estilos.duas}>
            <Painel titulo="Calendário de chuvas" id="s-calendario">
              {sazonal.isPending && <Carregando />}
              {sazonal.data &&
                (sazonal.data.meta.dados_insuficientes ? (
                  <EstadoDados tipo="insuficiente">
                    Nenhum mês completo com dado neste território.
                  </EstadoDados>
                ) : (
                  <Calendario dados={sazonal.data.dados} fontes={sazonal.data.meta.fontes} />
                ))}
            </Painel>
            <Painel titulo="Estatística descritiva" id="s-estatistica">
              {estat.isPending && <Carregando />}
              {estat.isError && <FalhaCarga erro={estat.error} />}
              {estat.data && (
                <>
                  {estat.data.dados.serie_curta && (
                    <EstadoDados tipo="insuficiente" titulo="Série curta: não use para caracterizar o clima.">
                      São {estat.data.dados.n} valores; o mínimo para descrever o clima é{" "}
                      {estat.data.dados.minimo_observacoes}.
                    </EstadoDados>
                  )}
                  <p className={estilos.legendaMedidas}>
                    Medidas da chuva {FREQUENCIAS.find((f) => f.valor === frequencia)?.rotulo.toLowerCase()}{" "}
                    no recorte, sobre {estat.data.dados.n} valores com dado.
                  </p>
                  <dl className={estilos.medidas}>
                    {estat.data.dados.medidas.map((m) => (
                      <div key={m.chave}>
                        <dt>{m.nome}</dt>
                        <dd className={estilos.valorMedida}>{m.texto}</dd>
                        <dd className={estilos.explicacaoMedida}>{m.explicacao}</dd>
                      </div>
                    ))}
                  </dl>
                  <LegendaFonte
                    fontes={estat.data.meta.fontes.map((f) => ({
                      nome: f.nome,
                      atualizadoEm: f.atualizado_em,
                    }))}
                  />
                </>
              )}
            </Painel>
          </div>
          {referencia.data && !referencia.data.meta.dados_insuficientes && (
            <Painel titulo="Como a média histórica é calculada" id="s-referencia">
              <p className={estilos.metodo}>
                {referencia.data.dados.metodo} Anos usados:{" "}
                {[...new Set(referencia.data.dados.meses.flatMap((m) => m.anos_usados))].sort().join(", ")}.
              </p>
            </Painel>
          )}
        </div>
      )}
    </>
  );
}
