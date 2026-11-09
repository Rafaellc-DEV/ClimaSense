import { useId } from "react";
import { useTerritorios } from "@/app/FiltroFrase";
import campo from "@/design-system/componentes/Campo.module.css";
import { nomeDistrito } from "@/lib/distritos";

export type NivelTerritorio = "municipio" | "distrito" | "bairro";

/**
 * Escolha de território num `<select>` nativo (rápido no celular). Os distritos aparecem como "Distrito 5" e os
 * bairros vêm agrupados pelo distrito, em ordem alfabética.
 */
export function SeletorTerritorio({
  rotulo,
  valor,
  aoMudar,
  niveis,
  vazio,
  erro,
  obrigatorio,
  rotuloOculto,
}: {
  rotulo: string;
  valor: string;
  aoMudar: (id: string) => void;
  niveis: NivelTerritorio[];
  /** Texto da opção vazia. */
  vazio: string;
  erro?: string;
  obrigatorio?: boolean;
  rotuloOculto?: boolean;
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
  const soBairros = niveis.includes("bairro");
  const soltos = lista.filter((t) => t.tipo === "bairro" && !distritos.some((d) => d.id === t.pai_id));
  return (
    <div className={campo.campo}>
      <label htmlFor={id} className={rotuloOculto ? "so-leitor" : campo.rotulo}>
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
        <option value="">{r.isPending ? "Carregando…" : vazio}</option>
        {niveis.includes("municipio") && lista.some((t) => t.id === "recife") && (
          <option value="recife">Recife — todos os distritos</option>
        )}
        {distritos.map((d) =>
          soBairros ? (
            <optgroup key={d.id} label={nomeDistrito(d.nome_exibicao)}>
              {niveis.includes("distrito") && (
                <option value={d.id}>{nomeDistrito(d.nome_exibicao)} (inteiro)</option>
              )}
              {bairrosDe(d.id).map((b) => (
                <option key={b.id} value={b.id}>
                  {b.nome_exibicao}
                </option>
              ))}
            </optgroup>
          ) : niveis.includes("distrito") ? (
            <option key={d.id} value={d.id}>
              {nomeDistrito(d.nome_exibicao)}
            </option>
          ) : null,
        )}
        {soBairros &&
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
