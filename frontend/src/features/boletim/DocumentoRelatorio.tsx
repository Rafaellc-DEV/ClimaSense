import { useRef, useState } from "react";
import { Check, Copy, PencilLine, Printer, RotateCcw } from "lucide-react";
import { useTerritorios } from "@/app/FiltroFrase";
import { useAviso } from "@/design-system/componentes/Aviso";
import { Botao } from "@/design-system/componentes/Botao";
import { CarregandoLista } from "@/design-system/componentes/Esqueleto";
import { Marca } from "@/design-system/componentes/Marca";
import { consulta, ErroApi, type Esquemas } from "@/lib/api";
import { INTERVALO, useConsultaViva } from "@/lib/consultas";
import { juntarFontes } from "@/lib/frescor";
import { fontesDado, TextoFonte } from "@/design-system/componentes/EstadoDados";
import { formatarData, formatarHora, formatarMm, formatarNumero } from "@/lib/formatos";
import { noProduto } from "@/lib/fontes";
import { infoEstagio } from "@/features/evento/estagios";
import { EstadoConsulta, MensagemPronta } from "@/features/evento/Evento";
import { atualizada, diaMes, nomeCurto, quandoAs, useFontesResumo } from "@/features/evento/textos";
import { dadosDe, NIVEL_ALERTA, type ResumoSaude } from "@/features/saude/tipos";
import {
  destaques,
  fraseChuva,
  fraseSaude,
  fraseSituacao,
  numeroBoletim,
  ordemPorNome,
  type Boletim,
} from "./relatorio";
import { BarraEdicao } from "./BarraEdicao";
import estilos from "./Boletim.module.css";

/**
 * Relatório executivo (RF-17) para a Secretaria de Saúde, dentro da tela de Ações: documento de uma página com a
 * marca, número e seções fixas, a partir do boletim situacional. "Editar documento" deixa a equipe mudar o texto
 * direto na folha; a versão editada fica congelada (não muda quando os dados atualizam) até "Desfazer edições".
 * Imprime limpo ("Salvar como PDF") e copia o texto. A situação é só a declarada pela equipe.
 */
export function DocumentoRelatorio() {
  const avisar = useAviso();
  const emitido = useRef(new Date()).current;
  const numero = numeroBoletim(emitido);
  const folha = useRef<HTMLElement>(null);
  const [editado, setEditado] = useState<string | null>(null);
  const [editando, setEditando] = useState(false);
  const r = useConsultaViva<Esquemas["RespostaDados_Boletim_"]>(
    `/boletim${consulta({ territorio_id: "recife" })}`,
  );
  const saudeR = useConsultaViva<unknown>("/saude/resumo", INTERVALO.saude);
  const fontes = useFontesResumo();
  const territorios = useTerritorios();
  const bairrosDe = (distritoId: string): string[] =>
    (territorios.data ?? [])
      .filter((t) => t.tipo === "bairro" && t.pai_id === distritoId)
      .map((t) => t.nome_exibicao)
      .sort((a, c) => a.localeCompare(c, "pt-BR"));

  const b = r.data?.dados as Boletim | undefined;
  const saude = dadosDe<ResumoSaude>(saudeR.data);
  const distritos = [...(b?.estagios ?? [])].sort(ordemPorNome);
  const emAndamento = b?.acoes_em_andamento ?? [];
  const concluidas = b?.acoes_concluidas ?? [];
  const resumo = b
    ? [fraseSituacao(distritos), fraseChuva(b.chuva), fraseSaude(saude, saudeR.isError)].filter(Boolean)
    : [];
  const topicos = destaques(b, saude, emAndamento.length);
  const fontesMeta = fontesDado(juntarFontes(r.data, saudeR.data));
  const fontesAtivas = fontes.lista.filter((f) => f.status !== "planejada").filter(noProduto);

  const texto = [
    `*Relatório executivo ClimaSense — Secretaria de Saúde* ${numero}`,
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

  function editar() {
    if (editado === null && folha.current) setEditado(folha.current.innerHTML);
    setEditando(true);
  }
  function concluir() {
    if (folha.current) setEditado(folha.current.innerHTML);
    setEditando(false);
  }
  function desfazer() {
    setEditado(null);
    setEditando(false);
  }

  async function copiar() {
    // depois de editado, copia o que está na folha; senão, o texto pronto para o WhatsApp
    const daFolha = folha.current?.innerText || folha.current?.textContent || "";
    const conteudo = editado !== null ? daFolha : texto;
    try {
      await navigator.clipboard.writeText(conteudo.trim());
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
    <section className={estilos.bloco} aria-labelledby="bo-bloco">
      <div className={`${estilos.naoImprimir} ${estilos.barra}`}>
        <div>
          <h2 id="bo-bloco" className={estilos.blocoTitulo}>
            Relatório executivo
          </h2>
          <p className={estilos.blocoProposito}>
            {editando
              ? "Clique no texto da folha para editar. Ao terminar, clique em Concluir edição."
              : "O resumo do evento em uma página, para a Secretaria de Saúde. Imprima ou copie o texto."}
          </p>
        </div>
        <div className={estilos.botoes}>
          {editando ? (
            <Botao icone={<Check />} onClick={concluir}>
              Concluir edição
            </Botao>
          ) : (
            <Botao variante="secundario" icone={<PencilLine />} onClick={editar} disabled={!b}>
              Editar documento
            </Botao>
          )}
          {editado !== null && !editando && (
            <Botao variante="secundario" icone={<RotateCcw />} onClick={desfazer}>
              Desfazer edições
            </Botao>
          )}
          <Botao variante="secundario" icone={<Copy />} onClick={copiar} disabled={!b || editando}>
            Copiar para WhatsApp
          </Botao>
          <Botao icone={<Printer />} onClick={() => window.print()} disabled={editando}>
            Imprimir / salvar PDF
          </Botao>
        </div>
      </div>

      {editando && <BarraEdicao />}

      {editado !== null ? (
        <article
          ref={folha}
          className={`${estilos.folha} ${editando ? estilos.editando : ""}`}
          aria-label="Relatório executivo — Secretaria de Saúde"
          contentEditable={editando}
          suppressContentEditableWarning
          dangerouslySetInnerHTML={{ __html: editado }}
        />
      ) : (
        <article ref={folha} className={estilos.folha} aria-labelledby="bo-titulo">
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
              Relatório executivo — Secretaria de Saúde
            </h2>
            <p className={estilos.subtitulo}>
              Chuvas, desastres e saúde · consolidado automaticamente
              {b?.periodo ? ` · ${formatarData(b.periodo.desde)} a ${formatarData(b.periodo.ate)}` : ""}
            </p>
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
                        <th scope="row">
                          {d.territorio_nome}
                          {bairrosDe(d.territorio_id).length > 0 && (
                            <small className={estilos.bairrosDoDistrito}>
                              Bairros: {bairrosDe(d.territorio_id).join(", ")}
                            </small>
                          )}
                        </th>
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
                <h3 id="bo-registro">Ações da equipe</h3>
                {emAndamento.length === 0 && concluidas.length === 0 ? (
                  <p>Nenhuma ação registrada no período.</p>
                ) : (
                  <ul className={estilos.registros}>
                    {[
                      ...emAndamento.map((a) => ["Em andamento", a] as const),
                      ...concluidas.map((a) => ["Concluída", a] as const),
                    ]
                      .slice(0, 12)
                      .map(([rotulo, a]) => (
                        <li key={a.id}>
                          <b>{a.territorio_nome}</b> ({rotulo}): {a.descricao}
                          {a.responsavel ? `. Responsável: ${a.responsavel}` : ""}
                          {a.inicio_em ? `. Desde ${quandoAs(a.inicio_em)}` : ""}.
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
              {fontesMeta.length > 0
                ? fontesMeta.map((f, i) => (
                    <li key={`${f.nome}-${i}`}>
                      <TextoFonte f={f} />.
                    </li>
                  ))
                : fontesAtivas.map((f) => (
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
      )}

      {editado === null && (
        <details className={`${estilos.naoImprimir} ${estilos.textoWhats}`}>
          <summary>Ver o texto para o WhatsApp</summary>
          <MensagemPronta mensagem={{ texto, wa_me_url: "" }} rotulo="Texto para o WhatsApp" />
        </details>
      )}
    </section>
  );
}
