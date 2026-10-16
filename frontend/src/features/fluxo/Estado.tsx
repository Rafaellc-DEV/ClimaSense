import { ESTADOS, ESTADOS_AVALIACAO } from "@/textos/glossario";
import estilos from "./Fluxo.module.css";

/** Estado do fluxo sempre em texto, com marcador (cor nunca sozinha, RN-17). */
export function SeloEstado({ estado, avaliacao }: { estado: string; avaliacao?: boolean }) {
  return (
    <span className={estilos.estado} data-estado={estado}>
      {(avaliacao ? ESTADOS_AVALIACAO : ESTADOS)[estado] ?? estado}
    </span>
  );
}

/** Abas por estado com contagem (filtro da lista). */
export function AbasEstado({
  estados,
  contagens,
  atual,
  aoMudar,
  rotulos,
}: {
  estados: string[];
  contagens: Record<string, number>;
  atual: string;
  aoMudar: (e: string) => void;
  rotulos: Record<string, string>;
}) {
  const total = Object.values(contagens).reduce((s, n) => s + n, 0);
  return (
    <div className={estilos.abas} role="group" aria-label="Filtrar por estado">
      {["todos", ...estados].map((e) => (
        <button
          key={e}
          type="button"
          className={estilos.aba}
          aria-pressed={atual === e}
          onClick={() => aoMudar(e)}
        >
          {e === "todos" ? "Todos" : rotulos[e]}
          <span aria-label={`${e === "todos" ? total : contagens[e] ?? 0} itens`}>
            {e === "todos" ? total : contagens[e] ?? 0}
          </span>
        </button>
      ))}
    </div>
  );
}
