import type { ReactNode } from "react";
import { BadgeCheck, ClipboardList, KeyRound, Megaphone } from "lucide-react";
import { Pilula } from "@/design-system/componentes/Pilula";
import { PAPEIS } from "@/textos/glossario";

export const ICONE_PAPEL: Record<string, ReactNode> = {
  analista: <ClipboardList />,
  revisor: <BadgeCheck />,
  coordenacao: <Megaphone />,
  administrador: <KeyRound />,
};

/** Papel como chip com ícone e nome. */
export function PapelPilula({ papel }: { papel: string }) {
  return (
    <Pilula tom="marca" icone={ICONE_PAPEL[papel]} pequena>
      {PAPEIS[papel] ?? papel}
    </Pilula>
  );
}

/** Iniciais para o avatar: “Ana Souza” vira “AS”. */
export function iniciais(nome: string) {
  const p = nome.trim().split(/\s+/);
  return ((p[0]?.[0] ?? "") + (p.length > 1 ? (p[p.length - 1][0] ?? "") : "")).toUpperCase();
}
