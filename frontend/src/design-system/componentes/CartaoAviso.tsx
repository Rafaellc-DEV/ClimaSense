import type { CSSProperties } from "react";
import { Link } from "react-router-dom";
import { NIVEIS, type ChaveNivel } from "../niveis";
import { quandoRelativo } from "@/lib/formatos";
import { SeloNivel } from "./SeloNivel";
import estilos from "./CartaoAviso.module.css";

export interface DadosAviso {
  id: string;
  titulo: string;
  nivel: string;
  territorios: { id: string; nome_exibicao: string }[];
  texto: string;
  orientacoes: string[];
  validade_inicio: string;
  validade_fim: string;
  emitido_por: string;
  publicado_em?: string | null;
}

/**
 * O cartão de aviso da população. É O MESMO componente na landing e na prévia do editor de comunicados
 * (RF-11.3): o que a equipe revisa é exatamente o que a população vê.
 *
 * Ordem do conteúdo (referência: NWS Hazard Simplification): o quê → onde → o que fazer → até quando e quem.
 * Texto sempre puro: o React escapa tudo, e quebras de linha viram parágrafos (RNF-SEG-04).
 */
export function CartaoAviso({
  aviso,
  agora,
  ligarDetalhe = false,
  previa = false,
  nivelTitulo = 3,
}: {
  aviso: DadosAviso;
  agora?: Date;
  ligarDetalhe?: boolean;
  previa?: boolean;
  nivelTitulo?: 2 | 3;
}) {
  const nivel = (aviso.nivel in NIVEIS ? aviso.nivel : "informativo") as ChaveNivel;
  const Titulo = `h${nivelTitulo}` as const;
  const onde = aviso.territorios.map((t) => t.nome_exibicao);
  const ref = agora ?? new Date();
  return (
    <article
      className={estilos.cartao}
      style={{ "--cor-nivel": NIVEIS[nivel].cor } as CSSProperties}
      data-nivel={nivel}
      aria-label={previa ? "Prévia do aviso" : undefined}
    >
      <SeloNivel nivel={nivel} />
      <Titulo className={estilos.titulo}>
        {ligarDetalhe ? (
          <Link to={`/avisos/${aviso.id}`}>{aviso.titulo || "Sem título"}</Link>
        ) : (
          aviso.titulo || "Sem título"
        )}
      </Titulo>
      <p className={estilos.onde}>
        <span className={estilos.rotulo}>Onde:</span>{" "}
        {onde.length ? onde.join(", ") : "território não escolhido"}
      </p>
      {aviso.texto
        .split(/\n+/)
        .filter((p) => p.trim())
        .map((p, i) => (
          <p key={i} className={estilos.texto}>
            {p}
          </p>
        ))}
      {aviso.orientacoes.length > 0 && (
        <div className={estilos.fazer}>
          <h4>O que fazer</h4>
          <ul>
            {aviso.orientacoes.map((o, i) => (
              <li key={i}>{o}</li>
            ))}
          </ul>
        </div>
      )}
      <p className={estilos.validade}>
        Vale até {quandoRelativo(aviso.validade_fim, ref)}. Emitido pela{" "}
        {aviso.emitido_por.replace(/^A /, "")}
        {aviso.publicado_em ? `, ${quandoRelativo(aviso.publicado_em, ref)}` : ""}.
      </p>
    </article>
  );
}
