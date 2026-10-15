import { VITRINE_ATIVA } from "@/lib/ambiente";

/** Provisória até o M9 (landing pública). Mantém a marca e aponta para a vitrine em desenvolvimento. */
export function PaginaInicial() {
  return (
    <main style={{ maxWidth: 760, margin: "0 auto", padding: "64px 24px" }}>
      <img src="/brand/logo.png" alt="ClimaSense" width={320} style={{ height: "auto" }} />
      <h1 style={{ fontSize: "var(--t-1)", lineHeight: 1.1, margin: "32px 0 16px" }}>
        A página inicial pública chega no marco M9.
      </h1>
      <p style={{ color: "var(--cs-tinta-2)" }}>
        Em emergência, ligue 199 (Defesa Civil), 193 (Bombeiros) ou 192 (SAMU).
      </p>
      {VITRINE_ATIVA && (
        <p style={{ marginTop: 24 }}>
          <a href="/_vitrine">Abrir a vitrine do design system</a>
        </p>
      )}
    </main>
  );
}
