import type { ReactNode } from "react";
import { RotateCcw } from "lucide-react";
import { Botao } from "@/design-system/componentes/Botao";
import { Campo } from "@/design-system/componentes/Campo";
import { SeloDesatualizado, fontesDado } from "@/design-system/componentes/EstadoDados";
import { Segmentado } from "@/design-system/componentes/Segmentado";
import { formatarNumero } from "@/lib/formatos";
import { formatarHoraMinuto } from "@/lib/formatos";
import { haQuanto, type FonteMeta } from "@/lib/frescor";
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
}

const CAMPOS: Def[] = [
  { campo: "chuva_prevista_mm", rotulo: "Chuva prevista (mm)", unidade: "mm", casas: 1 },
  { campo: "duracao_h", rotulo: "Duração da chuva (h)", unidade: "h", casas: 1 },
  {
    campo: "chuva_acumulada_mm",
    rotulo: "Chuva dos dias anteriores (mm)",
    unidade: "mm",
    casas: 1,
  },
  { campo: "mare_m", rotulo: "Maré (m)", unidade: "m", casas: 1 },
  { campo: "abrigos_abertos", rotulo: "Abrigos abertos", unidade: "", casas: 0 },
  { campo: "capacidade_abrigos", rotulo: "Capacidade dos abrigos", unidade: "", casas: 0 },
];

/** Fonte de cada premissa quando a API não manda `meta.fonte_por_premissa`. */
export const FONTE_PADRAO: Record<CampoNumerico, string> = {
  chuva_prevista_mm: "open-meteo-previsao",
  duracao_h: "open-meteo-previsao",
  chuva_acumulada_mm: "apac-chuva",
  mare_m: "open-meteo-mare",
  abrigos_abertos: "recife-abrigos",
  capacidade_abrigos: "recife-abrigos",
};

/** Acha a única fonte do campo: pelo mapa da API, ou pelo padrão fixo. Nunca devolve a lista inteira. */
export function fonteDoCampo(
  campo: CampoNumerico,
  fontes: FonteMeta[],
  mapa?: Partial<Record<CampoNumerico, string>> | null,
): FonteMeta | undefined {
  const id = mapa?.[campo] ?? FONTE_PADRAO[campo];
  return fontes.find((f) => f.id === id);
}

function Fonte({ f }: { f: FonteMeta | undefined }) {
  if (!f) return <span className={estilos.fonteCampo}>Fonte sem informação de hora</span>;
  const d = fontesDado([f])[0];
  const completo = d.atualizadoEm
    ? `${f.nome}, atualizado ${haQuanto(d.atualizadoEm)} (${formatarHoraMinuto(d.atualizadoEm)})`
    : `${f.nome}: sem hora de atualização`;
  return (
    <span className={estilos.fonteCampo} title={completo}>
      {f.nome} · {d.atualizadoEm ? haQuanto(d.atualizadoEm) : "sem hora"}
      {d.desatualizado === true && (
        <>
          {" · "}
          <SeloDesatualizado />
        </>
      )}
    </span>
  );
}

export function PainelPremissas({
  form,
  atuais,
  fontes,
  fontePorPremissa,
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
  fontePorPremissa?: Partial<Record<CampoNumerico, string>> | null;
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
          <b>Sem dado da fonte:</b> deixe vazio ou digite um valor.{" "}
          <Fonte f={fonteDoCampo(d.campo, fontes, fontePorPremissa)} />
        </>
      );
    const igual = form[d.campo] === String(atual).replace(".", ",");
    return (
      <>
        {igual ? "Valor atual" : `Alterado. Valor atual: ${formatarNumero(atual, d.casas)} ${d.unidade}.`}{" "}
        <Fonte f={fonteDoCampo(d.campo, fontes, fontePorPremissa)} />
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
