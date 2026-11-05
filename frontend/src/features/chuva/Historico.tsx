import { useMemo } from "react";
import type { EChartsOption } from "echarts";
import { QuadroGrafico } from "@/charts/QuadroGrafico";
import { estiloReferencia, token, useTemaAtual } from "@/charts/tema";
import { CarregandoLista } from "@/design-system/componentes/Esqueleto";
import { EstadoDados } from "@/design-system/componentes/EstadoDados";
import { Painel } from "@/design-system/componentes/Painel";
import { consulta, type Esquemas } from "@/lib/api";
import { useConsulta } from "@/lib/consultas";
import { diaNoRecife, formatarMm, formatarNumero, nomeMes } from "@/lib/formatos";
import { EstadoConsulta } from "@/features/evento/Evento";
import { atualizada, listaEmFrase, useFontesResumo } from "@/features/evento/textos";
import { listaDe, type ItemEstagio } from "@/features/evento/tipos";
import { Calendario } from "./Calendario";
import estilos from "./Chuva.module.css";

type Sazonalidade = Esquemas["Sazonalidade"];

/** Só os anos que têm ao menos um mês com dado: o calendário começa no primeiro ano útil. */
export function anosComDado(d: Sazonalidade): Sazonalidade {
  const anos = d.anos.filter((a) => d.celulas.some((c) => c.ano === a && c.valor !== null));
  return { anos, celulas: d.celulas.filter((c) => anos.includes(c.ano)) };
}

/** Este ano mês a mês contra a média dos anos anteriores, e a frase que resume a comparação. */
export function esteAno(d: Sazonalidade, ano: number) {
  const valor = (a: number, m: number) => d.celulas.find((c) => c.ano === a && c.mes === m)?.valor ?? null;
  const anteriores = d.anos.filter((a) => a < ano && d.celulas.some((c) => c.ano === a && c.valor !== null));
  const media = Array.from({ length: 12 }, (_, i) => {
    const v = anteriores.map((a) => valor(a, i + 1)).filter((x): x is number => x !== null);
    return v.length ? v.reduce((s, x) => s + x, 0) / v.length : null;
  });
  const atual = Array.from({ length: 12 }, (_, i) => valor(ano, i + 1));
  const meses = atual.map((v, i) => (v !== null && media[i] !== null ? i : -1)).filter((i) => i >= 0);
  const soma = meses.reduce((s, i) => s + (atual[i] as number), 0);
  const somaRef = meses.reduce((s, i) => s + (media[i] as number), 0);
  const faixa = anteriores.length ? `${anteriores[0]} a ${anteriores[anteriores.length - 1]}` : "";
  let frase: string;
  if (meses.length === 0) frase = `Ainda não há mês completo de ${ano} para comparar.`;
  else if (anteriores.length < 3)
    frase = `Em ${ano} choveu ${formatarMm(soma, 0)} no Recife. Ainda há poucos anos para comparar (${
      anteriores.length
    }).`;
  else {
    const pct = somaRef > 0 ? (soma / somaRef - 1) * 100 : 0;
    const ate = nomeMes(meses[meses.length - 1] + 1);
    const comparacao =
      Math.abs(pct) < 10
        ? `perto da média de ${faixa}`
        : `${formatarNumero(Math.abs(pct))}% ${pct > 0 ? "acima" : "abaixo"} da média de ${faixa}`;
    frase = `Em ${ano} choveu ${formatarMm(
      soma,
      0,
    )} no Recife até ${ate}, ${comparacao} para os mesmos meses.`;
  }
  return { atual, media, frase, faixa };
}

/** Bairros com mais atendimentos de alagamento (Defesa Civil), do maior para o menor. `null` = fonte sem carga. */
export function ondeAlagou(bairros: ItemEstagio[], limite = 10) {
  const comDado = bairros.filter((b) => typeof b.sugerido?.insumos?.ocorrencias_historicas === "number");
  if (comDado.length === 0) return null;
  return comDado
    .map((b) => ({ nome: b.territorio_nome, n: b.sugerido.insumos.ocorrencias_historicas as number }))
    .filter((b) => b.n > 0)
    .sort((a, b) => b.n - a.n || a.nome.localeCompare(b.nome, "pt-BR"))
    .slice(0, limite);
}

/** Aba “Histórico”: este ano contra a média, o calendário de meses e onde já alagou. */
export function Historico() {
  const modo = useTemaAtual();
  const ano = Number(diaNoRecife().slice(0, 4));
  const sazonal = useConsulta<Esquemas["RespostaDados_Sazonalidade_"]>(
    `/series/sazonalidade${consulta({ territorio_id: "recife" })}`,
  );
  const bairros = useConsulta<unknown>(`/estagios${consulta({ nivel: "bairro" })}`);
  const fontes = useFontesResumo();
  const dados =
    sazonal.data && !sazonal.data.meta.dados_insuficientes ? anosComDado(sazonal.data.dados) : null;

  const grafico = useMemo(() => {
    if (!dados) return null;
    const r = esteAno(dados, ano);
    const meses = Array.from({ length: 12 }, (_, i) => nomeMes(i + 1, true));
    const mesAtual = Number(diaNoRecife().slice(5, 7));
    const topo = Math.max(
      1,
      ...r.atual.filter((v): v is number => v !== null),
      ...r.media.map((v) => v ?? 0),
    );
    // mês que já passou (ou está correndo) e não tem dado completo: coluna riscada, nunca barra de zero
    const semDado = r.atual.map((v, i) => (v === null && i + 1 <= mesAtual ? topo : null));
    const opcao: EChartsOption = {
      grid: { left: 24, right: 16, top: 60, bottom: 8, containLabel: true },
      legend: { top: 0, left: 0, data: [String(ano), "Média dos anos anteriores"] },
      tooltip: {
        trigger: "axis",
        formatter: (ps: unknown) => {
          const l = ps as { seriesName: string; value: number | null; dataIndex: number }[];
          if (!l.length) return "";
          const i = l[0].dataIndex;
          const atual = r.atual[i];
          return `${nomeMes(i + 1)}<br>${ano}: <strong>${
            atual === null
              ? i + 1 <= mesAtual
                ? "sem dado completo"
                : "ainda não chegou"
              : formatarMm(atual, 0)
          }</strong><br>Média: <strong>${formatarMm(r.media[i], 0)}</strong>`;
        },
      },
      xAxis: { type: "category", data: meses },
      yAxis: { type: "value", name: "mm", min: 0 },
      series: [
        {
          name: "Sem dado",
          type: "bar",
          silent: true,
          barGap: "-100%",
          barWidth: "56%",
          z: 1,
          tooltip: { show: false },
          data: semDado,
          itemStyle: {
            color: token("--n-insuf-bg"),
            borderRadius: 0,
            decal: {
              symbol: "rect",
              dashArrayX: [1, 0],
              dashArrayY: [2, 4],
              rotation: Math.PI / 4,
              color: token("--g-eixo"),
            },
          },
        },
        {
          name: String(ano),
          type: "bar",
          barWidth: "56%",
          itemStyle: { color: token("--g-1"), borderRadius: [4, 4, 0, 0] },
          data: r.atual,
        },
        {
          name: "Média dos anos anteriores",
          type: "line",
          symbol: "circle",
          symbolSize: 8,
          data: r.media,
          ...estiloReferencia(),
          itemStyle: { color: token("--g-ref") },
        },
      ],
    };
    const tabela = {
      colunas: ["Mês", `${ano} (mm)`, "Média dos anos anteriores (mm)"],
      linhas: meses.map((m, i) => [
        m,
        r.atual[i],
        r.media[i] === null ? null : Math.round(r.media[i] as number),
      ]),
    };
    return { opcao, tabela, frase: r.frase, temSemDado: semDado.some((v) => v !== null) };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sazonal.data, ano, modo]);

  const alagou = ondeAlagou(listaDe<ItemEstagio>(bairros.data));
  const maximo = alagou?.[0]?.n ?? 1;

  return (
    <div className={estilos.pagina}>
      {sazonal.isPending && (
        <CarregandoLista linhas={1} altura="22rem" texto="Carregando o histórico de chuva…" />
      )}
      {sazonal.isError && (
        <EstadoConsulta erro={sazonal.error} oQue="o histórico de chuva" aoTentar={() => sazonal.refetch()} />
      )}
      {sazonal.data?.meta.dados_insuficientes && (
        <EstadoDados tipo="insuficiente" titulo="Ainda não há histórico de chuva para o Recife." />
      )}
      {grafico && (
        <QuadroGrafico
          titulo="Este ano até agora"
          resumo={grafico.frase}
          opcao={grafico.opcao}
          tabela={grafico.tabela}
          altura={320}
          legenda={
            grafico.temSemDado && (
              <div className={estilos.legendaCalor}>
                <span className={estilos.legendaSem}>
                  <i aria-hidden="true" /> Riscado: mês sem dado completo (não quer dizer que não choveu)
                </span>
              </div>
            )
          }
        />
      )}
      {dados && dados.anos.length > 0 && <Calendario dados={dados} />}

      <Painel id="ch-alagou" titulo="Onde já alagou / deslizou">
        {bairros.isPending && <CarregandoLista linhas={4} altura="1.5rem" texto="Carregando os bairros…" />}
        {bairros.isError && (
          <EstadoConsulta
            erro={bairros.error}
            oQue="o histórico por bairro"
            aoTentar={() => bairros.refetch()}
          />
        )}
        {bairros.isSuccess && alagou === null && (
          <EstadoDados
            tipo="insuficiente"
            titulo="Os atendimentos da Defesa Civil ainda não foram carregados."
          />
        )}
        {alagou && alagou.length === 0 && (
          <EstadoDados tipo="insuficiente" titulo="Nenhum atendimento de alagamento registrado por bairro." />
        )}
        {alagou && alagou.length > 0 && (
          <>
            <p className={estilos.apoio}>
              {listaEmFrase(alagou.slice(0, 3).map((b) => b.nome))} tiveram mais atendimentos de alagamento da
              Defesa Civil. Deslizamentos ainda não estão na base.
            </p>
            <ol className={estilos.barras} aria-label="Bairros com mais atendimentos de alagamento">
              {alagou.map((b) => (
                <li key={b.nome}>
                  <span>{b.nome}</span>
                  <span
                    className={estilos.barra}
                    style={{ width: `${Math.max(2, (b.n / maximo) * 100)}%` }}
                    aria-hidden="true"
                  />
                  <span className={estilos.valorBarra}>
                    {formatarNumero(b.n)}
                    <span className="so-leitor"> atendimentos</span>
                  </span>
                </li>
              ))}
            </ol>
          </>
        )}
      </Painel>

      <p className={estilos.rodape}>
        Chuva estimada por satélite e modelo (ERA5), {atualizada(fontes.hora("open-meteo-historico"))}.
        Alagamentos: atendimentos da Defesa Civil do Recife, 2014 a 2024,{" "}
        {atualizada(fontes.hora("recife-alagamento"), "o")}.
      </p>
    </div>
  );
}
