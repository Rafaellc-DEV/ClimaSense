import type { ReactNode } from "react";
import { Megaphone, Phone } from "lucide-react";
import { Link } from "react-router-dom";
import { useEstado } from "./useEstado";
import estilos from "./PaginaInicial.module.css";

export const TELEFONES = [
  { numero: "199", nome: "Defesa Civil" },
  { numero: "193", nome: "Bombeiros" },
  { numero: "192", nome: "SAMU" },
];

/** Telefones de emergência, clicáveis no celular (RF-01.6). */
export function FaixaEmergencia() {
  return (
    <section className={estilos.emergencia} aria-labelledby="emergencia">
      <div className={estilos.emergenciaInterna}>
        <h2 id="emergencia">
          <Phone aria-hidden="true" size={22} /> Em emergência, ligue
        </h2>
        <ul>
          {TELEFONES.map((t) => (
            <li key={t.numero}>
              <a href={`tel:${t.numero}`}>
                <span className={estilos.numero}>{t.numero}</span>
                <span>{t.nome}</span>
              </a>
            </li>
          ))}
        </ul>
      </div>
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
          <Link to="/" aria-label="ClimaSense, página inicial">
            <img
              src="/brand/logo.png"
              srcSet="/brand/logo@2x.png 2x"
              alt="ClimaSense"
              className={estilos.logo}
              width={188}
              height={47}
            />
          </Link>
          <nav aria-label="Seções" className={estilos.nav}>
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
        <div className={estilos.rodapeInterno}>
          <img
            src="/brand/logo-negativo.png"
            srcSet="/brand/logo-negativo@2x.png 2x"
            alt="ClimaSense"
            width={160}
            height={40}
          />
          <div>
            <p>
              O ClimaSense <strong>não substitui</strong> os alertas oficiais da Defesa Civil. Em caso de
              dúvida, siga as orientações dela.
            </p>
            <p>Projeto acadêmico de Análise e Visualização de Dados da CESAR School, 2026.</p>
          </div>
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
      </footer>
    </div>
  );
}
