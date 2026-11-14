import { useEffect, useMemo, useState } from "react";
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";
import { Botao } from "@/design-system/componentes/Botao";
import { CabecalhoTela } from "@/design-system/componentes/CabecalhoTela";
import { Campo } from "@/design-system/componentes/Campo";
import { Dialogo } from "@/design-system/componentes/Dialogo";
import { CarregandoLista } from "@/design-system/componentes/Esqueleto";
import { EstadoDados } from "@/design-system/componentes/EstadoDados";
import { Experimental } from "@/design-system/componentes/Pilula";
import { Segmentado } from "@/design-system/componentes/Segmentado";
import { api, enviar, type ErroApi } from "@/lib/api";
import { useConsulta, useConsultaViva } from "@/lib/consultas";
import { quandoRelativo } from "@/lib/formatos";
import { juntarFontes, type FonteMeta } from "@/lib/frescor";
import { useSessao } from "@/lib/sessao";
import { EstadoConsulta } from "@/features/evento/Evento";
import { quandoAs } from "@/features/evento/textos";
import { limiaresDe } from "@/features/evento/tipos";
import { MapaDoCenario } from "./MapaDoCenario";
import { DetalheDistrito, EstagioPorDistrito } from "./EstagioPorDistrito";
import { infoEstagio } from "@/features/evento/estagios";
import type { CenarioPronto } from "./cenarios";
import { OrdemAtencao } from "./OrdemAtencao";
import { PainelPremissas } from "./Premissas";
import { PrevisaoPreventiva, SeletorDias } from "./PrevisaoPreventiva";
import {
  deAtuais,
  paraPremissas,
  podeSimular,
  temAlgumDado,
  HORIZONTES,
  type CampoNumerico,
  type CenarioSalvo,
  type Formulario,
  type ItemSimulado,
  type Premissas,
  type ResultadoSimulacao,
} from "./tipos";
import estilos from "./Simulador.module.css";

interface Envelope<T> {
  dados: T;
  meta?: unknown;
}

const ATRASO_MS = 400;

/** Lê `meta.fonte_por_premissa`: qual fonte alimenta cada campo. Sem o mapa, a tela usa o padrão fixo. */
function fontePorPremissaDe(r: unknown): Partial<Record<CampoNumerico, string>> | null {
  const m = (r as { meta?: { fonte_por_premissa?: unknown } } | undefined)?.meta?.fonte_por_premissa;
  return m && typeof m === "object" ? (m as Partial<Record<CampoNumerico, string>>) : null;
}

/** Espera o usuário parar de digitar; o primeiro valor passa direto. */
function useAtraso<T>(valor: T, chave: string, ms: number): [T, (v: T) => void] {
  const [atrasado, setAtrasado] = useState(valor);
  const [primeiro, setPrimeiro] = useState(true);
  useEffect(() => {
    const t = setTimeout(
      () => {
        setAtrasado(valor);
        setPrimeiro(false);
      },
      primeiro ? 0 : ms,
    );
    return () => clearTimeout(t);
    // a chave descreve o valor: objeto novo com o mesmo conteúdo não reinicia a espera
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chave, ms]);
  return [atrasado, setAtrasado];
}

/**
 * Simulador de cenário: a pessoa muda a chuva e a maré e vê qual distrito pede mais atenção e com quais arboviroses.
 * Estimativa por regras, sempre com o selo Experimental (RN-11). Classe e ordem, nunca percentual (RN-06).
 */
export function TelaSimulador() {
  const clientes = useQueryClient();
  const [params] = useSearchParams();
  const [modo, setModo] = useState<"manual" | "atual">(params.get("modo") === "atual" ? "atual" : "manual");
  const [horizonteAtual, setHorizonteAtual] = useState<number>(24);
  const [dia, setDia] = useState("");
  const { pode, usuario } = useSessao();
  const [previaLocal, setPreviaLocal] = useState(false);
  const acessoPrevia = import.meta.env.DEV && usuario?.ambiente === "desenvolvimento" && pode("administrar");
  const demoAutomatica = acessoPrevia && import.meta.env.VITE_ML_DEMO_ACADEMICA === "true";
  useEffect(() => {
    if (demoAutomatica) {
      setModo("atual");
      setPreviaLocal(true);
    }
  }, [demoAutomatica]);
  const analise = useConsultaViva<Envelope<ResultadoSimulacao>>(
    modo === "atual"
      ? `/cenarios/impacto-previsto?horizonte_h=${horizonteAtual}${dia ? `&dia=${dia}` : ""}`
      : null,
  );
  const diaMl = analise.data?.dados.dias?.find((d) => d.data === dia);
  const periodoMl = !dia || diaMl?.periodo_parcial === false;
  const previaAtiva = modo === "atual" && previaLocal && acessoPrevia;
  const pesquisa = useConsulta<
    Envelope<
      ResultadoSimulacao["ml_alagamento"] & {
        itens: { territorio_id: string; classe: string; confianca?: string; fatores: string[] }[];
      }
    >
  >(previaAtiva && periodoMl ? `/risco-alagamento/previa-local${dia ? `?dia=${dia}` : ""}` : null, {
    retry: false,
    staleTime: 10_000,
  });
  useEffect(() => {
    if (dia && analise.error?.status === 422) setDia("");
  }, [dia, analise.error]);
  const atuais = useConsulta<Envelope<Partial<Premissas>>>("/cenarios/premissas-atuais", {
    staleTime: 5 * 60_000,
  });
  const parametros = useConsulta<unknown>("/estagios/parametros", { staleTime: 10 * 60_000 });
  const limiares = useMemo(() => limiaresDe(parametros.data), [parametros.data]);
  const salvos = useConsulta<Envelope<CenarioSalvo[]>>("/cenarios", { staleTime: 30_000 });

  // ---- premissas: o que a pessoa mudou por cima dos valores atuais
  const valoresAtuais = atuais.data?.dados;
  const base = useMemo(() => deAtuais(valoresAtuais), [valoresAtuais]);
  const [editado, setEditado] = useState<Formulario | null>(null);
  const form = editado ?? base;
  const premissas = useMemo(() => paraPremissas(form), [form]);
  const chave = premissas ? JSON.stringify(premissas) : "";
  const [pronta, setPronta] = useAtraso<Premissas | null>(premissas, chave, ATRASO_MS);
  const pronto = atuais.isPending ? null : pronta; // espera os valores atuais antes do primeiro cálculo

  // ao mexer na chuva sem duração definida, a duração assume o horizonte (a chuva espalhada em todo o cenário)
  const mudar = (campo: CampoNumerico, valor: string) =>
    setEditado({
      ...form,
      [campo]: valor,
      ...(campo === "chuva_prevista_mm" && valor.trim() !== "" && form.duracao_h === ""
        ? { duracao_h: String(form.horizonte_h) }
        : {}),
    });
  const mudarHorizonte = (h: number) => setEditado({ ...form, horizonte_h: h });
  const aplicarCenario = (c: CenarioPronto) =>
    setEditado({
      ...form,
      chuva_prevista_mm: String(c.chuva_prevista_mm).replace(".", ","),
      chuva_acumulada_mm: String(c.chuva_acumulada_mm).replace(".", ","),
      mare_m: String(c.mare_m).replace(".", ","),
      duracao_h: String(c.duracao_h),
    });
  const aplicar = (f: Formulario) => {
    setEditado(f);
    setPronta(paraPremissas(f));
  };

  // ---- cálculo: recalcula sozinho ao mudar a premissa (RF-24, RF-28)
  const calculo = useQuery<Envelope<ResultadoSimulacao>, ErroApi>({
    queryKey: ["simulador", pronto ? JSON.stringify(pronto) : null],
    queryFn: () => enviar<Envelope<ResultadoSimulacao>>("/cenarios/simular", pronto),
    enabled: modo === "manual" && pronto !== null && podeSimular(pronto),
    placeholderData: keepPreviousData,
    staleTime: 5 * 60_000,
    retry: false,
  });
  const resultado = modo === "atual" ? analise.data?.dados : calculo.data?.dados;
  const itens = useMemo(() => resultado?.itens ?? [], [resultado]);
  const distritos = useMemo(() => itens.filter((i) => i.nivel === "distrito"), [itens]);
  const bairros = useMemo(() => itens.filter((i) => i.nivel === "bairro"), [itens]);
  const mapaPesquisa = previaAtiva;
  const dadosPesquisa = previaAtiva && periodoMl && !pesquisa.isError ? pesquisa.data?.dados : undefined;
  const motivoPrevia = !acessoPrevia
    ? "Prévia experimental restrita a administrador em desenvolvimento."
    : !previaLocal
      ? "Prévia experimental desativada nesta tela. Ative a prévia local para consultar as classes."
      : dia && !diaMl
        ? "Aguardando as informações do dia selecionado."
        : !periodoMl
          ? "Dia selecionado parcial: o ML 0.2.0 exige um dia local completo."
          : pesquisa.isError
            ? `Erro ao consultar a prévia experimental: ${pesquisa.error.message}`
            : pesquisa.isPending
              ? "Consultando a prévia experimental…"
              : null;
  const modeloExperimental: ResultadoSimulacao["ml_alagamento"] = motivoPrevia
    ? { disponivel: false, motivo: motivoPrevia }
    : (dadosPesquisa ?? { disponivel: false, motivo: "A prévia não retornou classificações." });
  const modeloMapa = mapaPesquisa ? modeloExperimental : resultado?.ml_alagamento;
  const bairrosMapa = useMemo(() => {
    if (!mapaPesquisa) return bairros;
    const porId = new Map(
      (dadosPesquisa?.disponivel ? dadosPesquisa.itens : []).map((i) => [i.territorio_id, i]),
    );
    return bairros.map((b) => ({ ...b, ml_alagamento: porId.get(b.territorio_id) ?? null }));
  }, [bairros, mapaPesquisa, dadosPesquisa]);
  const [sel, setSel] = useState<string | null>(null);
  const [bairroSel, setBairroSel] = useState<string | null>(null);
  const item: ItemSimulado | undefined = distritos.find((d) => d.territorio_id === sel);
  const calculando = modo === "atual" ? analise.isFetching : calculo.isFetching;
  const estagios = new Set(distritos.map((d) => d.estagio_sugerido ?? "sem_dados"));
  const todosIguais = distritos.length > 1 && estagios.size === 1 && [...estagios][0] !== "sem_dados";
  const rotuloIgual = infoEstagio([...estagios][0]).rotulo;

  // ---- aviso único quando a previsão atual está velha (RF-19)
  const fontes = juntarFontes(modo === "atual" ? analise.data : atuais.data);
  const previsaoVelha = fontes.filter(
    (f: FonteMeta) => f.id.includes("previsao") && f.desatualizado === true,
  );

  // ---- salvar e abrir (RF-27)
  const [dialogo, setDialogo] = useState<"salvar" | "salvos" | null>(null);
  const [nome, setNome] = useState("");
  const [avisoSalvar, setAvisoSalvar] = useState<string | null>(null);
  const salvar = useMutation({
    mutationFn: () => enviar("/cenarios", { nome: nome.trim(), premissas: pronto }),
    onSuccess: () => {
      setAvisoSalvar(`Cenário "${nome.trim()}" salvo.`);
      setNome("");
      void clientes.invalidateQueries({ queryKey: ["/cenarios"] });
    },
    onError: () => setAvisoSalvar(null),
  });
  const abrir = useMutation({
    mutationFn: (id: string) => api<Envelope<CenarioSalvo>>(`/cenarios/${encodeURIComponent(id)}`),
    onSuccess: (r) => {
      setAvisoSalvar(null);
      setModo("manual");
      aplicar(deAtuais(r.dados.premissas));
      setDialogo(null);
    },
  });
  const textoErroSalvar = salvar.error instanceof Error ? salvar.error.message : null;

  return (
    <>
      <CabecalhoTela
        titulo="Simulador de cenário"
        proposito={
          modo === "manual"
            ? "Mude as premissas e veja quais distritos pedem atenção primeiro. Cálculo por regras: o resultado é estágio sugerido, não probabilidade."
            : "Analise a previsão de cada distrito com evidências territoriais. Regras e ML experimental apoiam a decisão humana."
        }
        atualizadoEm={modo === "atual" ? analise.dataUpdatedAt : atuais.dataUpdatedAt}
        acoes={
          <div className={estilos.acoesTopo}>
            <Experimental />
            <Botao variante="secundario" onClick={() => setDialogo("salvos")}>
              Cenários salvos
            </Botao>
            <Botao disabled={modo === "atual"} onClick={() => setDialogo("salvar")}>
              Salvar cenário
            </Botao>
          </div>
        }
      />
      <div className={estilos.pagina}>
        <Segmentado
          rotulo="Tipo de análise"
          valor={modo}
          opcoes={[
            { valor: "manual", rotulo: "Cenário hipotético" },
            { valor: "atual", rotulo: "Previsão por distrito" },
          ]}
          aoMudar={(m) => {
            setModo(m);
            setSel(null);
            setBairroSel(null);
          }}
        />
        <p role="status">
          {modo === "manual"
            ? "Cenário hipotético: as premissas escolhidas são aplicadas aos territórios; não representam a previsão específica de cada distrito."
            : "Previsão atual: cada bairro herda os valores do seu distrito. Avaliação experimental, não é estágio oficial."}
        </p>
        {previsaoVelha.length > 0 && (
          <p className={estilos.avisoVelho} role="status">
            <b>A previsão atual está desatualizada</b>
            {previsaoVelha[0].atualizado_em
              ? ` (última carga ${quandoAs(previsaoVelha[0].atualizado_em)})`
              : ""}
            . Confira o alerta oficial na APAC e no Cemaden antes de decidir.
          </p>
        )}

        {modo === "atual" && resultado && !analise.isError && (
          <SeletorDias
            dias={resultado.dias}
            dia={dia}
            aoDia={(valor) => {
              setDia(valor);
              setSel(null);
              setBairroSel(null);
            }}
          />
        )}
        <div className={estilos.grade}>
          {modo === "manual" ? (
            <PainelPremissas
              form={form}
              atuais={valoresAtuais}
              fontes={fontes}
              fontePorPremissa={fontePorPremissaDe(atuais.data)}
              limiares={limiares}
              carregando={atuais.isPending}
              indisponivel={atuais.isError}
              aoMudar={mudar}
              aoHorizonte={mudarHorizonte}
              aoUsarAtual={() => setEditado(null)}
              aoCenario={aplicarCenario}
            />
          ) : (
            <section className={estilos.painelBloco} aria-label="Previsão atual por distrito">
              <h2>Previsão por distrito</h2>
              {dia && (
                <Botao variante="secundario" onClick={() => setDia("")}>
                  Voltar ao horizonte contínuo
                </Botao>
              )}
              {!dia && (
                <Segmentado
                  rotulo="Horizonte da previsão"
                  valor={horizonteAtual}
                  opcoes={HORIZONTES.map((h) => ({ valor: h, rotulo: `${h} h` }))}
                  aoMudar={setHorizonteAtual}
                />
              )}
              <p>As regras permanecem disponíveis quando há insumos suficientes, mesmo sem modelo de ML.</p>
              {acessoPrevia && (
                <div>
                  <button
                    type="button"
                    aria-pressed={previaLocal}
                    onClick={() => setPreviaLocal((anterior) => !anterior)}
                  >
                    {previaLocal
                      ? "Fechar prévia local NÃO VALIDADA"
                      : "Ver prévia de pesquisa do ML (somente local)"}
                  </button>
                  {previaLocal && (
                    <p role="status">
                      PRÉVIA NÃO VALIDADA: resultados exclusivamente para pesquisa e demonstração acadêmica.
                      Não são alertas e não podem orientar decisões operacionais.
                      {modeloExperimental?.disponivel
                        ? " Prévia acadêmica calculada. Consulte as classes e os bairros sem classificação na tabela."
                        : ` ${modeloExperimental?.motivo}`}
                    </p>
                  )}
                </div>
              )}
              {resultado?.ml_alagamento && (
                <p role="status">
                  {resultado.ml_alagamento.disponivel
                    ? `ML operacional disponível, versão ${resultado.ml_alagamento.modelo?.versao ?? "não informada"}. Resultado paralelo à avaliação por regras.`
                    : `ML operacional indisponível: ${resultado.ml_alagamento.motivo ?? "aguarda validação"}. Consulte separadamente o estado da prévia acadêmica.`}
                </p>
              )}
            </section>
          )}

          <div className={estilos.colunaResultado} aria-busy={calculando}>
            <Resultado
              pronto={modo === "atual" ? null : pronto}
              invalido={modo === "manual" && premissas === null}
              carregandoAtuais={modo === "atual" ? analise.isPending : atuais.isPending}
              erro={modo === "atual" ? analise.error : calculo.error}
              resultado={resultado}
              aoTentar={() => void (modo === "atual" ? analise.refetch() : calculo.refetch())}
            >
              <MapaDoCenario
                bairros={bairrosMapa}
                aviso={resultado?.resumo?.impacto_pessoas_aviso ?? null}
                selecionado={bairroSel}
                aoSelecionar={setBairroSel}
                contexto={modo}
                mlAlagamento={modo === "atual" ? modeloMapa : undefined}
                previaLocal={mapaPesquisa}
                preventiva={Boolean(dia && resultado?.dia_selecionado === dia)}
              />
            </Resultado>
          </div>
        </div>

        {modo === "atual" && resultado && !analise.isError && (
          <PrevisaoPreventiva
            resultado={resultado}
            dia={dia}
            bairros={bairrosMapa}
            ml={modeloExperimental}
            atualizando={analise.isFetching}
            fontes={fontes}
          />
        )}

        {resultado && (
          <>
            {todosIguais && (
              <p className={estilos.aviso} role="status">
                {modo === "manual" ? "Neste cenário" : "Nesta avaliação"} todos os distritos ficam em{" "}
                <b>{rotuloIgual}</b>: a diferença está no risco de cada bairro (veja o mapa).
              </p>
            )}
            <EstagioPorDistrito distritos={distritos} selecionado={sel} aoEscolher={setSel} />
            {item && <DetalheDistrito item={item} aviso={resultado.resumo?.impacto_pessoas_aviso ?? null} />}
          </>
        )}

        {resultado && <OrdemAtencao resultado={resultado} distritos={distritos} aoEscolher={setSel} />}
        <p className={estilos.apoio}>
          Previsão e histórico de chuva: <Link to="/app/chuva">abrir Chuva</Link>.
        </p>
      </div>

      <Dialogo
        aberto={dialogo === "salvar"}
        aoMudar={(a) => !a && setDialogo(null)}
        titulo="Salvar cenário"
        descricao="Guarda as premissas, não dados de pessoas."
        acoes={
          <>
            <Botao variante="secundario" onClick={() => setDialogo(null)}>
              Fechar
            </Botao>
            <Botao
              type="submit"
              form="form-salvar-cenario"
              disabled={!nome.trim() || !pronto || !podeSimular(pronto) || salvar.isPending}
            >
              Salvar cenário
            </Botao>
          </>
        }
      >
        <form
          id="form-salvar-cenario"
          className={estilos.salvar}
          onSubmit={(e) => {
            e.preventDefault();
            if (nome.trim() && pronto) salvar.mutate();
          }}
        >
          <Campo
            rotulo="Nome do cenário"
            value={nome}
            maxLength={80}
            onChange={(e) => setNome(e.target.value)}
            ajuda="Por exemplo: Chuva forte de maio."
          />
        </form>
        {avisoSalvar && (
          <p role="status" className={estilos.ok}>
            {avisoSalvar}
          </p>
        )}
        {textoErroSalvar && (
          <p role="alert" className={estilos.erroSalvar}>
            Não foi possível salvar: {textoErroSalvar}
          </p>
        )}
      </Dialogo>

      <Dialogo
        aberto={dialogo === "salvos"}
        aoMudar={(a) => !a && setDialogo(null)}
        titulo="Cenários salvos"
        acoes={
          <Botao variante="secundario" onClick={() => setDialogo(null)}>
            Fechar
          </Botao>
        }
      >
        <Salvos consulta={salvos} abrindo={abrir.isPending} aoAbrir={(id) => abrir.mutate(id)} />
        {abrir.isError && (
          <p role="alert" className={estilos.erroSalvar}>
            Não foi possível abrir o cenário: {abrir.error.message}
          </p>
        )}
      </Dialogo>
    </>
  );
}

function Resultado({
  pronto,
  invalido,
  carregandoAtuais,
  erro,
  resultado,
  aoTentar,
  children,
}: {
  pronto: Premissas | null;
  invalido: boolean;
  carregandoAtuais: boolean;
  erro: ErroApi | null;
  resultado: ResultadoSimulacao | undefined;
  aoTentar: () => void;
  children: React.ReactNode;
}) {
  if (carregandoAtuais)
    return <CarregandoLista linhas={2} altura="5rem" texto="Buscando os valores atuais…" />;
  if (invalido)
    return (
      <EstadoDados tipo="insuficiente" titulo="Confira os campos em vermelho.">
        O cenário só é calculado com números válidos.
      </EstadoDados>
    );
  if (pronto !== null && !podeSimular(pronto))
    return (
      <EstadoDados tipo="insuficiente" titulo="Dados insuficientes para simular.">
        {temAlgumDado(pronto)
          ? "Falta a chuva prevista (fonte: Open-Meteo). Escolha um cenário pronto ou mova a chuva prevista para ver o resultado."
          : "Nenhuma fonte trouxe os valores atuais. Escolha um cenário pronto ou mova a chuva prevista para ver o resultado."}
      </EstadoDados>
    );
  if (erro && !resultado)
    return <EstadoConsulta erro={erro} oQue="o cálculo do cenário" aoTentar={aoTentar} />;
  if (!resultado) return <CarregandoLista linhas={2} altura="5rem" texto="Calculando…" />;
  return (
    <>
      {erro && <p className={estilos.apoio}>Não foi possível atualizar: a tela mostra o cálculo anterior.</p>}
      {children}
    </>
  );
}

function Salvos({
  consulta,
  abrindo,
  aoAbrir,
}: {
  consulta: ReturnType<typeof useConsulta<Envelope<CenarioSalvo[]>>>;
  abrindo: boolean;
  aoAbrir: (id: string) => void;
}) {
  if (consulta.isPending) return <CarregandoLista linhas={2} altura="3rem" texto="Carregando os cenários…" />;
  if (consulta.isError)
    return (
      <EstadoConsulta
        erro={consulta.error}
        oQue="os cenários salvos"
        aoTentar={() => void consulta.refetch()}
      />
    );
  const lista = consulta.data?.dados ?? [];
  if (lista.length === 0)
    return <p className={estilos.apoio}>Nenhum cenário salvo ainda. Salve um para consultar depois.</p>;
  return (
    <ul className={estilos.salvosLista}>
      {lista.map((c) => (
        <li key={c.id}>
          <button type="button" disabled={abrindo} onClick={() => aoAbrir(c.id)}>
            <span>
              {c.nome}
              {c.criado_em && <small> Salvo {quandoRelativo(c.criado_em)}</small>}
            </span>
            <span>Abrir</span>
          </button>
        </li>
      ))}
    </ul>
  );
}
