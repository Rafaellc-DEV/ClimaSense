import { useEffect, useState, type ReactNode } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import {
  CloudRain,
  Database,
  FileText,
  HeartPulse,
  LogOut,
  Megaphone,
  Map as MapIcon,
  Menu,
  NotebookPen,
  Settings,
  Siren,
  Tent,
  X,
} from "lucide-react";
import { Link, Navigate, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { Marca } from "@/design-system/componentes/Marca";
import rios from "@/assets/tracos/rios.svg?raw";
import type { Esquemas } from "@/lib/api";
import { enderecoInicial, funcionalidadeLigada } from "@/lib/funcionalidades";
import { useConsulta } from "@/lib/consultas";
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
  contador?: "comunicados";
  fim?: boolean;
}

/**
 * Oito itens, cada um responde a uma dor da equipe, na ordem do dia a dia: o mapa, o que fazer agora, a chuva, o registro, os
 * abrigos, a saúde depois da chuva, o aviso à população e o boletim. Fontes e Administração ficam no rodapé.
 */
const TODOS_PRINCIPAIS: ItemMenu[] = [
  { para: "/app", rotulo: "Mapa", icone: <MapIcon />, fim: true },
  { para: "/app/situacao", rotulo: "Situação", icone: <Siren /> },
  { para: "/app/chuva", rotulo: "Chuva", icone: <CloudRain /> },
  { para: "/app/registro", rotulo: "Registro do evento", icone: <NotebookPen /> },
  { para: "/app/abrigos", rotulo: "Abrigos", icone: <Tent /> },
  { para: "/app/saude", rotulo: "Saúde depois da chuva", icone: <HeartPulse /> },
  { para: "/app/comunicados", rotulo: "Comunicados", icone: <Megaphone />, contador: "comunicados" },
  { para: "/app/boletim", rotulo: "Boletim", icone: <FileText /> },
];
/** Itens de funcionalidades desligadas por chave (ADR 0011) não entram no menu. */
const principais = () =>
  TODOS_PRINCIPAIS.filter((i) => i.para !== "/app/comunicados" || funcionalidadeLigada("comunicados"));
const RODAPE: ItemMenu[] = [
  { para: "/app/fontes", rotulo: "Fontes", icone: <Database /> },
  { para: "/app/admin", rotulo: "Administração", icone: <Settings />, permissao: "administrar" },
];

function Contador({ n }: { n: number }) {
  if (n <= 0) return null;
  return (
    <span className={estilos.contador} aria-label={`${n} aguardando a sua revisão`}>
      {n}
    </span>
  );
}

function Navegacao({ aoEscolher }: { aoEscolher?: () => void }) {
  const { pode } = useSessao();
  const resumo = useConsulta<Esquemas["ResumoPainel"]>("/painel/resumo", {
    enabled: funcionalidadeLigada("comunicados"),
  });
  const contar = (i: ItemMenu) => (i.contador ? (resumo.data?.contadores[i.contador] ?? 0) : 0);

  const lista = (itens: ItemMenu[], classe?: string) => (
    <ul className={[estilos.grupo, classe].filter(Boolean).join(" ")}>
      {itens
        .filter((i) => !i.permissao || pode(i.permissao))
        .map((i) => (
          <li key={i.para}>
            <NavLink to={i.para} end={i.fim} onClick={aoEscolher}>
              <span className={estilos.icone} aria-hidden="true">
                {i.icone}
              </span>
              <span className={estilos.rotuloItem}>{i.rotulo}</span>
              <Contador n={contar(i)} />
            </NavLink>
          </li>
        ))}
    </ul>
  );

  return (
    <nav aria-label="Menu principal" className={estilos.nav}>
      <div className={estilos.bloco}>{lista(principais())}</div>
      <div className={`${estilos.bloco} ${estilos.blocoRodape}`}>{lista(RODAPE, estilos.grupoRodape)}</div>
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
function ConteudoLateral({ aoEscolher, aoSair }: { aoEscolher?: () => void; aoSair: () => void }) {
  const { usuario } = useSessao();
  if (!usuario) return null;
  const papeis = usuario.papeis.map((p) => PAPEIS[p] ?? p).join(", ");
  return (
    <>
      <Navegacao aoEscolher={aoEscolher} />
      <div className={estilos.conta}>
        <Link to="/app/conta" className={estilos.pessoa} onClick={aoEscolher}>
          <span className={estilos.avatar} aria-hidden="true">
            {usuario.nome.trim().charAt(0).toUpperCase()}
          </span>
          <span className={estilos.pessoaTextos}>
            <span className={estilos.nome}>{usuario.nome}</span>
            <span className={estilos.papeis}>{papeis}</span>
          </span>
        </Link>
        <button type="button" className={estilos.sair} onClick={aoSair}>
          <LogOut aria-hidden="true" size={20} /> Sair
        </button>
      </div>
      <div className={estilos.rios} aria-hidden="true" dangerouslySetInnerHTML={{ __html: rios }} />
    </>
  );
}

/** Área da equipe: menu lateral azul profundo (fixo nos dois temas) e, abaixo de 1024 px, uma gaveta. */
export function AppShell() {
  const { usuario, sair, garantir } = useSessao();
  const navegar = useNavigate();
  const local = useLocation();
  const [gaveta, setGaveta] = useState(false);
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
      <div className={estilos.grade}>
        <aside className={estilos.lateral} aria-label="Navegação">
          <Logo />
          <ConteudoLateral aoSair={sairDaConta} />
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
          <main id="conteudo" className={estilos.conteudo} tabIndex={-1}>
            <Outlet />
          </main>
        </div>
      </div>
      <AvisoSessao />
    </div>
  );
}
