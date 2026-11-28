import { useMemo } from "react";
import { useConsultaViva } from "./consultas";
import { estaVencida } from "./frescor";

/**
 * Fontes que saíram do produto (specs/foco-chuvas.md §2): a vacinação não foi pedida pelo cliente. Enquanto o
 * backend ainda listar a fonte, o front não a mostra em lugar nenhum.
 */
const FORA_DO_PRODUTO = new Set(["vacinacao"]);

export function noProduto<T extends { id?: string | null; fonte_id?: string | null }>(f: T) {
  return !FORA_DO_PRODUTO.has(f.id ?? f.fonte_id ?? "");
}

/**
 * Ids das fontes vencidas segundo `GET /fontes` (ADR 0019). Serve às telas que sabem de qual fonte vem cada dado,
 * mesmo antes de a resposta do dado chegar (ex.: esconder a camada do mapa). Enquanto `/fontes` não responde, o
 * conjunto fica vazio e a resposta de cada dado (`meta.fontes`) continua valendo.
 */
export function useFontesVencidas(): ReadonlySet<string> {
  const r = useConsultaViva<{ id: string; desatualizado?: boolean | null }[]>("/fontes");
  return useMemo(
    () => new Set((Array.isArray(r.data) ? r.data : []).filter(estaVencida).map((f) => f.id)),
    [r.data],
  );
}
