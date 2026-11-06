/** Faixa do topo do Mapa: estágio oficial da cidade dado pelo COP e a contagem de bairros por estágio (RF-01). */
import { useState, type FormEvent } from "react";
import { Radio } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { useAviso } from "@/design-system/componentes/Aviso";
import { Botao } from "@/design-system/componentes/Botao";
import { AreaTexto, Campo } from "@/design-system/componentes/Campo";
import { Dialogo } from "@/design-system/componentes/Dialogo";
import { Esqueleto } from "@/design-system/componentes/Esqueleto";
import { LegendaFonte, fontesDado } from "@/design-system/componentes/EstadoDados";
import { FaixaMare } from "@/design-system/componentes/FaixaMare";
import { Segmentado } from "@/design-system/componentes/Segmentado";
import { enviar, ErroApi } from "@/lib/api";
import { fontesDe } from "@/lib/frescor";
import { ESTAGIOS, ESTAGIOS_DECLARAVEIS } from "@/features/evento/estagios";
import { invalidarPrefixo, SeloEstagio } from "@/features/evento/Evento";
import { quandoAs } from "@/features/evento/textos";
import { desembrulhar, type Estagio } from "@/features/evento/tipos";
import { nomeDaFonte, type ContagemEstagio, type EstagioOficial } from "./tipos";
import estilos from "./Mapa.module.css";

interface Consulta {
  isPending: boolean;
  isError: boolean;
  isSuccess: boolean;
  error: Error | null;
  data?: unknown;
  refetch: () => unknown;
}

/** Valor de um `<input type="datetime-local">` com a hora de agora no fuso do navegador. */
function agoraLocal(): string {
  const d = new Date();
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
  return d.toISOString().slice(0, 16);
}

export function FaixaOficial({
  oficial,
  contagem,
  totalBairros,
  semBairros,
  carregandoBairros,
  podeInformar,
}: {
  oficial: Consulta;
  carregandoBairros: boolean;
  contagem: ContagemEstagio[];
  totalBairros: number;
  /** Os estágios dos bairros ainda não existem no servidor (404) ou falharam: texto do que falta. */
  semBairros: string | null;
  podeInformar: boolean;
}) {
  const [aberto, setAberto] = useState(false);
  const dados = desembrulhar<EstagioOficial | null>(oficial.data) ?? null;
  const indisponivel = oficial.isError && oficial.error instanceof ErroApi && oficial.error.status === 404;
  const definido = dados?.estagio ? dados : null;

  return (
    <>
      <FaixaMare id="mapa-oficial" titulo="Estágio oficial da cidade (COP)">
        {oficial.isPending && (
          <div role="status" aria-busy="true">
            <span className="so-leitor">Carregando o estágio do COP…</span>
            <Esqueleto largura="16rem" altura="2.5rem" forma="bloco" />
          </div>
        )}
        {definido && (
          <div className={estilos.oficial}>
            <p className={estilos.oficialEstagio}>
              <SeloEstagio estagio={definido.estagio} />
            </p>
            <p className={estilos.oficialQuem}>
              Informado pelo COP {definido.informado_em ? quandoAs(definido.informado_em) : "(sem hora)"}
              {definido.autor_nome ? `, registrado por ${definido.autor_nome}` : ""}.
            </p>
            {definido.observacao && <p className={estilos.oficialObs}>“{definido.observacao}”</p>}
            <p className={estilos.oficialFonte}>
              Fonte: {nomeDaFonte(definido.fonte)}
              {definido.registrado_em && <>, registrado {quandoAs(definido.registrado_em)}</>}.
            </p>
            <LegendaFonte fontes={fontesDado(fontesDe(oficial.data))} />
          </div>
        )}
        {oficial.isSuccess && !definido && (
          <div className={estilos.oficial}>
            <p className={estilos.oficialFrase}>
              <b>Dados insuficientes:</b> ninguém informou o estágio do COP.
            </p>
            <p className={estilos.oficialFonte}>
              Isso não quer dizer observação nem risco baixo. Falta a fonte: estágio informado pelo COP.
            </p>
          </div>
        )}
        {indisponivel && (
          <div className={estilos.oficial}>
            <p className={estilos.oficialFrase}>
              <b>Ainda não disponível.</b>
            </p>
            <p className={estilos.oficialFonte}>
              O servidor ainda não oferece o estágio do COP. Nada é mostrado até haver dado real.
            </p>
          </div>
        )}
        {oficial.isError && !indisponivel && (
          <div className={estilos.oficial}>
            <p className={estilos.oficialFrase}>
              <b>Não foi possível ver o estágio do COP agora.</b>
            </p>
            <Botao variante="claro" onClick={() => oficial.refetch()}>
              Tentar de novo
            </Botao>
          </div>
        )}
        {podeInformar && !indisponivel && !oficial.isPending && (
          <div className={estilos.oficialAcao}>
            <Botao variante="claro" icone={<Radio />} onClick={() => setAberto(true)}>
              Informar estágio do COP
            </Botao>
          </div>
        )}
        <ContagemBairros
          contagem={contagem}
          total={totalBairros}
          semBairros={semBairros}
          carregando={carregandoBairros}
        />
      </FaixaMare>
      {aberto && <DialogoOficial aoFechar={() => setAberto(false)} />}
    </>
  );
}

function ContagemBairros({
  contagem,
  total,
  semBairros,
  carregando,
}: {
  contagem: ContagemEstagio[];
  total: number;
  semBairros: string | null;
  carregando: boolean;
}) {
  return (
    <section className={estilos.contagem} aria-labelledby="mapa-contagem">
      <h3 id="mapa-contagem">Bairros por estágio</h3>
      {carregando ? (
        <p className={estilos.contagemVazia} role="status" aria-busy="true">
          Carregando os estágios dos bairros…
        </p>
      ) : semBairros ? (
        <p className={estilos.contagemVazia}>
          <b>Dados insuficientes:</b> {semBairros}
        </p>
      ) : (
        <>
          <ul>
            {contagem.map((c) => {
              const n = c.declarados + c.sugeridos;
              return (
                <li key={c.estagio} data-estagio={c.estagio} data-zero={n === 0}>
                  <b className="numeros">{n}</b>
                  <span>{c.rotulo}</span>
                  <small>
                    {c.estagio === "sem_dados"
                      ? "o sistema não consegue sugerir"
                      : n === 0
                        ? "nenhum"
                        : `${c.declarados} declarado${c.declarados === 1 ? "" : "s"}, ${c.sugeridos} sugerido${c.sugeridos === 1 ? "" : "s"}`}
                  </small>
                </li>
              );
            })}
          </ul>
          <p className={estilos.contagemTotal}>
            {total} bairros. “Sugerido” é o que o sistema indica; “declarado” é decisão da equipe.
          </p>
        </>
      )}
    </section>
  );
}

function DialogoOficial({ aoFechar }: { aoFechar: () => void }) {
  const cliente = useQueryClient();
  const avisar = useAviso();
  const [estagio, setEstagio] = useState<Estagio>("observacao");
  const [hora, setHora] = useState(agoraLocal);
  const [observacao, setObservacao] = useState("");
  const [erro, setErro] = useState<string>();
  const [ocupado, setOcupado] = useState(false);

  async function confirmar(e: FormEvent) {
    e.preventDefault();
    const momento = new Date(hora);
    if (!hora || Number.isNaN(momento.getTime())) {
      setErro("Informe a hora em que o COP definiu o estágio.");
      return;
    }
    if (momento.getTime() > Date.now() + 60_000) {
      setErro("A hora informada não pode estar no futuro.");
      return;
    }
    setOcupado(true);
    try {
      await enviar("/estagios/oficial", {
        estagio,
        informado_em: momento.toISOString(),
        observacao: observacao.trim() || null,
      });
    } catch (x) {
      setErro(x instanceof ErroApi ? x.message : "Não foi possível registrar. Tente de novo.");
      setOcupado(false);
      return;
    }
    void invalidarPrefixo(cliente, "/estagios");
    avisar({ titulo: "Estágio do COP registrado.", texto: "Fica com o seu nome e a hora informada." });
    aoFechar();
  }

  return (
    <Dialogo
      aberto
      aoMudar={(a) => !a && aoFechar()}
      titulo="Informar estágio do COP"
      descricao="Registre o estágio que o COP definiu para a cidade. Fica com o seu nome e a hora em que o COP informou."
      acoes={
        <>
          <Botao variante="secundario" onClick={aoFechar}>
            Cancelar
          </Botao>
          <Botao type="submit" form="form-oficial" disabled={ocupado}>
            {ocupado ? "Registrando…" : "Registrar estágio"}
          </Botao>
        </>
      }
    >
      <form id="form-oficial" className={estilos.form} onSubmit={confirmar} noValidate>
        <Segmentado
          rotulo="Estágio definido pelo COP"
          opcoes={ESTAGIOS_DECLARAVEIS.map((v) => ({ valor: v, rotulo: ESTAGIOS[v].rotulo }))}
          valor={estagio}
          aoMudar={setEstagio}
        />
        <Campo
          rotulo="Hora informada pelo COP"
          type="datetime-local"
          value={hora}
          max={agoraLocal()}
          onChange={(e) => {
            setHora(e.target.value);
            setErro(undefined);
          }}
          required
          erro={erro}
        />
        <AreaTexto
          privacidade
          rotulo="Observação (opcional)"
          rows={3}
          maxLength={500}
          value={observacao}
          onChange={(e) => setObservacao(e.target.value)}
        />
      </form>
    </Dialogo>
  );
}
