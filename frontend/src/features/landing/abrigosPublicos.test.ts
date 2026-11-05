import {
  abertoConfirmado,
  distanciaKm,
  filtrar,
  formatarDistancia,
  linkComoChegar,
  maisPertoDe,
  pertoDoBairro,
  type AbrigoPublico,
} from "./abrigosPublicos";

const local = (p: Partial<AbrigoPublico> & { id: string; nome: string }): AbrigoPublico => ({
  endereco: "Rua do Canal, 10",
  bairro_nome: "Várzea",
  distrito_nome: "Distrito Sanitário IV",
  latitude: -8.04,
  longitude: -34.95,
  aberto: null,
  tipo: "abrigo_temporario",
  ...p,
});

test("aberto exige true; rota cai para o endereço; sem nada, sem link", () => {
  expect(abertoConfirmado(local({ id: "1", nome: "x", aberto: null }))).toBe(false);
  expect(abertoConfirmado(local({ id: "1", nome: "x", aberto: false }))).toBe(false);
  expect(linkComoChegar(local({ id: "1", nome: "x", latitude: null }))).toContain(
    encodeURIComponent("Rua do Canal, 10"),
  );
  expect(linkComoChegar(local({ id: "1", nome: "x", latitude: null, endereco: null }))).toBeNull();
  expect(filtrar([local({ id: "1", nome: "x", tipo: "cras" })], "abrigos", false)).toHaveLength(0);
});

test("distância em linha reta (haversine) e formato", () => {
  expect(distanciaKm({ lat: -8, lon: -35 }, { lat: -8, lon: -35 })).toBe(0);
  // 0,01 grau de latitude ≈ 1,11 km
  expect(distanciaKm({ lat: -8, lon: -35 }, { lat: -8.01, lon: -35 })).toBeCloseTo(1.11, 1);
  expect(formatarDistancia(0.45)).toBe("450 m");
  expect(formatarDistancia(1.234)).toBe("1,2 km");
});

test("mais perto de um ponto: ignora CRAS e locais sem coordenada, sem inventar distância", () => {
  const r = maisPertoDe(
    [
      local({ id: "longe", nome: "Longe", latitude: -8.1, longitude: -34.9 }),
      local({ id: "perto", nome: "Perto", latitude: -8.041, longitude: -34.95 }),
      local({ id: "cras", nome: "CRAS", tipo: "cras", latitude: -8.04, longitude: -34.95 }),
      local({ id: "sem", nome: "Sem ponto", latitude: null, longitude: null }),
    ],
    { lat: -8.04, lon: -34.95 },
  );
  expect(r.map((x) => x.abrigo.id)).toEqual(["perto", "longe"]);
});

test("perto do bairro: mesmo bairro, depois mesmo distrito, depois o resto; aberto primeiro no grupo; sem CRAS", () => {
  const itens = [
    local({ id: "outro", nome: "Outro", bairro_nome: "Ibura", distrito_nome: "Distrito Sanitário IX" }),
    local({
      id: "dist",
      nome: "Mesmo distrito",
      bairro_nome: "Mustardinha",
      distrito_nome: "Distrito Sanitário V",
    }),
    local({ id: "b1", nome: "B fechado", bairro_nome: "Afogados", distrito_nome: "Distrito Sanitário V" }),
    local({
      id: "b2",
      nome: "B aberto",
      bairro_nome: "Afogados",
      distrito_nome: "Distrito Sanitário V",
      aberto: true,
    }),
    local({ id: "cras", nome: "CRAS", bairro_nome: "Afogados", tipo: "cras" }),
  ];
  const r = pertoDoBairro(itens, "afogados", "Distrito Sanitário V");
  expect(r.map((x) => x.abrigo.id)).toEqual(["b2", "b1", "dist", "outro"]);
  expect(r.map((x) => x.grupo)).toEqual(["bairro", "bairro", "distrito", "outro"]);
});
