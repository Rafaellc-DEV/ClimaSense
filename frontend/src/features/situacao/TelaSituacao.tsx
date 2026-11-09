import { useId, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { classesBotao } from "@/design-system/componentes/Botao";
import { CabecalhoTela } from "@/design-system/componentes/CabecalhoTela";
import campo from "@/design-system/componentes/Campo.module.css";
import { EstadoConsulta, SeloEstagio } from "@/features/evento/Evento";
import { nomeCurto, quandoAs } from "@/features/evento/textos";
import { desembrulhar, listaDe, type ItemEstagio } from "@/features/evento/tipos";
import { nomeDaFonte, type EstagioOficial } from "@/features/mapa/tipos";
import { consulta, ErroApi } from "@/lib/api";
import { useConsultaViva, ultimaAtualizacao } from "@/lib/consultas";
import { formatarNumero } from "@/lib/formatos";
import { fontesDe } from "@/lib/frescor";
import {
  CartaoIndicador,
  ChuvaPorDistrito,
  FontesAtualizacao,
  MensagemEstagio,
  type LinhaFonte,
} from "./Blocos";
import { achaFonte, faixaDeIncerteza, linhasMedidas, maiorDe, type CenarioHora } from "./dados";
import { GraficoChuvaMare } from "./GraficoChuvaMare";
import estilos from "./Situacao.module.css";

const mm = (v: number) => formatarNumero(v, 1);

/**
 * Situação do evento (RF-08, RF-09, RF-10): o painel de gestão e análise. Estágio oficial do COP, quatro números
 * com fonte e hora, chuva e maré, chuva por distrito, fontes e a mensagem de mudança de estágio. Cada bloco carrega
 * sozinho. Sem dado, diz "Dados insuficientes" e a fonte que falta (RN-01). Só dados reais (ADR 0008).
 */
export function TelaSituacao() {
  const idTerr = useId();
  const idPeriodo = useId();
  const [territorio, setTerritorio] = useState("recife");
  const [periodo, setPeriodo] = useState<"24" | "72">("24");

  const oficial = useConsultaViva<unknown>("/estagios/oficial");
  const distritos = useConsultaViva<unknown>(`/estagios${consulta({ nivel: "distrito" })}`);
  const fontesApi =
    useConsultaViva<
      { id: string; nome: string; ultima_atualizacao: string | null; desatualizado: boolean | null }[]
    >("/fontes");
  const grafico = useConsultaViva<{ dados: CenarioHora }>(
    `/cenarios/estimativa${consulta({ territorio_id: territorio, horizonte_h: Number(periodo) })}`,
    5 * 60_000,
    { staleTime: 5 * 60_000 },
  );

  const estagio = desembrulhar<EstagioOficial | null>(oficial.data) ?? null;
  const definido = estagio?.estagio ? estagio : null;
  const oficialIndisponivel = oficial.error instanceof ErroApi && oficial.error.status === 404;

  const todos = useMemo(() => listaDe<ItemEstagio>(distritos.data), [distritos.data]);
  const escolhidos = useMemo(
    () => (territorio === "recife" ? todos : todos.filter((i) => i.territorio_id === territorio)),
    [todos, territorio],
  );
  const metaFontes = fontesDe(distritos.data);

  const medida = maiorDe(escolhidos, "chuva_24h_mm");
  const prev24 = maiorDe(escolhidos, "chuva_prev_24h_mm");
  const prev72 = maiorDe(escolhidos, "chuva_prev_72h_mm");
  const mare = maiorDe(escolhidos, "mare_max_m");
  const mareEm = mare?.item.sugerido.insumos.mare_max_em;

  // faixa de incerteza do distrito que tem a maior previsão de 24 h
  const idFaixa = prev24?.item.territorio_id ?? null;
  const faixaConsulta = useConsultaViva<{ dados: CenarioHora }>(
    idFaixa ? `/cenarios/estimativa${consulta({ territorio_id: idFaixa, horizonte_h: 24 })}` : null,
    5 * 60_000,
    { staleTime: 5 * 60_000 },
  );
  const faixa = faixaDeIncerteza(faixaConsulta.data?.dados, 24);

  const idsMedida = (medida?.item.sugerido.insumos.chuva_24h_fontes as string[] | undefined) ?? [
    "apac-chuva",
  ];
  const nomeDe = (i: ItemEstagio | undefined) => (i ? nomeCurto(i.territorio_nome) : "");
  const carregando = distritos.isPending;

  const linhasFonte: LinhaFonte[] = useMemo(() => {
    const lista = fontesApi.data ?? [];
    const medidas = linhasMedidas(todos);
    const semLeitura = medidas.filter((l) => l.mm === null).length;
    const de = (id: string, nome: string, parcial?: string | null): LinhaFonte => {
      const f = lista.find((x) => x.id === id) ?? metaFontes.find((x) => x.id === id);
      const atualizado =
        (f && "ultima_atualizacao" in f
          ? f.ultima_atualizacao
          : (f as { atualizado_em?: string } | undefined)?.atualizado_em) ?? null;
      return { id, nome, atualizadoEm: atualizado, desatualizado: f?.desatualizado ?? null, parcial };
    };
    return [
      {
        id: "oficial",
        nome: "Estágio oficial da cidade (COP, registro da equipe)",
        atualizadoEm: definido?.informado_em ?? null,
        desatualizado: null,
      },
      de(
        "apac-chuva",
        "Chuva medida (pluviômetros, APAC e Cemaden)",
        medidas.length > 0 && semLeitura > 0 && semLeitura < medidas.length
          ? `${semLeitura} de ${medidas.length} distritos sem leitura.`
          : null,
      ),
      de("open-meteo-previsao", "Previsão de chuva (Open-Meteo)"),
      de("open-meteo-mare", "Previsão de maré (Open-Meteo Marine)"),
    ];
  }, [fontesApi.data, metaFontes, todos, definido]);

  return (
    <>
      <CabecalhoTela
        titulo="Situação do evento"
        proposito="Estágio oficial, chuva medida e prevista e maré, com fonte e hora em cada número."
        atualizadoEm={ultimaAtualizacao(oficial, distritos)}
        acoes={
          <div className={estilos.filtros}>
            <div className={campo.campo}>
              <label htmlFor={idTerr} className={estilos.rotuloFiltro}>
                Território
              </label>
              <select
                id={idTerr}
                className={campo.entrada}
                value={territorio}
                onChange={(e) => setTerritorio(e.target.value)}
              >
                <option value="recife">Recife, todos os distritos</option>
                {todos.map((i) => (
                  <option key={i.territorio_id} value={i.territorio_id}>
                    {nomeCurto(i.territorio_nome)}
                  </option>
                ))}
              </select>
            </div>
            <div className={campo.campo}>
              <label htmlFor={idPeriodo} className={estilos.rotuloFiltro}>
                Período
              </label>
              <select
                id={idPeriodo}
                className={campo.entrada}
                value={periodo}
                onChange={(e) => setPeriodo(e.target.value as "24" | "72")}
              >
                <option value="24">Próximas 24 h</option>
                <option value="72">Próximas 72 h</option>
              </select>
            </div>
          </div>
        }
      />
      <div className={estilos.pagina}>
        <section aria-labelledby="se-oficial" className={estilos.faixa}>
          <h2 id="se-oficial" className={estilos.faixaRotulo}>
            Estágio oficial da cidade (COP)
          </h2>
          {oficial.isPending ? (
            <p className={estilos.carregando} role="status">
              Carregando…
            </p>
          ) : oficial.isError && !oficialIndisponivel ? (
            <EstadoConsulta
              erro={oficial.error}
              oQue="o estágio oficial"
              aoTentar={() => oficial.refetch()}
            />
          ) : definido ? (
            <>
              <SeloEstagio estagio={definido.estagio!} />
              <p className={estilos.fonteLinha}>
                Registrado
                {definido.autor_nome ? ` por ${definido.autor_nome}` : ""}{" "}
                {definido.informado_em ? `${quandoAs(definido.informado_em)}` : "(sem hora)"}
                {definido.observacao ? `, a partir de ${definido.observacao}` : ""}. Fonte:{" "}
                {nomeDaFonte(definido.fonte)}.
              </p>
            </>
          ) : (
            <p className={estilos.insuficiente}>
              <b>Dados insuficientes:</b> falta o estágio informado pelo COP.
            </p>
          )}
          <Link to="/app/simulador" className={[classesBotao("principal"), estilos.simular].join(" ")}>
            Simular este cenário
          </Link>
        </section>

        {distritos.isError ? (
          <EstadoConsulta
            erro={distritos.error}
            oQue="os números da chuva e da maré"
            aoTentar={() => distritos.refetch()}
          />
        ) : (
          <div className={estilos.cartoes}>
            <CartaoIndicador
              rotulo="Chuva medida 24 h"
              selo={idsMedida.includes("apac-chuva") ? "Observado" : "Estimado"}
              tomSelo="info"
              carregando={carregando}
              valor={medida ? mm(medida.valor) : null}
              unidade="mm"
              detalhe={
                medida && territorio === "recife"
                  ? `Maior valor entre os distritos: ${nomeDe(medida.item)}`
                  : null
              }
              faltando="a chuva medida nas últimas 24 h (pluviômetros, APAC)"
              fontes={achaFonte(metaFontes, ...idsMedida)}
            />
            <CartaoIndicador
              rotulo="Chuva prevista 24 h"
              selo="Previsto"
              tomSelo="marca"
              carregando={carregando}
              valor={prev24 ? mm(prev24.valor) : null}
              unidade="mm"
              detalhe={
                prev24 && (
                  <>
                    {territorio === "recife" && `${nomeDe(prev24.item)}. `}
                    {faixa
                      ? `Faixa de ${formatarNumero(faixa.min, 0)} a ${formatarNumero(faixa.max, 0)} mm.`
                      : null}
                  </>
                )
              }
              faltando="a previsão de chuva por distrito (Open-Meteo)"
              fontes={achaFonte(metaFontes, "open-meteo-previsao")}
            />
            <CartaoIndicador
              rotulo="Maré máxima prevista"
              selo="Previsto"
              tomSelo="marca"
              carregando={carregando}
              valor={mare ? formatarNumero(mare.valor, 2) : null}
              unidade="m"
              detalhe={typeof mareEm === "string" ? `Pico ${quandoAs(mareEm)}` : null}
              faltando="a previsão de maré (Open-Meteo Marine)"
              fontes={achaFonte(metaFontes, "open-meteo-mare")}
            />
            <CartaoIndicador
              rotulo="Chuva prevista 72 h"
              selo="Previsto"
              tomSelo="marca"
              carregando={carregando}
              valor={prev72 ? mm(prev72.valor) : null}
              unidade="mm"
              detalhe={prev72 && territorio === "recife" ? nomeDe(prev72.item) : null}
              faltando="a previsão de chuva por distrito (Open-Meteo)"
              fontes={achaFonte(metaFontes, "open-meteo-previsao")}
              extra={
                <p className={estilos.insuficiente}>
                  <b>Dados insuficientes:</b> falta a umidade do solo para dizer se está saturado.
                </p>
              }
            />
          </div>
        )}

        <div className={estilos.dupla}>
          <GraficoChuvaMare cenario={grafico} fontes={metaFontes} />
          <ChuvaPorDistrito
            carregando={carregando}
            erro={distritos.isError ? distritos.error : null}
            aoTentar={() => distritos.refetch()}
            linhas={linhasMedidas(todos)}
            fontes={achaFonte(metaFontes, ...idsMedida)}
            destaque={territorio === "recife" ? null : territorio}
          />
        </div>

        <div className={estilos.dupla}>
          <FontesAtualizacao linhas={linhasFonte} carregando={fontesApi.isPending && distritos.isPending} />
          <MensagemEstagio
            estagio={definido?.estagio ?? null}
            territorioId={territorio}
            carregando={oficial.isPending}
          />
        </div>
      </div>
    </>
  );
}
