/** Teste de desktop/celular com respostas sintéticas; nenhuma chamada chega aos bancos. */
import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

test("previsão por distrito preserva mapa, acessibilidade e retorno ao cenário manual", async ({ page }) => {
  const agora = new Date().toISOString();
  const geo = {
    type: "FeatureCollection",
    features: [
      {
        type: "Feature",
        properties: { id: "bairro-a", nome: "Bairro de teste", distrito_id: "ds-1" },
        geometry: {
          type: "Polygon",
          coordinates: [
            [
              [-34.91, -8.05],
              [-34.9, -8.05],
              [-34.9, -8.04],
              [-34.91, -8.04],
              [-34.91, -8.05],
            ],
          ],
        },
      },
    ],
  };
  const item = {
    territorio_id: "bairro-a",
    nome: "Bairro de teste",
    nivel: "bairro",
    distrito_id: "ds-1",
    classe_alagamento: "alerta",
    classe_deslizamento: "sem_dados",
    estagio_sugerido: "alerta",
    confianca: "baixa",
    motivos: ["Chuva prevista do distrito exige atenção."],
    impacto_pessoas: null,
  };
  const resultado = {
    dados: {
      itens: [item],
      resumo: { impacto_pessoas_aviso: "Dados insuficientes: IBGE e CNES." },
      experimental: true,
      calculado_em: agora,
      tempo_calculo_ms: 1,
    },
    meta: { fontes: [] },
  };
  const usuario = {
    id: "00000000-0000-0000-0000-000000000001",
    nome: "Usuária de teste",
    email: "teste@example.invalid",
    papeis: ["analista"],
    permissoes: ["consultar", "editar"],
    troca_senha_obrigatoria: false,
    expira_em: new Date(Date.now() + 3600000).toISOString(),
    ambiente: "teste",
    inatividade_min: 60,
    mapa_tiles_url: "",
  };
  const dias = ["2026-05-10", "2026-05-11"].map((data, i) => ({
    data, inicio: `${data}T03:00:00Z`, fim: `${data}T23:00:00Z`, horas_periodo: 20,
    periodo_parcial: true, criterios: { atencao_mm: 25, alerta_mm: 50, critico_mm: 90 },
    distritos_em_atencao: i === 0 ? ["ds-1"] : [],
    distritos: [{ territorio_id: "ds-1", nome: "Distrito I", chuva_prevista_mm: i === 0 ? 50 : 0,
      chuva_disponivel_mm: i === 0 ? 50 : 0, horas_validas: 20, horas_esperadas: 20,
      cobertura_completa: true, desatualizada: false, referencia_em: agora,
      sinalizacao: i === 0 ? "alerta" : "observacao", chuva_intensa: i === 0 }],
  }));
  await page.route("**/api/v1/**", async (route) => {
    const url = new URL(route.request().url());
    const p = url.pathname.replace("/api/v1", "");
    const dia = url.searchParams.get("dia");
    const rotas: Record<string, unknown> = {
      "/auth/eu": usuario,
      "/cenarios": { dados: [] },
      "/cenarios/premissas-atuais": {
        dados: { chuva_prevista_mm: 80, duracao_h: 24, chuva_acumulada_mm: null, mare_m: 1, horizonte_h: 24 },
        meta: { fontes: [] },
      },
      "/estagios/parametros": { limiares: { chuva_prev_24h_atencao_mm: 30, chuva_prev_24h_alerta_mm: 50 } },
      "/cenarios/simular": resultado,
      "/cenarios/impacto-previsto": {
        ...resultado,
        dados: {
          ...resultado.dados,
          contexto: "previsao_atual",
          dias, dia_selecionado: dia, comparacoes_recentes: [],
          itens: [{ ...item, sinalizacao_preventiva: dia === "2026-05-10" ? "alerta" : dia ? "observacao" : null }],
          ml_alagamento: {
            disponivel: false,
            motivo: "Modelo não superou a referência simples",
            modelo: null,
          },
        },
      },
      "/territorios/bairros.geojson": geo,
      "/territorios/distritos.geojson": { type: "FeatureCollection", features: [] },
    };
    await route.fulfill({ status: p in rotas ? 200 : 404, json: rotas[p] ?? { detail: "Não simulado" } });
  });
  await page.goto("/app/simulador");
  await expect(page.getByText(/Cenário hipotético: as premissas/)).toBeVisible();
  await page.getByRole("radio", { name: "Previsão por distrito", exact: true }).check();
  await expect(page.getByText(/ML de alagamento indisponível: Modelo não superou/)).toBeVisible();
  await expect(page.getByRole("button", { name: "Salvar cenário" })).toBeDisabled();
  await expect(page.locator(".leaflet-container")).toBeVisible();
  await page.getByRole("button", { name: /Bairro de teste/ }).click();
  await expect(page.getByTestId("bairro-escolhido")).toBeVisible();
  await page.getByRole("radio", { name: /10\/05 · 1 distrito/ }).check();
  await expect(page.getByRole("radio", { name: "Atenção preventiva", exact: true })).toBeChecked();
  await expect(page.getByRole("region", { name: "Comparação meteorológica e territorial" })).toBeVisible();
  await expect(page.getByText(/Não são duas previsões independentes/)).toBeVisible();
  await expect(page.getByRole("heading", { name: "Bairros em atenção preventiva" })).toBeVisible();
  const corAtencao = await page.locator(".leaflet-interactive").first().getAttribute("fill");
  await page.screenshot({ path: `../tmp/alertas-${test.info().project.name}.png`, fullPage: true });
  await page.getByRole("radio", { name: /11\/05 · 0 distritos/ }).check();
  await expect(page.getByText(/Nenhuma ultrapassagem confirmada/)).toBeVisible();
  await expect(page.locator(".leaflet-interactive").first()).not.toHaveAttribute("fill", corAtencao!);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  const a11y = await new AxeBuilder({ page } as unknown as ConstructorParameters<typeof AxeBuilder>[0])
    .withTags(["wcag2a", "wcag2aa"])
    .analyze();
  expect(a11y.violations.filter((v) => v.impact === "critical" || v.impact === "serious")).toEqual([]);
  await page.getByRole("radio", { name: "Cenário hipotético", exact: true }).check();
  await expect(page.getByRole("button", { name: "Salvar cenário" })).toBeEnabled();
  await expect(page.locator(".leaflet-container")).toBeVisible();
});
