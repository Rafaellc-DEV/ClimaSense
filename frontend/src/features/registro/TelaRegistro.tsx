import { useState, type FormEvent } from "react";
import { FileText, Flag, PenLine, Siren } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { CabecalhoTela } from "@/design-system/componentes/CabecalhoTela";
import { useAviso } from "@/design-system/componentes/Aviso";
import { Botao } from "@/design-system/componentes/Botao";
import { AreaTexto } from "@/design-system/componentes/Campo";
import { Dialogo } from "@/design-system/componentes/Dialogo";
import { CarregandoLista } from "@/design-system/componentes/Esqueleto";
import { Painel } from "@/design-system/componentes/Painel";
import { enviar, ErroApi } from "@/lib/api";
import { useConsulta } from "@/lib/consultas";
import { formatarData, formatarHora } from "@/lib/formatos";
import { useSessao } from "@/lib/sessao";
import { EstadoConsulta, invalidarPrefixo, SelecaoTerritorio } from "@/features/evento/Evento";
import { quandoAs } from "@/features/evento/textos";
import { listaDe, type Acao } from "@/features/evento/tipos";
import { ENCERRAMENTO, eventoAtual, montarLinha, type Declaracao, type Entrada } from "./linhaTempo";
import estilos from "./Registro.module.css";

const ROTULO: Record<Entrada["tipo"], string> = {
  registro: "Registro",
  situacao: "Situação",
  boletim: "Boletim",
  encerramento: "Encerramento",
};
const ICONE: Record<Entrada["tipo"], React.ReactNode> = {
  registro: <PenLine />,
  situacao: <Siren />,
  boletim: <FileText />,
  encerramento: <Flag />,
};

/** Grava um registro do evento em /acoes: hora automática, território opcional (vazio = Recife inteiro). */
export function corpoRegistro(texto: string, territorio: string, extra: Record<string, unknown> = {}) {
  return {
    territorio_id: territorio || "recife",
    tipo: "outro",
    descricao: texto,
    situacao: "concluida",
    inicio_em: new Date().toISOString(),
    ...extra,
  };
}

/**
 * Registro do evento (dor 3): uma caixa “O que aconteceu?”, a linha do tempo com registros, situações e boletins, e o
 * encerramento com uma pergunta só. Sem quadro de tarefas: é um diário com hora.
 */
export function TelaRegistro() {
  const { pode } = useSessao();
  const podeEditar = pode("editar");
  const acoes = useConsulta<unknown>("/acoes");
  const historico = useConsulta<unknown>("/estagios/historico");
  const linha = montarLinha(listaDe<Acao>(acoes.data), listaDe<Declaracao>(historico.data));
  const { atual, encerrados } = eventoAtual(linha);
  const [encerrar, setEncerrar] = useState(false);

  return (
    <>
      <CabecalhoTela
        titulo="Registro do evento"
        proposito="O que aconteceu, com hora. Vira a memória do evento e entra no boletim."
      />
      <div className={estilos.pagina}>
        {podeEditar && <CaixaRegistro />}

        <Painel id="re-linha" titulo="Linha do tempo">
          {(acoes.isPending || historico.isPending) && (
            <CarregandoLista linhas={4} altura="3rem" texto="Carregando a linha do tempo…" />
          )}
          {acoes.isError && (
            <EstadoConsulta erro={acoes.error} oQue="os registros" aoTentar={() => acoes.refetch()} />
          )}
          {historico.isError && (
            <EstadoConsulta
              erro={historico.error}
              oQue="o histórico de situações"
              aoTentar={() => historico.refetch()}
            />
          )}
          {acoes.isSuccess && historico.isSuccess && atual.length === 0 && (
            <p className={estilos.vazio}>
              {encerrados.length
                ? `Nada registrado desde o último encerramento, ${quandoAs(encerrados[0].em)}.`
                : "Nada registrado ainda. Escreva acima o primeiro acontecimento."}
            </p>
          )}
          {atual.length > 0 && <Linha entradas={atual} />}
          {podeEditar && atual.length > 0 && (
            <div className={estilos.encerrar}>
              <Botao variante="secundario" icone={<Flag />} onClick={() => setEncerrar(true)}>
                Encerrar evento e registrar lição aprendida
              </Botao>
            </div>
          )}
        </Painel>

        {encerrados.length > 0 && (
          <details className={estilos.anteriores}>
            <summary>Eventos anteriores ({encerrados.length})</summary>
            <ul>
              {encerrados.map((e) => (
                <li key={e.id}>
                  <b>Encerrado em {formatarData(e.em)}</b>
                  {e.autor && <span className={estilos.autor}>, por {e.autor}</span>}
                  <p>{e.licao ? `Lição: ${e.licao}` : "Sem lição registrada."}</p>
                </li>
              ))}
            </ul>
          </details>
        )}
      </div>
      {encerrar && <DialogoEncerrarEvento aoFechar={() => setEncerrar(false)} />}
    </>
  );
}

function Linha({ entradas }: { entradas: Entrada[] }) {
  let dia = "";
  return (
    <ol className={estilos.linha} aria-label="Linha do tempo do evento">
      {entradas.map((e) => {
        const d = formatarData(e.em);
        const novoDia = d !== dia;
        dia = d;
        return (
          <li key={e.id} data-tipo={e.tipo}>
            {novoDia && <p className={estilos.dia}>{d}</p>}
            <div className={estilos.entrada}>
              <time dateTime={e.em} className={estilos.hora}>
                {formatarHora(e.em)}
              </time>
              <span className={estilos.marco} aria-hidden="true">
                {ICONE[e.tipo]}
              </span>
              <div className={estilos.corpo}>
                <p className={estilos.texto}>
                  <span className={estilos.tipo}>{ROTULO[e.tipo]}</span>
                  {e.territorio && <b>{e.territorio}: </b>}
                  {e.texto}
                </p>
                {e.autor && <p className={estilos.autor}>{e.autor}</p>}
              </div>
            </div>
          </li>
        );
      })}
    </ol>
  );
}

function useGravar(aoTerminar: () => void) {
  const cliente = useQueryClient();
  const avisar = useAviso();
  const [ocupado, setOcupado] = useState(false);
  const [erro, setErro] = useState<string>();
  async function gravar(corpo: unknown, confirmacao: string) {
    setOcupado(true);
    try {
      await enviar("/acoes", corpo);
      void invalidarPrefixo(cliente, "/acoes");
      void invalidarPrefixo(cliente, "/boletim");
      avisar({ titulo: confirmacao });
      setErro(undefined);
      aoTerminar();
    } catch (x) {
      setErro(x instanceof ErroApi ? x.message : "Não foi possível registrar. Tente de novo.");
    } finally {
      setOcupado(false);
    }
  }
  return { ocupado, erro, setErro, gravar };
}

function CaixaRegistro() {
  const [texto, setTexto] = useState("");
  const [territorio, setTerritorio] = useState("");
  const { ocupado, erro, setErro, gravar } = useGravar(() => {
    setTexto("");
    setTerritorio("");
  });
  function registrar(e: FormEvent) {
    e.preventDefault();
    if (!texto.trim()) {
      setErro("Escreva o que aconteceu em uma frase.");
      return;
    }
    void gravar(corpoRegistro(texto.trim(), territorio), "Registrado.");
  }
  return (
    <form className={estilos.caixa} onSubmit={registrar} noValidate aria-label="Novo registro">
      <AreaTexto
        rotulo="O que aconteceu?"
        ajuda="A hora é a de agora. Pode colar o que chegou pelo WhatsApp."
        rows={2}
        maxLength={2000}
        value={texto}
        onChange={(e) => {
          setTexto(e.target.value);
          setErro(undefined);
        }}
        erro={erro}
      />
      <div className={estilos.linhaCaixa}>
        <div className={estilos.territorio}>
          <SelecaoTerritorio
            rotulo="Território (opcional)"
            vazio="Recife inteiro"
            valor={territorio}
            aoMudar={setTerritorio}
          />
        </div>
        <Botao type="submit" disabled={ocupado}>
          {ocupado ? "Registrando…" : "Registrar"}
        </Botao>
      </div>
    </form>
  );
}

function DialogoEncerrarEvento({ aoFechar }: { aoFechar: () => void }) {
  const [licao, setLicao] = useState("");
  const { ocupado, erro, setErro, gravar } = useGravar(aoFechar);
  return (
    <Dialogo
      aberto
      aoMudar={(a) => !a && aoFechar()}
      titulo="Encerrar o evento"
      descricao="A linha do tempo fica guardada. O próximo registro começa um evento novo."
      acoes={
        <>
          <Botao variante="secundario" onClick={aoFechar}>
            Cancelar
          </Botao>
          <Botao type="submit" form="form-encerrar-evento" disabled={ocupado}>
            {ocupado ? "Encerrando…" : "Encerrar evento"}
          </Botao>
        </>
      }
    >
      <form
        id="form-encerrar-evento"
        onSubmit={(e) => {
          e.preventDefault();
          if (!licao.trim()) {
            setErro("Escreva em uma ou duas frases. Isso substitui a planilha de lições.");
            return;
          }
          void gravar(
            corpoRegistro(ENCERRAMENTO, "", { licao_aprendida: licao.trim() }),
            "Evento encerrado.",
          );
        }}
        noValidate
      >
        <AreaTexto
          rotulo="O que funcionou e o que mudar da próxima vez?"
          rows={4}
          maxLength={2000}
          value={licao}
          onChange={(e) => {
            setLicao(e.target.value);
            setErro(undefined);
          }}
          erro={erro}
        />
      </form>
    </Dialogo>
  );
}
