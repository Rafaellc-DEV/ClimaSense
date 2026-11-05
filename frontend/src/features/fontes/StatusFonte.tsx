import type { ReactNode } from "react";
import { CircleCheck, CircleDashed, Clock, TriangleAlert } from "lucide-react";
import { Pilula, type TomPilula } from "@/design-system/componentes/Pilula";
import { formatarDataHora } from "@/lib/formatos";
import estilos from "./Fontes.module.css";

export type Status = "atualizada" | "desatualizada" | "com_falha" | "planejada";

export const STATUS: Record<Status, { rotulo: string; tom: TomPilula; icone: ReactNode }> = {
  atualizada: { rotulo: "Atualizada", tom: "sucesso", icone: <CircleCheck /> },
  desatualizada: { rotulo: "Desatualizada", tom: "atencao", icone: <Clock /> },
  com_falha: { rotulo: "Com falha", tom: "alerta", icone: <TriangleAlert /> },
  planejada: { rotulo: "Planejada", tom: "neutro", icone: <CircleDashed /> },
};

/** Status da fonte sempre com texto, ícone e cor (RF-06.2). */
export function StatusFonte({ status }: { status: string }) {
  const s = STATUS[status as Status] ?? STATUS.planejada;
  return (
    <Pilula tom={s.tom} icone={s.icone}>
      {s.rotulo}
    </Pilula>
  );
}

/** “3 h”, “2 dias”: idade do último dado, em palavras curtas. */
export function idadeTexto(horas: number) {
  if (horas < 1) return "menos de 1 h";
  if (horas < 48) return `${Math.floor(horas)} h`;
  return `${Math.floor(horas / 24)} dias`;
}

/** Limite de tempo sem carga nova (“1 dia”, “30 dias”, “1 ano”). */
export function limiteTexto(horas: number) {
  if (horas % (24 * 365) === 0) return `${horas / (24 * 365)} ano${horas > 24 * 365 ? "s" : ""}`;
  if (horas % 24 === 0) return `${horas / 24} dia${horas > 24 ? "s" : ""}`;
  return `${horas} h`;
}

/**
 * Frescor num relance: uma barra que enche conforme o último dado se aproxima do limite, e o tempo em palavras.
 * Sem carga nunca vira “em dia”: mostra “Nunca carregada”.
 */
export function Frescor({
  ultima,
  limiteH,
  status,
  grande,
}: {
  ultima: string | null;
  limiteH: number;
  status: string;
  grande?: boolean;
}) {
  if (!ultima || status === "planejada")
    return (
      <span className={estilos.semCarga}>{status === "planejada" ? "Sem conector" : "Nunca carregada"}</span>
    );
  const idade = Math.max(0, (Date.now() - new Date(ultima).getTime()) / 3_600_000);
  const razao = Math.min(1, idade / limiteH);
  const tom =
    status === "com_falha"
      ? "falha"
      : razao >= 1 || status === "desatualizada"
        ? "velha"
        : razao > 0.7
          ? "perto"
          : "ok";
  return (
    <span className={estilos.frescor} data-tom={tom} data-grande={grande} title={formatarDataHora(ultima)}>
      <span className={estilos.trilho} aria-hidden="true">
        <i style={{ width: `${Math.max(6, razao * 100)}%` }} />
      </span>
      <span>
        há {idadeTexto(idade)}
        <small>, limite {limiteTexto(limiteH)}</small>
      </span>
    </span>
  );
}
