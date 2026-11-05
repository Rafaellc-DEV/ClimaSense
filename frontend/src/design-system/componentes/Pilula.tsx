import type { ReactNode } from "react";
import { FlaskConical } from "lucide-react";
import type { ChaveNivel } from "../niveis";
import estilos from "./Pilula.module.css";

export type TomPilula =
  | "neutro"
  | "marca"
  | "sucesso"
  | "info"
  | "atencao"
  | "alerta"
  | "critico"
  | "insuficiente";

/** Cada nível de aviso tem o tom de mesmo nome; assim a pílula e o SeloNivel usam as mesmas cores. */
const TOM_DO_NIVEL: Record<ChaveNivel, TomPilula> = {
  sem: "sucesso",
  informativo: "info",
  atencao: "atencao",
  alerta: "alerta",
  critico: "critico",
  insuficiente: "insuficiente",
};

export interface PilulaProps {
  /** Tom semântico. Ignorado quando `nivel` é informado. */
  tom?: TomPilula;
  /** Atalho: usa as cores do nível de aviso (mesmas do SeloNivel). O texto é sempre escrito (RN-17). */
  nivel?: ChaveNivel;
  /** Ícone decorativo à esquerda; sem ele, aparece um ponto colorido. */
  icone?: ReactNode;
  /** Sem ponto nem ícone. */
  semMarca?: boolean;
  pequena?: boolean;
  /** Para fundo de azul profundo (FaixaMare): vidro claro com texto branco. Não vale para `nivel`. */
  sobreMare?: boolean;
  children: ReactNode;
  className?: string;
}

/**
 * Chip de estado ou categoria: "Em revisão", "Atenção", "Confiança alta". Formato pílula, texto sempre visível.
 * Para o nível de aviso de um território, prefira `<Pilula nivel="alerta">Alerta</Pilula>` ou `SeloNivel` com régua.
 */
export function Pilula({
  tom = "neutro",
  nivel,
  icone,
  semMarca,
  pequena,
  sobreMare,
  children,
  className,
}: PilulaProps) {
  const t = nivel ? TOM_DO_NIVEL[nivel] : tom;
  return (
    <span
      className={[
        estilos.pilula,
        estilos[t],
        pequena && estilos.pequena,
        sobreMare && !nivel && estilos.sobreMare,
        className,
      ]
        .filter(Boolean)
        .join(" ")}
      data-tom={t}
    >
      {icone ? (
        <span className={estilos.icone} aria-hidden="true">
          {icone}
        </span>
      ) : (
        !semMarca && <i className={estilos.ponto} aria-hidden="true" />
      )}
      {children}
    </span>
  );
}

/** Selo fino “Experimental”: toda estimativa do estimador de referência leva este selo (RN-06). */
export function Experimental({ sobreMare, className }: { sobreMare?: boolean; className?: string }) {
  return (
    <Pilula tom="marca" pequena sobreMare={sobreMare} icone={<FlaskConical />} className={className}>
      Experimental
    </Pilula>
  );
}
