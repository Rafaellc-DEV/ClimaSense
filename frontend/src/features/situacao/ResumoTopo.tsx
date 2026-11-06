import { formatarMm, formatarNumero } from "@/lib/formatos";
import { ESTAGIOS } from "@/features/evento/estagios";
import { atualizada } from "@/features/evento/textos";
import type { ItemEstagio } from "@/features/evento/tipos";
import { contarSituacoes, horaDoInsumo, maiorValor, type CampoInsumo } from "./resumo";
import estilos from "./Situacao.module.css";

const SITUACOES = [
  { chave: "observacao", nivel: "informativo" },
  { chave: "atencao", nivel: "atencao" },
  { chave: "alerta", nivel: "alerta" },
  { chave: "critico", nivel: "critico" },
] as const;

function Medida({
  rotulo,
  campo,
  itens,
  hora,
  fonte,
}: {
  rotulo: string;
  campo: CampoInsumo;
  itens: ItemEstagio[];
  hora: string | null;
  fonte: string;
}) {
  const m = maiorValor(itens, campo);
  const mare = campo === "mare_max_m";
  return (
    <div className={estilos.medida} data-vazio={m === null}>
      <dt>{rotulo}</dt>
      <dd>
        {m === null ? (
          <span className={estilos.semDado}>sem dado</span>
        ) : mare ? (
          <>
            {formatarNumero(m.valor, 2)}
            <small> m</small>
          </>
        ) : (
          formatarMm(m.valor)
        )}
      </dd>
      <dd className={estilos.origem}>
        {m === null
          ? "A fonte não trouxe este dado."
          : mare
            ? "Maior maré prevista no Recife."
            : m.empatados
              ? "Maior valor, em mais de um distrito."
              : `Maior valor: ${m.nome}.`}
        <br />
        {fonte}, {atualizada(hora)}.
      </dd>
    </div>
  );
}

/** O resumo do topo: quantos distritos em cada situação e a chuva e a maré que importam agora. */
export function ResumoTopo({ itens, horaFonte }: { itens: ItemEstagio[]; horaFonte: string | null }) {
  const c = contarSituacoes(itens);
  const horaPrev = horaDoInsumo(itens, "previsao_emitida_em") ?? horaFonte;
  const horaMare = horaDoInsumo(itens, "mare_emitida_em");
  const calculo = itens
    .map((i) => i.sugerido?.calculado_em)
    .filter((x): x is string => !!x)
    .sort()
    .pop();
  return (
    <section className={estilos.resumo} aria-labelledby="si-resumo">
      <h2 id="si-resumo" className="so-leitor">
        Resumo
      </h2>
      <ul className={estilos.contagens} aria-label="Distritos por situação">
        {SITUACOES.map(({ chave, nivel }) => (
          <li key={chave} data-nivel={nivel} data-zero={c[chave] === 0}>
            <b>{c[chave]}</b>
            <span>
              {ESTAGIOS[chave].rotulo}
              <span className="so-leitor">{c[chave] === 1 ? ": 1 distrito" : `: ${c[chave]} distritos`}</span>
            </span>
          </li>
        ))}
        {c.sem_dados > 0 && (
          <li data-nivel="insuficiente">
            <b>{c.sem_dados}</b>
            <span>
              Sem dado<span className="so-leitor">: {c.sem_dados} distritos</span>
            </span>
          </li>
        )}
      </ul>
      <dl className={estilos.medidas} aria-label="Chuva e maré que importam agora">
        <Medida
          rotulo="Choveu nas últimas 24 h"
          campo="chuva_24h_mm"
          itens={itens}
          hora={calculo ?? null}
          fonte="Open-Meteo"
        />
        <Medida
          rotulo="Previsto para as próximas 24 h"
          campo="chuva_prev_24h_mm"
          itens={itens}
          hora={horaPrev}
          fonte="Open-Meteo"
        />
        <Medida
          rotulo="Previsto para as próximas 72 h"
          campo="chuva_prev_72h_mm"
          itens={itens}
          hora={horaPrev}
          fonte="Open-Meteo"
        />
        <Medida
          rotulo="Maré alta prevista"
          campo="mare_max_m"
          itens={itens}
          hora={horaMare}
          fonte="Previsão de maré"
        />
      </dl>
    </section>
  );
}
