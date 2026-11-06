import { useCallback, useEffect, useMemo, useState } from "react";
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Save, X } from "lucide-react";
import { token, useTemaAtual } from "@/charts/tema";
import { Botao } from "@/design-system/componentes/Botao";
import { CabecalhoTela } from "@/design-system/componentes/CabecalhoTela";
import { Campo } from "@/design-system/componentes/Campo";
import { CarregandoLista, Esqueleto } from "@/design-system/componentes/Esqueleto";
import {
  EstadoDados,
  LegendaFonte,
  SeloDesatualizado,
  fontesDado,
} from "@/design-system/componentes/EstadoDados";
import { FalhaCarga, Painel } from "@/design-system/componentes/Painel";
import { Experimental, Pilula } from "@/design-system/componentes/Pilula";
import { Segmentado } from "@/design-system/componentes/Segmentado";
import { api, enviar, type ErroApi } from "@/lib/api";
import { useConsulta } from "@/lib/consultas";
import { formatarHoraMinuto, formatarNumero, quandoRelativo } from "@/lib/formatos";
import { juntarFontes } from "@/lib/frescor";
import { useSessao } from "@/lib/sessao";
import { MapaBairros, type Aparencia, type ColecaoFeicoes } from "@/map/MapaBairros";
import type { ColecaoDistritos } from "@/map/MapaTerritorio";
import { distritoPorExtenso } from "@/textos/glossario";
import { EstadoConsulta } from "@/features/evento/Evento";
import { TOKEN_ESTAGIO } from "@/features/territorio/indicadoresMapa";
import estilosMapa from "@/features/mapa/Mapa.module.css";
import { useCamadas } from "@/features/mapa/usarCamadas";
import { CoberturaNoMapa, ControleCamadas, LegendaCamadas } from "@/features/mapa/PainelCamadas";
import {
  AVISO_DEFICIENCIA,
  INDICADORES,
  impactoDe,
  somaExposta,
  textoPessoas,
  valorDe,
} from "@/features/mapa/modeloCamadas";
import { PainelPremissas } from "./Premissas";
import {
  CLASSES,
  NIVEL_CLASSE,
  ROTULO_CLASSE,
  VISOES,
  classeDoItem,
  contar,
  deAtuais,
  fraseResumo,
  formatarSegundos,
  ordemDaClasse,
  paraPremissas,
  pressaoAbrigos,
  temAlgumDado,
  type CampoNumerico,
  type CenarioSalvo,
  type Formulario,
  type ItemSimulado,
  type Premissas,
  type ResultadoSimulacao,
  type Visao,
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

const ROTULO_MAPA =
  "Mapa dos bairros do Recife coloridos pela classe do cenário simulado. Use as setas para mover e as teclas + e - para aproximar. " +
  "Para escolher um bairro sem o mapa, use a lista de bairros logo abaixo.";

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
 * Simulador de cenário: a pessoa muda as premissas da chuva e o mapa dos 94 bairros se recalcula sozinho.
 * Estimativa por regras, sempre com o selo Experimental (RN-11). Classe, nunca percentual (RN-06).
 */
export function TelaSimulador() {
  const { usuario } = useSessao();
  useTemaAtual();
  const clientes = useQueryClient();
  const camadas = useCamadas();

  const atuais = useConsulta<Envelope<Partial<Premissas>>>("/cenarios/premissas-atuais", {
    staleTime: 5 * 60_000,
  });
  const geoBairros = useConsulta<ColecaoFeicoes>("/territorios/bairros.geojson", { staleTime: 30 * 60_000 });
  const geoDistritos = useConsulta<ColecaoDistritos>("/territorios/distritos.geojson", {
    staleTime: 30 * 60_000,
  });
  const prioridade = useConsulta<{ dados?: { itens?: { territorio_id: string; posicao: number }[] } }>(
    "/territorios/prioridade",
    { staleTime: 10 * 60_000 },
  );
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
  const alterado = editado !== null && JSON.stringify(editado) !== JSON.stringify(base);

  const mudar = (campo: CampoNumerico, valor: string) => setEditado({ ...form, [campo]: valor });
  const mudarHorizonte = (h: number) => setEditado({ ...form, horizonte_h: h });
  const aplicar = (f: Formulario) => {
    setEditado(f);
    setPronta(paraPremissas(f));
  };

  // ---- cálculo: recalcula sozinho ao mudar a premissa (RF-24, RF-28)
  const calculo = useQuery<Envelope<ResultadoSimulacao>, ErroApi>({
    queryKey: ["simulador", pronto ? JSON.stringify(pronto) : null],
    queryFn: () => enviar<Envelope<ResultadoSimulacao>>("/cenarios/simular", pronto),
    enabled: pronto !== null && temAlgumDado(pronto),
    placeholderData: keepPreviousData,
    staleTime: 5 * 60_000,
    retry: false,
  });
  const resultado = calculo.data?.dados;
  const itens = useMemo(() => resultado?.itens ?? [], [resultado]);
  const porId = useMemo(() => new Map(itens.map((i) => [i.territorio_id, i] as const)), [itens]);
  const calculando = calculo.isFetching;

  // ---- mapa
  const [visao, setVisao] = useState<Visao>("alagamento");
  const [contorno, setContorno] = useState(true);
  const [sel, setSel] = useState<string | null>(null);
  useEffect(() => {
    if (!sel) return;
    const aoTeclar = (e: KeyboardEvent) => e.key === "Escape" && setSel(null);
    document.addEventListener("keydown", aoTeclar);
    return () => document.removeEventListener("keydown", aoTeclar);
  }, [sel]);

  const aparencia = useCallback(
    (id: string): Aparencia => {
      const ordem = classeDoItem(porId.get(id), visao);
      return {
        ordem,
        origem: ordem === null ? "sem_dados" : visao === "situacao" ? "sugerido" : "declarado",
      };
    },
    [porId, visao],
  );
  const modoPopulacao = camadas.modo === "populacao";
  const porBairroPop = camadas.populacao.porBairro;
  const indicadorPop = camadas.indicador;
  const dica = useCallback(
    (id: string, nome: string) => {
      if (modoPopulacao) {
        const pop = valorDe(porBairroPop.get(id), indicadorPop);
        const rotulo = INDICADORES.find((i) => i.valor === indicadorPop)?.rotulo ?? "";
        return `<strong>${nome.replace(/</g, "&lt;")}</strong><br>${rotulo}: ${textoPessoas(pop)}`;
      }
      const o = classeDoItem(porId.get(id), visao);
      const texto = o === null ? "Dados insuficientes" : ROTULO_CLASSE[o];
      return `<strong>${nome.replace(/</g, "&lt;")}</strong><br>${texto}`;
    },
    [porId, visao, modoPopulacao, porBairroPop, indicadorPop],
  );

  const posicao = useMemo(
    () => new Map((prioridade.data?.dados?.itens ?? []).map((p) => [p.territorio_id, p.posicao] as const)),
    [prioridade.data],
  );
  const ordenados = useMemo(
    () =>
      [...itens].sort((a, b) => {
        const oa = classeDoItem(a, visao) ?? -1;
        const ob = classeDoItem(b, visao) ?? -1;
        return (
          ob - oa ||
          (posicao.get(a.territorio_id) ?? 9999) - (posicao.get(b.territorio_id) ?? 9999) ||
          a.nome.localeCompare(b.nome, "pt-BR")
        );
      }),
    [itens, visao, posicao],
  );
  const contagem = useMemo(() => contar(itens, visao), [itens, visao]);
  const item = sel ? porId.get(sel) : undefined;

  // ---- salvar e abrir (RF-27)
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
      aplicar(deAtuais(r.dados.premissas));
    },
  });

  const fontes = fontesDado(juntarFontes(atuais.data, calculo.data));
  const semBairros = geoBairros.isError;
  const territorios = geoBairros.data;
  const textoErroSalvar = salvar.error instanceof Error ? salvar.error.message : null;

  return (
    <>
      <CabecalhoTela
        titulo="Simulador"
        proposito="Mude a chuva, a maré ou os abrigos e veja quais bairros ficam mais expostos. O mapa se atualiza sozinho."
        atualizadoEm={atuais.dataUpdatedAt}
        acoes={<Experimental />}
      />
      <div className={estilos.pagina}>
        <PainelPremissas
          form={form}
          atuais={valoresAtuais}
          fontes={juntarFontes(atuais.data)}
          fontePorPremissa={fontePorPremissaDe(atuais.data)}
          carregando={atuais.isPending}
          indisponivel={atuais.isError}
          alterado={alterado}
          aoMudar={mudar}
          aoHorizonte={mudarHorizonte}
          aoVoltar={() => setEditado(null)}
        />

        <section className={estilos.resultado} aria-labelledby="sim-resultado" aria-busy={calculando}>
          <h2 id="sim-resultado" className="so-leitor">
            Resultado do cenário
          </h2>
          <ResumoResultado
            premissas={pronto}
            itens={itens}
            visao={visao}
            resultado={resultado}
            calculando={calculando}
            erro={calculo.error}
            aoTentar={() => void calculo.refetch()}
            semDados={pronto !== null && !temAlgumDado(pronto)}
            invalido={premissas === null}
            carregandoAtuais={atuais.isPending}
          />
          {itens.length > 0 && <Contagem contagem={contagem} />}
        </section>

        <div className={estilos.corpo}>
          <div className={estilos.colunaMapa}>
            <div className={estilos.barraMapa}>
              <Segmentado
                rotulo="Colorir o mapa por"
                opcoes={VISOES.map((v) => ({ valor: v.valor, rotulo: v.rotulo }))}
                valor={visao}
                aoMudar={setVisao}
              />
              <label className={estilos.camada}>
                <input type="checkbox" checked={contorno} onChange={(e) => setContorno(e.target.checked)} />
                Contorno dos distritos
              </label>
            </div>
            <section
              className={[estilosMapa.mapa, estilos.mapa].join(" ")}
              data-calculando={calculando}
              aria-label="Mapa dos bairros por classe do cenário"
            >
              {geoBairros.isPending && (
                <div className={estilosMapa.esqueletoMapa} aria-busy="true">
                  <Esqueleto forma="bloco" altura="100%" />
                  <span className="so-leitor" role="status">
                    Carregando o mapa…
                  </span>
                </div>
              )}
              {semBairros && (
                <FalhaCarga erro={geoBairros.error} aoTentar={() => void geoBairros.refetch()} />
              )}
              {territorios && (
                <MapaBairros
                  territorios={territorios}
                  contorno={contorno ? geoDistritos.data : null}
                  tilesUrl={usuario?.mapa_tiles_url ?? ""}
                  rotulo={ROTULO_MAPA}
                  aparencia={aparencia}
                  dica={dica}
                  selecionado={sel}
                  aoSelecionar={setSel}
                  tokensEstagio={TOKEN_ESTAGIO}
                  {...camadas.propsMapa}
                />
              )}
              <CoberturaNoMapa c={camadas} />
              {calculando && (
                <p className={estilos.calculando} role="status">
                  Calculando…
                </p>
              )}
            </section>
            <ControleCamadas c={camadas} rotuloBase="Classe do cenário" />
            {camadas.modo === "estagio" && <Legenda visao={visao} />}
            <LegendaCamadas c={camadas} />
            {fontes.length > 0 && (
              <div className={estilos.fontes}>
                {fontes.some((f) => f.desatualizado === true) && (
                  <p data-aviso="desatualizado">
                    <SeloDesatualizado /> Alguma fonte está vencida: confira antes de decidir.
                  </p>
                )}
                <details>
                  <summary>Fontes do cenário e hora de cada uma ({fontes.length})</summary>
                  <LegendaFonte fontes={fontes} />
                </details>
              </div>
            )}
          </div>

          <div className={estilos.colunaLateral}>
            {item ? (
              <PainelBairro
                item={item}
                aviso={resultado?.resumo?.impacto_pessoas_aviso ?? null}
                aoFechar={() => setSel(null)}
              />
            ) : (
              <p className={estilosMapa.dicaClique}>
                Toque em um bairro no mapa, ou escolha na lista, para ver o motivo da classe.
              </p>
            )}
            <ListaPorClasse itens={ordenados} visao={visao} selecionado={sel} aoEscolher={setSel} />
            <Painel id="sim-salvar" titulo="Salvar este cenário">
              <form
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
                  ajuda="Por exemplo: Chuva forte de maio. Guarda as premissas, não dados de pessoas."
                />
                <Botao
                  type="submit"
                  icone={<Save size={18} />}
                  disabled={!nome.trim() || !pronto || !temAlgumDado(pronto) || salvar.isPending}
                >
                  Salvar cenário
                </Botao>
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
            </Painel>
            <Painel id="sim-salvos" titulo="Cenários salvos">
              <Salvos consulta={salvos} abrindo={abrir.isPending} aoAbrir={(id) => abrir.mutate(id)} />
              {abrir.isError && (
                <p role="alert" className={estilos.erroSalvar}>
                  Não foi possível abrir o cenário: {abrir.error.message}
                </p>
              )}
            </Painel>
          </div>
        </div>
      </div>
    </>
  );
}

function ResumoResultado({
  premissas,
  itens,
  visao,
  resultado,
  calculando,
  erro,
  aoTentar,
  semDados,
  invalido,
  carregandoAtuais,
}: {
  premissas: Premissas | null;
  itens: ItemSimulado[];
  visao: Visao;
  resultado: ResultadoSimulacao | undefined;
  calculando: boolean;
  erro: ErroApi | null;
  aoTentar: () => void;
  semDados: boolean;
  invalido: boolean;
  carregandoAtuais: boolean;
}) {
  if (carregandoAtuais)
    return <CarregandoLista linhas={1} altura="4rem" texto="Buscando os valores atuais…" />;
  if (invalido)
    return (
      <EstadoDados tipo="insuficiente" titulo="Confira os campos em vermelho.">
        O cenário só é calculado com números válidos.
      </EstadoDados>
    );
  if (semDados)
    return (
      <EstadoDados tipo="insuficiente" titulo="Dados insuficientes para simular.">
        Nenhuma fonte trouxe os valores atuais. Digite a chuva prevista, a maré ou os abrigos para ver o
        cenário.
      </EstadoDados>
    );
  if (erro && !resultado)
    return <EstadoConsulta erro={erro} oQue="o cálculo do cenário" aoTentar={aoTentar} />;
  if (!resultado || !premissas) return <CarregandoLista linhas={1} altura="4rem" texto="Calculando…" />;

  const pressao = pressaoAbrigos(resultado.resumo?.pressao_abrigos);
  const pedeAbrigos = premissas.abrigos_abertos === null || premissas.capacidade_abrigos === null;
  return (
    <div className={estilos.resumo}>
      <p className={estilos.frase}>{fraseResumo(premissas, itens, visao)}</p>
      <p className={estilos.estado} role="status">
        {calculando
          ? "Calculando…"
          : resultado.tempo_calculo_ms !== null && resultado.tempo_calculo_ms !== undefined
            ? `Calculado em ${formatarSegundos(resultado.tempo_calculo_ms)}`
            : "Calculado agora"}
        {!calculando && resultado.calculado_em ? `, às ${formatarHoraMinuto(resultado.calculado_em)}` : ""}.
        {erro && " Não foi possível atualizar: o mapa mostra o cálculo anterior."}
      </p>
      <ExpostosNoResumo resumo={resultado.resumo} />
      <p className={estilos.abrigos}>
        <b>Pressão nos abrigos:</b>{" "}
        {pressao ? (
          pressao.ordem !== null ? (
            <Pilula nivel={NIVEL_CLASSE[pressao.ordem]}>{pressao.texto}</Pilula>
          ) : (
            pressao.texto
          )
        ) : (
          <>
            Dados insuficientes
            {pedeAbrigos ? ": informe os abrigos abertos e a capacidade." : "."}
          </>
        )}
      </p>
    </div>
  );
}

/** Residentes do bairro e equipamentos de saúde: contagem, nunca percentual (RN-06). Sem dado, nunca zero (RN-01). */
function PopulacaoExposta({
  impacto,
  aviso,
}: {
  impacto: ReturnType<typeof impactoDe>;
  aviso: string | null;
}) {
  if (!impacto)
    return (
      <p className={estilosMapa.apagado}>
        {aviso ??
          "Dados insuficientes: sem estágio de atenção ou mais neste bairro, ou falta a fonte IBGE (Censo 2022)."}
      </p>
    );
  const n = (v: number | null | undefined) =>
    v === null || v === undefined ? "Dados insuficientes" : formatarNumero(v);
  return (
    <>
      <dl className={estilosMapa.numeros}>
        <div>
          <dt>Idosos (60 anos ou mais)</dt>
          <dd>
            <b>{n(impacto.idosos_60_mais)}</b>
            {impacto.idosos_60_mais != null && <small>residentes</small>}
          </dd>
        </div>
        <div>
          <dt>Crianças (0 a 14 anos)</dt>
          <dd>
            <b>{n(impacto.criancas_0_14)}</b>
            {impacto.criancas_0_14 != null && <small>residentes</small>}
          </dd>
        </div>
        <div>
          <dt>Equipamentos de saúde</dt>
          <dd>
            <b>{n(impacto.equipamentos_saude)}</b>
            {impacto.equipamentos_saude != null && <small>no bairro</small>}
          </dd>
        </div>
        <div>
          <dt>Pessoas com deficiência</dt>
          <dd>
            <b>Dados insuficientes</b>
            <small>{AVISO_DEFICIENCIA}</small>
          </dd>
        </div>
      </dl>
      <p className={estilosMapa.fonteLinha}>
        Moradores do bairro, não pessoas atingidas. Fonte: IBGE, Censo 2022 e CNES.
      </p>
    </>
  );
}

function ExpostosNoResumo({ resumo }: { resumo: ResultadoSimulacao["resumo"] }) {
  const s = somaExposta(resumo);
  if (!s) return null;
  if (s.bairros_em_alerta === 0)
    return (
      <p className={estilos.abrigos}>
        <b>Moradores vulneráveis expostos:</b> nenhum bairro em alerta ou acima neste cenário.
      </p>
    );
  const parte = (v: number | null | undefined, rotulo: string) =>
    v === null || v === undefined ? `${rotulo}: dados insuficientes` : `${formatarNumero(v)} ${rotulo}`;
  return (
    <p className={estilos.abrigos} data-testid="expostos-resumo">
      <b>Moradores vulneráveis em bairros em alerta ou acima:</b> {parte(s.idosos_60_mais, "idosos 60+")} e{" "}
      {parte(s.criancas_0_14, "crianças 0–14")}.{s.parcial && " Soma parcial: algum bairro está sem número."}
    </p>
  );
}

function Contagem({ contagem }: { contagem: { por: number[]; sem: number } }) {
  return (
    <ul className={estilos.contagem} aria-label="Bairros por classe">
      {[3, 2, 1, 0].map((o) => (
        <li key={o} data-classe={CLASSES[o]} data-zero={contagem.por[o] === 0}>
          <b>{formatarNumero(contagem.por[o])}</b> {ROTULO_CLASSE[o]}
        </li>
      ))}
      <li data-classe="sem_dados" data-zero={contagem.sem === 0}>
        <b>{formatarNumero(contagem.sem)}</b> Dados insuficientes
      </li>
    </ul>
  );
}

function Legenda({ visao }: { visao: Visao }) {
  useTemaAtual();
  return (
    <div className={estilosMapa.legenda} role="group" aria-label="Legenda do mapa">
      <ul>
        {ROTULO_CLASSE.map((r, i) => (
          <li key={r}>
            <i
              className={visao === "situacao" ? estilosMapa.corListrada : undefined}
              style={
                visao === "situacao"
                  ? { borderColor: token(TOKEN_ESTAGIO[i]) }
                  : { background: token(TOKEN_ESTAGIO[i]) }
              }
              aria-hidden="true"
            />
            {r}
          </li>
        ))}
        <li>
          <i className={estilosMapa.corSemDado} aria-hidden="true" />
          Dados insuficientes
        </li>
      </ul>
      <p className={estilosMapa.legendaNota}>
        Cinza tracejado não quer dizer risco baixo: falta dado. A cor é uma classe estimada, não uma chance.
      </p>
    </div>
  );
}

function PainelBairro({
  item,
  aviso: avisoImpacto,
  aoFechar,
}: {
  item: ItemSimulado;
  aviso: string | null;
  aoFechar: () => void;
}) {
  const classe = (v: string | null | undefined) => {
    const o = ordemDaClasse(v);
    return o === null ? (
      <Pilula nivel="insuficiente">Dados insuficientes</Pilula>
    ) : (
      <Pilula nivel={NIVEL_CLASSE[o]}>{ROTULO_CLASSE[o]}</Pilula>
    );
  };
  const motivos = item.motivos ?? [];
  const semMotivo = classeDoItem(item, "alagamento") === null && classeDoItem(item, "deslizamento") === null;
  return (
    <section className={estilosMapa.painel} aria-labelledby="sim-bairro" data-testid="painel-bairro">
      <div className={estilosMapa.painelTopo}>
        <div>
          <h2 id="sim-bairro">{item.nome}</h2>
          {item.distrito_id && (
            <p className={estilosMapa.painelDistrito}>{distritoPorExtenso(item.distrito_id)}</p>
          )}
        </div>
        <button type="button" className={estilosMapa.fechar} onClick={aoFechar} aria-label="Fechar o painel">
          <X aria-hidden="true" />
        </button>
      </div>
      <dl className={estilosMapa.dupla}>
        <div>
          <dt>Alagamento</dt>
          <dd>{classe(item.classe_alagamento)}</dd>
        </div>
        <div>
          <dt>Deslizamento</dt>
          <dd>{classe(item.classe_deslizamento)}</dd>
        </div>
        <div>
          <dt>Situação sugerida</dt>
          <dd>{classe(item.estagio_sugerido)}</dd>
        </div>
        <div>
          <dt>Confiança</dt>
          <dd>{item.confianca ? <span>{item.confianca}</span> : <span>Sem dado</span>}</dd>
        </div>
      </dl>
      <div className={estilosMapa.bloco}>
        <h3>Por que esta classe</h3>
        {motivos.length > 0 ? (
          <ul className={estilos.motivos}>
            {motivos.map((m) => (
              <li key={m}>{m}</li>
            ))}
          </ul>
        ) : (
          <p className={estilosMapa.apagado}>
            {semMotivo
              ? "Dados insuficientes: falta dado de uma das fontes para explicar este bairro."
              : "O cálculo não trouxe motivo para este bairro."}
          </p>
        )}
      </div>
      <div className={estilosMapa.bloco}>
        <h3>População vulnerável exposta</h3>
        <PopulacaoExposta impacto={impactoDe(item.impacto_pessoas)} aviso={avisoImpacto} />
      </div>
      <p className={estilos.estimativa}>
        <Experimental /> Estimativa por regras, ainda sem validação. Confira o alerta oficial na APAC e no
        Cemaden.
      </p>
    </section>
  );
}

const LIMITE = 12;

function ListaPorClasse({
  itens,
  visao,
  selecionado,
  aoEscolher,
}: {
  itens: ItemSimulado[];
  visao: Visao;
  selecionado: string | null;
  aoEscolher: (id: string) => void;
}) {
  const [todos, setTodos] = useState(false);
  const visiveis = todos ? itens : itens.slice(0, LIMITE);
  return (
    <Painel
      id="sim-lista"
      titulo="Bairros, do mais exposto ao menos"
      dica="É o mesmo resultado do mapa, em lista. Bairros sem dado ficam no fim, sem classe."
    >
      {itens.length === 0 ? (
        <p className={estilosMapa.apagado}>Os bairros aparecem aqui quando o cenário for calculado.</p>
      ) : (
        <>
          <ul className={estilosMapa.prioritarios}>
            {visiveis.map((i) => {
              const o = classeDoItem(i, visao);
              return (
                <li key={i.territorio_id}>
                  <button
                    type="button"
                    className={estilosMapa.itemPrioritario}
                    aria-pressed={selecionado === i.territorio_id}
                    onClick={() => aoEscolher(i.territorio_id)}
                  >
                    <span className={estilos.itemNome}>{i.nome}</span>
                    {o === null ? (
                      <Pilula nivel="insuficiente" pequena>
                        Dados insuficientes
                      </Pilula>
                    ) : (
                      <Pilula nivel={NIVEL_CLASSE[o]} pequena>
                        {ROTULO_CLASSE[o]}
                      </Pilula>
                    )}
                  </button>
                </li>
              );
            })}
          </ul>
          {itens.length > LIMITE && (
            <Botao variante="discreto" onClick={() => setTodos((t) => !t)} aria-expanded={todos}>
              {todos ? "Mostrar só os primeiros" : `Ver todos os ${itens.length} bairros`}
            </Botao>
          )}
        </>
      )}
    </Painel>
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
    return <p className={estilosMapa.apagado}>Nenhum cenário salvo ainda. Salve um para consultar depois.</p>;
  return (
    <ul className={estilosMapa.prioritarios}>
      {lista.map((c) => (
        <li key={c.id}>
          <button
            type="button"
            className={estilosMapa.itemPrioritario}
            disabled={abrindo}
            onClick={() => aoAbrir(c.id)}
          >
            <span className={estilos.itemNome}>
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
