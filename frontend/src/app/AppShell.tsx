import { useEffect, useState, type ReactNode } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import {
  ChartColumn,
  ClipboardList,
  Database,
  FlaskConical,
  HeartPulse,
  LogOut,
  Map as MapIcon,
  Menu,
  PanelLeftClose,
  PanelLeftOpen,
  Settings,
  Siren,
  X,
} from "lucide-react";
import { Link, Navigate, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { Marca } from "@/design-system/componentes/Marca";
import rios from "@/assets/tracos/rios.svg?raw";
import { enderecoInicial } from "@/lib/funcionalidades";
import { useSessao } from "@/lib/sessao";
import { PAPEIS } from "@/textos/glossario";
import { AMBIENTE_DEMO } from "./ambiente";
import { AvisoSessao } from "./AvisoSessao";
import estilos from "./AppShell.module.css";

/** O cabeçalho das telas mora no design system; este re-export mantém os imports antigos funcionando. */
export { CabecalhoTela } from "@/design-system/componentes/CabecalhoTela";

interface ItemMenu {
  para: string;
  rotulo: string;
  icone: ReactNode;
  permissao?: string;
  fim?: boolean;
}

/**
 * As telas da equipe, na ordem do dia a dia: o mapa, os dashboards (P-61, aprovado pelo dono em 26/11/2026), a situação do evento, a saúde, as ações e o simulador.
 * Fontes e Administração ficam no rodapé. Chuva, Registro e Boletim viraram parte destas telas (rotas
 * antigas redirecionam, ver App.tsx).
 */
const PRINCIPAIS: ItemMenu[] = [
  { para: "/app", rotulo: "Mapa", icone: <MapIcon />, fim: true },
  { para: "/app/dashboards", rotulo: "Dashboards", icone: <ChartColumn /> },
  { para: "/app/situacao", rotulo: "Situação do evento", icone: <Siren /> },
  { para: "/app/saude", rotulo: "Saúde", icone: <HeartPulse /> },
  { para: "/app/acoes", rotulo: "Ações", icone: <ClipboardList /> },
  { para: "/app/simulador", rotulo: "Simulador", icone: <FlaskConical /> },
];
const RODAPE: ItemMenu[] = [
  { para: "/app/fontes", rotulo: "Fontes", icone: <Database /> },
  { para: "/app/admin", rotulo: "Administração", icone: <Settings />, permissao: "administrar" },
];

function Navegacao({
  aoEscolher,
  recolhido = false,
  aoAlternarMenu,
}: {
  aoEscolher?: () => void;
  recolhido?: boolean;
  /** Só no menu fixo do computador: o item "Recolher menu" logo abaixo de Fontes. */
  aoAlternarMenu?: () => void;
}) {
  const { pode } = useSessao();
  const lista = (itens: ItemMenu[], classe?: string) => (
    <ul className={[estilos.grupo, classe].filter(Boolean).join(" ")}>
      {itens
        .filter((i) => !i.permissao || pode(i.permissao))
        .map((i) => (
          <li key={i.para}>
            <NavLink to={i.para} end={i.fim} onClick={aoEscolher} title={recolhido ? i.rotulo : undefined}>
              <span className={estilos.icone} aria-hidden="true">
                {i.icone}
              </span>
              <span className={estilos.rotuloItem}>{i.rotulo}</span>
            </NavLink>
          </li>
        ))}
    </ul>
  );

  return (
    <nav aria-label="Menu principal" className={estilos.nav}>
      <div className={estilos.bloco}>{lista(PRINCIPAIS)}</div>
      <div className={`${estilos.bloco} ${estilos.blocoRodape}`}>
        {lista(RODAPE, estilos.grupoRodape)}
        {aoAlternarMenu && (
          <ul className={[estilos.grupo, estilos.grupoRodape].join(" ")}>
            <li>
              <button
                type="button"
                className={estilos.itemMenu}
                onClick={aoAlternarMenu}
                aria-expanded={!recolhido}
                aria-label={recolhido ? "Expandir menu" : "Recolher menu"}
                title={recolhido ? "Expandir menu" : undefined}
              >
                <span className={estilos.icone} aria-hidden="true">
                  {recolhido ? <PanelLeftOpen /> : <PanelLeftClose />}
                </span>
                <span className={estilos.rotuloItem}>Recolher menu</span>
              </button>
            </li>
          </ul>
        )}
      </div>
    </nav>
  );
}

function Logo() {
  return (
    <Link to="/app" className={estilos.marca} aria-label="ClimaSense, painel inicial">
      <Marca decorativa />
    </Link>
  );
}

/** Conteúdo do menu lateral e da gaveta: logo branca, navegação, pessoa e saída. */
function ConteudoLateral({
  aoEscolher,
  aoSair,
  recolhido = false,
  aoAlternarMenu,
}: {
  aoEscolher?: () => void;
  aoSair: () => void;
  recolhido?: boolean;
  aoAlternarMenu?: () => void;
}) {
  const { usuario } = useSessao();
  if (!usuario) return null;
  const papeis = usuario.papeis.map((p) => PAPEIS[p] ?? p).join(", ");
  return (
    <>
      <Navegacao aoEscolher={aoEscolher} recolhido={recolhido} aoAlternarMenu={aoAlternarMenu} />
      <div className={estilos.conta}>
        <Link
          to="/app/conta"
          className={estilos.pessoa}
          onClick={aoEscolher}
          title={recolhido ? `${usuario.nome}, minha conta` : undefined}
        >
          <span className={estilos.avatar} aria-hidden="true">
            {usuario.nome.trim().charAt(0).toUpperCase()}
          </span>
          <span className={estilos.pessoaTextos}>
            <span className={estilos.nome}>{usuario.nome}</span>
            <span className={estilos.papeis}>{papeis}</span>
          </span>
        </Link>
        <button
          type="button"
          className={estilos.sair}
          onClick={aoSair}
          title={recolhido ? "Sair" : undefined}
        >
          <LogOut aria-hidden="true" size={20} /> <span className={estilos.sairTexto}>Sair</span>
        </button>
      </div>
      <div className={estilos.rios} aria-hidden="true" dangerouslySetInnerHTML={{ __html: rios }} />
    </>
  );
}

const CHAVE_MENU = "climasense.menu-recolhido";

/** Lembra se o menu ficou recolhido. Navegador sem armazenamento (modo privado) só não lembra. */
function lerRecolhido(): boolean {
  try {
    return window.localStorage.getItem(CHAVE_MENU) === "1";
  } catch {
    return false;
  }
}

/** Área da equipe: menu lateral azul profundo (fixo nos dois temas) e, abaixo de 1024 px, uma gaveta. */
export function AppShell() {
  const { usuario, sair, garantir } = useSessao();
  const navegar = useNavigate();
  const local = useLocation();
  const [gaveta, setGaveta] = useState(false);
  const [recolhido, setRecolhido] = useState(lerRecolhido);
  const alternarMenu = () =>
    setRecolhido((v) => {
      try {
        window.localStorage.setItem(CHAVE_MENU, v ? "0" : "1");
      } catch {
        /* sem armazenamento: vale só nesta visita */
      }
      return !v;
    });
  useEffect(garantir, [garantir]);
  useEffect(() => setGaveta(false), [local.pathname]);
  // botões em pílula só na gestão (ver --r-botao em tokens.css)
  useEffect(() => {
    document.documentElement.dataset.area = "gestao";
    return () => {
      delete document.documentElement.dataset.area;
    };
  }, []);

  if (usuario === undefined) return <p className={estilos.verificando}>Verificando a sua sessão…</p>;
  if (!usuario || usuario.troca_senha_obrigatoria)
    return <Navigate to="/entrar" replace state={{ voltarPara: local.pathname + local.search }} />;

  const comDemo = AMBIENTE_DEMO || usuario.ambiente === "demonstracao";
  const sairDaConta = async () => {
    await sair();
    navegar(enderecoInicial());
  };

  return (
    <div className={estilos.casca}>
      <a href="#conteudo" className={estilos.pular}>
        Pular para o conteúdo
      </a>
      <div className={estilos.grade} data-recolhido={recolhido}>
        <aside className={estilos.lateral} aria-label="Navegação" data-recolhido={recolhido}>
          <Logo />
          <ConteudoLateral aoSair={sairDaConta} recolhido={recolhido} aoAlternarMenu={alternarMenu} />
        </aside>
        <div className={estilos.coluna}>
          {/* Sem o nome da seção: o <h1> da página já o traz. No computador o topo só existe quando tem filtro ou aviso;
              no celular ele guarda o menu e a logo. */}
          <header className={estilos.topo} data-vazio={!comDemo}>
            <div className={estilos.topoInterno}>
              <Dialog.Root open={gaveta} onOpenChange={setGaveta}>
                <Dialog.Trigger className={estilos.botaoMenu} aria-label="Menu">
                  <Menu aria-hidden="true" size={24} />
                </Dialog.Trigger>
                <Dialog.Portal>
                  <Dialog.Overlay className={estilos.veu} />
                  <Dialog.Content className={estilos.gaveta} aria-describedby={undefined}>
                    <Dialog.Title className="so-leitor">Menu</Dialog.Title>
                    <div className={estilos.gavetaTopo}>
                      <Logo />
                      <Dialog.Close className={estilos.fecharGaveta} aria-label="Fechar o menu">
                        <X aria-hidden="true" size={24} />
                      </Dialog.Close>
                    </div>
                    <ConteudoLateral aoEscolher={() => setGaveta(false)} aoSair={sairDaConta} />
                  </Dialog.Content>
                </Dialog.Portal>
              </Dialog.Root>
              <span className={estilos.marcaTopo}>
                <Logo />
              </span>
              {comDemo && <span className={estilos.demo}>Ambiente de demonstração</span>}
            </div>
          </header>
          <main
            id="conteudo"
            className={estilos.conteudo}
            tabIndex={-1}
            data-tela={local.pathname === "/app/dashboards" ? "painel" : undefined}
          >
            <Outlet />
          </main>
        </div>
      </div>
      <AvisoSessao />
    </div>
  );
}
