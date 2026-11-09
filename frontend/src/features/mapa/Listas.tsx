/** Listas do Mapa: territórios prioritários (RF-06, RF-22) e a lista de bairros, alternativa ao mapa para teclado. */
import { useMemo, useState } from "react";
import { MapPin } from "lucide-react";
import { Campo } from "@/design-system/componentes/Campo";
import { Botao } from "@/design-system/componentes/Botao";
import { CarregandoLista } from "@/design-system/componentes/Esqueleto";
import { EstadoDados, LegendaFonte, fontesDado } from "@/design-system/componentes/EstadoDados";
import { Painel } from "@/design-system/componentes/Painel";
import { EstadoConsulta, SeloEstagio } from "@/features/evento/Evento";
import { listaDe, type ItemEstagio } from "@/features/evento/tipos";
import { nomeDistrito } from "@/lib/distritos";
import { formatarNumero } from "@/lib/formatos";
import { fontesDe } from "@/lib/frescor";
import { emVigor, semAcento, type ItemPrioridadeTerritorio } from "./tipos";
import estilos from "./Mapa.module.css";

interface Consulta {
  isPending: boolean;
  isError: boolean;
  isSuccess: boolean;
  error: Error | null;
  data?: unknown;
  refetch: () => unknown;
}

const LIMITE = 8;

function contagem(n: number | null | undefined, singular: string, plural: string) {
  if (n === null || n === undefined) return `${plural}: sem dado`;
  return `${formatarNumero(n)} ${n === 1 ? singular : plural}`;
}

export function Prioritarios({
  consulta,
  selecionado,
  aoEscolher,
}: {
  consulta: Consulta;
  selecionado: string | null;
  aoEscolher: (id: string) => void;
}) {
  const [todos, setTodos] = useState(false);
  const itens = useMemo(
    () => listaDe<ItemPrioridadeTerritorio>(consulta.data).sort((a, b) => a.posicao - b.posicao),
    [consulta.data],
  );
  const visiveis = todos ? itens : itens.slice(0, LIMITE);
  return (
    <Painel
      id="mapa-prioritarios"
      titulo="Territórios prioritários"
      dica="Os mais vulneráveis vêm primeiro. A ordem usa o critério escrito em cada item e as ocorrências já registradas. Prioridade não é chance de acontecer."
    >
      {consulta.isPending && (
        <CarregandoLista linhas={3} altura="3.5rem" texto="Carregando as prioridades…" />
      )}
      {consulta.isError && (
        <EstadoConsulta
          erro={consulta.error}
          oQue="a lista de prioridades"
          aoTentar={() => consulta.refetch()}
        />
      )}
      {consulta.isSuccess && itens.length === 0 && (
        <EstadoDados tipo="insuficiente" titulo="Dados insuficientes.">
          Falta a fonte de ocorrências de alagamento e deslizamento para ordenar os territórios.
        </EstadoDados>
      )}
      {itens.length > 0 && (
        <>
          <ol className={estilos.prioritarios}>
            {visiveis.map((p) => (
              <li key={p.territorio_id}>
                <button
                  type="button"
                  className={estilos.itemPrioritario}
                  aria-pressed={selecionado === p.territorio_id}
                  onClick={() => aoEscolher(p.territorio_id)}
                >
                  <span className={estilos.posicao} aria-hidden="true">
                    {p.posicao}
                  </span>
                  <span className={estilos.prioTextos}>
                    <b>
                      {nomeDistrito(p.nome)}
                      <span className="so-leitor">, prioridade {p.posicao}. Mostrar no mapa</span>
                    </b>
                    <span className={estilos.prioNumeros}>
                      {contagem(
                        p.ocorrencias_alagamento,
                        "ocorrência de alagamento",
                        "ocorrências de alagamento",
                      )}
                      {" · "}
                      {contagem(
                        p.ocorrencias_deslizamento,
                        "ocorrência de deslizamento",
                        "ocorrências de deslizamento",
                      )}
                    </span>
                    {p.criterio && <small>{p.criterio}</small>}
                  </span>
                </button>
              </li>
            ))}
          </ol>
          {itens.length > LIMITE && (
            <Botao variante="discreto" onClick={() => setTodos((t) => !t)}>
              {todos ? "Mostrar só os primeiros" : `Ver os ${itens.length} territórios`}
            </Botao>
          )}
          <LegendaFonte fontes={fontesDado(fontesDe(consulta.data))}>
            {fontesDe(consulta.data).length === 0 && (
              <span>Fonte: ocorrências registradas da Defesa Civil.</span>
            )}
          </LegendaFonte>
        </>
      )}
    </Painel>
  );
}

/** Todos os bairros em lista, do mais grave para o menos grave: o que o mapa mostra, sem precisar do mapa. */
export function ListaBairros({
  bairros,
  selecionado,
  aoEscolher,
}: {
  bairros: ItemEstagio[];
  selecionado: string | null;
  aoEscolher: (id: string) => void;
}) {
  const [busca, setBusca] = useState("");
  const filtrados = bairros.filter((b) => semAcento(b.territorio_nome).includes(semAcento(busca)));
  return (
    <details className={estilos.listaBairros}>
      <summary>Ver os {bairros.length} bairros em lista</summary>
      <Campo
        rotulo="Buscar bairro"
        type="search"
        value={busca}
        onChange={(e) => setBusca(e.target.value)}
        autoComplete="off"
      />
      <p className="so-leitor" role="status">
        {filtrados.length} {filtrados.length === 1 ? "bairro encontrado" : "bairros encontrados"}
      </p>
      <ul>
        {filtrados.map((b) => {
          const v = emVigor(b);
          return (
            <li key={b.territorio_id}>
              <button
                type="button"
                aria-pressed={selecionado === b.territorio_id}
                onClick={() => aoEscolher(b.territorio_id)}
              >
                <MapPin aria-hidden="true" size={18} />
                <span className={estilos.nomeBairro}>{b.territorio_nome}</span>
                <SeloEstagio estagio={v.estagio} pequena />
                <small>
                  {v.origem === "declarado"
                    ? "declarado"
                    : v.origem === "sugerido"
                      ? "sugerido"
                      : "sem dados"}
                </small>
              </button>
            </li>
          );
        })}
        {filtrados.length === 0 && <li className={estilos.apagado}>Nenhum bairro com esse nome.</li>}
      </ul>
    </details>
  );
}
