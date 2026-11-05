import { useState } from "react";
import { BellOff } from "lucide-react";
import { CartaoAviso } from "@/design-system/componentes/CartaoAviso";
import type { useAvisos } from "./useEstado";
import estilos from "./AbasLanding.module.css";

const VISIVEIS = 3;

/** Lista vertical dos comunicados em vigor: 3 à vista e “Ver todos” para o resto. Nada de trilho horizontal. */
export function AbaComunicados({ avisos }: { avisos: ReturnType<typeof useAvisos> }) {
  const [todos, setTodos] = useState(false);
  const lista = avisos.data ?? [];
  const mostrados = todos ? lista : lista.slice(0, VISIVEIS);
  return (
    <div className={estilos.painel}>
      <p className={estilos.lead}>
        Publicados pela Vigilância em Saúde do Recife, com o que fazer e até quando valem. Cada comunicado sai
        daqui sozinho quando vence.
      </p>
      {avisos.isPending && <p className={estilos.lead}>Carregando os comunicados…</p>}
      {avisos.isError && (
        <div className={estilos.vazio} role="alert">
          <div>
            <p className={estilos.vazioTitulo}>Não foi possível verificar os avisos agora.</p>
            <p>Isso não quer dizer que não há risco. Em emergência, ligue 199.</p>
            <button type="button" className={estilos.mais} onClick={() => void avisos.refetch()}>
              Tentar de novo
            </button>
          </div>
        </div>
      )}
      {avisos.data &&
        !avisos.isError &&
        (lista.length ? (
          <>
            <ul id="avisos" className={estilos.comunicados} aria-label="Comunicados em vigor">
              {mostrados.map((a) => (
                <li key={a.id}>
                  <CartaoAviso aviso={a} ligarDetalhe />
                </li>
              ))}
            </ul>
            {lista.length > VISIVEIS && (
              <button
                type="button"
                className={estilos.mais}
                onClick={() => setTodos((t) => !t)}
                aria-expanded={todos}
              >
                {todos ? "Mostrar menos" : `Ver todos os ${lista.length} comunicados`}
              </button>
            )}
          </>
        ) : (
          <div className={estilos.vazio}>
            <BellOff aria-hidden="true" size={32} />
            <div>
              <p className={estilos.vazioTitulo}>Nenhum comunicado em vigor agora.</p>
              <p>
                Quando a equipe publicar um, ele aparece aqui com o que fazer e até quando vale. Isso não
                significa ausência de risco. Em chuva forte, evite áreas que alagam e acompanhe a Defesa
                Civil.
              </p>
            </div>
          </div>
        ))}
    </div>
  );
}
