/**
 * Resumo de vulnerabilidade do bairro (RF-07, RF-04): idosos e crianças residentes, equipamentos de saúde (com
 * "em área de risco") e áreas de risco mapeadas, em uma grade de números. A fonte e a hora aparecem uma vez só, no
 * rodapé do painel (RF-19). Só contagens agregadas (RNF-03); falta de dado nunca vira zero (RN-01).
 */
import type { ReactNode } from "react";
import { EstadoDados, LegendaFonte, fontesDado } from "@/design-system/componentes/EstadoDados";
import { EstadoConsulta } from "@/features/evento/Evento";
import { ErroApi } from "@/lib/api";
import { useConsulta } from "@/lib/consultas";
import { formatarHoraMinuto, formatarNumero } from "@/lib/formatos";
import { fontesDe } from "@/lib/frescor";
import {
  AVISO_DEFICIENCIA,
  cnesEmRisco,
  faltaDe,
  textoPessoas,
  valorDe,
  type ResumoVulnerabilidade,
} from "./modeloCamadas";
import { Dica } from "./Dica";
import estilos from "./Mapa.module.css";

const LIMITE_EQUIPAMENTOS = 3;

type Resposta = { dados?: ResumoVulnerabilidade } & ResumoVulnerabilidade;

export function useResumoVulnerabilidade(territorioId: string | null) {
  return useConsulta<Resposta>(
    territorioId ? `/territorios/${encodeURIComponent(territorioId)}/resumo-vulnerabilidade` : null,
    { staleTime: 5 * 60_000 },
  );
}

export function ResumoBairro({ territorioId }: { territorioId: string }) {
  const q = useResumoVulnerabilidade(territorioId);
  let corpo;
  if (q.isPending) corpo = <p className={estilos.apagado}>Carregando…</p>;
  else if (q.isError && !q.data) {
    corpo =
      q.error instanceof ErroApi && q.error.status === 404 ? (
        <EstadoDados tipo="insuficiente" titulo="Ainda não disponível">
          O servidor ainda não oferece o resumo de população e equipamentos deste bairro.
        </EstadoDados>
      ) : (
        <EstadoConsulta erro={q.error} oQue="o resumo do bairro" aoTentar={() => void q.refetch()} />
      );
  } else {
    const falta = faltaDe(q.data);
    corpo =
      falta !== null ? (
        <EstadoDados tipo="insuficiente" titulo="Dados insuficientes">
          Falta a fonte {falta || "IBGE (Censo 2022) e CNES"}. Isso não quer dizer que não haja.
        </EstadoDados>
      ) : (
        <Conteudo r={(q.data?.dados ?? q.data) as ResumoVulnerabilidade} />
      );
  }
  return (
    <section className={estilos.bloco} aria-labelledby="painel-vulneravel">
      <h3 id="painel-vulneravel">População e saúde no bairro</h3>
      {corpo}
    </section>
  );
}

/**
 * Rodapé único do painel do bairro: a fonte e a hora de tudo o que está nele (RF-19), uma vez só.
 * Fonte vencida continua com o selo de aviso (vem de `LegendaFonte`).
 */
export function RodapeFontes({
  territorioId,
  fonteEstagio,
}: {
  territorioId: string | null;
  /** Fonte e hora do estágio sugerido; vazio quando o sistema não sugeriu. */
  fonteEstagio?: string | null;
}) {
  const q = useResumoVulnerabilidade(territorioId);
  const temResumo = !!q.data && faltaDe(q.data) === null;
  const fontes = temResumo ? fontesDado(fontesDe(q.data)) : [];
  if (!fonteEstagio && !temResumo) return null;
  return (
    <footer className={estilos.rodape} aria-label="Fontes e hora da atualização">
      {fonteEstagio && <p>Estágio: {fonteEstagio}.</p>}
      {temResumo && (
        <LegendaFonte fontes={fontes}>
          {fontes.length === 0 && <span>Fonte: IBGE (Censo 2022), CNES e Defesa Civil.</span>}{" "}
          <span>Consultado às {formatarHoraMinuto(q.dataUpdatedAt)}.</span>
        </LegendaFonte>
      )}
    </footer>
  );
}

function Numero({
  rotulo,
  valor,
  apoio,
  dica,
  destaque,
}: {
  rotulo: string;
  valor: ReactNode;
  apoio?: ReactNode;
  dica?: string;
  destaque?: boolean;
}) {
  return (
    <div className={destaque ? estilos.numeroAlerta : undefined}>
      <dt>
        {rotulo}
        {dica && <Dica texto={dica} rotulo={`Saiba mais sobre ${rotulo.toLowerCase()}`} />}
      </dt>
      <dd>
        <b data-semdado={valor === "Dados insuficientes" ? "" : undefined}>{valor}</b>
        {apoio && <small>{apoio}</small>}
      </dd>
    </div>
  );
}

const AVISO_PARCIAL =
  "Só parte do Recife foi mapeada: bairro sem área mapeada não quer dizer bairro sem risco.";

function Conteudo({ r }: { r: ResumoVulnerabilidade }) {
  const idosos = valorDe(r, "idosos_60_mais");
  const criancas = valorDe(r, "criancas_0_14");
  const equipamentos = r.equipamentos ?? null;
  const emRisco = cnesEmRisco(r);
  const qtdEmRisco = Array.isArray(r.equipamentos_em_area_de_risco)
    ? r.equipamentos_em_area_de_risco.length
    : typeof r.equipamentos_em_area_de_risco === "number"
      ? r.equipamentos_em_area_de_risco
      : null;
  const parcial = r.cobertura_risco_parcial === true;
  const apoioPessoas = (v: typeof idosos) =>
    v.suprimido ? "poucos moradores, número oculto" : v.valor !== null ? "moradores" : undefined;

  return (
    <>
      <dl className={estilos.numeros}>
        <Numero rotulo="Idosos (60+)" valor={textoPessoas(idosos)} apoio={apoioPessoas(idosos)} />
        <Numero rotulo="Crianças (0 a 14)" valor={textoPessoas(criancas)} apoio={apoioPessoas(criancas)} />
        <Numero
          rotulo="Equipamentos de saúde"
          valor={equipamentos === null ? "Dados insuficientes" : formatarNumero(equipamentos.length)}
          apoio={
            equipamentos === null
              ? "falta a fonte CNES"
              : qtdEmRisco !== null && qtdEmRisco > 0
                ? `${formatarNumero(qtdEmRisco)} em área de risco`
                : equipamentos.length === 0
                  ? "nenhum registrado no CNES"
                  : undefined
          }
          destaque={qtdEmRisco !== null && qtdEmRisco > 0}
        />
        <Numero
          rotulo="Áreas de risco"
          valor={typeof r.areas_risco !== "number" ? "Dados insuficientes" : formatarNumero(r.areas_risco)}
          apoio={
            typeof r.areas_risco !== "number"
              ? "falta a fonte Defesa Civil"
              : parcial
                ? "mapeadas, cobertura parcial"
                : r.areas_risco === 1
                  ? "mapeada"
                  : "mapeadas"
          }
          dica={parcial ? AVISO_PARCIAL : undefined}
        />
      </dl>
      <p className={estilos.linhaApoio}>
        <b>Pessoas com deficiência:</b> {AVISO_DEFICIENCIA}
      </p>

      {equipamentos !== null && equipamentos.length > 0 && (
        <>
          <ul className={estilos.itens} aria-label="Equipamentos de saúde do bairro">
            {equipamentos.slice(0, LIMITE_EQUIPAMENTOS).map((e, i) => (
              <ItemEquipamento key={`${e.cnes ?? e.nome}-${i}`} e={e} emRisco={emRisco} />
            ))}
          </ul>
          {equipamentos.length > LIMITE_EQUIPAMENTOS && (
            <details className={estilos.verTodos}>
              <summary>Ver todos os {formatarNumero(equipamentos.length)} equipamentos</summary>
              <ul className={estilos.itens}>
                {equipamentos.slice(LIMITE_EQUIPAMENTOS).map((e, i) => (
                  <ItemEquipamento key={`${e.cnes ?? e.nome}-${i}`} e={e} emRisco={emRisco} />
                ))}
              </ul>
            </details>
          )}
          {qtdEmRisco === null && (
            <p className={estilos.linhaApoio}>
              Dados insuficientes para dizer quais estão em área de risco
              {parcial ? " (cobertura parcial)" : ""}.
            </p>
          )}
          {qtdEmRisco === 0 && parcial && (
            <p className={estilos.linhaApoio}>
              Nenhum em área de risco nos locais mapeados (cobertura parcial).
            </p>
          )}
        </>
      )}
    </>
  );
}

function ItemEquipamento({
  e,
  emRisco,
}: {
  e: NonNullable<ResumoVulnerabilidade["equipamentos"]>[number];
  emRisco: Set<string>;
}) {
  return (
    <li>
      <span className={estilos.itemNome}>{e.nome ?? "Equipamento sem nome"}</span>
      {e.tipo && <small>{e.tipo}</small>}
      {e.cnes != null && emRisco.has(String(e.cnes)) && (
        <span className={estilos.etiquetaRisco}>em área de risco</span>
      )}
    </li>
  );
}
