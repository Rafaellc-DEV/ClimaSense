import { quandoAs } from "@/features/evento/textos";
import { formatarNumero } from "@/lib/formatos";
import type { ItemSimulado } from "./tipos";

/** Evidência da previsão atual; nunca atribui a chuva do distrito a uma estação do bairro. */
export function EvidenciasImpacto({ item }: { item: ItemSimulado }) {
  const a = item.avaliacao;
  if (!a) return null;
  const mm = (v: number | null) => (v === null ? "Dados insuficientes" : `${formatarNumero(v, 1)} mm`);
  return (
    <div>
      <h4>Insumos da previsão atual</h4>
      <p>
        Chuva prevista em {a.horizonte_h} h: {mm(a.chuva_no_horizonte_mm)}. Fonte: {a.fonte_meteorologica}
        {a.emitido_em_fonte ? `, captura ${quandoAs(a.emitido_em_fonte)}` : ", sem captura disponível"}. O
        bairro herda a previsão do ponto representativo do distrito.
      </p>
      <p>
        Chuva medida em 72 h: {mm(a.chuva_observada_72h_mm)}. Fonte: APAC; {a.estacoes_validas} estações
        válidas{a.observada_em ? `, leitura ${quandoAs(a.observada_em)}` : ""}.
      </p>
      <p>
        Validade: {quandoAs(a.inicio_validade)} a {quandoAs(a.fim_validade)}. Método: {a.metodo}, versão{" "}
        {a.versao}.
      </p>
      {a.contexto_deslizamento && <p>{a.contexto_deslizamento}</p>}
      {a.suscetibilidade && (
        <p>
          Carta SGB:{" "}
          {a.suscetibilidade.alta > 0 ? "há área de alta suscetibilidade" : "consulte a cobertura da carta"}.
          Fonte: {a.fonte_territorial}. Suscetibilidade não é probabilidade de desastre.
        </p>
      )}
      {a.faltando.length > 0 && <p role="status">Dados insuficientes: {a.faltando.join(", ")}.</p>}
      {item.ml_alagamento && (
        <div>
          <h4>ML de alagamento — Experimental</h4>
          <p>
            Classe: {item.ml_alagamento.classe}. Confiança: {item.ml_alagamento.confianca ?? "baixa"}.
            Avaliação diária de hoje e amanhã, independente do horizonte das regras.
          </p>
          <ul>
            {item.ml_alagamento.fatores.map((f) => (
              <li key={f}>{f}</li>
            ))}
          </ul>
        </div>
      )}
      <details>
        <summary>Limitações da avaliação</summary>
        <ul>
          {a.limitacoes.map((l) => (
            <li key={l}>{l}</li>
          ))}
        </ul>
      </details>
    </div>
  );
}
