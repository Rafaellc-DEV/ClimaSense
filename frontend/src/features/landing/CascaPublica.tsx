import type { ReactNode } from "react";
import { Megaphone, Phone } from "lucide-react";
import { Link } from "react-router-dom";
import { Marca } from "@/design-system/componentes/Marca";
import rios from "@/assets/tracos/rios.svg?raw";
import { useEstado } from "./useEstado";
import estilos from "./PaginaInicial.module.css";

export const TELEFONES = [
  { numero: "199", nome: "Defesa Civil" },
  { numero: "193", nome: "Bombeiros" },
  { numero: "192", nome: "SAMU" },
];

/** Linha d’água: fecha o herói e abre o rodapé. A linha fina por cima é a maré que acabou de baixar. */
export function Onda({
  cor,
  linha = false,
  className,
}: {
  cor: string;
  linha?: boolean;
  className?: string;
}) {
  return (
    <svg
      className={[estilos.onda, className].filter(Boolean).join(" ")}
      viewBox="0 0 1440 120"
      preserveAspectRatio="none"
      aria-hidden="true"
      focusable="false"
    >
      {linha && (
        <path
          d="M0,50 C200,8 340,4 540,38 C720,70 880,84 1060,50 C1220,20 1340,20 1440,40"
          fill="none"
          stroke="rgba(255,255,255,0.75)"
          strokeWidth="2"
          vectorEffect="non-scaling-stroke"
        />
      )}
      <path
        d="M0,72 C180,32 330,22 520,60 C700,96 860,112 1040,74 C1200,42 1330,40 1440,62 L1440,121 L0,121 Z"
        fill={cor}
      />
    </svg>
  );
}

/** Telefones de emergência, clicáveis no celular (RF-01.6). */
export function FaixaEmergencia() {
  return (
    <section className={estilos.emergencia} aria-labelledby="emergencia">
      <h2 id="emergencia" className={estilos.etiqueta}>
        <Phone aria-hidden="true" size={18} /> Em emergência, ligue
      </h2>
      <ul className={estilos.circulos}>
        {TELEFONES.map((t) => (
          <li key={t.numero}>
            <a
              href={`tel:${t.numero}`}
              className={estilos.circulo}
              aria-label={`Ligar para ${t.nome === "SAMU" ? "o" : "a"} ${t.nome}, ${t.numero}`}
            >
              <span className={estilos.disco}>
                <span className={estilos.numero}>{t.numero}</span>
              </span>
              <span className={estilos.rotuloCirculo}>{t.nome}</span>
            </a>
          </li>
        ))}
      </ul>
    </section>
  );
}

/** Botão “Comunicados” do topo, com quantos estão em vigor agora. */
function BotaoComunicados({ inicio }: { inicio: boolean }) {
  const s = useEstado();
  const n = s.tipo === "ok" ? s.estado.avisos_ativos : 0;
  return (
    <a
      href={inicio ? "#comunicados" : "/#comunicados"}
      className={estilos.botaoComunicados}
      aria-label={n ? `Comunicados: ${n} em vigor` : "Comunicados"}
    >
      <Megaphone aria-hidden="true" size={20} />
      <span>Comunicados</span>
      {n > 0 && (
        <span className={estilos.contagem} aria-hidden="true">
          {n}
        </span>
      )}
    </a>
  );
}

export function CascaPublica({ children, inicio = false }: { children: ReactNode; inicio?: boolean }) {
  const ancora = (id: string) => (inicio ? `#${id}` : `/#${id}`);
  return (
    <div className={estilos.pagina}>
      <a href="#conteudo" className={estilos.pular}>
        Pular para o conteúdo
      </a>
      <header className={estilos.topo}>
        <div className={estilos.topoInterno}>
          <Link to="/" aria-label="ClimaSense, página inicial" className={estilos.logo}>
            <Marca decorativa />
          </Link>
          <nav aria-label="Seções" className={estilos.nav}>
            <a href={ancora("mapa")} className={estilos.linkNav}>
              Mapa
            </a>
            <a href={ancora("como-funciona")} className={estilos.linkNav}>
              Como funciona
            </a>
            <a href={ancora("sobre")} className={estilos.linkNav}>
              Sobre
            </a>
            <BotaoComunicados inicio={inicio} />
            <Link to="/entrar" className={estilos.entrar}>
              <span className={estilos.entrarLongo}>Acesso da equipe</span>
              <span className={estilos.entrarCurto}>Equipe</span>
            </Link>
          </nav>
        </div>
      </header>
      <main id="conteudo">{children}</main>
      <footer className={estilos.rodape}>
        <Onda cor="var(--cs-mare)" className={estilos.ondaRodape} />
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
            <h2 className={estilos.rodapeTitulo}>Canais oficiais</h2>
            <ul aria-label="Canais oficiais">
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
    </div>
  );
}
