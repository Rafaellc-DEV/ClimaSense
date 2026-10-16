import { useEffect, useState, type ReactNode } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import {
  ClipboardCheck,
  CloudRainWind,
  Database,
  LayoutDashboard,
  ChartLine,
  LogOut,
  Map as IconeMapa,
  Megaphone,
  Menu,
  Settings,
  X,
} from "lucide-react";
import { Link, Navigate, NavLink, Outlet, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import type { Esquemas } from "@/lib/api";
import { useConsulta } from "@/lib/consultas";
import { buscaDoRecorte } from "@/lib/recorte";
import { useSessao } from "@/lib/sessao";
import { PAPEIS } from "@/textos/glossario";
import { AvisoSessao } from "./AvisoSessao";
import { FiltroFrase } from "./FiltroFrase";
import estilos from "./AppShell.module.css";

interface ItemMenu {
  para: string;
  rotulo: string;
  icone: ReactNode;
  permissao?: string;
  contador?: "avaliacoes" | "comunicados";
  fim?: boolean;
}

/** RF-04.2: no máximo 8 itens de primeiro nível, sempre com ícone e texto. */
const ITENS: ItemMenu[] = [
  { para: "/app", rotulo: "Painel inicial", icone: <LayoutDashboard />, fim: true },
  { para: "/app/mapa", rotulo: "Mapa do território", icone: <IconeMapa /> },
  { para: "/app/series", rotulo: "Séries e sazonalidade", icone: <ChartLine /> },
  { para: "/app/cenarios", rotulo: "Cenários de alagamento", icone: <CloudRainWind /> },
  { para: "/app/avaliacoes", rotulo: "Avaliações", icone: <ClipboardCheck />, contador: "avaliacoes" },
  { para: "/app/comunicados", rotulo: "Comunicados", icone: <Megaphone />, contador: "comunicados" },
  { para: "/app/fontes", rotulo: "Fontes de dados", icone: <Database /> },
  { para: "/app/admin", rotulo: "Administração", icone: <Settings />, permissao: "administrar" },
];

/** Telas em que o recorte global (território e período) vale e aparece no topo. */
const COM_RECORTE = ["/app", "/app/mapa", "/app/series", "/app/cenarios", "/app/avaliacoes"];

function Navegacao({ aoEscolher }: { aoEscolher?: () => void }) {
  const { pode } = useSessao();
  const [params] = useSearchParams();
  const resumo = useConsulta<Esquemas["ResumoPainel"]>("/painel/resumo");
  const busca = buscaDoRecorte(params);
  return (
    <nav aria-label="Menu principal" className={estilos.nav}>
      <ul>
        {ITENS.filter((i) => !i.permissao || pode(i.permissao)).map((i) => {
          const n = i.contador ? resumo.data?.contadores[i.contador] ?? 0 : 0;
          return (
            <li key={i.para}>
              <NavLink to={{ pathname: i.para, search: busca }} end={i.fim} onClick={aoEscolher}>
                <span className={estilos.icone} aria-hidden="true">
                  {i.icone}
                </span>
                <span className={estilos.rotuloItem}>{i.rotulo}</span>
                {n > 0 && (
                  <span className={estilos.contador} aria-label={`${n} aguardando a sua revisão`}>
                    {n}
                  </span>
                )}
              </NavLink>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}

function Marca() {
  return (
    <Link to="/app" className={estilos.marca} aria-label="ClimaSense, painel inicial">
      <img src="/brand/logo.png" srcSet="/brand/logo@2x.png 2x" alt="" width={176} height={44} />
    </Link>
  );
}

/** Área da equipe: menu lateral fixo (296 px) e, abaixo de 1024 px, uma gaveta aberta pelo botão “Menu”. */
export function AppShell() {
  const { usuario, sair, garantir } = useSessao();
  const navegar = useNavigate();
  const local = useLocation();
  const [gaveta, setGaveta] = useState(false);
  useEffect(garantir, [garantir]);
  useEffect(() => setGaveta(false), [local.pathname]);

  if (usuario === undefined) return <p className={estilos.verificando}>Verificando a sua sessão…</p>;
  if (!usuario || usuario.troca_senha_obrigatoria)
    return <Navigate to="/entrar" replace state={{ voltarPara: local.pathname + local.search }} />;

  const comRecorte = COM_RECORTE.includes(local.pathname.replace(/\/$/, ""));
  const conta = (
    <div className={estilos.conta}>
      <p className={estilos.nome}>{usuario.nome}</p>
      <p className={estilos.papeis}>{usuario.papeis.map((p) => PAPEIS[p] ?? p).join(", ")}</p>
      <button
        type="button"
        className={estilos.sair}
        onClick={async () => {
          await sair();
          navegar("/");
        }}
      >
        <LogOut aria-hidden="true" size={20} /> Sair
      </button>
    </div>
  );

  return (
    <div className={estilos.casca}>
      <a href="#conteudo" className={estilos.pular}>
        Pular para o conteúdo
      </a>
      {usuario.ambiente !== "producao" && (
        <p className={estilos.faixaAmbiente} role="note">
          Ambiente de {usuario.ambiente === "teste" ? "testes" : "desenvolvimento"}. Os dados são reais; as
          contas e os avisos publicados aqui não chegam à população.
        </p>
      )}
      <div className={estilos.grade}>
        <aside className={estilos.lateral} aria-label="Navegação">
          <Marca />
          <Navegacao />
          {conta}
          <p className={estilos.lugar}>Recife, Pernambuco</p>
        </aside>

        <div className={estilos.coluna}>
          <header className={estilos.topo}>
            <Dialog.Root open={gaveta} onOpenChange={setGaveta}>
              <Dialog.Trigger className={estilos.botaoMenu}>
                <Menu aria-hidden="true" size={22} /> Menu
              </Dialog.Trigger>
              <Dialog.Portal>
                <Dialog.Overlay className={estilos.veu} />
                <Dialog.Content className={estilos.gaveta} aria-describedby={undefined}>
                  <Dialog.Title className="so-leitor">Menu</Dialog.Title>
                  <div className={estilos.gavetaTopo}>
                    <Marca />
                    <Dialog.Close className={estilos.fecharGaveta}>
                      <X aria-hidden="true" size={22} /> Fechar
                    </Dialog.Close>
                  </div>
                  <Navegacao aoEscolher={() => setGaveta(false)} />
                  {conta}
                </Dialog.Content>
              </Dialog.Portal>
            </Dialog.Root>
            {comRecorte ? <FiltroFrase /> : <span />}
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

/** Cabeçalho comum das telas da equipe: título (--t-2) e uma frase dizendo para que a tela serve. */
export function CabecalhoTela({
  titulo,
  proposito,
  acoes,
}: {
  titulo: string;
  proposito: ReactNode;
  acoes?: ReactNode;
}) {
  useEffect(() => {
    document.title = `${titulo} | ClimaSense`;
  }, [titulo]);
  return (
    <header className={estilos.cabecalhoTela}>
      <div>
        <h1>{titulo}</h1>
        <p>{proposito}</p>
      </div>
      {acoes && <div className={estilos.acoesTela}>{acoes}</div>}
    </header>
  );
}
