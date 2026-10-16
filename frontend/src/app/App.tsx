import { lazy, Suspense } from "react";
import { QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Navigate, Route, Routes, useLocation } from "react-router-dom";
import { ProvedorAvisos } from "@/design-system/componentes/Aviso";
import { Carregando } from "@/design-system/componentes/Painel";
import { PaginaInicial } from "@/features/landing/PaginaInicial";
import { clienteConsultas } from "@/lib/api";
import { VITRINE_ATIVA } from "@/lib/ambiente";
import { ProvedorSessao } from "@/lib/sessao";

const carregar = <K extends string>(f: () => Promise<Record<K, React.ComponentType>>, nome: K) =>
  lazy(() => f().then((m) => ({ default: m[nome] })));

const Vitrine = carregar(() => import("@/features/vitrine/Vitrine"), "Vitrine");
const Entrar = carregar(() => import("@/features/entrar/Entrar"), "Entrar");
const DetalheAvisoPublico = carregar(() => import("@/features/landing/DetalheAviso"), "DetalheAviso");
const AppShell = carregar(() => import("./AppShell"), "AppShell");
const Painel = carregar(() => import("@/features/painel/Painel"), "Painel");
const Mapa = carregar(() => import("@/features/territorio/TelaMapa"), "TelaMapa");
const Series = carregar(() => import("@/features/series/TelaSeries"), "TelaSeries");
const Cenarios = carregar(() => import("@/features/cenarios/TelaCenarios"), "TelaCenarios");
const Avaliacoes = carregar(() => import("@/features/avaliacoes/ListaAvaliacoes"), "ListaAvaliacoes");
const Avaliacao = carregar(() => import("@/features/avaliacoes/DetalheAvaliacao"), "DetalheAvaliacao");
const NovaAvaliacao = carregar(() => import("@/features/avaliacoes/DetalheAvaliacao"), "NovaAvaliacao");
const Comunicados = carregar(() => import("@/features/comunicados/ListaComunicados"), "ListaComunicados");
const Comunicado = carregar(() => import("@/features/comunicados/EditorComunicado"), "EditorComunicado");
const NovoComunicado = carregar(() => import("@/features/comunicados/EditorComunicado"), "NovoComunicado");
const Fontes = carregar(() => import("@/features/fontes/TelaFontes"), "TelaFontes");
const Fonte = carregar(() => import("@/features/fontes/DetalheFonte"), "DetalheFonte");
const Admin = carregar(() => import("@/features/admin/TelaAdmin"), "TelaAdmin");
const Conta = carregar(() => import("@/features/entrar/TrocarSenha"), "TelaConta");

/** O endereço antigo /equipe vira /app, mantendo o resto do caminho. */
function RedirecionarEquipe() {
  const l = useLocation();
  return <Navigate to={l.pathname.replace(/^\/equipe/, "/app") + l.search} replace />;
}

export function App() {
  return (
    <QueryClientProvider client={clienteConsultas}>
      <ProvedorAvisos>
        <ProvedorSessao>
          <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
            <Suspense fallback={<Carregando />}>
              <Routes>
                <Route path="/" element={<PaginaInicial />} />
                <Route path="/avisos/:id" element={<DetalheAvisoPublico />} />
                <Route path="/entrar" element={<Entrar />} />
                <Route path="/app" element={<AppShell />}>
                  <Route index element={<Painel />} />
                  <Route path="mapa" element={<Mapa />} />
                  <Route path="series" element={<Series />} />
                  <Route path="cenarios" element={<Cenarios />} />
                  <Route path="avaliacoes" element={<Avaliacoes />} />
                  <Route path="avaliacoes/nova" element={<NovaAvaliacao />} />
                  <Route path="avaliacoes/:id" element={<Avaliacao />} />
                  <Route path="comunicados" element={<Comunicados />} />
                  <Route path="comunicados/novo" element={<NovoComunicado />} />
                  <Route path="comunicados/:id" element={<Comunicado />} />
                  <Route path="fontes" element={<Fontes />} />
                  <Route path="fontes/:id" element={<Fonte />} />
                  <Route path="admin/*" element={<Admin />} />
                  <Route path="conta" element={<Conta />} />
                </Route>
                <Route path="/equipe/*" element={<RedirecionarEquipe />} />
                {VITRINE_ATIVA && <Route path="/_vitrine" element={<Vitrine />} />}
                <Route path="*" element={<PaginaInicial />} />
              </Routes>
            </Suspense>
          </BrowserRouter>
        </ProvedorSessao>
      </ProvedorAvisos>
    </QueryClientProvider>
  );
}
