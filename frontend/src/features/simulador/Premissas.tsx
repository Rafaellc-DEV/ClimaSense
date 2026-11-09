import { useId, type ReactNode } from "react";
import { Botao } from "@/design-system/componentes/Botao";
import campo from "@/design-system/componentes/Campo.module.css";
import { Segmentado } from "@/design-system/componentes/Segmentado";
import { quandoAs } from "@/features/evento/textos";
import { formatarNumero } from "@/lib/formatos";
import type { FonteMeta } from "@/lib/frescor";
import { cenariosProntos, textoCenario, type CenarioPronto } from "./cenarios";
import {
  DURACOES,
  erroDoCampo,
  HORIZONTES,
  lerNumero,
  type CampoNumerico,
  type Formulario,
  type Premissas as TipoPremissas,
} from "./tipos";
import estilos from "./Simulador.module.css";

/** Fonte de cada premissa quando a API não manda `meta.fonte_por_premissa`. */
export const FONTE_PADRAO: Record<CampoNumerico, string> = {
  chuva_prevista_mm: "open-meteo-previsao",
  duracao_h: "open-meteo-previsao",
  chuva_acumulada_mm: "apac-chuva",
  mare_m: "open-meteo-mare",
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

interface Controle {
  campo: Exclude<CampoNumerico, "duracao_h">;
  rotulo: string;
  unidade: string;
  min: number;
  max: number;
  passo: number;
  casas: number;
}

const CONTROLES: Controle[] = [
  {
    campo: "chuva_prevista_mm",
    rotulo: "Chuva prevista em 24 h",
    unidade: "mm",
    min: 0,
    max: 200,
    passo: 1,
    casas: 0,
  },
  {
    campo: "chuva_acumulada_mm",
    rotulo: "Chuva acumulada em 72 h",
    unidade: "mm",
    min: 0,
    max: 300,
    passo: 1,
    casas: 0,
  },
  {
    campo: "mare_m",
    rotulo: "Maré prevista no pico",
    unidade: "m",
    min: -0.5,
    max: 4,
    passo: 0.05,
    casas: 2,
  },
];

/** Gatilhos lidos da configuração real (`/estagios/parametros`); o que não vier, não aparece. */
export function dicaDoControle(c: Controle["campo"], lim: Record<string, number>): string | null {
  const n = (v: number | undefined) => (v === undefined ? null : formatarNumero(v, v % 1 ? 1 : 0));
  if (c === "chuva_prevista_mm") {
    const a = n(lim.chuva_prev_24h_atencao_mm);
    const b = n(lim.chuva_prev_24h_alerta_mm);
    return a && b ? `Gatilhos: atenção ${a} mm · alerta ${b} mm` : null;
  }
  if (c === "chuva_acumulada_mm") {
    const a = n(lim.chuva_prev_72h_atencao_mm);
    const b = n(lim.chuva_prev_72h_alerta_mm);
    return a && b ? `Gatilhos de 72 h: atenção ${a} mm · alerta ${b} mm` : null;
  }
  const m = n(lim.mare_alta_m);
  return m ? `Maré alta a partir de ${m} m` : null;
}

function Deslizante({
  def,
  valor,
  dica,
  aoMudar,
}: {
  def: Controle;
  valor: string;
  dica: ReactNode;
  aoMudar: (v: string) => void;
}) {
  const id = useId();
  const n = lerNumero(valor);
  const numero = typeof n === "number" ? n : null;
  const erro = erroDoCampo(def.campo, valor);
  const min = Math.min(def.min, numero ?? def.min);
  const max = Math.max(def.max, numero ?? def.max);
  const texto = numero === null ? "Sem dado" : `${formatarNumero(numero, def.casas)} ${def.unidade}`;
  return (
    <div className={estilos.controle}>
      <div className={estilos.controleTopo}>
        <label htmlFor={id}>{def.rotulo}</label>
        <output htmlFor={id} className={estilos.valor} data-vazio={numero === null}>
          {texto}
        </output>
      </div>
      <input
        id={id}
        type="range"
        min={min}
        max={max}
        step={def.passo}
        value={numero ?? min}
        aria-valuetext={texto}
        aria-invalid={erro ? true : undefined}
        onChange={(e) => aoMudar(e.target.value.replace(".", ","))}
      />
      <p className={estilos.dicaControle}>{dica}</p>
    </div>
  );
}

/** Uma linha com a fonte de cada premissa e a hora; sem hora, diz o que falta (RF-19). */
export function LinhaFonte({
  fontes,
  fontePorPremissa,
}: {
  fontes: FonteMeta[];
  fontePorPremissa?: Partial<Record<CampoNumerico, string>> | null;
}) {
  const usadas = [
    ...new Map(
      (Object.keys(FONTE_PADRAO) as CampoNumerico[])
        .map((c) => fonteDoCampo(c, fontes, fontePorPremissa))
        .filter((f): f is FonteMeta => !!f)
        .map((f) => [f.id, f] as const),
    ).values(),
  ];
  if (usadas.length === 0)
    return (
      <p className={estilos.fonteLinha}>
        <b>Dados insuficientes:</b> nenhuma fonte trouxe os valores atuais.
      </p>
    );
  return (
    <p className={estilos.fonteLinha}>
      Fonte:{" "}
      {usadas.map((f, i) => (
        <span key={f.id}>
          {i > 0 && "; "}
          {f.atualizado_em ? (
            <>
              {f.nome}, atualizada {quandoAs(f.atualizado_em)}
            </>
          ) : (
            <>
              <b>Dados insuficientes:</b> falta a fonte {f.nome}
            </>
          )}
        </span>
      ))}
      .
    </p>
  );
}

export function PainelPremissas({
  form,
  atuais,
  fontes,
  fontePorPremissa,
  limiares,
  carregando,
  indisponivel,
  aoMudar,
  aoHorizonte,
  aoUsarAtual,
  aoCenario,
}: {
  form: Formulario;
  atuais: Partial<TipoPremissas> | undefined;
  fontes: FonteMeta[];
  fontePorPremissa?: Partial<Record<CampoNumerico, string>> | null;
  limiares: Record<string, number>;
  carregando: boolean;
  indisponivel: boolean;
  aoMudar: (campo: CampoNumerico, valor: string) => void;
  aoHorizonte: (h: number) => void;
  aoUsarAtual: () => void;
  aoCenario: (c: CenarioPronto) => void;
}) {
  const prontos = cenariosProntos(limiares);
  const igual = (c: CenarioPronto) =>
    lerNumero(form.chuva_prevista_mm) === c.chuva_prevista_mm &&
    lerNumero(form.chuva_acumulada_mm) === c.chuva_acumulada_mm &&
    lerNumero(form.mare_m) === c.mare_m &&
    lerNumero(form.duracao_h) === c.duracao_h;
  const idDuracao = useId();
  const duracao = lerNumero(form.duracao_h);
  const duracoes = [...DURACOES] as number[];
  if (typeof duracao === "number" && !duracoes.includes(duracao)) duracoes.push(duracao);
  duracoes.sort((a, b) => a - b);

  const dica = (c: Controle): ReactNode => {
    const regra = dicaDoControle(c.campo, limiares);
    const atual = atuais?.[c.campo];
    if (carregando) return "Buscando o valor atual…";
    if (indisponivel) return "Valores atuais ainda não disponíveis. Mova o controle para simular.";
    if (atual === null || atual === undefined)
      return (
        <>
          <b>Sem dado da fonte.</b> Mova o controle para simular. {regra}
        </>
      );
    return regra;
  };

  return (
    <section className={estilos.premissas} aria-labelledby="sim-premissas">
      <div>
        <h2 id="sim-premissas">Premissas</h2>
        <p className={estilos.apoio}>Valores iniciais da previsão atual.</p>
      </div>
      {prontos.length > 0 && (
        <div className={estilos.prontos} role="group" aria-label="Cenários prontos">
          <p className={estilos.apoio}>Cenários prontos, pelos gatilhos reais:</p>
          {prontos.map((c) => (
            <button
              key={c.chave}
              type="button"
              className={estilos.pronto}
              aria-pressed={igual(c)}
              title={`${c.rotulo}: ${c.chuva_prevista_mm} mm em 24 h, ${c.chuva_acumulada_mm} mm em 72 h, maré de ${c.mare_m} m, chuva de ${c.duracao_h} h`}
              onClick={() => aoCenario(c)}
            >
              {textoCenario(c)}
            </button>
          ))}
        </div>
      )}
      {CONTROLES.map((c) => (
        <Deslizante
          key={c.campo}
          def={c}
          valor={form[c.campo]}
          dica={dica(c)}
          aoMudar={(v) => aoMudar(c.campo, v)}
        />
      ))}
      <div className={campo.campo}>
        <label htmlFor={idDuracao} className={campo.rotulo}>
          Duração da chuva
        </label>
        <select
          id={idDuracao}
          className={campo.entrada}
          value={form.duracao_h}
          onChange={(e) => aoMudar("duracao_h", e.target.value)}
        >
          {form.duracao_h === "" && <option value="">Sem dado</option>}
          {duracoes.map((d) => (
            <option key={d} value={String(d)}>
              {d} h
            </option>
          ))}
        </select>
      </div>
      <Segmentado
        rotulo="Horizonte do cenário"
        opcoes={HORIZONTES.map((h) => ({ valor: h, rotulo: `${h} h` }))}
        valor={form.horizonte_h}
        aoMudar={aoHorizonte}
      />
      <Botao variante="secundario" onClick={aoUsarAtual} larguraTotal>
        Usar a previsão atual
      </Botao>
      {!carregando && <LinhaFonte fontes={fontes} fontePorPremissa={fontePorPremissa} />}
    </section>
  );
}
