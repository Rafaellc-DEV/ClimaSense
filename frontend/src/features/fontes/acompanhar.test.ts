import { acompanhar, PRAZO_COLETA_MS } from "./acompanhar";

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

test("devolve falha da fonte e zero registros sem converter em sucesso", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => new Response(JSON.stringify({ status: "falha", gravados: 0 }))),
  );
  const r = await acompanhar("teste", new AbortController().signal);
  expect(r.status).toBe("falha");
});

test("erro de autorização encerra acompanhamento sem repetição", async () => {
  const fetch = vi.fn(async () => new Response(JSON.stringify({ detail: "Sem permissão" }), { status: 403 }));
  vi.stubGlobal("fetch", fetch);
  await expect(acompanhar("teste", new AbortController().signal)).rejects.toThrow(/Consulte o histórico/);
  expect(fetch).toHaveBeenCalledTimes(1);
});

test("três falhas de rede encerram acompanhamento", async () => {
  vi.useFakeTimers();
  const fetch = vi.fn(async () => {
    throw new Error("rede");
  });
  vi.stubGlobal("fetch", fetch);
  const r = expect(acompanhar("teste", new AbortController().signal)).rejects.toThrow(/Consulte o histórico/);
  await vi.advanceTimersByTimeAsync(10_000);
  await r;
  expect(fetch).toHaveBeenCalledTimes(3);
});

test("execução abandonada não mantém tela ocupada indefinidamente", async () => {
  vi.useFakeTimers();
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => new Response(JSON.stringify({ status: "em_andamento" }))),
  );
  const r = expect(acompanhar("teste", new AbortController().signal)).rejects.toThrow(
    /pode continuar no servidor/,
  );
  await vi.advanceTimersByTimeAsync(PRAZO_COLETA_MS + 3000);
  await r;
});
