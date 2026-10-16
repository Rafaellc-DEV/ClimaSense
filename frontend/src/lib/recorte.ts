/**
 * Recorte global de território e período (RF-05), guardado na URL: `?territorio=&inicio=&fim=`.
 * Vale para todas as telas analíticas, sobrevive à troca de tela (o menu leva os parâmetros) e ao recarregar.
 */
import { useCallback, useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import { diaNoRecife, somarDias } from "./formatos";

export interface Recorte {
  territorio: string;
  inicio: string;
  fim: string;
}

export const CHAVES_RECORTE = ["territorio", "inicio", "fim"] as const;

export function recortePadrao(hoje = diaNoRecife()): Recorte {
  return { territorio: "recife", inicio: `${hoje.slice(0, 4)}-01-01`, fim: hoje };
}

export interface Predefinicao {
  rotulo: string;
  periodo: (hoje: string) => { inicio: string; fim: string };
}

export const PREDEFINICOES: Predefinicao[] = [
  { rotulo: "Últimos 7 dias", periodo: (h) => ({ inicio: somarDias(h, -6), fim: h }) },
  { rotulo: "Últimos 30 dias", periodo: (h) => ({ inicio: somarDias(h, -29), fim: h }) },
  { rotulo: "Este ano", periodo: (h) => ({ inicio: `${h.slice(0, 4)}-01-01`, fim: h }) },
  { rotulo: "Últimos 12 meses", periodo: (h) => ({ inicio: somarDias(h, -364), fim: h }) },
];

const DATA = /^\d{4}-\d{2}-\d{2}$/;

export function lerRecorte(p: URLSearchParams, hoje = diaNoRecife()): Recorte {
  const padrao = recortePadrao(hoje);
  const inicio = p.get("inicio");
  const fim = p.get("fim");
  const r = {
    territorio: p.get("territorio") || padrao.territorio,
    inicio: inicio && DATA.test(inicio) ? inicio : padrao.inicio,
    fim: fim && DATA.test(fim) ? fim : padrao.fim,
  };
  return r.inicio > r.fim ? { ...r, inicio: r.fim } : r;
}

/** Só os parâmetros do recorte, para levar de uma tela para outra. */
export function buscaDoRecorte(p: URLSearchParams): string {
  const s = new URLSearchParams();
  for (const k of CHAVES_RECORTE) {
    const v = p.get(k);
    if (v) s.set(k, v);
  }
  const t = s.toString();
  return t ? `?${t}` : "";
}

export function useRecorte() {
  const [params, setParams] = useSearchParams();
  const recorte = useMemo(() => lerRecorte(params), [params]);
  const mudar = useCallback(
    (novo: Partial<Recorte>) =>
      setParams(
        (atual) => {
          const p = new URLSearchParams(atual);
          for (const [k, v] of Object.entries(novo)) if (v) p.set(k, v);
          return p;
        },
        { replace: false },
      ),
    [setParams],
  );
  return { recorte, mudar };
}
