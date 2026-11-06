/** Peças comuns às telas do evento de chuva: situação, origem do dado (F7), mensagem de WhatsApp (F2) e o 404. */
import { useId, useRef } from "react";
import type { QueryClient } from "@tanstack/react-query";
import { Copy, ExternalLink, MessageCircle, ShieldCheck } from "lucide-react";
import { useAviso } from "@/design-system/componentes/Aviso";
import { Botao, classesBotao } from "@/design-system/componentes/Botao";
import { EstadoDados } from "@/design-system/componentes/EstadoDados";
import { Pilula } from "@/design-system/componentes/Pilula";
import { enviar, ErroApi } from "@/lib/api";
import { formatarDataHora, formatarNumero } from "@/lib/formatos";
import { useTerritorios } from "@/app/FiltroFrase";
import campo from "@/design-system/componentes/Campo.module.css";
import { infoEstagio } from "./estagios";
import { linkWhatsApp, type FonteEvento, type MensagemWhatsApp } from "./tipos";
import estilos from "./Evento.module.css";

export const LINK_APAC = "https://www.apac.pe.gov.br/";
export const LINK_CEMADEN = "https://www.gov.br/cemaden/pt-br";

/** Situação com cor e nome escrito (RN-17). `sem_dados` sai em cinza tracejado, nunca verde. */
export function SeloEstagio({ estagio, pequena }: { estagio: string | null | undefined; pequena?: boolean }) {
  const e = infoEstagio(estagio);
  return (
    <Pilula nivel={e.nivel} pequena={pequena}>
      {e.rotulo}
    </Pilula>
  );
}

/** F7: lembrete de conferir o alerta oficial. Aparece em toda tela que mostra situação ou aviso. */
export function ConfiraOficial({ sobreMare }: { sobreMare?: boolean }) {
  return (
    <p className={[estilos.confira, sobreMare && estilos.sobreMare].filter(Boolean).join(" ")}>
      <ShieldCheck aria-hidden="true" size={18} />
      <span>
        Confira o alerta oficial na{" "}
        <a href={LINK_APAC} target="_blank" rel="noopener noreferrer">
          APAC<span className="so-leitor"> (abre em nova aba)</span>
        </a>{" "}
        e no{" "}
        <a href={LINK_CEMADEN} target="_blank" rel="noopener noreferrer">
          Cemaden<span className="so-leitor"> (abre em nova aba)</span>
        </a>
        .
      </span>
    </p>
  );
}

/** F7: de onde veio, quando e para qual território exato. Partes ausentes viram “sem dado”, nunca somem caladas. */
export function Origem({
  fontes,
  hora,
  rotuloHora = "Calculado em",
  territorio,
}: {
  fontes: (FonteEvento | string)[];
  hora: string | null | undefined;
  rotuloHora?: string;
  territorio: string;
}) {
  const nomes = fontes.map((f) => (typeof f === "string" ? f : f.nome)).filter(Boolean);
  return (
    <p className={estilos.origem}>
      <span>
        <b>Fonte:</b> {nomes.length ? nomes.join(", ") : "sem dado"}
      </span>
      <span>
        <b>{rotuloHora}:</b> {hora ? formatarDataHora(hora) : "sem dado"}
      </span>
      <span>
        <b>Território:</b> {territorio}
      </span>
    </p>
  );
}

/**
 * Falha de consulta. 404 quer dizer que o servidor ainda não oferece este recurso: a tela diz isso com honestidade
 * e não mostra nada inventado no lugar.
 */
export function EstadoConsulta({
  erro,
  aoTentar,
  oQue,
}: {
  erro: Error | null;
  aoTentar?: () => void;
  /** “as situações”, “os abrigos”. */
  oQue: string;
}) {
  if (erro instanceof ErroApi && erro.status === 404)
    return (
      <EstadoDados tipo="insuficiente" titulo="Ainda não disponível.">
        O servidor ainda não oferece {oQue}. Nada é mostrado até haver dados reais.
      </EstadoDados>
    );
  return (
    <EstadoDados
      tipo="falha"
      titulo="Não foi possível carregar."
      acao={
        aoTentar && (
          <Botao variante="secundario" onClick={aoTentar}>
            Tentar de novo
          </Botao>
        )
      }
    >
      {erro?.message}
    </EstadoDados>
  );
}

/** Copia para a área de transferência; sem a API do navegador, seleciona o campo e usa o comando antigo. */
async function copiar(texto: string, campo: HTMLTextAreaElement | null) {
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(texto);
      return true;
    }
  } catch {
    /* cai no plano B */
  }
  if (!campo) return false;
  campo.select();
  try {
    return document.execCommand("copy");
  } catch {
    return false;
  }
}

/**
 * F2: texto pronto para os grupos de WhatsApp. Nada é enviado sozinho: a pessoa copia ou abre o WhatsApp com o
 * texto já escrito e escolhe o grupo.
 */
export function MensagemPronta({ mensagem, rotulo }: { mensagem: MensagemWhatsApp; rotulo: string }) {
  const avisar = useAviso();
  const campo = useRef<HTMLTextAreaElement>(null);
  const id = useId();
  // medição do piloto: quantas mensagens são copiadas ou abertas no WhatsApp (sem bloquear a pessoa se falhar)
  const registrar = (evento: "copiar" | "abrir_whatsapp") => {
    if (mensagem.uso)
      void enviar("/estagios/mensagem/uso", { evento, ...mensagem.uso }).catch(() => undefined);
  };
  return (
    <div className={estilos.mensagem}>
      <label className={estilos.rotuloMensagem} htmlFor={id}>
        {rotulo}
      </label>
      <textarea
        id={id}
        ref={campo}
        className={estilos.textoMensagem}
        readOnly
        value={mensagem.texto}
        rows={Math.min(14, Math.max(5, mensagem.texto.split("\n").length + 1))}
      />
      <div className={estilos.botoesMensagem}>
        <Botao
          icone={<Copy />}
          onClick={async () => {
            const ok = await copiar(mensagem.texto, campo.current);
            if (ok) registrar("copiar");
            avisar(
              ok
                ? { titulo: "Mensagem copiada.", texto: "Cole no grupo de WhatsApp do distrito." }
                : { titulo: "Não foi possível copiar.", texto: "Selecione o texto e copie.", tipo: "erro" },
            );
          }}
        >
          Copiar
        </Botao>
        <a
          className={classesBotao("secundario")}
          href={linkWhatsApp(mensagem)}
          target="_blank"
          rel="noopener noreferrer"
          onClick={() => registrar("abrir_whatsapp")}
        >
          <MessageCircle aria-hidden="true" /> Abrir no WhatsApp
          <ExternalLink aria-hidden="true" size={16} />
          <span className="so-leitor"> (abre em nova aba)</span>
        </a>
      </div>
      <p className={estilos.nota}>Nada é enviado automaticamente. Você escolhe o grupo no WhatsApp.</p>
    </div>
  );
}

/**
 * Escolha de território num `<select>` nativo (rápido no celular), com bairros agrupados por distrito.
 * `niveis` limita o que aparece: abrigo fica num bairro; ação pode ser distrito ou bairro.
 */
export function SelecaoTerritorio({
  rotulo,
  valor,
  aoMudar,
  niveis = ["distrito", "bairro"],
  vazio,
  erro,
  obrigatorio,
}: {
  rotulo: string;
  valor: string;
  aoMudar: (id: string) => void;
  niveis?: ("municipio" | "distrito" | "bairro")[];
  /** Texto da opção vazia (“Todos os territórios”). Sem ele, a opção vazia pede uma escolha. */
  vazio?: string;
  erro?: string;
  obrigatorio?: boolean;
}) {
  const id = useId();
  const r = useTerritorios();
  const lista = r.data ?? [];
  const distritos = lista
    .filter((t) => t.tipo === "distrito")
    .sort((a, b) => a.nome_exibicao.localeCompare(b.nome_exibicao, "pt-BR", { numeric: true }));
  const bairrosDe = (d: string) =>
    lista
      .filter((t) => t.tipo === "bairro" && t.pai_id === d)
      .sort((a, b) => a.nome_exibicao.localeCompare(b.nome_exibicao, "pt-BR"));
  const soltos = lista.filter((t) => t.tipo === "bairro" && !distritos.some((d) => d.id === t.pai_id));
  return (
    <div className={campo.campo}>
      <label htmlFor={id} className={campo.rotulo}>
        {rotulo}
      </label>
      <select
        id={id}
        className={campo.entrada}
        value={valor}
        onChange={(e) => aoMudar(e.target.value)}
        required={obrigatorio}
        aria-invalid={erro ? true : undefined}
        aria-describedby={erro ? `${id}-erro` : undefined}
        disabled={r.isPending}
      >
        <option value="">{r.isPending ? "Carregando…" : (vazio ?? "Escolha um território")}</option>
        {niveis.includes("municipio") && lista.some((t) => t.id === "recife") && (
          <option value="recife">Recife inteiro</option>
        )}
        {distritos.map((d) =>
          niveis.includes("bairro") ? (
            <optgroup key={d.id} label={d.nome_exibicao}>
              {niveis.includes("distrito") && (
                <option value={d.id}>{d.nome_exibicao} (distrito inteiro)</option>
              )}
              {bairrosDe(d.id).map((b) => (
                <option key={b.id} value={b.id}>
                  {b.nome_exibicao}
                </option>
              ))}
            </optgroup>
          ) : (
            <option key={d.id} value={d.id}>
              {d.nome_exibicao}
            </option>
          ),
        )}
        {niveis.includes("bairro") &&
          soltos.map((b) => (
            <option key={b.id} value={b.id}>
              {b.nome_exibicao}
            </option>
          ))}
      </select>
      {r.isError && <p className={campo.ajuda}>Não foi possível carregar a lista de territórios.</p>}
      {erro && (
        <p id={`${id}-erro`} className={campo.erro} role="alert">
          {erro}
        </p>
      )}
    </div>
  );
}

/** Nome de exibição de um território pelo id, com a lista de `/territorios`. */
export function useNomeTerritorio() {
  const r = useTerritorios();
  return (id: string | null | undefined, reserva?: string | null) =>
    reserva || (id ? (r.data?.find((t) => t.id === id)?.nome_exibicao ?? id) : "sem dado");
}

/** Invalida toda consulta cujo caminho começa com o prefixo (a chave é o caminho com a query string). */
export function invalidarPrefixo(cliente: QueryClient, prefixo: string) {
  return cliente.invalidateQueries({
    predicate: (q) => typeof q.queryKey[0] === "string" && q.queryKey[0].startsWith(prefixo),
  });
}

/** Número formatado, ou `null` (o Indicador mostra “Sem dado”, nunca zero). */
export function numeroOuNulo(v: number | null | undefined, casas = 0): string | null {
  return v === null || v === undefined ? null : formatarNumero(v, casas);
}
