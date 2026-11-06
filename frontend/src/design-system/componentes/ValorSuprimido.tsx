import estilos from "./ValorSuprimido.module.css";

export const TEXTO_SUPRESSAO = "Valor pequeno omitido para proteger a privacidade";

/**
 * Contagem pequena que a API omite (RNF-03): aparece como “< 5”, com a explicação ao passar o mouse, focar ou ler. Nunca
 * zero, nunca vazio. Barras e gráficos não desenham este valor.
 */
export function ValorSuprimido({ minimo = 5 }: { minimo?: number }) {
  return (
    <span className={estilos.valor} title={TEXTO_SUPRESSAO} tabIndex={0} data-suprimido="true">
      <span aria-hidden="true">&lt; {minimo}</span>
      <span className="so-leitor">
        menos de {minimo} casos. {TEXTO_SUPRESSAO}.
      </span>
    </span>
  );
}
