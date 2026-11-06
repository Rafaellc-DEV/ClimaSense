/** Painel do território escolhido no mapa (RF-07): estágio, alertas oficiais, abrigos e ações. */
import { useEffect, useRef } from "react";
import { X } from "lucide-react";
import { Botao } from "@/design-system/componentes/Botao";
import { EstadoDados } from "@/design-system/componentes/EstadoDados";
import { ConfiraOficial, EstadoConsulta, SeloEstagio } from "@/features/evento/Evento";
import { ESTAGIOS, infoEstagio } from "@/features/evento/estagios";
import { quandoAs } from "@/features/evento/textos";
import type { Abrigo, ItemEstagio } from "@/features/evento/tipos";
import { formatarDataHora } from "@/lib/formatos";
import { distritoPorExtenso } from "@/textos/glossario";
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

function situacaoAbrigo(a: Abrigo): string {
  if (a.status_fonte === null || a.status_fonte === undefined) return "situação não informada";
  return a.aberto ? "aberto" : "fechado";
}

function ItemAbrigo({ a }: { a: Abrigo }) {
  return (
    <li>
      <span className={estilos.abrigoNome}>{a.nome}</span>
      <span className={estilos.abrigoSit} data-aberto={a.status_fonte ? a.aberto : undefined}>
        {situacaoAbrigo(a)}
      </span>
      {a.endereco && <small>{a.endereco}</small>}
      {a.atualizado_em && <small>Atualizado {quandoAs(a.atualizado_em)}</small>}
    </li>
  );
}

export interface PropsPainel {
  item: ItemEstagio;
  abrigos: { lista: Abrigo[]; carregando: boolean; erro: Error | null; aoTentar: () => void };
  podeDeclarar: boolean;
  aoDeclarar: (i: ItemEstagio) => void;
  aoRetirar: (i: ItemEstagio) => void;
  aoFechar: () => void;
}

export function PainelTerritorio({
  item,
  abrigos,
  podeDeclarar,
  aoDeclarar,
  aoRetirar,
  aoFechar,
}: PropsPainel) {
  const titulo = useRef<HTMLHeadingElement>(null);
  useEffect(() => titulo.current?.focus({ preventScroll: true }), [item.territorio_id]);

  const vigor = emVigor(item);
  const sug = infoEstagio(item.sugerido?.estagio);
  const semSugestao = sug === ESTAGIOS.sem_dados;
  const dec = item.declarado;
  const alertas = item.alertas_oficiais as Alerta[] | undefined;
  const ehDistrito = item.nivel === "distrito";
  const distritoId = ehDistrito ? item.territorio_id : item.distrito_id;
  const doTerritorio = abrigos.lista.filter((a) =>
    ehDistrito ? a.distrito_id === item.territorio_id : a.bairro_id === item.territorio_id,
  );
  const proximos = abrigos.lista
    .filter(
      (a) => !ehDistrito && distritoId && a.distrito_id === distritoId && a.bairro_id !== item.territorio_id,
    )
    .sort((a, b) => Number(b.aberto) - Number(a.aberto) || a.nome.localeCompare(b.nome, "pt-BR"))
    .slice(0, 5);

  return (
    <aside className={estilos.painel} aria-labelledby="painel-nome">
      <header className={estilos.painelTopo}>
        <div>
          <h2 id="painel-nome" ref={titulo} tabIndex={-1}>
            {item.territorio_nome}
          </h2>
          <p className={estilos.painelDistrito}>
            {ehDistrito
              ? "Distrito sanitário"
              : distritoId
                ? distritoPorExtenso(distritoId)
                : "Distrito não informado"}
          </p>
        </div>
        <button type="button" className={estilos.fechar} onClick={aoFechar} aria-label="Fechar o painel">
          <X aria-hidden="true" size={24} />
        </button>
      </header>

      <section className={estilos.bloco} aria-labelledby="painel-estagio">
        <h3 id="painel-estagio">Estágio</h3>
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
        <dl className={estilos.dupla}>
          <div>
            <dt>Declarado</dt>
            <dd>
              {dec && infoEstagio(dec.estagio).ordem >= 0 ? (
                <>
                  <b>{infoEstagio(dec.estagio).rotulo}</b>
                  <small>
                    {dec.herdado
                      ? `declarado para ${dec.territorio_origem_nome ?? "o distrito ou a cidade"}`
                      : `por ${dec.autor_nome}, ${quandoAs(dec.declarado_em)}`}
                  </small>
                  {dec.justificativa && <small>“{dec.justificativa}”</small>}
                </>
              ) : (
                <span className={estilos.apagado}>Ninguém declarou.</span>
              )}
            </dd>
          </div>
          <div>
            <dt>Sugerido pelo sistema</dt>
            <dd>
              {semSugestao ? (
                <>
                  <b>Dados insuficientes</b>
                  <small>
                    Falta{" "}
                    {item.sugerido?.faltando?.length
                      ? item.sugerido.faltando.join(", ")
                      : "a previsão de chuva ou de maré"}
                    . Isso não quer dizer risco baixo.
                  </small>
                </>
              ) : (
                <>
                  <b>{sug.rotulo}</b>
                  {item.sugerido.motivos.slice(0, 3).map((m) => (
                    <small key={m}>{m}</small>
                  ))}
                  <small>
                    Fonte: {item.sugerido.fontes?.map((f) => f.nome).join(", ") || "sem dado"}
                    {item.sugerido.calculado_em && `, calculado ${quandoAs(item.sugerido.calculado_em)}`}
                  </small>
                </>
              )}
            </dd>
          </div>
        </dl>
        {podeDeclarar && (
          <div className={estilos.acoesPainel}>
            <Botao onClick={() => aoDeclarar(item)}>
              Declarar<span className="so-leitor"> estágio de {item.territorio_nome}</span>
            </Botao>
            {dec && !dec.herdado && infoEstagio(dec.estagio).ordem >= 0 && (
              <Botao variante="secundario" onClick={() => aoRetirar(item)}>
                Retirar declaração
              </Botao>
            )}
          </div>
        )}
      </section>

      <section className={estilos.bloco} aria-labelledby="painel-alertas">
        <h3 id="painel-alertas">Alertas oficiais</h3>
        {alertas === undefined ? (
          <EstadoDados tipo="insuficiente">
            Falta a fonte de alertas oficiais (APAC, Cemaden, Defesa Civil).
          </EstadoDados>
        ) : alertas.length === 0 ? (
          <p>
            Nenhum alerta oficial ativo registrado no sistema. Isso não quer dizer que não haja: confira
            abaixo.
          </p>
        ) : (
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
        )}
        <ConfiraOficial />
      </section>

      <section className={estilos.bloco} aria-labelledby="painel-abrigos">
        <h3 id="painel-abrigos">Abrigos</h3>
        {abrigos.carregando && <p className={estilos.apagado}>Carregando os abrigos…</p>}
        {abrigos.erro && <EstadoConsulta erro={abrigos.erro} oQue="os abrigos" aoTentar={abrigos.aoTentar} />}
        {!abrigos.carregando && !abrigos.erro && (
          <>
            {doTerritorio.length === 0 ? (
              <p>Nenhum abrigo cadastrado {ehDistrito ? "neste distrito" : "neste bairro"}.</p>
            ) : (
              <ul className={estilos.abrigos}>
                {doTerritorio.map((a) => (
                  <ItemAbrigo key={a.id} a={a} />
                ))}
              </ul>
            )}
            {proximos.length > 0 && (
              <>
                <h4>Outros abrigos do mesmo distrito</h4>
                <ul className={estilos.abrigos}>
                  {proximos.map((a) => (
                    <ItemAbrigo key={a.id} a={a} />
                  ))}
                </ul>
              </>
            )}
          </>
        )}
      </section>

      <section className={estilos.bloco} aria-labelledby="painel-breve">
        <h3 id="painel-breve">População vulnerável e equipamentos de saúde</h3>
        <p className={estilos.emBreve}>
          <b>Em breve.</b> Pessoas com deficiência, idosos, crianças e unidades de saúde do território entram
          quando as fontes forem integradas. Por enquanto, não há número para mostrar.
        </p>
      </section>
    </aside>
  );
}
