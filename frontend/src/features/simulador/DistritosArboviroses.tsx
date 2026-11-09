import { LegendaFonte, type FonteDado } from "@/design-system/componentes/EstadoDados";
import { ValorSuprimido } from "@/design-system/componentes/ValorSuprimido";
import { diaMes } from "@/features/evento/textos";
import { formatarNumero } from "@/lib/formatos";
import type { AgravoDistrito, ArbovirosesDistrito, ClasseArbovirose, ResumoArboviroses } from "./tipos";
import estilos from "./Simulador.module.css";

const ROTULO_CLASSE_ARBO: Record<ClasseArbovirose, string> = { baixa: "baixa", media: "média", alta: "alta" };
const NOME_AGRAVO: Record<string, string> = { dengue: "Dengue", chikungunya: "Chikungunya", zika: "Zika" };
export const nomeAgravo = (a: string) => NOME_AGRAVO[a.toLowerCase()] ?? a;

/**
 * Arboviroses em uma linha, como na tabela: "Dengue alta · Chikungunya média · Zika: dados insuficientes".
 * Sem classe é falta de dado, nunca "baixa". Contexto, não previsão causal (RN-06, RN-11).
 */
export function textoArboviroses(a: ArbovirosesDistrito | null | undefined): string {
  if (!a || a.agravos.length === 0) return "Dados insuficientes";
  return a.agravos
    .map((g) =>
      g.classe_impacto && !g.dados_insuficientes
        ? `${g.nome} ${ROTULO_CLASSE_ARBO[g.classe_impacto]}`
        : `${g.nome}: dados insuficientes`,
    )
    .join(" · ");
}

/** Casos: suprimido vira "< 5", sem dado vira "dados insuficientes", nunca zero inventado. */
function Casos({ casos, suprimido }: { casos: number | null; suprimido: boolean }) {
  if (suprimido) return <ValorSuprimido />;
  if (casos === null) return <>dados insuficientes</>;
  return <>{formatarNumero(casos)}</>;
}

function Agravo({ a }: { a: AgravoDistrito }) {
  const s = a.semana_recente;
  if (a.dados_insuficientes)
    return (
      <li className={estilos.agravo}>
        <b>{a.nome}</b>
        <span>
          <b>Dados insuficientes.</b>{" "}
          {(a.motivo ?? "Falta a fonte de casos.").replace(/^Dados insuficientes:?\s*/i, "")}
        </span>
      </li>
    );
  return (
    <li className={estilos.agravo}>
      <b>{a.nome}</b>
      <span>
        Casos no ano{a.ano_distrito ? ` (${a.ano_distrito})` : ""}, neste distrito:{" "}
        <Casos casos={a.casos_ano_distrito} suprimido={a.casos_ano_suprimido} />.
      </span>
      <span>
        {s ? (
          <>
            Semana {s.semana} (a partir de {diaMes(s.inicio)}), no Recife inteiro:{" "}
            <Casos casos={s.casos} suprimido={s.suprimido} />
            {s.incompleta ? " (semana incompleta)" : ""}.
          </>
        ) : (
          "Sem semana recente com dado."
        )}
      </span>
    </li>
  );
}

export function ListaAgravos({ arboviroses }: { arboviroses: ArbovirosesDistrito | null | undefined }) {
  const agravos = arboviroses?.agravos ?? [];
  if (agravos.length === 0)
    return (
      <p className={estilos.apoio}>
        <b>Dados insuficientes:</b> o cálculo não trouxe as arboviroses deste distrito.
      </p>
    );
  return (
    <ul className={estilos.agravos}>
      {agravos.map((a) => (
        <Agravo key={a.agravo} a={a} />
      ))}
    </ul>
  );
}

/** Aviso curto de que arboviroses são contexto, mais a fonte e a hora de cada fonte (RF-19). */
export function NotaArboviroses({ resumo }: { resumo: ResumoArboviroses | null | undefined }) {
  const fontes: FonteDado[] = (resumo?.fontes ?? []).map((f) => ({
    nome: f.nome,
    atualizadoEm: f.atualizado_em,
  }));
  return (
    <div className={estilos.notaArbo}>
      <p>
        {resumo?.aviso ??
          "Arboviroses são contexto, não previsão causal da chuva. Casos da semana são do Recife inteiro; casos do ano são por distrito."}
      </p>
      {resumo && fontes.length === 0 ? (
        <p>
          <b>Dados insuficientes:</b> falta a fonte de casos de dengue, chikungunya e zika.
        </p>
      ) : (
        <LegendaFonte fontes={fontes} />
      )}
    </div>
  );
}
