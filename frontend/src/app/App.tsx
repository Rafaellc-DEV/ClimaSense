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
const Situacao = carregar(() => import("@/features/situacao/TelaSituacao"), "TelaSituacao");
const Chuva = carregar(() => import("@/features/chuva/TelaChuva"), "TelaChuva");
const Registro = carregar(() => import("@/features/registro/TelaRegistro"), "TelaRegistro");
const Abrigos = carregar(() => import("@/features/abrigos/TelaAbrigos"), "TelaAbrigos");
const Saude = carregar(() => import("@/features/saude/TelaSaude"), "TelaSaude");
const Boletim = carregar(() => import("@/features/boletim/TelaBoletim"), "TelaBoletim");
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

/**
 * Telas que saíram do menu levam para a tela nova que ficou com o conteúdo delas, sem 404. Endereço desconhecido
 * dentro de /app volta para a Situação.
 */
const ANTIGAS: [string, string][] = [
  ["painel", "/app"],
  ["estagios", "/app"],
  ["mapa", "/app"],
  ["avaliacoes/*", "/app"],
  ["avaliacoes", "/app"],
  ["cenarios", "/app/chuva"],
  ["series", "/app/chuva?aba=historico"],
  ["acoes", "/app/registro"],
];

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
                  <Route index element={<Situacao />} />
                  <Route path="chuva" element={<Chuva />} />
                  <Route path="registro" element={<Registro />} />
                  <Route path="abrigos" element={<Abrigos />} />
                  <Route path="saude" element={<Saude />} />
                  <Route path="boletim" element={<Boletim />} />
                  {ANTIGAS.map(([de, para]) => (
                    <Route key={de} path={de} element={<Navigate to={para} replace />} />
                  ))}
                  <Route path="comunicados" element={<Comunicados />} />
                  <Route path="comunicados/novo" element={<NovoComunicado />} />
                  <Route path="comunicados/:id" element={<Comunicado />} />
                  <Route path="fontes" element={<Fontes />} />
                  <Route path="fontes/:id" element={<Fonte />} />
                  <Route path="admin/*" element={<Admin />} />
                  <Route path="conta" element={<Conta />} />
                  <Route path="*" element={<Navigate to="/app" replace />} />
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
