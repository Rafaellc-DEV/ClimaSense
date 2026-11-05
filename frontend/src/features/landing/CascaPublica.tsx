import type { ReactNode } from "react";
import { Phone } from "lucide-react";
import { Link, useLocation } from "react-router-dom";
import rios from "@/assets/tracos/rios.svg?raw";
import { Marca } from "@/design-system/componentes/Marca";
import { BarraEmergencia } from "./BarraEmergencia";
import { useRolarAoChegar } from "./navegacaoLanding";
import { Onda } from "./Onda";
import { DEFESA_CIVIL_RECIFE } from "./telefones";
import estilos from "./PaginaInicial.module.css";
import topo from "./CascaPublica.module.css";

export { TELEFONES } from "./telefones";

/**
 * Casca das páginas públicas: pular para o conteúdo, barra do topo (logo, telefone da Defesa Civil e acesso da
 * equipe), conteúdo, rodapé com as fontes e, no celular, a barra fixa de emergência. O espaço dela é reservado no fim da página
 * (padding-bottom e scroll-padding-bottom) para o foco nunca ficar escondido atrás dela.
 */
export function CascaPublica({
  children,
  aoAbrirAbrigos,
}: {
  children: ReactNode;
  /** Só na página inicial: o atalho “Abrigos” da barra de emergência troca de aba sem recarregar. */
  aoAbrirAbrigos?: () => void;
}) {
  const naHome = useLocation().pathname === "/";
  useRolarAoChegar(naHome);
  return (
    <div className={`${estilos.pagina} ${topo.casca}`}>
      <a href="#conteudo" className={estilos.pular}>
        Pular para o conteúdo
      </a>
      <header className={topo.topo}>
        <div className={topo.interno}>
          <Link to="/" aria-label="ClimaSense, página inicial" className={topo.logo}>
            <Marca decorativa />
          </Link>
          <div className={topo.acoes}>
            <a
              href={DEFESA_CIVIL_RECIFE.href}
              className={topo.ligar}
              aria-label={`Ligar para a Defesa Civil do Recife, ${DEFESA_CIVIL_RECIFE.texto}, 24 horas, grátis`}
            >
              <Phone aria-hidden="true" size={20} />
              <span>
                Ligar <b>{DEFESA_CIVIL_RECIFE.texto}</b>
              </span>
            </a>
            <Link to="/entrar" className={topo.entrar}>
              <span className={topo.entrarLongo}>Acesso da equipe</span>
              <span className={topo.entrarCurto}>Equipe</span>
            </Link>
          </div>
        </div>
      </header>
      <main id="conteudo" className={estilos.principal}>
        {children}
      </main>
      <footer className={estilos.rodape}>
        <Onda cor="var(--cs-mare)" alto />
        <div className={estilos.rodapeInterno}>
          <div className={estilos.rodapeMarca}>
            <Marca />
            <p>Antecipar riscos. Orientar decisões. Cuidar do território.</p>
          </div>
          <div>
            <h2 className={estilos.rodapeTitulo}>Importante</h2>
            <p>
              O ClimaSense <strong>não substitui</strong> os alertas oficiais da Defesa Civil. Em caso de
              dúvida, siga as orientações dela.
            </p>
            <p>Projeto acadêmico de Análise e Visualização de Dados da CESAR School, 2026.</p>
          </div>
          <div>
            <h2 className={estilos.rodapeTitulo}>Fontes e canais oficiais</h2>
            <ul aria-label="Fontes e canais oficiais">
              <li>
                <a href="https://www2.recife.pe.gov.br" target="_blank" rel="noopener noreferrer">
                  Prefeitura do Recife
                </a>
              </li>
              <li>
                <a href="https://www.apac.pe.gov.br" target="_blank" rel="noopener noreferrer">
                  APAC, agência estadual de águas e clima
                </a>
              </li>
              <li>
                <a href="https://dados.recife.pe.gov.br" target="_blank" rel="noopener noreferrer">
                  Dados Abertos do Recife
                </a>
              </li>
              <li>
                <Link to="/#sobre">De onde vêm os dados</Link>
              </li>
              <li>
                <Link to="/entrar">Acesso da equipe</Link>
              </li>
            </ul>
          </div>
          <div
            className={estilos.rodapeCidade}
            aria-hidden="true"
            dangerouslySetInnerHTML={{ __html: rios }}
          />
        </div>
      </footer>
      <BarraEmergencia aoAbrirAbrigos={aoAbrirAbrigos} />
    </div>
  );
}
