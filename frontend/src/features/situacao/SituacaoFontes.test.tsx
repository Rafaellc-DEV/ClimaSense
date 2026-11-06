import { render, screen } from "@testing-library/react";
import { App } from "@/app/App";
import { AGORA, itemEstagio, simularApi, usuarioTeste } from "@/features/evento/testes";
import { clienteConsultas } from "@/lib/api";

const HORA = new Date(Date.now() - 2 * 3_600_000).toISOString();
const distrito = itemEstagio({
  territorio_id: "ds-1",
  territorio_nome: "Distrito Sanitário I",
  sugerido: { estagio: "observacao", motivos: [], insumos: { chuva_24h_mm: 3 }, calculado_em: AGORA },
});

function api(fontes: unknown[]) {
  return {
    "/auth/eu": usuarioTeste(),
    "/painel/resumo": { contadores: { avaliacoes: 0, comunicados: 0 }, fontes: [] },
    "/estagios?nivel=distrito": { dados: { itens: [distrito] }, meta: { fontes } },
    "/estagios?nivel=bairro": { itens: [] },
    "/estagios/parametros": { limiares: {}, padrao: true },
    "/abrigos": { itens: [], totais: { abrigos_abertos: 0, abrigos_cadastrados: 3, atualizado_em: AGORA } },
  };
}

afterEach(() => {
  vi.unstubAllGlobals();
  clienteConsultas.clear();
});

test("Situação mostra fonte, hora, selo Desatualizado e “Atualizado às”", async () => {
  simularApi(
    api([
      {
        id: "open-meteo-previsao",
        nome: "Open-Meteo",
        atualizado_em: HORA,
        limite_frescor_h: 1,
        desatualizado: true,
      },
      {
        id: "mare",
        nome: "Previsão de maré",
        atualizado_em: null,
        limite_frescor_h: 24,
        desatualizado: null,
      },
    ]),
  );
  window.history.pushState({}, "", "/app");
  render(<App />);
  expect((await screen.findAllByText("Desatualizado")).length).toBeGreaterThan(0);
  expect(screen.getAllByText(/Open-Meteo, atualizado há 2 h/).length).toBeGreaterThan(0);
  expect(screen.getAllByText(/falta a fonte Previsão de maré/).length).toBeGreaterThan(0);
  expect(screen.getByText(/Atualizado às \d\d:\d\d/)).toBeInTheDocument();
});

test("sem meta.fontes a Situação mantém o texto antigo e não mostra selo", async () => {
  simularApi(api([]));
  window.history.pushState({}, "", "/app");
  render(<App />);
  expect(await screen.findByText(/Previsão de chuva e maré: Open-Meteo/)).toBeInTheDocument();
  expect(screen.queryByText("Desatualizado")).not.toBeInTheDocument();
});
