/**
 * Painel do território escolhido no mapa (RF-07), feito para ler em 5 segundos: nome e distrito, o estágio em
 * destaque, alertas oficiais em uma linha, os números do bairro em grade e a fonte uma vez só, no rodapé (RF-19).
 * O sistema sugere; a equipe declara (RN-05). Sem dado, "Dados insuficientes" e a fonte que falta (RN-01).
 */
import { nomeDoDistrito } from "@/map/paleta";
import { useEffect, useRef } from "react";
import { ChevronLeft, ShieldCheck, X } from "lucide-react";
import { Botao } from "@/design-system/componentes/Botao";
import { EstadoDados } from "@/design-system/componentes/EstadoDados";
import { LINK_APAC, LINK_CEMADEN, SeloEstagio } from "@/features/evento/Evento";
import { ESTAGIOS, infoEstagio } from "@/features/evento/estagios";
import { quandoAs } from "@/features/evento/textos";
import type { ItemEstagio } from "@/features/evento/tipos";
import { nomeDistrito } from "@/lib/distritos";
import { formatarDataHora } from "@/lib/formatos";
import { Dica } from "./Dica";
import { FichaChuva, FichaHistorico } from "./FichaSituacao";
import { ResumoBairro, RodapeFontes } from "./ResumoBairro";
import { emVigor } from "./tipos";
import estilos from "./Mapa.module.css";

type Alerta = {
  origem?: string;
  evento?: string | null;
  nivel?: string;
  emitido_em?: string;
  expira_em?: string | null;
  area?: string | null;
  url?: string | null;
};

export interface PropsPainel {
  item: ItemEstagio;
  podeDeclarar: boolean;
  aoDeclarar: (i: ItemEstagio) => void;
  aoRetirar: (i: ItemEstagio) => void;
  aoFechar: () => void;
  /** Sem cabeçalho nem resumo do bairro: usado dentro do painel do distrito (que já tem os dois). */
  semTopo?: boolean;
  /** Volta do bairro para o distrito dele (nível acima). */
  voltarDistrito?: { rotulo: string; aoClicar: () => void };
  /** Distrito do bairro e limiares dos estágios: a ficha mostra a chuva do distrito contra o gatilho. */
  distritoItem?: ItemEstagio;
  limiares?: Record<string, number>;
}

/** "Quem decidiu" em poucas palavras, para a linha do estágio. */
export function textoOrigem(origem: string | null | undefined): string {
  if (origem === "declarado") return "declarado pela equipe";
  if (origem === "sugerido") return "sugerido pelo sistema";
  return "o sistema não consegue sugerir";
}

/** Conferência na fonte oficial, em uma frase curta (RN-01: sem alerta registrado não quer dizer que não haja). */
function ConferirOficial() {
  return (
    <span className={estilos.conferir}>
      <ShieldCheck aria-hidden="true" size={15} />
      conferir{" "}
      <a href={LINK_APAC} target="_blank" rel="noopener noreferrer">
        APAC<span className="so-leitor"> (abre em nova aba)</span>
      </a>{" "}
      /{" "}
      <a href={LINK_CEMADEN} target="_blank" rel="noopener noreferrer">
        Cemaden<span className="so-leitor"> (abre em nova aba)</span>
      </a>
    </span>
  );
}

export function PainelTerritorio({
  item,
  podeDeclarar,
  aoDeclarar,
  aoRetirar,
  aoFechar,
  semTopo,
  voltarDistrito,
  distritoItem,
  limiares,
}: PropsPainel) {
  const titulo = useRef<HTMLHeadingElement>(null);
  useEffect(() => titulo.current?.focus({ preventScroll: true }), [item.territorio_id]);

  const vigor = emVigor(item);
  const sug = infoEstagio(item.sugerido?.estagio);
  const semSugestao = sug === ESTAGIOS.sem_dados;
  const dec = item.declarado;
  const temDeclaracao = !!dec && infoEstagio(dec.estagio).ordem >= 0;
  const alertas = item.alertas_oficiais as Alerta[] | undefined;
  const ehDistrito = item.nivel === "distrito";
  const distritoId = ehDistrito ? item.territorio_id : item.distrito_id;
  const fonteEstagio = semSugestao
    ? null
    : `${item.sugerido.fontes?.map((f) => f.nome).join(", ") || "fonte não informada"}${
        item.sugerido.calculado_em ? `, calculado ${quandoAs(item.sugerido.calculado_em)}` : ""
      }`;

  return (
    <aside className={estilos.painel} aria-labelledby="painel-nome">
      {!semTopo && (
        <header className={estilos.painelTopo}>
          <div>
            <h2 id="painel-nome" ref={titulo} tabIndex={-1}>
              {nomeDistrito(item.territorio_nome)}
            </h2>
            {voltarDistrito ? (
              <button type="button" className={estilos.voltarNivel} onClick={voltarDistrito.aoClicar}>
                <ChevronLeft aria-hidden="true" size={16} />
                {voltarDistrito.rotulo}
              </button>
            ) : (
              <p className={estilos.painelDistrito}>
                {ehDistrito ? "Distrito" : distritoId ? nomeDoDistrito(distritoId) : "Distrito não informado"}
              </p>
            )}
          </div>
          <button type="button" className={estilos.fechar} onClick={aoFechar} aria-label="Fechar o painel">
            <X aria-hidden="true" size={22} />
          </button>
        </header>
      )}

      <section className={estilos.bloco} aria-labelledby="painel-estagio">
        <h3 id="painel-estagio" className="so-leitor">
          Estágio
        </h3>
        <p className={estilos.estagioVigor}>
          <SeloEstagio estagio={vigor.estagio} />
          <span>· {textoOrigem(vigor.origem)}</span>
        </p>
        <p className={estilos.linhaApoio}>
          <span>
            Declarado:{" "}
            {temDeclaracao ? (
              <>
                <b>{infoEstagio(dec.estagio).rotulo}</b>{" "}
                <span>
                  {dec.herdado
                    ? `declarado para ${dec.territorio_origem_nome ?? "o distrito ou a cidade"}`
                    : `por ${dec.autor_nome}, ${quandoAs(dec.declarado_em)}`}
                </span>
                {dec.justificativa && <span> “{dec.justificativa}”</span>}
              </>
            ) : (
              <b>ninguém</b>
            )}
          </span>
          <span aria-hidden="true"> · </span>
          <span>
            Sugerido: <b>{semSugestao ? "Dados insuficientes" : sug.rotulo}</b>
          </span>
        </p>
        {semSugestao && (
          <p className={estilos.linhaApoio}>
            Falta{" "}
            {item.sugerido?.faltando?.length
              ? item.sugerido.faltando.join(", ")
              : "a previsão de chuva ou de maré"}
            . Isso não quer dizer risco baixo.
          </p>
        )}
        {!semSugestao && item.sugerido.motivos.length > 0 && (
          <details className={estilos.verTodos}>
            <summary>Por que {sug.rotulo.toLowerCase()}?</summary>
            <ul className={estilos.motivos}>
              {item.sugerido.motivos.slice(0, 3).map((m) => (
                <li key={m}>{m}</li>
              ))}
            </ul>
          </details>
        )}
        {podeDeclarar && (
          <div className={estilos.acoesPainel}>
            <Botao onClick={() => aoDeclarar(item)}>
              Declarar<span className="so-leitor"> estágio de {item.territorio_nome}</span>
            </Botao>
            {dec && !dec.herdado && temDeclaracao && (
              <Botao variante="secundario" onClick={() => aoRetirar(item)}>
                Retirar declaração
              </Botao>
            )}
          </div>
        )}
      </section>

      <section className={estilos.bloco} aria-labelledby="painel-alertas">
        {alertas === undefined ? (
          <>
            <h3 id="painel-alertas">Alertas oficiais</h3>
            <EstadoDados tipo="insuficiente">
              Falta a fonte de alertas oficiais (APAC, Cemaden, Defesa Civil).
            </EstadoDados>
          </>
        ) : alertas.length === 0 ? (
          <div className={estilos.linhaAlerta}>
            <h3 id="painel-alertas">Alertas oficiais:</h3> <span>sem alerta oficial ativo</span>
            <Dica
              texto="Sem alerta registrado no sistema não quer dizer que não haja. Confira na APAC e no Cemaden."
              rotulo="Saiba mais sobre os alertas oficiais"
            />
            <span aria-hidden="true">·</span> <ConferirOficial />
          </div>
        ) : (
          <>
            <h3 id="painel-alertas">Alertas oficiais ({alertas.length})</h3>
            <ul className={estilos.alertas}>
              {alertas.map((a, i) => (
                <li key={`${a.origem}-${a.emitido_em}-${i}`}>
                  <b>
                    {a.origem ?? "Fonte não informada"}
                    {a.evento ? `: ${a.evento}` : ""}
                    {a.nivel ? ` (${a.nivel})` : ""}
                  </b>
                  <small>
                    Emitido {a.emitido_em ? formatarDataHora(a.emitido_em) : "em hora não informada"}
                    {a.expira_em ? `, vale até ${formatarDataHora(a.expira_em)}` : ""}
                  </small>
                  <small>
                    Território: {a.area || `${item.territorio_nome} (alerta do município do Recife)`}
                  </small>
                  {a.url && (
                    <a href={a.url} target="_blank" rel="noopener noreferrer">
                      Ver o aviso na fonte<span className="so-leitor"> (abre em nova aba)</span>
                    </a>
                  )}
                </li>
              ))}
            </ul>
            <p className={estilos.linhaApoio}>
              <ConferirOficial />
            </p>
          </>
        )}
      </section>

      {ehDistrito ? (
        semTopo ? null : (
          <section className={estilos.bloco} aria-labelledby="painel-vulneravel">
            <h3 id="painel-vulneravel">População e saúde</h3>
            <p className={estilos.apagado}>Os números são por bairro: escolha um bairro deste distrito.</p>
          </section>
        )
      ) : (
        <>
          {!semTopo && <FichaChuva distrito={distritoItem} limiares={limiares} />}
          <ResumoBairro territorioId={item.territorio_id} />
          {!semTopo && <FichaHistorico bairroId={item.territorio_id} />}
        </>
      )}

      <RodapeFontes territorioId={ehDistrito ? null : item.territorio_id} fonteEstagio={fonteEstagio} />
    </aside>
  );
}
