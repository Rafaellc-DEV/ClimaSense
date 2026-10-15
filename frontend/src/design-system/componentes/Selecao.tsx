import { useId } from "react";
import * as Select from "@radix-ui/react-select";
import { Check, ChevronDown } from "lucide-react";
import campo from "./Campo.module.css";
import estilos from "./Selecao.module.css";

export interface OpcaoSelecao {
  valor: string;
  rotulo: string;
}

export interface SelecaoProps {
  rotulo: string;
  opcoes: OpcaoSelecao[];
  valor: string;
  aoMudar: (valor: string) => void;
  ajuda?: string;
  rotuloOculto?: boolean;
}

export function Selecao({ rotulo, opcoes, valor, aoMudar, ajuda, rotuloOculto }: SelecaoProps) {
  const id = useId();
  return (
    <div className={campo.campo}>
      <label id={`${id}-rotulo`} htmlFor={id} className={rotuloOculto ? "so-leitor" : campo.rotulo}>
        {rotulo}
      </label>
      <Select.Root value={valor} onValueChange={aoMudar}>
        <Select.Trigger id={id} className={estilos.gatilho} aria-labelledby={`${id}-rotulo`}>
          <Select.Value />
          <Select.Icon>
            <ChevronDown size={20} aria-hidden="true" />
          </Select.Icon>
        </Select.Trigger>
        <Select.Portal>
          <Select.Content className={estilos.conteudo} position="popper" sideOffset={4}>
            <Select.Viewport>
              {opcoes.map((o) => (
                <Select.Item key={o.valor} value={o.valor} className={estilos.item}>
                  <Select.ItemText>{o.rotulo}</Select.ItemText>
                  <Select.ItemIndicator>
                    <Check size={18} aria-hidden="true" />
                  </Select.ItemIndicator>
                </Select.Item>
              ))}
            </Select.Viewport>
          </Select.Content>
        </Select.Portal>
      </Select.Root>
      {ajuda && <p className={campo.ajuda}>{ajuda}</p>}
    </div>
  );
}
