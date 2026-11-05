import { Link } from "react-router-dom";
import { TriangleAlert } from "lucide-react";
import type { ChaveNivel } from "@/design-system/niveis";
import type { Esquemas } from "@/lib/api";
import { quandoRelativo } from "@/lib/formatos";
import type { Situacao } from "./useEstado";
import estilos from "./AvisoAtivo.module.css";

/** Como o nível entra na frase: “Alerta para 2 bairros até amanhã, 18h.” */
const ABERTURA: Record<string, string> = {
  informativo: "Aviso preventivo",
  atencao: "Atenção",
  alerta: "Alerta",
  critico: "Situação crítica",
};

function onde(t: Esquemas["TerritorioRef"][]): string {
  if (t.some((x) => x.tipo === "municipio")) return "todo o Recife";
  if (t.length === 1) return t[0].tipo === "distrito" ? `o ${t[0].nome_exibicao}` : t[0].nome_exibicao;
  const bairros = t.filter((x) => x.tipo === "bairro").length;
  const distritos = t.length - bairros;
  return [
    bairros && `${bairros} bairro${bairros > 1 ? "s" : ""}`,
    distritos && `${distritos} distrito${distritos > 1 ? "s" : ""}`,
  ]
    .filter(Boolean)
    .join(" e ");
}

/**
 * Banner fino no topo do herói, SÓ quando há aviso ativo publicado (padrão “notification banner”): a informação não
 * fica abaixo da dobra. Sem aviso, carregando ou com falha ele não existe; a honestidade da resposta “sem aviso”
 * mora na aba Comunicados e no resultado da busca. É a única região aria-live desta parte da página.
 * Para retirar a funcionalidade: apague este componente (e o CSS) e o uso dele em PaginaInicial.
 */
export function AvisoAtivo({
  situacao,
  aoVerComunicados,
}: {
  situacao: Situacao;
  aoVerComunicados: () => void;
}) {
  const principal = situacao.tipo === "ok" ? situacao.estado.principal : null;
  const n = situacao.tipo === "ok" ? situacao.estado.avisos_ativos : 0;
  const nivel = principal?.nivel as ChaveNivel | undefined;
  return (
    <div role="status" className={estilos.regiao}>
      {principal && nivel && (
        <div className={estilos.aviso} data-nivel={nivel}>
          <TriangleAlert aria-hidden="true" size={20} className={estilos.icone} />
          <div className={estilos.corpo}>
            <p className={estilos.texto}>
              {ABERTURA[nivel]} para {onde(principal.territorios)} até{" "}
              {quandoRelativo(principal.validade_fim)}.
              {n > 1 && ` E mais ${n - 1 === 1 ? "1 aviso" : `${n - 1} avisos`} em vigor.`}
            </p>
            <p className={estilos.links}>
              <Link to={`/avisos/${principal.id}`}>Ler o comunicado completo</Link>
              <button type="button" onClick={aoVerComunicados}>
                Ver comunicados
              </button>
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
