/**
 * Leitura dos dados de decisão e dos indicadores derivados, com atualização automática (RF-10, RF-24). Serve ao
 * Dashboards (completo) e ao topo do Mapa (só o que os quatro números pedem). As consultas têm a mesma chave das telas
 * que já as usam: o cache evita pedir duas vezes.
 */
import { useMemo } from "react";
import { useQueries } from "@tanstack/react-query";
import { desembrulhar, limiaresDe, listaDe, type ItemEstagio } from "@/features/evento/tipos";
import type { ItemPrioridadeTerritorio } from "@/features/mapa/tipos";
import type { ResumoSaude } from "@/features/saude/tipos";
import { api, consulta } from "@/lib/api";
import { useConsultaViva, ultimaAtualizacao } from "@/lib/consultas";
import { juntarFontes } from "@/lib/frescor";
import {
  chuvaMedida,
  decisoesPendentes,
  gatilhos,
  maiorChuva,
  mediaDoMes,
  mesEAno,
  pessoasEmAlerta,
  type AcoesApi,
  type BairroVulneravel,
  type ImpactoApi,
  type Janela,
  type MaiorChuva,
  type SituacaoChuvaApi,
} from "./indicadores";

export function useDadosDecisao({
  janela,
  distritoId = null,
  completo = true,
}: {
  janela: Janela;
  distritoId?: string | null;
  /** `false` no Mapa: só estágios, prioridade, limiares, chuva e impacto. */
  completo?: boolean;
}) {
  const oficial = useConsultaViva<unknown>("/estagios/oficial");
  const distritos = useConsultaViva<unknown>(`/estagios${consulta({ nivel: "distrito" })}`);
  const bairros = useConsultaViva<unknown>(`/estagios${consulta({ nivel: "bairro" })}`);
  const prioridade = useConsultaViva<unknown>("/territorios/prioridade");
  const parametros = useConsultaViva<unknown>("/estagios/parametros", 5 * 60_000);
  const situacao = useConsultaViva<unknown>("/situacao/chuva");
  const impacto = useConsultaViva<unknown>(
    `/cenarios/impacto-previsto${consulta({ horizonte_h: janela })}`,
    5 * 60_000,
  );
  const acoes = useConsultaViva<unknown>("/acoes", 60_000, { enabled: completo });
  const saude = useConsultaViva<unknown>("/saude/resumo", 10 * 60_000, { enabled: completo });
  // moradores por bairro (Censo 2022, não muda): referência quando nenhum bairro está em Atenção
  const vulneraveis = useConsultaViva<unknown>("/territorios/camadas/vulneraveis", 30 * 60_000, {
    enabled: completo,
    staleTime: 30 * 60_000,
  });

  const itensDistrito = useMemo(() => listaDe<ItemEstagio>(distritos.data), [distritos.data]);
  const itensBairro = useMemo(() => listaDe<ItemEstagio>(bairros.data), [bairros.data]);
  const posicao = useMemo(
    () =>
      new Map(
        listaDe<ItemPrioridadeTerritorio>(prioridade.data).map((p) => [p.territorio_id, p.posicao] as const),
      ),
    [prioridade.data],
  );
  const limiares = useMemo(() => limiaresDe(parametros.data), [parametros.data]);
  const chuva = desembrulhar<SituacaoChuvaApi>(situacao.data);
  const dadosImpacto = desembrulhar<ImpactoApi>(impacto.data);
  const dadosAcoes = desembrulhar<AcoesApi>(acoes.data);
  const dadosSaude = desembrulhar<ResumoSaude>(saude.data);
  const bairrosVulneraveis = listaDe<BairroVulneravel>(vulneraveis.data);

  // referência do mês (reanálise ERA5) por distrito: muda devagar, fica em cache por horas (I-04)
  const refs = useQueries({
    queries: (completo ? itensDistrito : []).map((d) => {
      const caminho = `/series/referencia${consulta({ territorio_id: d.territorio_id })}`;
      return {
        queryKey: [caminho],
        queryFn: () => api<unknown>(caminho),
        staleTime: 6 * 3_600_000,
      };
    }),
  });
  const mediaMensal = useMemo(() => {
    const { mes } = mesEAno(new Date());
    return new Map(itensDistrito.map((d, i) => [d.territorio_id, mediaDoMes(refs[i]?.data, mes)] as const));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [itensDistrito, refs.map((r) => r.dataUpdatedAt).join(",")]);

  // escopo: Recife inteiro ou um distrito
  const distritosEscopo = useMemo(
    () => (distritoId ? itensDistrito.filter((d) => d.territorio_id === distritoId) : itensDistrito),
    [itensDistrito, distritoId],
  );
  const territoriosDecisao = useMemo(() => {
    const base = itensBairro.length > 0 ? itensBairro : itensDistrito;
    return distritoId
      ? base.filter((i) => (i.nivel === "bairro" ? i.distrito_id : i.territorio_id) === distritoId)
      : base;
  }, [itensBairro, itensDistrito, distritoId]);

  const semEstagios = distritos.isPending && bairros.isPending;
  const pendencias =
    semEstagios || (!distritos.data && !bairros.data) ? null : decisoesPendentes(territoriosDecisao, posicao);
  const gatilhosResumo = distritos.data ? gatilhos(distritosEscopo, limiares, janela) : null;
  const linhasChuva = useMemo(() => chuvaMedida(chuva, janela), [chuva, janela]);
  const maior: MaiorChuva | null = useMemo(() => {
    if (!distritoId) return maiorChuva(chuva, janela);
    const l = linhasChuva.find((x) => x.id === distritoId);
    return l && l.mm !== null ? { id: l.id, nome: l.nome, mm: l.mm, estacoes: l.estacoes } : null;
  }, [chuva, janela, distritoId, linhasChuva]);
  const pessoas = pessoasEmAlerta(dadosImpacto, distritoId);

  const fontes = useMemo(
    () => juntarFontes(distritos.data, situacao.data, impacto.data),
    [distritos.data, situacao.data, impacto.data],
  );
  const momento = ultimaAtualizacao(oficial, distritos, bairros, situacao, impacto);

  return {
    oficial,
    distritos,
    bairros,
    prioridade,
    parametros,
    situacao,
    impacto,
    acoes,
    saude,
    vulneraveis,
    bairrosVulneraveis,
    itensDistrito,
    itensBairro,
    distritosEscopo,
    posicao,
    limiares,
    chuva,
    dadosImpacto,
    dadosAcoes,
    dadosSaude,
    mediaMensal,
    pendencias,
    gatilhos: gatilhosResumo,
    linhasChuva,
    maior,
    pessoas,
    fontes,
    momento,
  };
}

export type DadosDecisao = ReturnType<typeof useDadosDecisao>;
