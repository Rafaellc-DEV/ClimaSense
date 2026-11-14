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
        Sinalização preventiva interna, não é alerta oficial da Defesa Civil. São 72 horas completas a partir
        da próxima hora cheia, agrupadas por data de Recife. O primeiro e o último dia podem ser parciais; não
        extrapolamos para 24 h.
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
                Limites existentes para chuva prevista em até 24 h: atenção ≥{" "}
                {mm(escolhido.criterios.atencao_mm)}, alerta ≥ {mm(escolhido.criterios.alerta_mm)}, crítico ≥{" "}
                {mm(escolhido.criterios.critico_mm)}. Soma incompleta só sinaliza ultrapassagem já
                demonstrada; nunca confirma ausência de atenção.
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
                APAC para o período futuro selecionado: observação ainda indisponível. O acumulado observado
                nas últimas 72 h não é comparável a essa previsão futura. ML:{" "}
                {ml?.motivo ?? "classes de pesquisa; não validado para uso operacional"}.
              </p>
            </>
          )}
        </>
      )}
      <details>
        <summary>APAC observada × previsão arquivada na mesma hora</summary>
        <p>
          Última leitura de 1 h por distrito, coletada nas últimas 2 h. Só há pareamento se o fim da janela
          for uma hora exata e a previsão já existia antes do início. Pluviômetro pontual e ponto distrital
          têm representatividade diferente; este quadro não calcula acurácia.
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
                  : ` ${c.motivo}`}
              </li>
            ))}
          </ul>
        ) : (
          <p>Sem leitura APAC recente disponível para pareamento. Não preenchemos ausência com zero.</p>
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
