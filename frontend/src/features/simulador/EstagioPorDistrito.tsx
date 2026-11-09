import { Experimental, Pilula } from "@/design-system/componentes/Pilula";
import { NIVEIS } from "@/design-system/niveis";
import { SeloEstagio } from "@/features/evento/Evento";
import { ESTAGIOS, infoEstagio } from "@/features/evento/estagios";
import { formatarNumero } from "@/lib/formatos";
import { nomeDistrito } from "@/lib/distritos";
import { impactoDe } from "@/features/mapa/modeloCamadas";
import { ListaAgravos } from "./DistritosArboviroses";
import { NIVEL_CLASSE, ROTULO_CLASSE, ordemDaClasse, type ItemSimulado } from "./tipos";
import estilos from "./Simulador.module.css";

const LEGENDA = ["critico", "alerta", "atencao", "observacao"] as const;

const maiuscula = (t: string) => t.charAt(0).toUpperCase() + t.slice(1);
export const textoConfianca = (c: string | null | undefined) => (c ? maiuscula(c) : "sem dado");

export const ordemNome = (a: ItemSimulado, b: ItemSimulado) =>
  nomeDistrito(a.nome).localeCompare(nomeDistrito(b.nome), "pt-BR", { numeric: true });

/** Classe (observação a crítico) em pílula, ou "Dados insuficientes". */
export function ClasseAlagamento({ classe }: { classe: string | null | undefined }) {
  const o = ordemDaClasse(classe);
  return o === null ? (
    <Pilula nivel="insuficiente" pequena>
      Dados insuficientes
    </Pilula>
  ) : (
    <Pilula nivel={NIVEL_CLASSE[o]} pequena>
      {ROTULO_CLASSE[o]}
    </Pilula>
  );
}

/**
 * Mapa esquemático: um bloco por distrito, colorido pelo estágio sugerido. Não é um mapa geográfico: a posição dos
 * blocos não diz onde fica o distrito. Sem estágio, o bloco fica cinza com "Sem dados", nunca verde (RN-01).
 */
export function EstagioPorDistrito({
  distritos,
  selecionado,
  aoEscolher,
}: {
  distritos: ItemSimulado[];
  selecionado: string | null;
  aoEscolher: (id: string) => void;
}) {
  const ordenados = [...distritos].sort(ordemNome);
  return (
    <section className={estilos.painelBloco} aria-labelledby="sim-estagios">
      <div className={estilos.painelTopo}>
        <h2 id="sim-estagios">Estágio sugerido por distrito</h2>
        <Experimental />
      </div>
      <p className={estilos.apoio}>Atualiza ao mudar uma premissa. Toque num distrito para ver o porquê.</p>
      {ordenados.length === 0 ? (
        <p className={estilos.apoio}>Os distritos aparecem aqui quando o cenário for calculado.</p>
      ) : (
        <ul className={estilos.blocos}>
          {ordenados.map((d) => {
            const info = infoEstagio(d.estagio_sugerido);
            const nivel = NIVEIS[info.nivel];
            return (
              <li key={d.territorio_id}>
                <button
                  type="button"
                  className={estilos.bloco}
                  data-nivel={info.nivel}
                  style={{ "--cor": nivel.cor, "--fundo": nivel.fundo } as React.CSSProperties}
                  aria-pressed={selecionado === d.territorio_id}
                  onClick={() => aoEscolher(d.territorio_id)}
                >
                  <b>{nomeDistrito(d.nome)}</b>
                  <span className={estilos.chipEstagio}>{info.rotulo}</span>
                  <span className={estilos.confiancaBloco}>Confiança: {textoConfianca(d.confianca)}</span>
                </button>
              </li>
            );
          })}
        </ul>
      )}
      <div className={estilos.legenda}>
        <ul aria-label="Legenda dos estágios">
          {LEGENDA.map((e) => (
            <li key={e}>
              <SeloEstagio estagio={e} pequena />
            </li>
          ))}
          <li>
            <Pilula nivel={ESTAGIOS.sem_dados.nivel} pequena>
              Sem dados
            </Pilula>
          </li>
        </ul>
        <small>
          Esquemático por distrito (a posição não é a do mapa). Cinza é falta de dado, não risco baixo.
        </small>
      </div>
    </section>
  );
}

const n = (v: number | null | undefined) =>
  v === null || v === undefined ? "Dados insuficientes" : formatarNumero(v);

/** Moradores da área (contagem, nunca percentual). O que não existe aparece como "Dados insuficientes" (RN-01). */
export function PessoasExpostas({
  impacto,
  aviso,
  unidade,
}: {
  impacto: ReturnType<typeof impactoDe>;
  aviso: string | null;
  unidade: "distrito" | "bairro";
}) {
  return (
    <>
      {impacto ? (
        <dl className={estilos.exposicao}>
          <div>
            <dt>Idosos</dt>
            <dd>{n(impacto.idosos_60_mais)}</dd>
          </div>
          <div>
            <dt>Crianças</dt>
            <dd>{n(impacto.criancas_0_14)}</dd>
          </div>
          <div>
            <dt>Com deficiência</dt>
            <dd>Dados insuficientes</dd>
          </div>
          <div>
            <dt>Unidades de saúde</dt>
            <dd>{n(impacto.equipamentos_saude)}</dd>
          </div>
        </dl>
      ) : (
        <p className={estilos.apoio}>
          <b>Dados insuficientes.</b>{" "}
          {aviso ?? `Sem estágio de atenção ou mais neste ${unidade}, ou falta a fonte IBGE (Censo 2022).`}
        </p>
      )}
      <p className={estilos.apoio}>
        Moradores do {unidade}, não pessoas atingidas. Agregado, sem dados individuais. Fonte: IBGE, Censo
        2022 e CNES.
      </p>
    </>
  );
}

/** Detalhe do distrito escolhido: por que este estágio e quem mora na área (contagens, nunca percentual). */
export function DetalheDistrito({ item, aviso }: { item: ItemSimulado; aviso: string | null }) {
  const info = infoEstagio(item.estagio_sugerido);
  const motivos = item.motivos ?? [];
  const impacto = impactoDe(item.impacto_pessoas);
  const alag = ordemDaClasse(item.classe_alagamento);
  const desl = ordemDaClasse(item.classe_deslizamento);
  const classe = (o: number | null) => (o === null ? "dados insuficientes" : ROTULO_CLASSE[o].toLowerCase());
  return (
    <section className={estilos.painelBloco} aria-labelledby="sim-detalhe" data-testid="detalhe-distrito">
      <h2 id="sim-detalhe">
        {nomeDistrito(item.nome)} · {info.rotulo}
      </h2>
      <p className={estilos.apoio}>
        Alagamento: {classe(alag)} · deslizamento: {classe(desl)} · confiança:{" "}
        {textoConfianca(item.confianca).toLowerCase()}
      </p>
      <div className={estilos.detalheGrade}>
        <div>
          <h3>Por que este estágio</h3>
          {motivos.length > 0 ? (
            <ul className={estilos.motivos}>
              {motivos.map((m) => (
                <li key={m}>{nomeDistrito(m)}</li>
              ))}
            </ul>
          ) : (
            <p className={estilos.apoio}>
              <b>Dados insuficientes:</b> o cálculo não trouxe motivo para este distrito.
            </p>
          )}
        </div>
        <div>
          <h3>Pessoas expostas</h3>
          <PessoasExpostas impacto={impacto} aviso={aviso} unidade="distrito" />
        </div>
      </div>
      <h3>Arboviroses (contexto)</h3>
      <ListaAgravos arboviroses={item.arboviroses} />
    </section>
  );
}
