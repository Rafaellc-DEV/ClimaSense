import { CircleCheck, CircleDashed, Clock, TriangleAlert } from "lucide-react";
import estilos from "./Fontes.module.css";

export type Status = "atualizada" | "desatualizada" | "com_falha" | "planejada";

export const STATUS: Record<Status, { rotulo: string; icone: JSX.Element }> = {
  atualizada: { rotulo: "Atualizada", icone: <CircleCheck aria-hidden="true" size={20} /> },
  desatualizada: { rotulo: "Desatualizada", icone: <Clock aria-hidden="true" size={20} /> },
  com_falha: { rotulo: "Com falha", icone: <TriangleAlert aria-hidden="true" size={20} /> },
  planejada: { rotulo: "Planejada", icone: <CircleDashed aria-hidden="true" size={20} /> },
};

/** Status da fonte sempre com texto, ícone e cor (RF-06.2). */
export function StatusFonte({ status }: { status: string }) {
  const s = STATUS[status as Status] ?? STATUS.planejada;
  return (
    <span className={estilos.status} data-status={status}>
      {s.icone}
      {s.rotulo}
    </span>
  );
}
