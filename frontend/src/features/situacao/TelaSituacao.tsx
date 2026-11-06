import { useMemo } from "react";
import { CabecalhoTela } from "@/design-system/componentes/CabecalhoTela";
import {
  EstadoDados,
  fontesDado,
  LegendaFonte,
  type FonteDado,
} from "@/design-system/componentes/EstadoDados";
import { Indicador } from "@/design-system/componentes/Indicador";
import { Painel } from "@/design-system/componentes/Painel";
import { Pilula } from "@/design-system/componentes/Pilula";
import { EstadoConsulta } from "@/features/evento/Evento";
import { nomeCurto } from "@/features/evento/textos";
import { desembrulhar, listaDe, type SituacaoDistrito, type SituacaoEvento } from "@/features/evento/tipos";
import { ListaAbrigos } from "@/features/abrigos/TelaAbrigos";
import { ListaAdaptavel } from "@/features/fluxo/ListaAdaptavel";
import type { ItemPrioridadeTerritorio } from "@/features/mapa/tipos";
import { useConsultaViva, ultimaAtualizacao } from "@/lib/consultas";
import { fontesDe, type FonteMeta } from "@/lib/frescor";
import { formatarNumero } from "@/lib/formatos";
import estilos from "./Situacao.module.css";

const ID_FONTE_PESSOAS = "recife-abrigos-ocupacao";

/**
 * Distritos do mais vulnerável ao menos (RF-22): a ordem de `/territorios/prioridade`. Quem não aparece lá vai para o
 * fim, em ordem de nome. Sem a lista de prioridade, fica só a ordem de nome (e a tela diz isso).
 */
export function ordenarDistritos(
  distritos: SituacaoDistrito[],
  prioridade: ItemPrioridadeTerritorio[],
): SituacaoDistrito[] {
  const posicao = new Map(
    prioridade.filter((p) => p.nivel === "distrito").map((p) => [p.territorio_id, p.posicao] as const),
  );
  return [...distritos].sort(
    (a, b) =>
      (posicao.get(a.distrito_id) ?? Number.MAX_SAFE_INTEGER) -
        (posicao.get(b.distrito_id) ?? Number.MAX_SAFE_INTEGER) ||
      a.distrito_nome.localeCompare(b.distrito_nome, "pt-BR", { numeric: true }),
  );
}

/** Um número do evento: “Dados insuficientes” quando é null; “soma parcial” quando falta contagem em abrigo aberto. */
function Numero({ valor, parcial }: { valor: number | null; parcial?: boolean }) {
  if (valor === null) return <span className={estilos.semDadoCelula}>Dados insuficientes</span>;
  return (
    <>
      {formatarNumero(valor)}
      {parcial && <span className={estilos.parcial}>soma parcial</span>}
    </>
  );
}

/**
 * Situação do evento (RF-08, RF-09, RF-10): os dois números que o cliente acompanha, abrigos abertos e desabrigados,
 * na cidade e por distrito sanitário (mais vulneráveis primeiro, RF-22), e a lista de abrigos para a equipe lançar as
 * pessoas abrigadas e os desabrigados atendidos. A situação por estágio mora no Mapa. Atualiza sozinha a cada 60 s.
 */
export function TelaSituacao() {
  const r = useConsultaViva<unknown>("/abrigos/situacao");
  const prioridade = useConsultaViva<unknown>("/territorios/prioridade");
  const dados = desembrulhar<SituacaoEvento>(r.data);
  const fontes = fontesDe(r.data);
  const cidade = dados?.cidade;
  const prio = listaDe<ItemPrioridadeTerritorio>(prioridade.data);
  const distritos = useMemo(() => ordenarDistritos(dados?.distritos ?? [], prio), [dados, prio]);
  const porVulnerabilidade = prio.some((p) => p.nivel === "distrito");

  // cada número mostra a fonte que lhe cabe; sem `meta.fontes`, o rótulo antigo com a hora da equipe
  const fonteAbertos: FonteDado[] =
    fontes.length > 0
      ? fontesDado(fontes)
      : [{ nome: "Feed do COP e registro da equipe", atualizadoEm: cidade?.atualizado_em ?? null }];
  const soPessoas = fontes.filter((f: FonteMeta) => f.id === ID_FONTE_PESSOAS);
  const fonteDesabrigados: FonteDado[] =
    soPessoas.length > 0
      ? fontesDado(soPessoas)
      : fontes.length > 0
        ? fontesDado(fontes)
        : [{ nome: "Registro da equipe", atualizadoEm: cidade?.atualizado_em ?? null }];

  const semCadastro = cidade?.abrigos_cadastrados === 0;
  const parcial = cidade?.parcial === true;
  const avisoParcial = parcial
    ? `${formatarNumero(cidade?.abertos_sem_contagem ?? 0)} ${
        cidade?.abertos_sem_contagem === 1
          ? "abrigo aberto ainda sem contagem"
          : "abrigos abertos ainda sem contagem"
      }: o total pode ser maior.`
    : undefined;

  return (
    <>
      <CabecalhoTela
        titulo="Situação do evento"
        proposito="Quantos abrigos estão abertos e quantas pessoas ficaram desabrigadas, na cidade e em cada distrito."
        atualizadoEm={ultimaAtualizacao(r, prioridade)}
      />
      <div className={estilos.pagina}>
        {r.isError ? (
          <EstadoConsulta erro={r.error} oQue="a situação do evento" aoTentar={() => r.refetch()} />
        ) : (
          <section aria-labelledby="se-cidade" className={estilos.numerosCidade}>
            <h2 id="se-cidade" className="so-leitor">
              Recife
            </h2>
            <Indicador
              rotulo="Abrigos abertos"
              carregando={r.isPending}
              valor={cidade?.abrigos_abertos == null ? null : formatarNumero(cidade.abrigos_abertos)}
              insuficiente={cidade?.abrigos_abertos == null}
              explicacao={
                semCadastro
                  ? "Nenhum abrigo cadastrado ainda. Isso não quer dizer que não haja abrigo aberto."
                  : undefined
              }
              fonte={fonteAbertos}
            />
            <Indicador
              rotulo="Desabrigados"
              carregando={r.isPending}
              valor={cidade?.desabrigados == null ? null : formatarNumero(cidade.desabrigados)}
              insuficiente={cidade?.desabrigados == null}
              explicacao={avisoParcial}
              selo={
                parcial && cidade?.desabrigados != null ? (
                  <Pilula tom="atencao">Soma parcial</Pilula>
                ) : undefined
              }
              fonte={fonteDesabrigados}
            />
          </section>
        )}

        {!r.isError && (
          <Painel
            id="se-distritos"
            titulo="Por distrito sanitário"
            dica="Os distritos mais vulneráveis vêm primeiro: a ordem é a do histórico de atendimentos de alagamento e deslizamento da Defesa Civil. Pessoas abrigadas e desabrigados são lançados pela equipe, abrigo por abrigo."
          >
            {r.isSuccess && distritos.length === 0 ? (
              <EstadoDados tipo="insuficiente" titulo="Dados insuficientes.">
                Falta o cadastro de abrigos por distrito. Cadastre os abrigos na lista abaixo.
              </EstadoDados>
            ) : (
              <>
                <ListaAdaptavel
                  legenda="Abrigos e desabrigados por distrito sanitário, dos mais vulneráveis aos menos"
                  carregando={r.isPending}
                  linhas={distritos}
                  chaveLinha={(d) => d.distrito_id}
                  colunas={[
                    {
                      chave: "distrito",
                      titulo: "Distrito",
                      celula: (d) => (
                        <span className={estilos.distritoNome}>{nomeCurto(d.distrito_nome)}</span>
                      ),
                    },
                    {
                      chave: "abertos",
                      titulo: "Abrigos abertos",
                      numerica: true,
                      celula: (d) => <Numero valor={d.abrigos_abertos} />,
                    },
                    {
                      chave: "abrigadas",
                      titulo: "Pessoas abrigadas",
                      numerica: true,
                      celula: (d) => <Numero valor={d.pessoas_abrigadas} parcial={d.parcial} />,
                    },
                    {
                      chave: "desabrigados",
                      titulo: "Desabrigados",
                      numerica: true,
                      celula: (d) => <Numero valor={d.desabrigados} parcial={d.parcial} />,
                    },
                  ]}
                />
                {r.isSuccess && (
                  <p className={estilos.detalhe}>
                    {porVulnerabilidade
                      ? "Ordem: do distrito mais vulnerável ao menos."
                      : "Ordem por nome: falta a fonte de ocorrências da Defesa Civil para ordenar por vulnerabilidade."}
                  </p>
                )}
                <LegendaFonte fontes={fontesDado(fontes)} />
              </>
            )}
          </Painel>
        )}

        <ListaAbrigos />
      </div>
    </>
  );
}
