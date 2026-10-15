import type { ReactNode } from "react";
import * as Tabs from "@radix-ui/react-tabs";
import estilos from "./Abas.module.css";

export interface ItemAba {
  valor: string;
  rotulo: string;
  contagem?: number;
  conteudo: ReactNode;
}

export function Abas({
  itens,
  valor,
  aoMudar,
  rotulo,
}: {
  itens: ItemAba[];
  valor?: string;
  aoMudar?: (v: string) => void;
  rotulo: string;
}) {
  return (
    <Tabs.Root value={valor} defaultValue={valor ? undefined : itens[0]?.valor} onValueChange={aoMudar}>
      <Tabs.List className={estilos.lista} aria-label={rotulo}>
        {itens.map((i) => (
          <Tabs.Trigger key={i.valor} value={i.valor} className={estilos.aba}>
            {i.rotulo}
            {i.contagem !== undefined && (
              <span className={estilos.contagem} aria-label={`${i.contagem} itens`}>
                {i.contagem}
              </span>
            )}
          </Tabs.Trigger>
        ))}
      </Tabs.List>
      {itens.map((i) => (
        <Tabs.Content key={i.valor} value={i.valor}>
          {i.conteudo}
        </Tabs.Content>
      ))}
    </Tabs.Root>
  );
}
