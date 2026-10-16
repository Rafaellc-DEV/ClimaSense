/**
 * CSV para planilhas brasileiras (RF-07.10, RF-08.8): BOM UTF-8, separador `;`, vírgula decimal e
 * proteção contra fórmulas (`= + - @` no início viram texto). `csvCell` é o porte do model.js original.
 */
import { csvCell } from "@/map/model";

export type ValorCsv = string | number | null | undefined;

export function celula(valor: ValorCsv): string {
  if (valor === null || valor === undefined) return csvCell("");
  if (typeof valor === "number") return csvCell(String(valor).replace(".", ","));
  return csvCell(valor);
}

export function montarCsv(linhas: ValorCsv[][]): string {
  return "﻿" + linhas.map((l) => l.map(celula).join(";")).join("\r\n");
}

export function baixarCsv(nomeArquivo: string, linhas: ValorCsv[][]): void {
  const blob = new Blob([montarCsv(linhas)], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = nomeArquivo;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
