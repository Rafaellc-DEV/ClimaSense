import { useState, type ReactNode } from "react";
import { CarregandoLista } from "@/design-system/componentes/Esqueleto";
import { Botao } from "@/design-system/componentes/Botao";
import { fontesDado, LegendaFonte } from "@/design-system/componentes/EstadoDados";
import { Pilula } from "@/design-system/componentes/Pilula";
import { EstadoConsulta, MensagemPronta } from "@/features/evento/Evento";
import type { MensagemWhatsApp } from "@/features/evento/tipos";
import { enviar, type ErroApi } from "@/lib/api";
import { nomeDistrito } from "@/lib/distritos";
import { haQuanto, type FonteMeta } from "@/lib/frescor";
import { formatarHoraMinuto } from "@/lib/formatos";
import type { LinhaDistrito } from "./dados";
import estilos from "./Situacao.module.css";

/* ------------------------------------------------------------------ cartão de indicador */
export function CartaoIndicador({
  rotulo,
  selo,
  tomSelo,
  carregando,
  valor,
  unidade,
  detalhe,
  faltando,
  fontes,
  extra,
}: {
  rotulo: string;
  selo: string;
  tomSelo: "info" | "marca";
  carregando: boolean;
  valor: string | null;
  unidade: string;
  detalhe?: ReactNode;
  /** A fonte que falta, quando não há valor. */
  faltando: string;
  fontes: FonteMeta[];
  extra?: ReactNode;
}) {
  return (
    <div role="group" aria-label={rotulo} className={estilos.cartao}>
      <div className={estilos.cartaoTopo}>
        <h3 className={estilos.cartaoRotulo}>{rotulo}</h3>
        <Pilula tom={tomSelo} pequena semMarca>
          {selo}
        </Pilula>
      </div>
      {carregando ? (
        <p className={estilos.carregando}>Carregando…</p>
      ) : valor === null ? (
        <p className={estilos.insuficiente}>
          <b>Dados insuficientes:</b> falta {faltando}.
        </p>
      ) : (
        <>
          <p className={estilos.valorGrande}>
            <span className="numeros">{valor}</span> <small>{unidade}</small>
          </p>
          {detalhe && <p className={estilos.detalheCartao}>{detalhe}</p>}
          {extra}
          <LegendaFonte fontes={fontesDado(fontes)} />
        </>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ chuva por distrito */
export function ChuvaPorDistrito({
  carregando,
  erro,
  aoTentar,
  linhas,
  fontes,
  destaque,
}: {
  carregando: boolean;
  erro: ErroApi | null;
  aoTentar: () => void;
  linhas: LinhaDistrito[];
  fontes: FonteMeta[];
  destaque: string | null;
}) {
  const comLeitura = linhas.filter((l) => l.mm !== null);
  const sem = linhas.length - comLeitura.length;
  const maximo = Math.max(1, ...comLeitura.map((l) => l.mm as number));
  return (
    <section className={estilos.bloco} aria-labelledby="se-distritos">
      <h2 id="se-distritos" className={estilos.pergunta}>
        Chuva por distrito
      </h2>
      {carregando ? (
        <div className={estilos.esqueleto}>
          <p className={estilos.carregando}>Carregando…</p>
          <CarregandoLista linhas={4} altura="1.4rem" texto="Carregando a chuva por distrito…" />
        </div>
      ) : erro ? (
        <EstadoConsulta erro={erro} oQue="a chuva por distrito" aoTentar={aoTentar} />
      ) : comLeitura.length === 0 ? (
        <p className={estilos.insuficiente}>
          <b>Dados insuficientes:</b> falta a chuva medida nas últimas 24 h (pluviômetros, APAC).
        </p>
      ) : (
        <>
          <p className={estilos.apoio}>Medida nas últimas 24 h, do maior ao menor.</p>
          <ol
            className={estilos.barras}
            aria-label="Chuva medida nas últimas 24 h por distrito, em milímetros"
          >
            {linhas.map((l) => (
              <li key={l.id} data-destaque={l.id === destaque || undefined}>
                <span className={estilos.nome}>{l.nome}</span>
                <span className={estilos.trilho} aria-hidden="true">
                  {l.mm === null ? (
                    <span className={estilos.semLeitura} />
                  ) : (
                    <span
                      className={[estilos.barra, estilos.b72].join(" ")}
                      style={{ width: `${Math.max(1.5, (l.mm / maximo) * 100)}%` }}
                    />
                  )}
                </span>
                <span className={estilos.valor}>
                  {l.mm === null ? (
                    <em>Sem leitura</em>
                  ) : (
                    <>
                      <span className="numeros">
                        {l.mm.toLocaleString("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 })}
                      </span>{" "}
                      mm
                    </>
                  )}
                </span>
              </li>
            ))}
          </ol>
          <LegendaFonte fontes={fontesDado(fontes)}>
            {sem > 0 && (
              <span>
                {sem} de {linhas.length} distritos sem leitura nas últimas 24 h.
              </span>
            )}
          </LegendaFonte>
        </>
      )}
    </section>
  );
}

/* ------------------------------------------------------------------ fontes e atualização */
export interface LinhaFonte {
  id: string;
  nome: string;
  atualizadoEm: string | null;
  desatualizado: boolean | null;
  parcial?: string | null;
}

function seloDaFonte(f: LinhaFonte) {
  if (!f.atualizadoEm)
    return (
      <Pilula tom="insuficiente" pequena>
        Sem dado
      </Pilula>
    );
  if (f.desatualizado === true)
    return (
      <Pilula tom="alerta" pequena>
        Desatualizado
      </Pilula>
    );
  if (f.parcial)
    return (
      <Pilula tom="atencao" pequena>
        Dados parciais
      </Pilula>
    );
  return (
    <Pilula tom="sucesso" pequena>
      Atualizado
    </Pilula>
  );
}

export function FontesAtualizacao({ linhas, carregando }: { linhas: LinhaFonte[]; carregando: boolean }) {
  return (
    <section className={estilos.bloco} aria-labelledby="se-fontes">
      <h2 id="se-fontes" className={estilos.pergunta}>
        Fontes e atualização
      </h2>
      {carregando ? (
        <p className={estilos.carregando}>Carregando…</p>
      ) : (
        <ul className={estilos.fontes}>
          {linhas.map((f) => (
            <li key={f.id}>
              {seloDaFonte(f)}
              <span>
                <b>{f.nome}</b>
                <br />
                <span className={estilos.apoio}>
                  {f.atualizadoEm
                    ? `Atualizado ${haQuanto(f.atualizadoEm)} (${formatarHoraMinuto(f.atualizadoEm)}).`
                    : "Dados insuficientes: a fonte ainda não enviou dados."}
                  {f.parcial && ` ${f.parcial}`}
                  {f.desatualizado === true && " O dado está vencido: use com cautela."}
                </span>
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

/* ------------------------------------------------------------------ mensagem de mudança de estágio */
/** Troca o distrito em romano pelo número, no texto e no link (RF-31: nada é enviado automaticamente). */
export function normalizarMensagem(m: MensagemWhatsApp): MensagemWhatsApp {
  const texto = nomeDistrito(m.texto);
  return { ...m, texto, wa_me_url: `https://wa.me/?text=${encodeURIComponent(texto)}` };
}

export function MensagemEstagio({
  estagio,
  territorioId,
  carregando,
}: {
  estagio: string | null;
  territorioId: string;
  carregando: boolean;
}) {
  const [mensagem, setMensagem] = useState<MensagemWhatsApp | null>(null);
  const [pendente, setPendente] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const preparar = async () => {
    if (!estagio) return;
    setPendente(true);
    setErro(null);
    try {
      const m = await enviar<MensagemWhatsApp>("/estagios/mensagem", {
        territorio_ids: [territorioId],
        estagio,
        justificativa: "Estágio oficial da cidade informado pelo COP.",
      });
      setMensagem({ ...normalizarMensagem(m), uso: { territorio_ids: [territorioId], estagio } });
    } catch (e) {
      setErro((e as Error).message);
    } finally {
      setPendente(false);
    }
  };
  return (
    <section className={estilos.bloco} aria-labelledby="se-mensagem">
      <h2 id="se-mensagem" className={estilos.pergunta}>
        Mensagem de mudança de estágio
      </h2>
      {carregando ? (
        <p className={estilos.carregando}>Carregando…</p>
      ) : !estagio ? (
        <p className={estilos.insuficiente}>
          <b>Dados insuficientes:</b> falta o estágio informado pelo COP para montar a mensagem.
        </p>
      ) : mensagem ? (
        <MensagemPronta mensagem={mensagem} rotulo="Texto pronto para o grupo de WhatsApp" />
      ) : (
        <>
          <p className={estilos.apoio}>
            Texto pronto para o grupo de WhatsApp. Nada é enviado automaticamente.
          </p>
          <div>
            <Botao variante="secundario" onClick={preparar} disabled={pendente}>
              {pendente ? "Preparando…" : "Preparar mensagem"}
            </Botao>
          </div>
          {erro && <p className={estilos.insuficiente}>{erro}</p>}
        </>
      )}
    </section>
  );
}
