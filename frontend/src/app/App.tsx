import { lazy, Suspense } from "react";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { ProvedorAvisos } from "@/design-system/componentes/Aviso";
import { PaginaInicial } from "@/features/landing/PaginaInicial";
import { VITRINE_ATIVA } from "@/lib/ambiente";

const Vitrine = lazy(() => import("@/features/vitrine/Vitrine").then((m) => ({ default: m.Vitrine })));

export function App() {
  return (
    <ProvedorAvisos>
      <BrowserRouter>
        <Suspense fallback={<p style={{ padding: 32 }}>Carregando…</p>}>
          <Routes>
            <Route path="/" element={<PaginaInicial />} />
            {VITRINE_ATIVA && <Route path="/_vitrine" element={<Vitrine />} />}
            <Route path="*" element={<PaginaInicial />} />
          </Routes>
        </Suspense>
      </BrowserRouter>
    </ProvedorAvisos>
  );
}
