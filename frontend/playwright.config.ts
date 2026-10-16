import { defineConfig, devices } from "@playwright/test";

/** No Windows usa o Edge já instalado; no CI (Linux), o Chromium do Playwright. */
const canal = process.platform === "win32" ? "msedge" : undefined;

/** Testes com respostas simuladas da API, sobre o build de produção. */
export default defineConfig({
  testDir: "./tests/e2e",
  testIgnore: ["**/integrado/**"],
  timeout: 30_000,
  use: { baseURL: "http://localhost:4173", trace: "retain-on-failure", channel: canal },
  webServer: {
    command: "npx cross-env VITE_VITRINE=1 npm run build && npm run preview -- --port 4173",
    port: 4173,
    reuseExistingServer: true,
  },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 1000 }, channel: canal } },
    { name: "celular", use: { ...devices["Pixel 7"], channel: canal } },
  ],
});
