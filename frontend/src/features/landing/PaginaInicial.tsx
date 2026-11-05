import { useCallback, useEffect, useRef, useState } from "react";
import { MessageCircle, Phone } from "lucide-react";
import { AbasLanding, type AbaLanding } from "./AbasLanding";
import { CascaPublica } from "./CascaPublica";
import { AvisoAtivo } from "./AvisoAtivo";
import { HeroiBusca } from "./HeroiBusca";
import { Recolhivel } from "./Recolhivel";
import { ResultadoBusca } from "./ResultadoBusca";
import { SecaoSobre } from "./SecaoSobre";
import { useRevelar } from "./efeitos";
import { DEFESA_CIVIL_RECIFE, WHATSAPP_DEFESA_CIVIL } from "./telefones";
import { useAbrigos } from "./useAbrigos";
import { useBusca } from "./useBusca";
import { useAvisos, useEstado } from "./useEstado";
import estilos from "./PaginaInicial.module.css";

/** Âncoras antigas e da barra de emergência que abrem uma aba. */
const HASH_ABA: Record<string, AbaLanding> = {
  "#comunicados": "comunicados",
  "#avisos": "comunicados",
  "#abrigos": "abrigos",
  "#mapa": "mapa",
};

/**
 * Landing pública. De cima para baixo: o banner de aviso ativo (só se houver), a pergunta com o campo de busca, o resultado
 * no mesmo lugar, as abas Comunicados | Abrigos | Mapa, como receber alertas e, recolhido, como funciona e quem
 * somos. A busca é uma só para a página inteira.
 */
export function PaginaInicial() {
  const situacao = useEstado();
  const avisos = useAvisos();
  const abrigos = useAbrigos();
  const busca = useBusca();
  const [aba, setAba] = useState<AbaLanding>(() => HASH_ABA[location.hash] ?? "comunicados");
  const alertas = useRef<HTMLElement>(null);
  useRevelar(alertas);
  const niveis = situacao.tipo === "ok" ? situacao.estado.niveis_por_distrito : null;

  useEffect(() => {
    document.title = "ClimaSense: avisos de chuva e alagamento no Recife";
  }, []);

  const irParaAba = useCallback((a: AbaLanding) => {
    setAba(a);
    // espera a aba abrir para levar a tela até ela
    requestAnimationFrame(
      () =>
        document.getElementById("avisos-e-abrigos")?.scrollIntoView?.({
          block: "start",
          behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth",
        }),
    );
  }, []);

  useEffect(() => {
    const aoMudarHash = () => {
      const a = HASH_ABA[location.hash];
      if (a) irParaAba(a);
    };
    window.addEventListener("hashchange", aoMudarHash);
    return () => window.removeEventListener("hashchange", aoMudarHash);
  }, [irParaAba]);

  return (
    <CascaPublica aoAbrirAbrigos={() => irParaAba("abrigos")}>
      <HeroiBusca
        busca={busca}
        resultado={<ResultadoBusca busca={busca} abrigos={abrigos} irParaAba={irParaAba} />}
        aviso={<AvisoAtivo situacao={situacao} aoVerComunicados={() => irParaAba("comunicados")} />}
      />

      <AbasLanding
        aba={aba}
        aoMudar={setAba}
        avisos={avisos}
        niveis={niveis}
        abrigos={abrigos}
        busca={busca}
      />

      <section ref={alertas} className={estilos.alertas} aria-labelledby="alertas-h">
        <div className={estilos.alertasInterno}>
          <h2 id="alertas-h">Receber alertas</h2>
          <p>
            Fale com a Defesa Civil do Recife pelo WhatsApp ou por telefone. A ligação é grátis e atendem 24
            horas.
          </p>
          <ul className={estilos.canais}>
            <li>
              <a href={WHATSAPP_DEFESA_CIVIL} target="_blank" rel="noopener noreferrer">
                <span className={estilos.disco}>
                  <MessageCircle aria-hidden="true" size={20} />
                </span>
                WhatsApp da Defesa Civil do Recife
                <span className="so-leitor"> (abre em nova aba)</span>
              </a>
            </li>
            <li>
              <a
                href={DEFESA_CIVIL_RECIFE.href}
                aria-label={`Ligar para a Defesa Civil do Recife, ${DEFESA_CIVIL_RECIFE.texto}`}
              >
                <span className={estilos.disco}>
                  <Phone aria-hidden="true" size={20} />
                </span>
                Ligar {DEFESA_CIVIL_RECIFE.texto}
              </a>
            </li>
          </ul>
        </div>
      </section>

      <div className={estilos.explicacoes}>
        <Recolhivel id="como-funciona" titulo="Como um aviso chega até você">
          <ol className={estilos.passos}>
            <li>
              <h3>Dados de chuva, maré e território</h3>
              <p>A chuva prevista, o nível do mar e o mapa oficial dos distritos vêm de fontes públicas.</p>
            </li>
            <li>
              <h3>A equipe avalia</h3>
              <p>A Vigilância em Saúde analisa os territórios e escreve o aviso em linguagem simples.</p>
            </li>
            <li>
              <h3>Outra pessoa revisa e publica</h3>
              <p>Só avisos revisados aparecem aqui, sempre com a validade.</p>
            </li>
          </ol>
        </Recolhivel>

        <Recolhivel id="sobre" titulo="Quem somos e de onde vêm os dados">
          <SecaoSobre />
        </Recolhivel>
      </div>
    </CascaPublica>
  );
}
