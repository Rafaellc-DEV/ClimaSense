import { CircleOff, MapPin, MessageCircle, TriangleAlert } from "lucide-react";
import { Botao } from "@/design-system/componentes/Botao";
import { CarregandoLista } from "@/design-system/componentes/Esqueleto";
import { formatarMm, formatarNumero } from "@/lib/formatos";
import { ESTAGIOS, infoEstagio } from "@/features/evento/estagios";
import { EstadoConsulta, SeloEstagio } from "@/features/evento/Evento";
import { nomeCurto, quandoAs } from "@/features/evento/textos";
import type { ItemEstagio } from "@/features/evento/tipos";
import { pedeDecisao } from "./Declarar";
import { estagioEmVigor, insumo, separarBairros } from "./resumo";
import estilos from "./Situacao.module.css";

export interface EstadoBairros {
  carregando: boolean;
  erro: Error | null;
  aoTentar: () => void;
  lista: ItemEstagio[];
}

interface Props {
  item: ItemEstagio;
  /** Cartão de quem pede decisão: maior, com destaque. */
  grande: boolean;
  comuns: string[];
  faltaComum: boolean;
  selecionado: boolean;
  aoSelecionar: () => void;
  bairros: EstadoBairros;
  podeDeclarar: boolean;
  aoDeclarar: (i: ItemEstagio) => void;
  aoRetirar: (i: ItemEstagio) => void;
  aoWhatsApp: (i: ItemEstagio) => void;
}

/** O porquê do que o sistema diz, sem os motivos comuns a todos. `null` quando não há nada próprio a dizer. */
export function frasePorQue(i: ItemEstagio, comuns: string[], faltaComum: boolean): string | null {
  const sug = infoEstagio(i.sugerido?.estagio);
  if (sug === ESTAGIOS.sem_dados)
    return faltaComum
      ? null
      : `Sem dado: falta ${(i.sugerido?.faltando ?? []).join(", ") || "insumo para sugerir"}.`;
  if (!pedeDecisao(i)) return null;
  const proprios = (i.sugerido?.motivos ?? []).filter((m) => !comuns.includes(m));
  return proprios.join(" ") || null;
}

function Numero({ rotulo, valor }: { rotulo: string; valor: number | null }) {
  return (
    <div>
      <dt>{rotulo}</dt>
      <dd data-vazio={valor === null}>{valor === null ? "sem dado" : formatarMm(valor)}</dd>
    </div>
  );
}

export function CartaoDistrito({
  item: d,
  grande,
  comuns,
  faltaComum,
  selecionado,
  aoSelecionar,
  bairros,
  podeDeclarar,
  aoDeclarar,
  aoRetirar,
  aoWhatsApp,
}: Props) {
  const nome = nomeCurto(d.territorio_nome);
  const pede = pedeDecisao(d);
  const sug = infoEstagio(d.sugerido?.estagio);
  const semDado = sug === ESTAGIOS.sem_dados;
  const porQue = frasePorQue(d, comuns, faltaComum);
  const avisos = d.alertas_oficiais;
  return (
    <article
      id={`distrito-${d.territorio_id}`}
      className={estilos.cartao}
      data-pede={pede}
      data-grande={grande}
      data-selecionado={selecionado}
      aria-labelledby={`nome-${d.territorio_id}`}
    >
      <header className={estilos.cabecaCartao}>
        <h4 id={`nome-${d.territorio_id}`} className={estilos.nome} title={d.territorio_nome}>
          <button
            type="button"
            data-nome
            className={estilos.nomeBotao}
            aria-pressed={selecionado}
            onClick={aoSelecionar}
          >
            <MapPin aria-hidden="true" size={18} />
            {nome}
            <span className="so-leitor">
              {" "}
              ({d.territorio_nome}): {selecionado ? "tirar o destaque do mapa" : "mostrar no mapa"}
            </span>
          </button>
        </h4>
        <span className={estilos.seloGrande}>
          <SeloEstagio estagio={estagioEmVigor(d)} />
          <small hidden={!grande && !d.declarado && !semDado}>
            {d.declarado
              ? d.declarado.herdado
                ? "declarada para a cidade"
                : `declarada por ${d.declarado.autor_nome}, ${quandoAs(d.declarado.declarado_em)}`
              : semDado
                ? "o sistema não consegue sugerir"
                : "sugerida pelo sistema, ninguém declarou"}
          </small>
        </span>
      </header>

      {pede && (
        <p className={estilos.diverge}>
          <TriangleAlert aria-hidden="true" size={18} />
          <span>
            <b>O sistema sugere {sug.rotulo}</b>
            {d.declarado
              ? `; a equipe declarou ${infoEstagio(d.declarado.estagio).rotulo}.`
              : ", ninguém declarou."}
            {porQue && <span className={estilos.porQue}> {porQue}</span>}
          </span>
        </p>
      )}
      {!pede && porQue && <p className={estilos.porQueSimples}>{porQue}</p>}

      <dl className={estilos.numeros}>
        <Numero rotulo="Choveu em 24 h" valor={insumo(d, "chuva_24h_mm")} />
        <Numero rotulo="Previsto em 24 h" valor={insumo(d, "chuva_prev_24h_mm")} />
        <Numero rotulo="Previsto em 72 h" valor={insumo(d, "chuva_prev_72h_mm")} />
      </dl>
      <p
        className={estilos.avisos}
        data-ativo={!!avisos?.length}
        hidden={!grande && Array.isArray(avisos) && avisos.length === 0}
      >
        {avisos === undefined
          ? "Avisos oficiais: sem dado."
          : avisos.length === 0
            ? "Nenhum aviso oficial ativo."
            : avisos.length === 1
              ? "1 aviso oficial ativo."
              : `${formatarNumero(avisos.length)} avisos oficiais ativos.`}
      </p>

      <BairrosDoDistrito
        compacto={!grande}
        distrito={d}
        estado={bairros}
        podeDeclarar={podeDeclarar}
        aoDeclarar={aoDeclarar}
      />

      <div className={estilos.acoesCartao}>
        {podeDeclarar && (
          <Botao variante={pede ? "principal" : "secundario"} onClick={() => aoDeclarar(d)}>
            Declarar<span className="so-leitor"> situação de {d.territorio_nome}</span>
          </Botao>
        )}
        {podeDeclarar && d.declarado && !d.declarado.herdado && (
          <Botao variante="discreto" icone={<CircleOff />} onClick={() => aoRetirar(d)}>
            Retirar<span className="so-leitor"> declaração de {d.territorio_nome}</span>
          </Botao>
        )}
        <Botao variante="discreto" icone={<MessageCircle />} onClick={() => aoWhatsApp(d)}>
          WhatsApp<span className="so-leitor"> para {d.territorio_nome}</span>
        </Botao>
      </div>
    </article>
  );
}

/* ------------------------------------------------------------------ bairros do distrito */
function BairrosDoDistrito({
  compacto,
  distrito,
  estado,
  podeDeclarar,
  aoDeclarar,
}: {
  compacto: boolean;
  distrito: ItemEstagio;
  estado: EstadoBairros;
  podeDeclarar: boolean;
  aoDeclarar: (i: ItemEstagio) => void;
}) {
  const nome = nomeCurto(distrito.territorio_nome);
  if (estado.carregando) return <CarregandoLista linhas={1} altura="2rem" texto="Carregando os bairros…" />;
  if (estado.erro)
    return <EstadoConsulta erro={estado.erro} oQue="as situações por bairro" aoTentar={estado.aoTentar} />;
  const { total, destaque, outros } = separarBairros(distrito, estado.lista);
  if (total === 0) return <p className={estilos.detalhe}>Sem situação por bairro neste distrito.</p>;
  return (
    <div className={estilos.bairros}>
      {destaque.length > 0 ? (
        <>
          <p className={estilos.tituloBairros}>
            {destaque.length === 1
              ? "1 bairro passa do distrito"
              : `${destaque.length} bairros passam do distrito`}
          </p>
          <ul
            className={estilos.bairrosDestaque}
            aria-label={`Bairros de ${distrito.territorio_nome} que pedem atenção`}
          >
            {destaque.map((b) => {
              const ocorr = b.sugerido?.insumos?.ocorrencias_historicas;
              return (
                <li key={b.territorio_id} data-pede={pedeDecisao(b)}>
                  <span className={estilos.nomeBairro}>{b.territorio_nome}</span>
                  <SeloEstagio estagio={b.declarado?.estagio ?? b.sugerido?.estagio} pequena />
                  <small>
                    {b.declarado && !b.declarado.herdado ? "declarada" : "sugerida"}
                    {typeof ocorr === "number" && ocorr > 0
                      ? `, ${
                          ocorr === 1
                            ? "1 alagamento registrado"
                            : `${formatarNumero(ocorr)} alagamentos registrados`
                        }`
                      : ""}
                  </small>
                  {podeDeclarar && (
                    <Botao variante="discreto" onClick={() => aoDeclarar(b)}>
                      Declarar<span className="so-leitor"> situação de {b.territorio_nome}</span>
                    </Botao>
                  )}
                </li>
              );
            })}
          </ul>
        </>
      ) : compacto ? null : (
        <p className={estilos.detalhe}>
          {total === 1 ? "O bairro segue" : `Os ${total} bairros seguem`} a situação sugerida do {nome}.
        </p>
      )}
      {outros.length > 0 && (
        <details className={estilos.outrosBairros}>
          <summary>
            {destaque.length > 0 ? `Outros ${outros.length} bairros` : `Ver os ${outros.length} bairros`}
            <span className="so-leitor"> do {distrito.territorio_nome}</span>
          </summary>
          <ul className={estilos.listaOutros} aria-label={`Demais bairros de ${distrito.territorio_nome}`}>
            {outros.map((b) => (
              <li key={b.territorio_id}>
                <span>{b.territorio_nome}</span>
                <SeloEstagio estagio={b.declarado?.estagio ?? b.sugerido?.estagio} pequena />
                {podeDeclarar && (
                  <Botao variante="discreto" onClick={() => aoDeclarar(b)}>
                    Declarar<span className="so-leitor"> situação de {b.territorio_nome}</span>
                  </Botao>
                )}
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}
