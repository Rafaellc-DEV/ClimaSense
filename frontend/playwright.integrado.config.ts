import { defineConfig, devices } from "@playwright/test";

/**
 * Testes de ponta a ponta contra o sistema de verdade: API (porta 8000), banco com dados reais e o Vite (5173).
 * Suba antes com `dev.ps1`. As contas vêm de tmp/senhas-equipe-local.txt (fora do Git), criado com
 * `python -m climasense.admin criar-equipe`.
 */
const canal = process.platform === "win32" ? "msedge" : undefined;
export default defineConfig({
  testDir: "./tests/e2e/integrado",
  timeout: 60_000,
  workers: 1,
  fullyParallel: false,
  use: { baseURL: "http://localhost:5173", trace: "retain-on-failure", channel: canal },
  webServer: { command: "npm run dev", port: 5173, reuseExistingServer: true },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 1000 }, channel: canal } },
  ],
});
