/**
 * Painel do distrito escolhido no Mapa (RF-01, RF-07, RF-22): nome, estágio, números úteis e a lista dos bairros,
 * os mais vulneráveis primeiro. A lista vem do GeoJSON, então aparece antes dos dados lentos; o que ainda carrega
 * mostra "Carregando…" e nunca um número inventado (RN-01).
 */
import { useEffect, useRef } from "react";
import { MapPin, X } from "lucide-react";
import { LegendaFonte, type FonteDado } from "@/design-system/componentes/EstadoDados";
import { SeloEstagio } from "@/features/evento/Evento";
import type { ItemEstagio } from "@/features/evento/tipos";
import { formatarHoraMinuto, formatarNumero } from "@/lib/formatos";
import { corDoDistrito, siglaDoDistrito, nomeDoDistrito } from "@/map/paleta";
import { PainelTerritorio, type PropsPainel } from "./PainelTerritorio";
import { VoltarRecife } from "./ControlesMapa";
import { contarPorEstagio, emVigor, type ItemPrioridadeTerritorio } from "./tipos";
import estilos from "./Mapa.module.css";

export interface PropsPainelDistrito {
  id: string;
  bairros: { id: string; nome: string }[];
  /** Estágio do distrito; `undefined` enquanto carrega ou se a fonte falhou. */
  item?: ItemEstagio;
  itensBairro: Map<string, ItemEstagio>;
  posicaoBairro: Map<string, number>;
  /** Linha do distrito na lista de prioridade (posição e contagens do Censo). */
  prioridade?: ItemPrioridadeTerritorio;
  totalDistritos: number;
  carregandoEstagios: boolean;
  carregandoPrioridade: boolean;
  fontesPrioridade: FonteDado[];
  prioridadeEm: number;
  podeDeclarar: boolean;
  aoDeclarar: PropsPainel["aoDeclarar"];
  aoRetirar: PropsPainel["aoRetirar"];
  aoEscolherBairro: (id: string) => void;
  aoVoltar: () => void;
}

function Numero({
  rotulo,
  valor,
  carregando,
}: {
  rotulo: string;
  valor: number | null | undefined;
  carregando: boolean;
}) {
  return (
    <div>
      <dt>{rotulo}</dt>
      <dd>
        <b className="numeros">
          {carregando && valor === undefined
            ? "Carregando…"
            : valor == null
              ? "Dados insuficientes"
              : formatarNumero(valor)}
        </b>
      </dd>
    </div>
  );
}

export function PainelDistrito(p: PropsPainelDistrito) {
  const titulo = useRef<HTMLHeadingElement>(null);
  useEffect(() => titulo.current?.focus({ preventScroll: true }), [p.id]);

  const nome = nomeDoDistrito(p.id);
  const itens = p.bairros
    .map((b) => ({ ...b, item: p.itensBairro.get(b.id), pos: p.posicaoBairro.get(b.id) }))
    .sort((a, b) => {
      const oa = a.item ? (emVigor(a.item).ordem ?? -1) : -1;
      const ob = b.item ? (emVigor(b.item).ordem ?? -1) : -1;
      if (oa !== ob) return ob - oa;
      const pa = a.pos ?? Number.MAX_SAFE_INTEGER;
      const pb = b.pos ?? Number.MAX_SAFE_INTEGER;
      return pa !== pb ? pa - pb : a.nome.localeCompare(b.nome, "pt-BR");
    });
  const contagem = contarPorEstagio(itens.flatMap((i) => (i.item ? [i.item] : []))).filter(
    (c) => c.declarados + c.sugeridos > 0,
  );
  const vigor = p.item ? emVigor(p.item) : null;
  const pr = p.prioridade;

  return (
    <aside className={estilos.painel} aria-labelledby="painel-nome" data-nivel="distrito">
      <header className={estilos.painelTopo}>
        <div>
          <h2 id="painel-nome" ref={titulo} tabIndex={-1}>
            <i className={estilos.chipCor} style={{ background: corDoDistrito(p.id) }} aria-hidden="true" />
            {nome}
          </h2>
          <p className={estilos.painelDistrito}>
            {siglaDoDistrito(p.id)} · {p.bairros.length} bairros
          </p>
        </div>
        <button type="button" className={estilos.fechar} onClick={p.aoVoltar} aria-label="Fechar o painel">
          <X aria-hidden="true" size={24} />
        </button>
      </header>
      <VoltarRecife aoClicar={p.aoVoltar} />

      <section className={estilos.bloco} aria-labelledby="distrito-estagio">
        <h3 id="distrito-estagio">Estágio do distrito</h3>
        {vigor ? (
          <p className={estilos.estagioVigor}>
            <SeloEstagio estagio={vigor.estagio} />
            <span>
              {vigor.origem === "declarado"
                ? "declarado pela equipe"
                : vigor.origem === "sugerido"
                  ? "sugerido pelo sistema; ninguém declarou"
                  : "o sistema não consegue sugerir e ninguém declarou"}
            </span>
          </p>
        ) : p.carregandoEstagios ? (
          <p className={estilos.apagado} role="status">
            Carregando o estágio…
          </p>
        ) : (
          <p>
            <b>Dados insuficientes:</b> falta a fonte dos estágios (previsão de chuva e de maré).
          </p>
        )}
        {contagem.length > 0 && (
          <ul className={estilos.miniContagem} aria-label="Bairros por estágio">
            {contagem.map((c) => (
              <li key={c.estagio} data-estagio={c.estagio}>
                <b>{c.declarados + c.sugeridos}</b> {c.rotulo.toLowerCase()}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className={estilos.bloco} aria-labelledby="distrito-numeros">
        <h3 id="distrito-numeros">Números do distrito</h3>
        <dl className={estilos.numeros}>
          <div>
            <dt>Prioridade</dt>
            <dd>
              <b className="numeros">
                {pr
                  ? `${pr.posicao}º de ${p.totalDistritos}`
                  : p.carregandoPrioridade
                    ? "Carregando…"
                    : "Dados insuficientes"}
              </b>
              <small>1º é o mais vulnerável. Não é chance de acontecer.</small>
            </dd>
          </div>
          <Numero
            rotulo="Idosos (60 anos ou mais)"
            valor={pr ? (pr.idosos_60_mais ?? null) : undefined}
            carregando={p.carregandoPrioridade}
          />
          <Numero
            rotulo="Crianças (0 a 14 anos)"
            valor={pr ? (pr.criancas_0_14 ?? null) : undefined}
            carregando={p.carregandoPrioridade}
          />
          <Numero
            rotulo="Ocorrências de alagamento"
            valor={pr ? (pr.ocorrencias_alagamento ?? null) : undefined}
            carregando={p.carregandoPrioridade}
          />
          <Numero
            rotulo="Ocorrências de deslizamento"
            valor={pr ? (pr.ocorrencias_deslizamento ?? null) : undefined}
            carregando={p.carregandoPrioridade}
          />
        </dl>
        <LegendaFonte fontes={p.fontesPrioridade}>
          {p.fontesPrioridade.length === 0 && (
            <span>
              Fonte: IBGE (Censo 2022) e ocorrências registradas da Defesa Civil
              {p.prioridadeEm ? `, consultado às ${formatarHoraMinuto(p.prioridadeEm)}` : ""}.
            </span>
          )}
        </LegendaFonte>
      </section>

      <section className={estilos.bloco} aria-labelledby="distrito-bairros">
        <h3 id="distrito-bairros">Bairros do distrito</h3>
        <p className={estilos.apagado}>Os mais vulneráveis primeiro. Toque em um bairro para ver o resumo.</p>
        <ul className={estilos.bairrosDoDistrito}>
          {itens.map((b) => (
            <li key={b.id}>
              <button type="button" onClick={() => p.aoEscolherBairro(b.id)}>
                <MapPin aria-hidden="true" size={18} />
                <span className={estilos.nomeBairro}>{b.nome}</span>
                {b.item ? (
                  <SeloEstagio estagio={emVigor(b.item).estagio} pequena />
                ) : (
                  <small>{p.carregandoEstagios ? "Carregando…" : "Dados insuficientes"}</small>
                )}
              </button>
            </li>
          ))}
        </ul>
      </section>

      {p.item && (
        <details className={estilos.maisDetalhe}>
          <summary>Alertas oficiais e declaração do estágio do distrito</summary>
          <PainelTerritorio
            item={p.item}
            semTopo
            podeDeclarar={p.podeDeclarar}
            aoDeclarar={p.aoDeclarar}
            aoRetirar={p.aoRetirar}
            aoFechar={p.aoVoltar}
          />
        </details>
      )}
    </aside>
  );
}
