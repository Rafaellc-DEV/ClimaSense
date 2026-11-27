import { itemEstagio } from "@/features/evento/testes";
import type { ItemEstagio } from "@/features/evento/tipos";
import {
  acoesPorDistrito,
  alertasVigentes,
  chuvaMedida,
  decisoesPendentes,
  exposicaoPorDistrito,
  gatilhos,
  gerarInsights,
  janelaLeptospirose,
  limiarSeguinte,
  leituraAgravo,
  maiorChuva,
  mareNoPico,
  pessoasEmAlerta,
  previstaVsMedia,
  tendenciaDaSerie,
  topVulneraveis,
  type ImpactoApi,
  type SituacaoChuvaApi,
} from "./indicadores";

const LIM = {
  chuva_24h_atencao_mm: 25,
  chuva_24h_alerta_mm: 50,
  chuva_24h_critico_mm: 90,
  chuva_prev_24h_atencao_mm: 25,
  chuva_prev_24h_alerta_mm: 50,
  chuva_prev_24h_critico_mm: 90,
  chuva_prev_72h_atencao_mm: 60,
  chuva_prev_72h_alerta_mm: 100,
  chuva_prev_72h_critico_mm: 150,
  mare_alta_m: 0.6,
};
const AGORA = new Date("2026-11-26T15:00:00Z");

function item(id: string, nome: string, estagio: string, insumos = {}, extra: Partial<ItemEstagio> = {}) {
  return itemEstagio({
    territorio_id: id,
    territorio_nome: nome,
    sugerido: { estagio: estagio as never, motivos: [], insumos, calculado_em: AGORA.toISOString() },
    ...extra,
  });
}
const decl = (estagio: string) => ({
  estagio: estagio as never,
  justificativa: "",
  autor_nome: "A",
  declarado_em: "",
});

test("decisões pendentes: sugerido acima do declarado, mais vulnerável primeiro, sem dado à parte", () => {
  const itens = [
    item("b1", "Cohab", "alerta", {}, { nivel: "bairro", distrito_id: "ds-8" }),
    item("b2", "Ibura", "atencao", {}, { nivel: "bairro", distrito_id: "ds-8" }),
    item("b3", "Aflitos", "sem_dados", {}, { nivel: "bairro", distrito_id: "ds-3" }),
    item("b4", "Derby", "observacao", {}, { nivel: "bairro", distrito_id: "ds-3" }),
    item("b5", "Várzea", "alerta", {}, { nivel: "bairro", distrito_id: "ds-4", declarado: decl("alerta") }),
    item("b6", "Areias", "critico", {}, { nivel: "bairro", distrito_id: "ds-5", declarado: decl("atencao") }),
  ];
  const r = decisoesPendentes(itens, new Map([["b2", 1]]));
  expect(r.itens.map((i) => i.nome)).toEqual(["Areias", "Cohab", "Ibura"]);
  expect(r.total).toBe(3);
  expect(r.distritos).toBe(2);
  expect(r.semDados).toBe(1); // Aflitos não vira "observação"
  expect(r.itens[0].declarado).toBe("atencao");
});

test("próximo gatilho: menor distância entre os insumos ao limiar do próximo estágio", () => {
  const ds = [
    item("ds-1", "Distrito Sanitário I", "observacao", {
      chuva_24h_mm: 5,
      chuva_prev_24h_mm: 10,
      chuva_prev_72h_mm: 53,
    }),
    item("ds-2", "Distrito Sanitário II", "atencao", { chuva_prev_24h_mm: 30 }),
    item("ds-3", "Distrito Sanitário III", "sem_dados"),
    item("ds-4", "Distrito Sanitário IV", "critico", { chuva_prev_24h_mm: 200 }),
    item("ds-5", "Distrito Sanitário V", "observacao", {}),
  ];
  const r = gatilhos(ds, LIM);
  expect(r.itens[0]).toMatchObject({
    nome: "Distrito 1",
    insumo: "chuva_prev_72h_mm",
    falta: 7,
    proximo: "atencao",
  });
  expect(r.itens[1]).toMatchObject({ nome: "Distrito 2", falta: 20, proximo: "alerta" });
  expect(r.semDados).toBe(2); // sem_dados e sem nenhum insumo: nunca distância zero
  expect(r.noTopo).toBe(1);
});

test("chuva medida: zero medido continua zero e a falta de leitura fica nula e ao fim", () => {
  const s = {
    distritos: [
      {
        territorio_id: "ds-1",
        territorio_nome: "Distrito Sanitário I",
        chuva_24h_mm: 0,
        chuva_72h_mm: 4,
        estacoes_total: 2,
        estacoes_com_leitura: 2,
      },
      {
        territorio_id: "ds-2",
        territorio_nome: "Distrito Sanitário II",
        chuva_24h_mm: null,
        chuva_72h_mm: null,
        motivo: "Dados insuficientes: sem pluviômetro",
      },
      {
        territorio_id: "ds-3",
        territorio_nome: "Distrito Sanitário III",
        chuva_24h_mm: 12,
        chuva_72h_mm: 20,
      },
    ],
    maior_24h: { territorio_id: "ds-3", territorio_nome: "Distrito Sanitário III", mm: 12 },
    maior_72h: null,
    estacoes: { total: 19, com_leitura: 12, sem_leitura: 7 },
    previsao: { previsao_emitida_em: null, mare_emitida_em: null, chuva: [], mare: [] },
  } satisfies SituacaoChuvaApi;
  const l = chuvaMedida(s, 24);
  expect(l.map((x) => [x.nome, x.mm])).toEqual([
    ["Distrito 3", 12],
    ["Distrito 1", 0],
    ["Distrito 2", null],
  ]);
  expect(maiorChuva(s, 24)).toMatchObject({ nome: "Distrito 3", mm: 12, estacoes: "12 de 19 estações" });
  expect(maiorChuva(s, 72)).toBeNull();
  expect(maiorChuva(undefined, 24)).toBeNull();
});

test("prevista contra a média: média do mês dividida pelos dias, na janela; sem média, sem razão", () => {
  const ds = [
    item("ds-1", "Distrito Sanitário I", "atencao", { chuva_prev_24h_mm: 6, chuva_prev_72h_mm: 12 }),
    item("ds-2", "Distrito Sanitário II", "atencao", { chuva_prev_24h_mm: 6 }),
  ];
  const medias = new Map<string, number | null>([
    ["ds-1", 90], // novembro tem 30 dias: 3 mm por dia
    ["ds-2", null],
  ]);
  const a = previstaVsMedia(ds, medias, AGORA, 24);
  expect(a[0]).toMatchObject({ mediaMm: 3, razao: 2 });
  expect(a[1]).toMatchObject({ mediaMm: null, razao: null });
  expect(previstaVsMedia(ds, medias, AGORA, 72)[0]).toMatchObject({ mediaMm: 9 });
});

test("maré no pico: alta só a partir do limiar; sem dado, nulo", () => {
  const baixo = item("ds-1", "Distrito Sanitário I", "atencao", { mare_no_pico_m: 0.4 });
  const alto = item("ds-2", "Distrito Sanitário II", "atencao", {
    mare_no_pico_m: 2.1,
    pico_chuva_em: AGORA.toISOString(),
  });
  expect(mareNoPico([baixo, alto], LIM)).toMatchObject({ nome: "Distrito 2", mareM: 2.1, alta: true });
  expect(mareNoPico([baixo], LIM)?.alta).toBe(false);
  expect(mareNoPico([item("ds-3", "x", "atencao")], LIM)).toBeNull();
});

const pessoas = (idosos: number | null, criancas: number | null, unidades: number | null) => ({
  idosos_60_mais: idosos,
  criancas_0_14: criancas,
  equipamentos_saude: unidades,
});
const impacto: ImpactoApi = {
  itens: [
    {
      territorio_id: "ds-7",
      nome: "Distrito Sanitário VII",
      nivel: "distrito",
      distrito_id: "ds-7",
      estagio_sugerido: "alerta",
      impacto_pessoas: null,
    },
    {
      territorio_id: "b1",
      nome: "Cohab",
      nivel: "bairro",
      distrito_id: "ds-7",
      estagio_sugerido: "alerta",
      impacto_pessoas: pessoas(100, 200, 3),
    },
    {
      territorio_id: "b2",
      nome: "Ibura",
      nivel: "bairro",
      distrito_id: "ds-7",
      estagio_sugerido: "atencao",
      impacto_pessoas: pessoas(50, 60, 2),
    },
    {
      territorio_id: "b3",
      nome: "Pequeno",
      nivel: "bairro",
      distrito_id: "ds-7",
      estagio_sugerido: "critico",
      impacto_pessoas: pessoas(null, 10, null),
    },
  ],
};

test("pessoas em bairros em alerta: soma só alerta ou crítico; contagem suprimida deixa o total parcial", () => {
  const p = pessoasEmAlerta(impacto, "ds-7");
  expect(p).toMatchObject({ bairros: 2, idosos: null, parcial: true }); // bairro sem número: não vira zero
  const e = exposicaoPorDistrito(impacto);
  expect(e).toHaveLength(1);
  expect(e[0]).toMatchObject({
    nome: "Distrito 7",
    bairrosAlerta: 2,
    idosos: 100,
    criancas: 210,
    unidadesAtencao: 5,
    parcial: true,
  });
});

test("pessoas em alerta: sem previsão é Dados insuficientes, nunca zero; com previsão e sem bairro, zero", () => {
  const semPrevisao: ImpactoApi = { itens: [{ ...impacto.itens[0], estagio_sugerido: "sem_dados" }] };
  expect(pessoasEmAlerta(semPrevisao)).toBeNull();
  expect(pessoasEmAlerta(undefined)).toBeNull();
  const calmo: ImpactoApi = { itens: [{ ...impacto.itens[0], estagio_sugerido: "observacao" }] };
  expect(pessoasEmAlerta(calmo)).toMatchObject({ bairros: 0, idosos: 0 });
  const comResumo: ImpactoApi = {
    ...impacto,
    resumo: {
      pessoas_vulneraveis_em_alerta: {
        bairros_em_alerta: 2,
        idosos_60_mais: 9,
        criancas_0_14: 8,
        parcial: false,
      },
    },
  };
  expect(pessoasEmAlerta(comResumo)).toMatchObject({ bairros: 2, idosos: 9, criancas: 8 });
});

test("alertas oficiais: sem repetir e só dentro da validade", () => {
  const a = {
    origem: "APAC",
    nivel: "laranja",
    emitido_em: "2026-11-26T10:00:00Z",
    expira_em: "2026-11-26T20:00:00Z",
    evento: "Chuva forte",
  };
  const vencido = {
    origem: "INMET",
    nivel: "amarelo",
    emitido_em: "2026-11-25T10:00:00Z",
    expira_em: "2026-11-25T20:00:00Z",
  };
  const ds = [
    item("ds-1", "I", "atencao", {}, { alertas_oficiais: [a, vencido] }),
    item("ds-2", "II", "atencao", {}, { alertas_oficiais: [a] }),
  ];
  const r = alertasVigentes(ds, AGORA);
  expect(r).toHaveLength(1);
  expect(r[0]).toMatchObject({ origem: "APAC", evento: "Chuva forte" });
});

test("saúde: tendência só com base suficiente; janela de leptospirose mostra o dia", () => {
  const agravo = (extra: object) =>
    ({
      agravo: "dengue",
      nome: "Dengue",
      nivel_alerta: 2,
      incompleta: false,
      variacao_4s_pct: 30,
      ...extra,
    }) as never;
  expect(leituraAgravo(agravo({}))).toMatchObject({ tendencia: "sobe", nivel: 2 });
  expect(leituraAgravo(agravo({ variacao_4s_pct: -40 })).tendencia).toBe("cai");
  expect(leituraAgravo(agravo({ variacao_4s_pct: 3 })).tendencia).toBe("estavel");
  const inc = leituraAgravo(agravo({ incompleta: true, variacao_4s_pct: -40 }));
  expect(inc.tendencia).toBeNull();
  expect(inc.semTendencia).toMatch(/incompleta/);
  expect(leituraAgravo(agravo({ variacao_4s_pct: null })).tendencia).toBeNull();
  const j = { ativa: true, inicio: "2026-11-18", fim: "2026-12-17", motivo: null, territorios: [] };
  expect(janelaLeptospirose(j, AGORA)).toEqual({ dia: 9, total: 30 });
  expect(janelaLeptospirose({ ...j, ativa: false }, AGORA)).toBeNull();
  expect(janelaLeptospirose(null, AGORA)).toBeNull();
});

test("ações: distrito em atenção ou mais sem ação em andamento sobe ao topo", () => {
  const ds = [
    item("ds-1", "Distrito Sanitário I", "observacao"),
    item("ds-2", "Distrito Sanitário II", "alerta"),
    item("ds-3", "Distrito Sanitário III", "atencao"),
  ];
  const r = acoesPorDistrito(ds, {
    por_distrito: [
      { distrito_id: "ds-2", distrito_nome: "II", contagens: { em_andamento: 2 } },
      { distrito_id: "ds-3", distrito_nome: "III", contagens: { planejada: 1 } },
    ],
  });
  expect(r.map((l) => [l.nome, l.semAcao])).toEqual([
    ["Distrito 3", true],
    ["Distrito 2", false],
    ["Distrito 1", false],
  ]);
  expect(acoesPorDistrito(ds, undefined)).toEqual([]);
});

test("insights: no máximo 3, o mais grave primeiro, em texto simples e sem percentual de chance", () => {
  const pend = decisoesPendentes(
    [item("b1", "Cohab", "alerta", {}, { nivel: "bairro", distrito_id: "ds-8" })],
    new Map(),
  );
  const ds = [item("ds-1", "Distrito Sanitário I", "atencao", { chuva_prev_72h_mm: 95 })];
  const r = gerarInsights({
    pendencias: pend,
    gatilhos: gatilhos(ds, LIM),
    razoes: [],
    acoes: [],
    alertas: [],
    pessoas: { bairros: 2, idosos: 10, criancas: 20, parcial: false },
    leptospirose: { dia: 9, total: 30 },
    chuva: undefined,
    fontes: [{ id: "x", nome: "Previsão de chuva", atualizado_em: AGORA.toISOString(), desatualizado: true }],
    janela: 24,
    agora: AGORA,
    quando: () => "hoje às 12h",
  });
  expect(r).toHaveLength(3);
  expect(r[0].texto).toBe("1 bairro com sugestão de estágio acima do declarado: Cohab.");
  expect(r[1].id).toBe("fonte-vencida");
  expect(r[2].id).toBe("perto-do-gatilho");
  expect(r.every((i) => !/%/.test(i.texto))).toBe(true);
});

test("insights: sem nada a destacar, diz quanto falta em vez de 'tudo observação'", () => {
  const ds = [item("ds-1", "Distrito Sanitário I", "observacao", { chuva_prev_72h_mm: 30 })];
  const r = gerarInsights({
    pendencias: decisoesPendentes([], new Map()),
    gatilhos: gatilhos(ds, LIM),
    razoes: [],
    acoes: [],
    alertas: [],
    pessoas: null,
    leptospirose: null,
    chuva: undefined,
    fontes: [],
    janela: 24,
    agora: AGORA,
    quando: () => "",
  });
  expect(r).toHaveLength(1);
  expect(r[0].texto).toMatch(/Nenhuma decisão pendente.*Distrito 1.*30 mm/);
});

test("gatilho por janela: 72 h usa só o acumulado previsto de 72 h; 24 h usa a medida e a prevista de 24 h", () => {
  const ds = [
    item("ds-1", "Distrito Sanitário I", "observacao", {
      chuva_24h_mm: 20,
      chuva_prev_24h_mm: 21,
      chuva_prev_72h_mm: 40,
    }),
  ];
  expect(gatilhos(ds, LIM, 72).itens[0]).toMatchObject({ insumo: "chuva_prev_72h_mm", falta: 20 });
  expect(gatilhos(ds, LIM, 24).itens[0]).toMatchObject({ insumo: "chuva_prev_24h_mm", falta: 4 });
});

test("limiar seguinte: o próximo estágio acima do valor; acima do crítico, atingido", () => {
  expect(limiarSeguinte(10, "chuva_24h", LIM)).toMatchObject({
    limiar: 25,
    estagio: "atencao",
    atingido: false,
  });
  expect(limiarSeguinte(60, "chuva_24h", LIM)).toMatchObject({ limiar: 90, estagio: "critico" });
  expect(limiarSeguinte(95, "chuva_24h", LIM)).toMatchObject({ estagio: "critico", atingido: true });
  expect(limiarSeguinte(1, "chuva_inexistente", LIM)).toBeNull();
});

test("bairros com mais moradores vulneráveis do distrito: omitido e sem dado ficam de fora, nunca como zero", () => {
  const b = (id: string, ds: string, idosos: number | null, criancas: number | null, supr = false) => ({
    bairro_id: id,
    nome: id,
    distrito_id: ds,
    idosos_60_mais: idosos,
    criancas_0_14: criancas,
    suprimido: { idosos_60_mais: supr, criancas_0_14: false },
  });
  const r = topVulneraveis(
    [
      b("a", "ds-2", 100, 50),
      b("b", "ds-2", 300, 10),
      b("c", "ds-2", null, 5),
      b("d", "ds-2", null, 5, true),
      b("e", "ds-3", 999, 9),
      b("f", "ds-2", 1, 1),
      b("g", "ds-2", 20, 20),
    ],
    "ds-2",
  );
  expect(r.map((x) => x.id)).toEqual(["b", "a", "g"]);
  expect(topVulneraveis(undefined, "ds-2")).toEqual([]);
  expect(topVulneraveis([b("a", "ds-2", 1, 1)], null)).toEqual([]);
});

test("tendência do dengue ignora a semana incompleta e pede 5 semanas completas", () => {
  const sem = (casos: number, incompleta = false) => ({ casos, incompleta });
  expect(tendenciaDaSerie([sem(100), sem(100), sem(100), sem(100), sem(150), sem(1, true)])).toBe("sobe");
  expect(tendenciaDaSerie([sem(150), sem(100), sem(100), sem(100), sem(100), sem(900, true)])).toBe("cai");
  expect(tendenciaDaSerie([sem(100), sem(100), sem(100), sem(100), sem(105)])).toBe("estavel");
  expect(tendenciaDaSerie([sem(100), sem(100), sem(100), sem(150)])).toBeNull();
});
