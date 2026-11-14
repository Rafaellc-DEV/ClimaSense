import { Segmentado } from "@/design-system/componentes/Segmentado";
import { formatarNumero } from "@/lib/formatos";
import { infoEstagio } from "@/features/evento/estagios";
import type { FonteMeta } from "@/lib/frescor";
import type { ItemSimulado, ResultadoSimulacao } from "./tipos";
import estilos from "./Simulador.module.css";

const dataLocal = (data: string) =>
  new Intl.DateTimeFormat("pt-BR", {
    timeZone: "America/Recife",
    day: "2-digit",
    month: "2-digit",
  }).format(new Date(data.length === 10 ? `${data}T12:00:00-03:00` : data));
const horaLocal = (data: string) =>
  new Intl.DateTimeFormat("pt-BR", {
    timeZone: "America/Recife",
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(data));
const mm = (n: number | null | undefined) => (n == null ? "Sem dados" : `${formatarNumero(n)} mm`);

function resumoSemAtencao(dia: NonNullable<ResultadoSimulacao["dias"]>[number]): string {
  const valores = dia.distritos
    .map((d) => (d.cobertura_completa ? d.chuva_prevista_mm : d.chuva_disponivel_mm))
    .filter((valor): valor is number => valor != null && Number.isFinite(valor));
  const completos =
    dia.distritos.length > 0 &&
    dia.distritos.every((d) => d.cobertura_completa && d.chuva_prevista_mm != null);
  const insuficientes =
    !completos ||
    dia.distritos.some((d) => d.sinalizacao === "sem_dados" || d.desatualizada || !d.referencia_em);
  const acumulado = valores.length
    ? `${completos ? "Maior acumulado previsto: " : "Maior acumulado disponível: pelo menos "}${mm(Math.max(...valores))}.`
    : "Acumulado previsto indisponível.";
  const cobertura = completos
    ? `Dados completos nas ${dia.horas_periodo} h do período.`
    : "Dados parciais ou ausentes.";
  return `${acumulado} ${cobertura}${dia.periodo_parcial ? " Dia parcial." : ""}${dia.distritos.some((d) => d.desatualizada) ? " Há previsões desatualizadas." : ""} ${
    insuficientes
      ? "Dados insuficientes para confirmar se os limites foram atingidos."
      : "Nenhum limite de chuva atingido no período avaliado."
  }`;
}

export function SeletorDias({
  dias = [],
  dia,
  aoDia,
}: {
  dias: ResultadoSimulacao["dias"];
  dia: string;
  aoDia: (dia: string) => void;
}) {
  return (
    <section className={estilos.preventiva} aria-label="Dias de chuva intensa">
      <h2>Dias com chuva intensa</h2>
      <p>
        As previsões de chuva vêm da Open-Meteo. O ClimaSense usa esses dados para identificar territórios que
        merecem atenção. Essas sinalizações não são alertas oficiais da Defesa Civil.
      </p>
      <p>
        Consulte as próximas 72 horas, organizadas por dia no horário de Recife. O primeiro e o último dia
        podem ser parciais: mostramos apenas as horas dentro dessa janela.
      </p>
      {dias.length ? (
        <Segmentado
          rotulo="Dia da sinalização"
          valor={dia}
          aoMudar={aoDia}
          opcoes={[
            { valor: "", rotulo: "Horizonte contínuo" },
            ...dias.map((d) => ({
              valor: d.data,
              rotulo: `${dataLocal(d.data)} · ${d.distritos_em_atencao.length} ${d.distritos_em_atencao.length === 1 ? "distrito" : "distritos"} em atenção${d.periodo_parcial ? " · parcial" : ""}${d.distritos.some((s) => s.sinalizacao === "sem_dados") ? " · dados insuficientes" : ""}`,
            })),
          ]}
        />
      ) : (
        <p role="status">Sem calendário de previsão disponível. Isso não significa ausência de risco.</p>
      )}
      {dias.some((d) => d.distritos_em_atencao.length === 0) && (
        <ul className={estilos.apoio} aria-label="Resumo dos dias sem distritos em atenção">
          {dias
            .filter((d) => d.distritos_em_atencao.length === 0)
            .map((d) => (
              <li key={d.data}>
                <strong>{dataLocal(d.data)}</strong> — {resumoSemAtencao(d)}
              </li>
            ))}
        </ul>
      )}
    </section>
  );
}

export function PrevisaoPreventiva({
  resultado,
  dia,
  bairros,
  ml,
  atualizando,
  fontes,
}: {
  resultado: ResultadoSimulacao;
  dia: string;
  bairros: ItemSimulado[];
  ml: ResultadoSimulacao["ml_alagamento"];
  atualizando: boolean;
  fontes: FonteMeta[];
}) {
  const dias = resultado.dias ?? [];
  const escolhido = dias.find((d) => d.data === dia);
  const distritos = resultado.itens.filter((i) => i.nivel === "distrito");
  const leiturasApac = resultado.comparacoes_recentes ?? [];
  const ultimaApac = leiturasApac.reduce<string | undefined>(
    (ultima, c) => (!ultima || Date.parse(c.atualizada_em) > Date.parse(ultima) ? c.atualizada_em : ultima),
    fontes.find((f) => f.id === "apac-chuva")?.atualizado_em ?? undefined,
  );
  const textoAtualizacaoApac = ultimaApac
    ? `Última atualização disponível da APAC: ${horaLocal(ultimaApac)}.`
    : "A última atualização da APAC não foi informada.";
  const motivoSemComparacao =
    leiturasApac.length === 0
      ? "Não há leitura recente da APAC disponível."
      : leiturasApac.every((c) => !c.compativel)
        ? "As leituras da APAC disponíveis não têm uma previsão arquivada para o mesmo período."
        : null;
  return (
    <section aria-label="Sinalizações preventivas de chuva intensa" className={estilos.preventiva}>
      <h2>Comparação meteorológica e interpretação territorial</h2>
      <ul aria-label="Fontes meteorológicas e atualização">
        {fontes
          .filter((f) => ["open-meteo-previsao", "open-meteo-mare", "apac-chuva"].includes(f.id))
          .map((f) => (
            <li key={f.id}>
              {f.nome}:{" "}
              {f.atualizado_em
                ? `última atualização ${horaLocal(f.atualizado_em)}`
                : "sem atualização disponível"}
              ;
              {f.desatualizado === true
                ? " desatualizada"
                : f.desatualizado === false
                  ? " dentro do prazo da fonte"
                  : " frescor desconhecido"}
              .
            </li>
          ))}
      </ul>
      {dias.length === 0 ? (
        <p role="status">Sem calendário de previsão disponível. Isso não significa ausência de risco.</p>
      ) : (
        <>
          {!escolhido && (
            <p>
              Selecione uma data para destacar no mapa os bairros dos distritos que atingem os limites de
              chuva.
            </p>
          )}
          {escolhido && (
            <>
              <h3>Open-Meteo × interpretação territorial do ClimaSense · {dataLocal(escolhido.data)}</h3>
              <p>
                Período: {horaLocal(escolhido.inicio)} a {horaLocal(escolhido.fim)} (Recife).
                {escolhido.periodo_parcial &&
                  ` São ${escolhido.horas_periodo} horas deste dia, sem extrapolar para 24 h.`}{" "}
                A Open-Meteo fornece a chuva; o ClimaSense aplica regras sobre essa mesma previsão, histórico
                territorial e maré disponível. Não são duas previsões independentes de chuva.
              </p>
              <p>
                Limites de chuva prevista em até 24 h: atenção ≥ {mm(escolhido.criterios.atencao_mm)}, alerta
                ≥ {mm(escolhido.criterios.alerta_mm)}, crítico ≥ {mm(escolhido.criterios.critico_mm)}. Com
                dados parciais, só sinalizamos um limite que já foi atingido nas horas disponíveis.
              </p>
              <p className={estilos.apoio}>Em telas pequenas, deslize a tabela para ver todas as colunas.</p>
              <div
                className={estilos.tabelaPreventiva}
                tabIndex={0}
                role="region"
                aria-label="Comparação meteorológica e territorial"
              >
                <table>
                  <caption>Mesmo distrito e período selecionado; bairros herdam a chuva distrital</caption>
                  <thead>
                    <tr>
                      <th>Distrito</th>
                      <th>Previsão Open-Meteo</th>
                      <th>Sinalização interna</th>
                      <th>Regras territoriais</th>
                      <th>ML 0.2.0 experimental</th>
                    </tr>
                  </thead>
                  <tbody>
                    {escolhido.distritos.map((d) => {
                      const regra = distritos.find((i) => i.territorio_id === d.territorio_id);
                      const classesMl = [
                        ...new Set(
                          bairros
                            .filter((b) => b.distrito_id === d.territorio_id)
                            .map((b) => b.ml_alagamento?.classe)
                            .filter(Boolean),
                        ),
                      ];
                      return (
                        <tr key={d.territorio_id}>
                          <th scope="row">{d.nome}</th>
                          <td>
                            {d.cobertura_completa
                              ? mm(d.chuva_prevista_mm)
                              : d.chuva_disponivel_mm == null
                                ? "Sem dados"
                                : `Pelo menos ${mm(d.chuva_disponivel_mm)}`}
                            <small>
                              {d.horas_validas}/{d.horas_esperadas} h disponíveis.{" "}
                              {d.desatualizada ? "Previsão desatualizada." : ""}
                              {d.referencia_em ? ` Captura: ${horaLocal(d.referencia_em)}.` : " Sem captura."}
                            </small>
                          </td>
                          <td>
                            {d.sinalizacao === "observacao"
                              ? "Limite não atingido no período disponível"
                              : infoEstagio(d.sinalizacao).rotulo}
                          </td>
                          <td>{infoEstagio(regra?.estagio_sugerido).rotulo}</td>
                          <td>
                            {ml?.disponivel
                              ? classesMl.length
                                ? classesMl.join(", ")
                                : "Sem dados nos bairros"
                              : "Indisponível"}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
              <a href="#sim-mapa">Ver territórios destacados no mapa</a>
              <p>
                APAC: observação ainda indisponível para o período futuro selecionado. Essa comparação não
                pôde ser realizada; a previsão da Open-Meteo continua disponível acima.
              </p>
              <p className={estilos.apoio}>
                ML experimental: {ml?.motivo ?? "classes de pesquisa; não validado para uso operacional"}.
              </p>
            </>
          )}
        </>
      )}
      {motivoSemComparacao && (
        <p role="status" aria-label="Comparação com a APAC">
          Comparação Open-Meteo × APAC não realizada. {motivoSemComparacao} {textoAtualizacaoApac} As
          informações disponíveis da Open-Meteo permanecem exibidas.
        </p>
      )}
      <details>
        <summary>APAC observada × previsão arquivada na mesma hora</summary>
        <p>
          Comparamos leituras recentes da APAC com previsões que já existiam antes da chuva, no mesmo distrito
          e horário. A estação mede um ponto do território; este quadro não mede acurácia.
        </p>
        {resultado.comparacoes_recentes?.length ? (
          <ul>
            {resultado.comparacoes_recentes.map((c) => (
              <li key={c.territorio_id}>
                {distritos.find((d) => d.territorio_id === c.territorio_id)?.nome ?? c.territorio_id}: APAC{" "}
                {mm(c.observada_mm)}, estação {c.estacao}; {horaLocal(c.inicio)} a {horaLocal(c.fim)};
                atualização {horaLocal(c.atualizada_em)}.
                {c.compativel
                  ? ` Open-Meteo arquivada: ${mm(c.prevista_mm)}, captura ${horaLocal(c.previsao_referencia_em!)}.`
                  : ` Comparação não realizada: ${c.motivo ?? "não há previsão arquivada compatível com esta leitura."} Última atualização disponível desta leitura: ${horaLocal(c.atualizada_em)}.`}
              </li>
            ))}
          </ul>
        ) : (
          <p>
            {textoAtualizacaoApac} Sem leitura recente, não é possível comparar a chuva observada com a
            prevista.
          </p>
        )}
      </details>
      <p role="status">
        {atualizando
          ? "Atualizando as previsões…"
          : "Consulta renovada automaticamente a cada minuto enquanto a tela está aberta."}
        {resultado.calculado_em && ` Verificada em ${horaLocal(resultado.calculado_em)}.`}
      </p>
    </section>
  );
}
