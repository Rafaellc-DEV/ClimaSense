import type { ReactNode } from "react";
import { RotateCcw } from "lucide-react";
import { Botao } from "@/design-system/componentes/Botao";
import { Campo } from "@/design-system/componentes/Campo";
import { TextoFonte, fontesDado } from "@/design-system/componentes/EstadoDados";
import { Segmentado } from "@/design-system/componentes/Segmentado";
import { formatarNumero } from "@/lib/formatos";
import type { FonteMeta } from "@/lib/frescor";
import {
  erroDoCampo,
  HORIZONTES,
  type CampoNumerico,
  type Formulario,
  type Premissas as TipoPremissas,
} from "./tipos";
import estilos from "./Simulador.module.css";

interface Def {
  campo: CampoNumerico;
  rotulo: string;
  unidade: string;
  casas: number;
  grupo: "chuva" | "mare" | "abrigos";
}

const CAMPOS: Def[] = [
  { campo: "chuva_prevista_mm", rotulo: "Chuva prevista (mm)", unidade: "mm", casas: 1, grupo: "chuva" },
  { campo: "duracao_h", rotulo: "Duração da chuva (h)", unidade: "h", casas: 1, grupo: "chuva" },
  {
    campo: "chuva_acumulada_mm",
    rotulo: "Chuva dos dias anteriores (mm)",
    unidade: "mm",
    casas: 1,
    grupo: "chuva",
  },
  { campo: "mare_m", rotulo: "Maré (m)", unidade: "m", casas: 1, grupo: "mare" },
  { campo: "abrigos_abertos", rotulo: "Abrigos abertos", unidade: "", casas: 0, grupo: "abrigos" },
  { campo: "capacidade_abrigos", rotulo: "Capacidade dos abrigos", unidade: "", casas: 0, grupo: "abrigos" },
];

const PADRAO_GRUPO: Record<Def["grupo"], RegExp> = {
  abrigos: /abrigo/i,
  mare: /mar[eé]|t[aá]bua/i,
  chuva: /chuva|previs|open-?meteo|apac|cemaden|pluvi|boletim/i,
};

/** A API entrega as fontes juntas; o campo mostra as que combinam com ele e, se nenhuma combinar, todas (nunca esconde a origem). */
export function fontesDoGrupo(grupo: Def["grupo"], fontes: FonteMeta[]): FonteMeta[] {
  const dele = fontes.filter((f) => PADRAO_GRUPO[grupo].test(`${f.id} ${f.nome}`));
  return dele.length ? dele : fontes;
}

function Fonte({ grupo, fontes }: { grupo: Def["grupo"]; fontes: FonteMeta[] }) {
  const lista = fontesDado(fontesDoGrupo(grupo, fontes));
  return (
    <>
      {lista.map((f, i) => (
        <span key={`${f.nome}-${i}`} className={estilos.fonteCampo}>
          {i > 0 ? "; " : ""}
          Fonte: <TextoFonte f={f} />
        </span>
      ))}
    </>
  );
}

export function PainelPremissas({
  form,
  atuais,
  fontes,
  carregando,
  indisponivel,
  alterado,
  aoMudar,
  aoHorizonte,
  aoVoltar,
}: {
  form: Formulario;
  atuais: Partial<TipoPremissas> | undefined;
  fontes: FonteMeta[];
  carregando: boolean;
  indisponivel: boolean;
  alterado: boolean;
  aoMudar: (campo: CampoNumerico, valor: string) => void;
  aoHorizonte: (h: number) => void;
  aoVoltar: () => void;
}) {
  const dica = (d: Def): ReactNode => {
    if (carregando) return "Buscando o valor atual…";
    if (indisponivel)
      return "Valores atuais ainda não disponíveis. Digite o valor se quiser simular este campo.";
    const atual = atuais?.[d.campo];
    if (atual === null || atual === undefined)
      return (
        <>
          <b>Sem dado da fonte.</b> <Fonte grupo={d.grupo} fontes={fontes} /> Digite o valor para simular.
        </>
      );
    const igual = form[d.campo] === String(atual).replace(".", ",");
    return (
      <>
        {igual ? "Valor atual" : `Alterado. Valor atual: ${formatarNumero(atual, d.casas)} ${d.unidade}.`}{" "}
        <Fonte grupo={d.grupo} fontes={fontes} />
      </>
    );
  };

  return (
    <section className={estilos.premissas} aria-labelledby="sim-premissas">
      <div className={estilos.premissasTopo}>
        <h2 id="sim-premissas">Premissas do cenário</h2>
        <Botao variante="discreto" icone={<RotateCcw size={18} />} onClick={aoVoltar} disabled={!alterado}>
          Voltar aos valores atuais
        </Botao>
      </div>
      <div className={estilos.campos}>
        {CAMPOS.map((d) => (
          <Campo
            key={d.campo}
            rotulo={d.rotulo}
            inputMode="decimal"
            autoComplete="off"
            value={form[d.campo]}
            placeholder="sem dado"
            onChange={(e) => aoMudar(d.campo, e.target.value)}
            erro={erroDoCampo(d.campo, form[d.campo])}
            ajuda={dica(d)}
          />
        ))}
      </div>
      <Segmentado
        rotulo="Horizonte do cenário: próximas horas"
        opcoes={HORIZONTES.map((h) => ({ valor: h, rotulo: `${h} h` }))}
        valor={form.horizonte_h}
        aoMudar={aoHorizonte}
      />
    </section>
  );
}
