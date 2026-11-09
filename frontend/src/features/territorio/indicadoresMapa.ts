import type { ChaveNivel } from "@/design-system/niveis";
import type { Esquemas } from "@/lib/api";
import { formatarNumero } from "@/lib/formatos";

export type ChaveIndicador = "estagio" | "quantidade_bairros" | "area_km2" | "prioridade" | "ocorrencias";

export interface InfoIndicador {
  /** Nome curto, na pílula de “Colorir por”. */
  curto: string;
  /** Nome completo, no título da legenda. */
  rotulo: string;
  unidade: string;
  casas: number;
  ajuda: string;
  interpretar: string;
  fonte: string;
}

export const INDICADORES: Record<ChaveIndicador, InfoIndicador> = {
  estagio: {
    curto: "Situação",
    rotulo: "Situação por distrito",
    unidade: "",
    casas: 0,
    ajuda: "A cor é a situação declarada pela equipe; sem declaração, a sugerida pelo sistema.",
    interpretar:
      "Distrito hachurado está sem dados para sugerir: não quer dizer risco baixo. Confira o alerta oficial na APAC e no Cemaden.",
    fonte: "estagios",
  },
  quantidade_bairros: {
    curto: "Bairros",
    rotulo: "Quantidade de bairros",
    unidade: "bairros",
    casas: 0,
    ajuda: "Quanto mais quente a cor (do amarelo ao vermelho), maior o número de bairros.",
    interpretar:
      "As cores mostram quantos bairros cada distrito tem. Não representam população, risco nem a qualidade dos serviços de saúde.",
    fonte: "territorio-oficial",
  },
  area_km2: {
    curto: "Área",
    rotulo: "Área do distrito (km²)",
    unidade: "km²",
    casas: 1,
    ajuda: "Quanto mais quente a cor (do amarelo ao vermelho), maior a área do distrito.",
    interpretar:
      "As cores mostram a área geográfica, calculada a partir dos limites oficiais. A área não representa população nem demanda por serviços.",
    fonte: "territorio-oficial",
  },
  prioridade: {
    curto: "Prioridade",
    rotulo: "Prioridade do cenário de 72 h (experimental)",
    unidade: "",
    casas: 0,
    ajuda: "A cor é o nível indicado pela regra experimental para as próximas 72 horas.",
    interpretar:
      "Prioridade é uma indicação para a equipe avaliar, nunca a chance de alagar. A regra é experimental e não foi validada.",
    fonte: "open-meteo-previsao",
  },
  ocorrencias: {
    curto: "Ocorrências",
    rotulo: "Ocorrências de alagamento",
    unidade: "ocorrências",
    casas: 0,
    ajuda: "Contagem de ocorrências registradas pela Defesa Civil, quando a fonte estiver integrada.",
    interpretar: "Ocorrências registradas não são confirmadas por padrão e dependem de quem registrou.",
    fonte: "recife-alagamento",
  },
};

/** “Colorir por” em destaque; os outros ficam em “Mais camadas”. */
export const INDICADORES_PRINCIPAIS: ChaveIndicador[] = ["estagio", "prioridade", "ocorrencias"];
export const INDICADORES_SECUNDARIOS: ChaveIndicador[] = ["quantidade_bairros", "area_km2"];

/** Situação operacional como número 0 a 3 (observação a crítico); `sem_dados` não tem número (hachura). */
export const ROTULO_ESTAGIO = ["Observação", "Atenção", "Alerta", "Crítico"];
export const TOKEN_ESTAGIO = ["--n-info", "--n-atencao", "--n-alerta", "--n-critico"];

/** Valores 0 a 3 que a API devolve para “prioridade” em /territorios/indicadores. */
export const NIVEL_PRIORIDADE: ChaveNivel[] = ["sem", "atencao", "alerta", "critico"];
export const ROTULO_PRIORIDADE = ["Sem indicação", "Atenção", "Alerta", "Situação crítica"];
/** Mesmas cores dos níveis (tokens --n-*), lidas pelo mapa em tempo de execução para valer nos dois temas. */
export const TOKEN_PRIORIDADE = ["--n-sem", "--n-atencao", "--n-alerta", "--n-critico"];

export type ItemPrioridade = Esquemas["climasense__api__esquemas_decisao__ItemPrioridade"];

export const NIVEL_DA_API: Record<ItemPrioridade["nivel"], ChaveNivel> = {
  sem_indicacao: "sem",
  atencao: "atencao",
  alerta: "alerta",
  critico: "critico",
  dados_insuficientes: "insuficiente",
};

export function rotuloClasse(
  indicador: ChaveIndicador,
  low: number,
  high: number,
  ultima: boolean,
  casas: number,
) {
  if (indicador === "quantidade_bairros" || indicador === "ocorrencias") {
    const lo = Math.ceil(low),
      hi = ultima ? Math.floor(high) : Math.ceil(high) - 1;
    return lo >= hi ? formatarNumero(lo) : `${formatarNumero(lo)} a ${formatarNumero(hi)}`;
  }
  return `${formatarNumero(low, casas + 2)} a ${ultima ? "" : "menos de "}${formatarNumero(high, casas + 2)}`;
}
