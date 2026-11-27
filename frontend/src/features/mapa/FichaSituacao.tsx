/**
 * Blocos da "ficha de situação" do bairro (RF-07): a chuva do distrito contra o gatilho e o histórico de ocorrências com
 * período. O bairro herda a chuva do distrito (RN-07). Sem dado, "Dados insuficientes" e a fonte que falta (RN-01);
 * zero medido continua zero (RN-02). Ocorrência sempre com período e fonte, nunca como situação de agora.
 */
import { EstadoDados } from "@/design-system/componentes/EstadoDados";
import { SeloExp } from "@/features/dashboards/CartaoPainel";
import { limiarSeguinte } from "@/features/dashboards/indicadores";
import { infoEstagio } from "@/features/evento/estagios";
import { desembrulhar, type ItemEstagio } from "@/features/evento/tipos";
import { ErroApi } from "@/lib/api";
import { useConsulta } from "@/lib/consultas";
import { nomeDistrito } from "@/lib/distritos";
import { formatarNumero } from "@/lib/formatos";
import estilos from "./Mapa.module.css";

const mm = (v: number) => formatarNumero(v, v < 10 && !Number.isInteger(v) ? 1 : 0);

const LINHAS = [
  { chave: "chuva_24h_mm", rotulo: "Medida 24 h", prefixo: "chuva_24h", previsao: false },
  { chave: "chuva_prev_24h_mm", rotulo: "Prevista 24 h", prefixo: "chuva_prev_24h", previsao: true },
  { chave: "chuva_prev_72h_mm", rotulo: "Prevista 72 h", prefixo: "chuva_prev_72h", previsao: true },
] as const;

/** Chuva do distrito do bairro (medida e prevista) contra o próximo limiar de estágio, em barras curtas. */
export function FichaChuva({
  distrito,
  limiares,
}: {
  distrito: ItemEstagio | undefined;
  limiares: Record<string, number> | undefined;
}) {
  const insumos = distrito?.sugerido?.insumos;
  return (
    <section className={estilos.bloco} aria-labelledby="ficha-chuva">
      <h3 id="ficha-chuva">
        Chuva do {distrito ? nomeDistrito(distrito.territorio_nome) : "distrito"} <SeloExp />
      </h3>
      {!insumos ? (
        <EstadoDados tipo="insuficiente">Falta: chuva por distrito (APAC e Open-Meteo).</EstadoDados>
      ) : (
        <ul className={estilos.fichaChuva}>
          {LINHAS.map((l) => {
            const v = typeof insumos[l.chave] === "number" ? (insumos[l.chave] as number) : null;
            const alvo = v === null || !limiares ? null : limiarSeguinte(v, l.prefixo, limiares);
            return (
              <li key={l.chave}>
                <span>{l.rotulo}</span>
                {v === null ? (
                  <b className={estilos.apagado}>Dados insuficientes</b>
                ) : (
                  <>
                    <b>{mm(v)} mm</b>
                    {alvo && (
                      <>
                        <span className={estilos.fichaBarra} aria-hidden="true">
                          <i style={{ width: `${Math.max(2, Math.min(100, (v / alvo.limiar) * 100))}%` }} />
                        </span>
                        <small>
                          {alvo.atingido
                            ? `passou de ${infoEstagio(alvo.estagio).rotulo}`
                            : `de ${mm(alvo.limiar)} mm (${infoEstagio(alvo.estagio).rotulo})`}
                        </small>
                      </>
                    )}
                  </>
                )}
              </li>
            );
          })}
        </ul>
      )}
      <p className={estilos.linhaApoio}>
        O bairro usa a chuva do distrito. A barra mostra quanto já chegou do próximo limiar.
      </p>
    </section>
  );
}

interface ItemHistorico {
  bairro_id: string;
  registros: number;
  dias_com_registro?: number | null;
  primeiro_registro?: string | null;
  ultimo_registro?: string | null;
}
interface RespostaHistorico {
  itens?: ItemHistorico[];
  periodo_inicio?: string | null;
  periodo_fim?: string | null;
}

const ano = (d: string | null | undefined) => (d && /^\d{4}/.test(d) ? d.slice(0, 4) : null);
const MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];
const mesAno = (d: string | null | undefined) => {
  const m = d ? /^(\d{4})-(\d{2})/.exec(d) : null;
  return m && Number(m[2]) >= 1 && Number(m[2]) <= 12 ? `${MESES[Number(m[2]) - 1]}/${m[1]}` : null;
};

function useHistorico(tipo: "alagamento" | "deslizamento") {
  return useConsulta<unknown>(`/ocorrencias/historico?tipo=${tipo}`, { staleTime: 30 * 60_000 });
}

/** Ocorrências já registradas no bairro, com período e fonte: retrato do passado, não situação de agora. */
export function FichaHistorico({ bairroId }: { bairroId: string }) {
  const alag = useHistorico("alagamento");
  const desl = useHistorico("deslizamento");
  const dados = [alag, desl].map((q) => desembrulhar<RespostaHistorico>(q.data));
  const pendente = alag.isPending || desl.isPending;
  const indisponivel = [alag, desl].some(
    (q) => q.isError && q.error instanceof ErroApi && q.error.status === 404,
  );
  // a base termina quando o último registro de qualquer bairro termina (dado real, não suposto)
  const fim = dados
    .flatMap((r) => [r?.periodo_fim ?? null, ...(r?.itens ?? []).map((i) => i.ultimo_registro ?? null)])
    .filter((x): x is string => !!x)
    .sort()
    .pop();
  const inicio = dados
    .flatMap((r) => [r?.periodo_inicio ?? null, ...(r?.itens ?? []).map((i) => i.primeiro_registro ?? null)])
    .filter((x): x is string => !!x)
    .sort()[0];
  const linha = (rotulo: string, r: RespostaHistorico | undefined) => {
    const i = r?.itens?.find((x) => x.bairro_id === bairroId);
    if (!r)
      return (
        <li key={rotulo}>
          {rotulo}: <b className={estilos.apagado}>Dados insuficientes</b>
        </li>
      );
    if (!i)
      return (
        <li key={rotulo}>
          {rotulo}: <b>sem registro</b> <small>(não é ausência de risco)</small>
        </li>
      );
    const de = ano(i.primeiro_registro);
    const ate = ano(i.ultimo_registro);
    return (
      <li key={rotulo}>
        {rotulo}:{" "}
        <b>
          {formatarNumero(i.registros)} {i.registros === 1 ? "registro" : "registros"}
        </b>
        {i.dias_com_registro != null && <> em {formatarNumero(i.dias_com_registro)} dias</>}
        {de && (
          <small>
            {" "}
            ({de}
            {ate && ate !== de ? `–${ate}` : ""})
          </small>
        )}
      </li>
    );
  };
  return (
    <section className={estilos.bloco} aria-labelledby="ficha-historico">
      <h3 id="ficha-historico">Histórico de ocorrências</h3>
      {pendente ? (
        <p className={estilos.apagado}>Carregando…</p>
      ) : indisponivel ? (
        <EstadoDados tipo="insuficiente" titulo="Ainda não disponível">
          O servidor ainda não oferece o histórico de ocorrências.
        </EstadoDados>
      ) : (
        <>
          <ul className={estilos.fichaHistorico}>
            {linha("Alagamento", dados[0])}
            {linha("Deslizamento", dados[1])}
          </ul>
          <p className={estilos.linhaApoio}>
            Defesa Civil{ano(inicio) ? `, desde ${ano(inicio)}` : ""}
            {mesAno(fim) ? ` até ${mesAno(fim)}` : ""}. Retrato do passado, não situação de agora.
          </p>
        </>
      )}
    </section>
  );
}
