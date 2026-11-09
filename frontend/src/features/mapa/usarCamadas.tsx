/**
 * Camadas do mapa (RF-02, RF-03, RF-04, RF-26): controle com caixas de seleção, legenda e fonte com hora de cada
 * camada ligada (RF-19). Usado no Mapa e no Simulador. Só a camada ligada é pedida à API.
 */
import { useMemo, useState } from "react";
import { useTemaAtual } from "@/charts/tema";
import { fontesDado, type FonteDado } from "@/design-system/componentes/EstadoDados";
import { ErroApi } from "@/lib/api";
import { INTERVALO, useConsultaViva } from "@/lib/consultas";
import { fontesDe } from "@/lib/frescor";
import type { AparenciaPopulacao, TipoPino } from "@/map/MapaBairros";
import {
  CAMINHO_CAMADA,
  FONTE_PADRAO,
  cortes,
  faixaDe,
  faltaDe,
  featuresDe,
  itensVulneraveis,
  metaDe,
  rotulosFaixas,
  tipoEquipamento,
  valorDe,
  type CoberturaRisco,
  type IdCamada,
  type Indicador,
  type PropsAreaRisco,
  type PropsEquipamento,
  type ValorPopulacao,
} from "./modeloCamadas";

type Ligadas = Record<IdCamada, boolean>;
type Dependentes = Exclude<IdCamada, "base">;

export type EstadoCamada =
  | { tipo: "desligada" }
  | { tipo: "carregando" }
  | { tipo: "indisponivel" }
  | { tipo: "erro"; erro: Error }
  | { tipo: "insuficiente"; falta: string }
  | { tipo: "ok" };

/** Faixas de cor da população, da menor para a maior contagem. */
export const TOKENS_POPULACAO = ["--g-seq-2", "--g-seq-3", "--g-seq-4", "--g-seq-6", "--g-seq-7"];

const FALTA_PADRAO: Record<Dependentes, string> = {
  equipamentos: "CNES",
  populacao: "IBGE, Censo 2022",
  areas: "Defesa Civil do Recife (áreas de risco)",
};

/** Cor (token) do tipo de área: deslizamento e alagamento têm cor fixa, os outros tipos recebem as demais. */
export function tokenTipoRisco(tipo: string): string {
  const t = tipo.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
  if (t.includes("desliz") || t.includes("encosta") || t.includes("morro")) return "--g-2";
  if (t.includes("alag") || t.includes("inunda") || t.includes("enchente")) return "--g-1";
  return "--g-4";
}

function estadoDe(
  ligada: boolean,
  q: { isPending: boolean; isError: boolean; error: Error | null; data: unknown },
  vazio: boolean,
  camada: Dependentes,
): EstadoCamada {
  if (!ligada) return { tipo: "desligada" };
  if (q.isError && !q.data) {
    if (q.error instanceof ErroApi && q.error.status === 404) return { tipo: "indisponivel" };
    return { tipo: "erro", erro: q.error ?? new Error("Falha ao carregar a camada.") };
  }
  if (q.isPending) return { tipo: "carregando" };
  const falta = faltaDe(q.data);
  if (falta !== null) return { tipo: "insuficiente", falta: falta || FALTA_PADRAO[camada] };
  if (vazio) return { tipo: "insuficiente", falta: FALTA_PADRAO[camada] };
  return { tipo: "ok" };
}

export interface FonteCamada {
  fontes: FonteDado[];
  padrao: string;
  consultadoEm: number;
}

export function useCamadas() {
  useTemaAtual();
  const [ligadas, setLigadas] = useState<Ligadas>({
    base: true,
    populacao: false,
    areas: false,
    equipamentos: false,
  });
  const [indicador, setIndicador] = useState<Indicador>("idosos_60_mais");

  /** População e estágio disputam a cor do bairro: ligar um desliga o outro. */
  const alternar = (id: IdCamada) =>
    setLigadas((l) => {
      const n = { ...l, [id]: !l[id] };
      if (id === "populacao" && n.populacao) n.base = false;
      if (id === "base" && n.base) n.populacao = false;
      return n;
    });

  const eq = useConsultaViva<unknown>(
    ligadas.equipamentos ? CAMINHO_CAMADA.equipamentos : null,
    INTERVALO.saude,
  );
  const vul = useConsultaViva<unknown>(ligadas.populacao ? CAMINHO_CAMADA.populacao : null, INTERVALO.saude);
  const ar = useConsultaViva<unknown>(ligadas.areas ? CAMINHO_CAMADA.areas : null, INTERVALO.saude);

  const featEq = useMemo(() => featuresDe<PropsEquipamento>(eq.data), [eq.data]);
  const featAr = useMemo(() => featuresDe<PropsAreaRisco>(ar.data), [ar.data]);
  const itensVul = useMemo(() => itensVulneraveis(vul.data), [vul.data]);

  const estados: Record<Dependentes, EstadoCamada> = {
    equipamentos: estadoDe(ligadas.equipamentos, eq, featEq.length === 0 && !!eq.data, "equipamentos"),
    populacao: estadoDe(ligadas.populacao, vul, itensVul.length === 0 && !!vul.data, "populacao"),
    areas: estadoDe(ligadas.areas, ar, featAr.length === 0 && !!ar.data, "areas"),
  };
  const consultas = { equipamentos: eq, populacao: vul, areas: ar };
  const fontes = Object.fromEntries(
    (Object.keys(consultas) as Dependentes[]).map((k) => [
      k,
      {
        fontes: fontesDado(fontesDe(consultas[k].data)),
        padrao: FONTE_PADRAO[k],
        consultadoEm: consultas[k].dataUpdatedAt,
      },
    ]),
  ) as Record<Dependentes, FonteCamada>;

  // população
  const porBairro = useMemo(() => new Map(itensVul.map((i) => [i.bairro_id, i] as const)), [itensVul]);
  const valores = useMemo(
    () =>
      itensVul
        .map((i) => valorDe(i, indicador))
        .filter((v): v is ValorPopulacao => v.valor !== null && !v.suprimido),
    [itensVul, indicador],
  );
  const cortesPop = useMemo(
    () =>
      cortes(
        valores.map((v) => v.valor as number),
        TOKENS_POPULACAO.length,
      ),
    [valores],
  );
  const minimoPop = valores.length ? Math.min(...valores.map((v) => v.valor as number)) : 0;
  const populacaoOk = estados.populacao.tipo === "ok";
  const aparenciaPopulacao = (id: string): AparenciaPopulacao => {
    const v = valorDe(porBairro.get(id), indicador);
    if (v.suprimido) return { classe: null, suprimido: true };
    return { classe: v.valor === null ? null : faixaDe(v.valor, cortesPop), suprimido: false };
  };

  const coberturaMeta = metaDe(ar.data).cobertura as CoberturaRisco | undefined;
  const tiposRisco = useMemo(
    () =>
      [...new Set(featAr.map((f) => String(f.properties?.tipo ?? "")))].sort((a, b) =>
        a.localeCompare(b, "pt-BR"),
      ),
    [featAr],
  );

  const modo: "estagio" | "populacao" | "nenhum" = ligadas.populacao
    ? populacaoOk
      ? "populacao"
      : "nenhum"
    : ligadas.base
      ? "estagio"
      : "nenhum";

  // identidade estável: o mapa só redesenha a camada quando o dado muda
  const colecaoAreas = useMemo(
    () => (estados.areas.tipo === "ok" ? { colecao: comoColecao(featAr), cor: tokenTipoRisco } : null),
    [featAr, estados.areas.tipo],
  );
  const colecaoEquip = useMemo(
    () =>
      estados.equipamentos.tipo === "ok"
        ? {
            colecao: comoColecao(featEq),
            tipo: (p: Record<string, unknown>): TipoPino => tipoEquipamento(p.tipo as string | undefined),
          }
        : null,
    [featEq, estados.equipamentos.tipo],
  );

  const propsMapa = {
    modo,
    populacao: aparenciaPopulacao,
    tokensPopulacao: TOKENS_POPULACAO,
    areasRisco: colecaoAreas,
    equipamentos: colecaoEquip,
  };

  return {
    ligadas,
    alternar,
    indicador,
    setIndicador,
    estados,
    fontes,
    propsMapa,
    populacao: {
      cortes: cortesPop,
      rotulos: rotulosFaixas(cortesPop, minimoPop),
      meta: metaDe(vul.data),
      porBairro,
      itens: itensVul,
    },
    risco: { tipos: tiposRisco, cobertura: coberturaMeta ?? null, total: featAr.length },
    totais: { equipamentos: featEq.length, areas: featAr.length },
    tentar: {
      equipamentos: () => void eq.refetch(),
      populacao: () => void vul.refetch(),
      areas: () => void ar.refetch(),
    },
    modo,
  };
}
export type Camadas = ReturnType<typeof useCamadas>;

function comoColecao(f: unknown[]): GeoJSON.FeatureCollection {
  return { type: "FeatureCollection", features: f as GeoJSON.Feature[] };
}
