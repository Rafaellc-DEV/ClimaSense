import { useRef } from "react";
import { Copy, Printer } from "lucide-react";
import { CabecalhoTela } from "@/design-system/componentes/CabecalhoTela";
import { useAviso } from "@/design-system/componentes/Aviso";
import { Botao } from "@/design-system/componentes/Botao";
import { CarregandoLista } from "@/design-system/componentes/Esqueleto";
import { Marca } from "@/design-system/componentes/Marca";
import { consulta, enviar, ErroApi, type Esquemas } from "@/lib/api";
import { useConsulta } from "@/lib/consultas";
import { diaNoRecife, formatarData, formatarHora, formatarMm, formatarNumero } from "@/lib/formatos";
import { noProduto } from "@/lib/fontes";
import { useSessao } from "@/lib/sessao";
import { infoEstagio } from "@/features/evento/estagios";
import { EstadoConsulta, MensagemPronta } from "@/features/evento/Evento";
import {
  atualizada,
  diaMes,
  listaEmFrase,
  nomeCurto,
  quandoAs,
  useFontesResumo,
} from "@/features/evento/textos";
import { listaDe, type Acao } from "@/features/evento/tipos";
import { eventoAtual, montarLinha, PREFIXO_BOLETIM, type Declaracao } from "@/features/registro/linhaTempo";
import { corpoRegistro } from "@/features/registro/TelaRegistro";
import { dadosDe, NIVEL_ALERTA, type ResumoSaude } from "@/features/saude/tipos";
import estilos from "./Boletim.module.css";

type Boletim = Esquemas["Boletim"];
type Distrito = Boletim["estagios"][number];

/** BOL-2026-1105-1700: ano, mês e dia, hora e minuto da emissão (hora do Recife). */
export function numeroBoletim(em: Date): string {
  const [a, m, d] = diaNoRecife(em).split("-");
  return `BOL-${a}-${m}${d}-${formatarHora(em).replace("h", "")}`;
}

const ordemPorNome = (a: Distrito, b: Distrito) =>
  a.territorio_nome.localeCompare(b.territorio_nome, "pt-BR", { numeric: true });

/** Frase da situação: só a declarada pela equipe. A sugestão do sistema não entra no boletim. */
function fraseSituacao(ds: Distrito[]): string {
  const declarados = ds.filter((d) => d.declarado);
  if (ds.length === 0) return "Sem informação da situação dos distritos.";
  if (declarados.length === 0) return "Nenhum distrito tem situação declarada pela equipe.";
  const grupos = new Map<string, string[]>();
  for (const d of [...declarados].sort(
    (a, b) => infoEstagio(b.declarado?.estagio).ordem - infoEstagio(a.declarado?.estagio).ordem,
  )) {
    const r = infoEstagio(d.declarado?.estagio).rotulo;
    grupos.set(r, [...(grupos.get(r) ?? []), nomeCurto(d.territorio_nome)]);
  }
  const partes = [...grupos.entries()].map(([r, n]) => `${listaEmFrase(n)} em ${r}`);
  const resto = ds.length - declarados.length;
  return `${partes.join("; ")}.${
    resto ? ` ${resto === 1 ? "Um distrito está" : `Os outros ${resto} estão`} sem declaração.` : ""
  }`;
}

function fraseChuva(c: Boletim["chuva"]): string {
  const ult =
    c.chuva_24h_mm === null
      ? "Sem leitura da chuva das últimas 24 h"
      : `Nas últimas 24 h choveu até ${formatarMm(c.chuva_24h_mm)}${
          c.chuva_24h_territorio ? ` (${nomeCurto(c.chuva_24h_territorio)})` : ""
        }`;
  const prev =
    c.chuva_prev_72h_mm === null
      ? "a previsão para os próximos 3 dias está indisponível"
      : `a previsão para os próximos 3 dias é de até ${formatarMm(c.chuva_prev_72h_mm)}${
          c.chuva_prev_72h_territorio ? ` (${nomeCurto(c.chuva_prev_72h_territorio)})` : ""
        }`;
  return `${ult}; ${prev}.`;
}

function fraseAbrigosSaude(
  b: Boletim | undefined,
  saude: ResumoSaude | undefined,
  saudeFalhou: boolean,
): string {
  const t = b?.abrigos.totais;
  const abrigos = !t
    ? "Sem informação de abrigos"
    : t.abrigos_cadastrados === 0 || t.abrigos_abertos === null
      ? "Sem informação de abrigos"
      : t.abrigos_abertos === 0
        ? "Nenhum abrigo aberto"
        : t.abrigos_abertos === 1
          ? "1 abrigo aberto"
          : `${formatarNumero(t.abrigos_abertos)} abrigos abertos`;
  const j = saude?.janela_leptospirose;
  const lepto = j?.ativa
    ? `janela de vigilância de leptospirose aberta até ${diaMes(j.fim)}`
    : saude
      ? "nenhuma janela de vigilância de leptospirose aberta"
      : saudeFalhou
        ? "dados de saúde ainda não disponíveis"
        : "";
  return lepto ? `${abrigos}; ${lepto}.` : `${abrigos}.`;
}

/** Destaques em tópicos, só com o que existe nos dados. */
function destaques(b: Boletim | undefined, saude: ResumoSaude | undefined, registros: number): string[] {
  const s: string[] = [];
  if (b) {
    for (const d of b.estagios) {
      const sug = infoEstagio(d.sugerido?.estagio).ordem;
      const dec = d.declarado ? infoEstagio(d.declarado.estagio).ordem : 0;
      if (sug >= 1 && sug > dec)
        s.push(
          `${nomeCurto(d.territorio_nome)}: o sistema sugere ${
            infoEstagio(d.sugerido.estagio).rotulo
          }, acima do declarado.`,
        );
    }
    if (b.chuva.chuva_prev_24h_mm !== null)
      s.push(
        `Maior chuva prevista em 24 h: ${formatarMm(b.chuva.chuva_prev_24h_mm)}${
          b.chuva.chuva_prev_24h_territorio ? ` no ${nomeCurto(b.chuva.chuva_prev_24h_territorio)}` : ""
        }.`,
      );
    if (b.mare.maxima_m !== null)
      s.push(
        `Maré mais alta: ${formatarNumero(b.mare.maxima_m, 2)} m${
          b.mare.maxima_em ? `, ${quandoAs(b.mare.maxima_em)}` : ""
        }.`,
      );
  }
  for (const a of saude?.agravos ?? []) {
    if (a.nivel_alerta && a.nivel_alerta >= 2)
      s.push(`${a.nome}: ${NIVEL_ALERTA[a.nivel_alerta].rotulo.toLowerCase()} no InfoDengue.`);
    else if (a.variacao_4s_pct !== null && a.variacao_4s_pct >= 10)
      s.push(`${a.nome}: casos subiram ${formatarNumero(a.variacao_4s_pct)}% em 4 semanas.`);
  }
  if (registros > 0)
    s.push(`${registros} ${registros === 1 ? "registro" : "registros"} no evento em andamento.`);
  return s.slice(0, 6);
}

/**
 * Boletim situacional: documento de uma página com a marca, número e seções fixas. Imprime limpo (“Salvar como
 * PDF”) e copia o texto para o WhatsApp. A situação é só a declarada pela equipe.
 */
export function TelaBoletim() {
  const { pode } = useSessao();
  const avisar = useAviso();
  const emitido = useRef(new Date()).current;
  const numero = numeroBoletim(emitido);
  const registrado = useRef(false);
  const r = useConsulta<Esquemas["RespostaDados_Boletim_"]>(
    `/boletim${consulta({ territorio_id: "recife" })}`,
  );
  const saudeR = useConsulta<unknown>("/saude/resumo");
  const acoes = useConsulta<unknown>("/acoes");
  const historico = useConsulta<unknown>("/estagios/historico");
  const fontes = useFontesResumo();

  const b = r.data?.dados;
  const saude = dadosDe<ResumoSaude>(saudeR.data);
  const distritos = [...(b?.estagios ?? [])].sort(ordemPorNome);
  const { atual } = eventoAtual(montarLinha(listaDe<Acao>(acoes.data), listaDe<Declaracao>(historico.data)));
  const registros = atual.filter((e) => e.tipo === "registro");
  const doEvento = atual.filter((e) => e.tipo !== "boletim");
  const resumo = b
    ? [fraseSituacao(distritos), fraseChuva(b.chuva), fraseAbrigosSaude(b, saude, saudeR.isError)]
    : [];
  const topicos = destaques(b, saude, registros.length);
  const fontesAtivas = fontes.lista.filter((f) => f.status !== "planejada").filter(noProduto);

  const texto = [
    `*Boletim situacional ClimaSense* ${numero}`,
    `Vigilância em Saúde, Recife/PE. Emitido ${formatarData(emitido)} às ${formatarHora(emitido)}.`,
    "",
    ...resumo,
    "",
    "*Situação declarada por distrito*",
    ...distritos.map(
      (d) =>
        `- ${nomeCurto(d.territorio_nome)}: ${
          d.declarado ? infoEstagio(d.declarado.estagio).rotulo : "sem declaração"
        }`,
    ),
    ...(topicos.length ? ["", "*Destaques*", ...topicos.map((t) => `- ${t}`)] : []),
    "",
    "Fonte: ClimaSense / Vigidesastres. Confira na APAC e no Cemaden. Defesa Civil: 199.",
  ].join("\n");

  /** Guarda a emissão na linha do tempo do evento (uma vez por número). Falha não impede imprimir nem copiar. */
  function registrarEmissao() {
    if (registrado.current || !pode("editar") || !b) return;
    registrado.current = true;
    void enviar("/acoes", corpoRegistro(`${PREFIXO_BOLETIM} ${numero}`, "")).catch(() => {
      registrado.current = false;
    });
  }

  async function copiar() {
    try {
      await navigator.clipboard.writeText(texto);
      registrarEmissao();
      avisar({ titulo: "Texto copiado.", texto: "Cole no grupo de WhatsApp." });
    } catch (x) {
      avisar({
        titulo: "Não foi possível copiar.",
        texto: x instanceof ErroApi ? x.message : "Use o texto abaixo do boletim.",
        tipo: "erro",
      });
    }
  }

  return (
    <>
      <div className={estilos.naoImprimir}>
        <CabecalhoTela
          titulo="Boletim"
          proposito="O resumo do evento em uma página, para a gerência e os distritos."
          acoes={
            <>
              <Botao variante="secundario" icone={<Copy />} onClick={copiar} disabled={!b}>
                Copiar para WhatsApp
              </Botao>
              <Botao
                icone={<Printer />}
                onClick={() => {
                  registrarEmissao();
                  window.print();
                }}
              >
                Imprimir / salvar PDF
              </Botao>
            </>
          }
        />
      </div>

      <article className={estilos.folha} aria-labelledby="bo-titulo">
        <header className={estilos.cabeca}>
          <div className={estilos.marca}>
            <Marca className={estilos.logo} />
            <p className={estilos.orgao}>Vigilância em Saúde · Recife/PE</p>
          </div>
          <div className={estilos.emissao}>
            <p className={estilos.numero}>{numero}</p>
            <p>
              {formatarData(emitido)}, {formatarHora(emitido)}
            </p>
            <p className={estilos.emitido}>Emitido</p>
          </div>
        </header>

        <div className={estilos.tituloBloco}>
          <h2 id="bo-titulo" className={estilos.titulo}>
            Boletim situacional
          </h2>
          <p className={estilos.subtitulo}>Chuvas, desastres e saúde · consolidado automaticamente</p>
        </div>

        {r.isPending && <CarregandoLista linhas={4} altura="2rem" texto="Montando o boletim…" />}
        {r.isError && <EstadoConsulta erro={r.error} oQue="o boletim" aoTentar={() => r.refetch()} />}

        {b && (
          <>
            <section className={estilos.resumo} aria-labelledby="bo-resumo">
              <h3 id="bo-resumo">Resumo</h3>
              <p>{resumo.join(" ")}</p>
            </section>

            {topicos.length > 0 && (
              <section className={estilos.secao} aria-labelledby="bo-destaques">
                <h3 id="bo-destaques">Destaques</h3>
                <ul className={estilos.topicos}>
                  {topicos.map((t) => (
                    <li key={t}>{t}</li>
                  ))}
                </ul>
              </section>
            )}

            <section className={estilos.secao} aria-labelledby="bo-situacao">
              <h3 id="bo-situacao">Situação por distrito</h3>
              <table className={estilos.tabela}>
                <caption className="so-leitor">Situação declarada pela equipe em cada distrito</caption>
                <thead>
                  <tr>
                    <th scope="col">Distrito</th>
                    <th scope="col">Situação declarada</th>
                    <th scope="col">Por quem e quando</th>
                  </tr>
                </thead>
                <tbody>
                  {distritos.map((d) => (
                    <tr key={d.territorio_id}>
                      <th scope="row">{d.territorio_nome}</th>
                      <td>
                        {d.declarado ? (
                          <b data-nivel={infoEstagio(d.declarado.estagio).nivel}>
                            {infoEstagio(d.declarado.estagio).rotulo}
                          </b>
                        ) : (
                          <span className={estilos.apagado}>sem declaração</span>
                        )}
                      </td>
                      <td>
                        {d.declarado
                          ? `${d.declarado.autor_nome}, ${quandoAs(d.declarado.declarado_em)}`
                          : ""}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>

            <section className={estilos.secao} aria-labelledby="bo-chuva">
              <h3 id="bo-chuva">Chuva e maré</h3>
              <dl className={estilos.numeros}>
                <div>
                  <dt>Últimas 24 h (medida)</dt>
                  <dd>{formatarMm(b.chuva.chuva_24h_mm)}</dd>
                </div>
                <div>
                  <dt>Próximas 24 h (prevista)</dt>
                  <dd>{formatarMm(b.chuva.chuva_prev_24h_mm)}</dd>
                </div>
                <div>
                  <dt>Próximos 3 dias (prevista)</dt>
                  <dd>{formatarMm(b.chuva.chuva_prev_72h_mm)}</dd>
                </div>
                <div>
                  <dt>Maré mais alta</dt>
                  <dd>
                    {b.mare.maxima_m === null ? "sem dado" : `${formatarNumero(b.mare.maxima_m, 2)} m`}
                    {b.mare.maxima_em && <small> {quandoAs(b.mare.maxima_em)}</small>}
                  </dd>
                </div>
              </dl>
              <p className={estilos.nota}>O maior valor entre os distritos.</p>
            </section>

            <section className={estilos.secao} aria-labelledby="bo-abrigos">
              <h3 id="bo-abrigos">Abrigos abertos</h3>
              {b.abrigos.totais.abrigos_cadastrados === 0 || b.abrigos.totais.abrigos_abertos === null ? (
                <p>Sem informação de abrigos.</p>
              ) : b.abrigos.abertos.length === 0 ? (
                <p>Nenhum abrigo aberto.</p>
              ) : (
                <ul className={estilos.topicos}>
                  {b.abrigos.abertos.map((a) => (
                    <li key={a.id}>
                      {a.nome}, {a.bairro_nome}
                      {a.capacidade !== null && ` (capacidade ${formatarNumero(a.capacidade)})`}
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <section className={estilos.secao} aria-labelledby="bo-saude">
              <h3 id="bo-saude">Saúde</h3>
              {saudeR.isPending && <CarregandoLista linhas={2} altura="1.5rem" />}
              {saudeR.isError && (
                <p>
                  {saudeR.error instanceof ErroApi && saudeR.error.status === 404
                    ? "Ainda não disponível."
                    : "Não foi possível carregar os dados de saúde."}
                </p>
              )}
              {saude && (
                <>
                  <table className={estilos.tabela}>
                    <caption className="so-leitor">
                      Dengue, chikungunya e leptospirose na última semana
                    </caption>
                    <thead>
                      <tr>
                        <th scope="col">Agravo</th>
                        <th scope="col">Semana</th>
                        <th scope="col">Casos</th>
                        <th scope="col">Nível</th>
                      </tr>
                    </thead>
                    <tbody>
                      {saude.agravos.map((a) => (
                        <tr key={a.agravo}>
                          <th scope="row">{a.nome}</th>
                          <td>
                            {a.ultima_semana ? diaMes(a.ultima_semana.inicio) : "sem dado"}
                            {a.incompleta && <small> (incompleta)</small>}
                          </td>
                          <td>{formatarNumero(a.casos)}</td>
                          <td>{a.nivel_alerta ? NIVEL_ALERTA[a.nivel_alerta].rotulo : "sem nível"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {saude.janela_leptospirose?.ativa && (
                    <p className={estilos.nota}>
                      Janela de vigilância de leptospirose até {diaMes(saude.janela_leptospirose.fim)}: 30
                      dias após o alagamento de {diaMes(saude.janela_leptospirose.inicio)}.
                    </p>
                  )}
                </>
              )}
            </section>

            <section className={estilos.secao} aria-labelledby="bo-registro">
              <h3 id="bo-registro">Registro do evento</h3>
              {acoes.isError ? (
                <p>Registro indisponível agora.</p>
              ) : doEvento.length === 0 ? (
                <p>Nada registrado no evento em andamento.</p>
              ) : (
                <ul className={estilos.registros}>
                  {doEvento.slice(0, 8).map((e) => (
                    <li key={e.id}>
                      <time dateTime={e.em}>{quandoAs(e.em)}</time> {e.territorio && <b>{e.territorio}: </b>}
                      {e.texto}
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </>
        )}

        <footer className={estilos.rodape}>
          <h3>De onde vêm os números</h3>
          <ul>
            {fontesAtivas.map((f) => (
              <li key={f.id}>
                {f.nome}, {atualizada(f.ultima_atualizacao)}.
              </li>
            ))}
            <li>Situação: declarada pela equipe, com nome e hora.</li>
          </ul>
          <p className={estilos.aviso}>
            O ClimaSense apoia a decisão da equipe. Não é alerta oficial: confira a APAC e o Cemaden. Defesa
            Civil: 199.
          </p>
        </footer>
      </article>

      <details className={`${estilos.naoImprimir} ${estilos.textoWhats}`}>
        <summary>Ver o texto para o WhatsApp</summary>
        <MensagemPronta mensagem={{ texto, wa_me_url: "" }} rotulo="Texto para o WhatsApp" />
      </details>
    </>
  );
}
