/**
 * Painel do bairro escolhido no mapa antes de o estágio dele chegar (a rota de estágios é lenta). O resumo de população
 * e equipamentos tem a própria consulta e aparece assim que chegar; o estágio fica como "Carregando…" ou, se a fonte
 * falhou, "Dados insuficientes" (RN-01).
 */
import { nomeDoDistrito } from "@/map/paleta";
import { useEffect, useRef } from "react";
import { ChevronLeft, X } from "lucide-react";
import { ResumoBairro } from "./ResumoBairro";
import estilos from "./Mapa.module.css";

export function PainelBairroPendente({
  id,
  nome,
  distritoId,
  carregando,
  aoVoltarDistrito,
  aoFechar,
}: {
  id: string;
  nome: string;
  distritoId: string | null;
  carregando: boolean;
  aoVoltarDistrito?: () => void;
  aoFechar: () => void;
}) {
  const titulo = useRef<HTMLHeadingElement>(null);
  useEffect(() => titulo.current?.focus({ preventScroll: true }), [id]);
  return (
    <aside className={estilos.painel} aria-labelledby="painel-nome">
      <header className={estilos.painelTopo}>
        <div>
          {distritoId && aoVoltarDistrito && (
            <button type="button" className={estilos.voltarNivel} onClick={aoVoltarDistrito}>
              <ChevronLeft aria-hidden="true" size={18} />
              {nomeDoDistrito(distritoId)}
            </button>
          )}
          <h2 id="painel-nome" ref={titulo} tabIndex={-1}>
            {nome}
          </h2>
          <p className={estilos.painelDistrito}>
            {distritoId ? nomeDoDistrito(distritoId) : "Distrito não informado"}
          </p>
        </div>
        <button type="button" className={estilos.fechar} onClick={aoFechar} aria-label="Fechar o painel">
          <X aria-hidden="true" size={24} />
        </button>
      </header>
      <section className={estilos.bloco} aria-labelledby="painel-estagio">
        <h3 id="painel-estagio">Estágio</h3>
        {carregando ? (
          <p className={estilos.apagado} role="status">
            Carregando o estágio…
          </p>
        ) : (
          <p>
            <b>Dados insuficientes:</b> falta a fonte dos estágios (previsão de chuva e de maré). Isso não
            quer dizer risco baixo.
          </p>
        )}
      </section>
      <ResumoBairro territorioId={id} />
    </aside>
  );
}
