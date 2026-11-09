/**
 * Resumo de vulnerabilidade do bairro (RF-07, RF-04): idosos e crianças residentes, equipamentos de saúde (com
 * "em área de risco"), áreas de risco mapeadas e cobertura. Cada número com a sua fonte (RF-19). Só contagens
 * agregadas (RNF-03); falta de dado nunca vira zero (RN-01).
 */
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
import estilos from "./Mapa.module.css";

const LIMITE_EQUIPAMENTOS = 5;

type Resposta = { dados?: ResumoVulnerabilidade } & ResumoVulnerabilidade;

export function useResumoVulnerabilidade(territorioId: string | null) {
  return useConsulta<Resposta>(
    territorioId ? `/territorios/${encodeURIComponent(territorioId)}/resumo-vulnerabilidade` : null,
    { staleTime: 5 * 60_000 },
  );
}

export function ResumoBairro({ territorioId }: { territorioId: string }) {
  const q = useResumoVulnerabilidade(territorioId);
  const titulo = <h3 id="painel-vulneravel">População vulnerável e equipamentos de saúde</h3>;
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
        <Conteudo
          r={(q.data?.dados ?? q.data) as ResumoVulnerabilidade}
          resposta={q.data}
          em={q.dataUpdatedAt}
        />
      );
  }
  return (
    <section className={estilos.bloco} aria-labelledby="painel-vulneravel">
      {titulo}
      {corpo}
    </section>
  );
}

function Conteudo({ r, resposta, em }: { r: ResumoVulnerabilidade; resposta: unknown; em: number }) {
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
  const fontes = fontesDado(fontesDe(resposta));
  return (
    <>
      <dl className={estilos.numeros}>
        <div>
          <dt>Idosos (60 anos ou mais)</dt>
          <dd>
            <b>{textoPessoas(idosos)}</b>
            {idosos.suprimido ? (
              <small>residentes; número pequeno, oculto para proteger a privacidade</small>
            ) : null}
            {!idosos.suprimido && idosos.valor !== null && <small>residentes</small>}
            <small>Fonte: IBGE, Censo 2022</small>
          </dd>
        </div>
        <div>
          <dt>Crianças (0 a 14 anos)</dt>
          <dd>
            <b>{textoPessoas(criancas)}</b>
            {criancas.suprimido ? (
              <small>residentes; número pequeno, oculto para proteger a privacidade</small>
            ) : null}
            {!criancas.suprimido && criancas.valor !== null && <small>residentes</small>}
            <small>Fonte: IBGE, Censo 2022</small>
          </dd>
        </div>
        <div>
          <dt>Pessoas com deficiência</dt>
          <dd>
            <b>Dados insuficientes</b>
            <small>{AVISO_DEFICIENCIA}</small>
          </dd>
        </div>
      </dl>

      <h4>Equipamentos de saúde</h4>
      {equipamentos === null ? (
        <p>
          <b>Dados insuficientes:</b> falta a fonte CNES.
        </p>
      ) : equipamentos.length === 0 ? (
        <p>Nenhum equipamento de saúde registrado no CNES neste bairro.</p>
      ) : (
        <>
          <p>
            <b>{formatarNumero(equipamentos.length)}</b>{" "}
            {equipamentos.length === 1 ? "equipamento" : "equipamentos"} neste bairro
            {qtdEmRisco !== null && qtdEmRisco > 0 && (
              <>
                , <b>{formatarNumero(qtdEmRisco)} em área de risco</b>
              </>
            )}
            .
          </p>
          <ul className={estilos.itens}>
            {equipamentos.slice(0, LIMITE_EQUIPAMENTOS).map((e, i) => (
              <li key={`${e.cnes ?? e.nome}-${i}`}>
                <span className={estilos.itemNome}>{e.nome ?? "Equipamento sem nome"}</span>
                {e.tipo && <small>{e.tipo}</small>}
                {e.cnes != null && emRisco.has(String(e.cnes)) && (
                  <span className={estilos.etiquetaRisco}>em área de risco</span>
                )}
              </li>
            ))}
          </ul>
          {equipamentos.length > LIMITE_EQUIPAMENTOS && (
            <p className={estilos.apagado}>
              e mais {formatarNumero(equipamentos.length - LIMITE_EQUIPAMENTOS)}. Ligue a camada “Equipamentos
              de saúde” para ver todos no mapa.
            </p>
          )}
          {qtdEmRisco === null && (
            <p className={estilos.apagado}>
              Dados insuficientes para dizer quais estão em área de risco
              {parcial ? " (cobertura parcial)" : ""}.
            </p>
          )}
          {qtdEmRisco === 0 && parcial && (
            <p className={estilos.apagado}>
              Nenhum em área de risco nos locais mapeados. A cobertura é parcial.
            </p>
          )}
          <small className={estilos.fonteLinha}>Fonte: CNES</small>
        </>
      )}

      <h4>Áreas de risco mapeadas</h4>
      {typeof r.areas_risco !== "number" ? (
        <p>
          <b>Dados insuficientes:</b> falta a fonte Defesa Civil (áreas de risco).
        </p>
      ) : (
        <p>
          <b>{formatarNumero(r.areas_risco)}</b> {r.areas_risco === 1 ? "área mapeada" : "áreas mapeadas"}
          {parcial && ", cobertura parcial"}.
          {parcial && (
            <>
              {" "}
              <span className={estilos.apagado}>
                Só parte do Recife foi mapeada: bairro sem área não quer dizer bairro sem risco.
              </span>
            </>
          )}{" "}
          <small className={estilos.fonteLinha}>Fonte: Defesa Civil</small>
        </p>
      )}
      <p className={estilos.apagado}>Consultado às {formatarHoraMinuto(em)}.</p>
      <LegendaFonte fontes={fontes} />
    </>
  );
}
