import type { CSSProperties } from "react";
import { NIVEIS, type ChaveNivel } from "../niveis";
import estilos from "./BotoesNivel.module.css";

export interface OpcaoNivel {
  valor: string;
  rotulo: string;
  nivel: ChaveNivel;
  descricao?: string;
}

/**
 * Escolha de nível ou prioridade como 4 botões-régua (design §8.8): a mesma linguagem da landing.
 * É um grupo de rádio de verdade (teclado com setas, um selecionado por vez).
 */
export function BotoesNivel({
  nome,
  legenda,
  opcoes,
  valor,
  aoMudar,
  desativado,
}: {
  nome: string;
  legenda: string;
  opcoes: OpcaoNivel[];
  valor: string;
  aoMudar: (v: string) => void;
  desativado?: boolean;
}) {
  return (
    <fieldset className={estilos.grupo} disabled={desativado}>
      <legend className={estilos.legenda}>{legenda}</legend>
      <div className={estilos.opcoes}>
        {opcoes.map((o) => {
          const n = NIVEIS[o.nivel];
          return (
            <label
              key={o.valor}
              className={estilos.opcao}
              style={{ "--cor": n.cor, "--fundo": n.fundo } as CSSProperties}
              data-marcado={valor === o.valor}
            >
              <input
                type="radio"
                name={nome}
                value={o.valor}
                checked={valor === o.valor}
                onChange={() => aoMudar(o.valor)}
              />
              <span className={estilos.regua} aria-hidden="true">
                {[4, 3, 2, 1].map((m) => (
                  <i key={m} data-cheio={m <= n.marcas} />
                ))}
              </span>
              <span className={estilos.texto}>
                <strong>{o.rotulo}</strong>
                {o.descricao && <span>{o.descricao}</span>}
              </span>
            </label>
          );
        })}
      </div>
    </fieldset>
  );
}

export const OPCOES_NIVEL_AVISO: OpcaoNivel[] = [
  { valor: "informativo", rotulo: "Fique atento", nivel: "informativo", descricao: "Orientação preventiva." },
  { valor: "atencao", rotulo: "Atenção", nivel: "atencao", descricao: "Pede cuidado na região." },
  { valor: "alerta", rotulo: "Alerta", nivel: "alerta", descricao: "Pede ação preventiva." },
  { valor: "critico", rotulo: "Situação crítica", nivel: "critico", descricao: "Siga a Defesa Civil já." },
];

export const OPCOES_PRIORIDADE: OpcaoNivel[] = [
  { valor: "sem_indicacao", rotulo: "Sem indicação", nivel: "sem", descricao: "Não pede ação agora." },
  { valor: "atencao", rotulo: "Atenção", nivel: "atencao", descricao: "Acompanhar de perto." },
  { valor: "alerta", rotulo: "Alerta", nivel: "alerta", descricao: "Preparar ação preventiva." },
  { valor: "critico", rotulo: "Situação crítica", nivel: "critico", descricao: "Agir e comunicar já." },
];
