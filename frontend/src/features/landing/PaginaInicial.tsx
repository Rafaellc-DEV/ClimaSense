import { useEffect } from "react";
import rios from "@/assets/tracos/rios.svg?raw";
import { CartaoAviso } from "@/design-system/componentes/CartaoAviso";
import { ReguaMare } from "@/design-system/componentes/ReguaMare";
import { SeloNivel } from "@/design-system/componentes/SeloNivel";
import type { ChaveNivel } from "@/design-system/niveis";
import { useConsulta } from "@/lib/consultas";
import { quandoRelativo } from "@/lib/formatos";
import type { Esquemas } from "@/lib/api";
import { TIPOS_FONTE } from "@/textos/glossario";
import { BuscaBairro } from "./BuscaBairro";
import { CascaPublica, FaixaEmergencia } from "./CascaPublica";
import { MapaAvisos } from "./MapaAvisos";
import { useAvisos, useEstado, type Situacao } from "./useEstado";
import estilos from "./PaginaInicial.module.css";

/** Como o nível entra na frase de estado: “Alerta para 2 bairros até amanhã, 18h.” */
const ABERTURA: Record<string, string> = {
  informativo: "Aviso preventivo",
  atencao: "Atenção",
  alerta: "Alerta",
  critico: "Situação crítica",
};

function onde(t: Esquemas["TerritorioRef"][]): string {
  if (t.some((x) => x.tipo === "municipio")) return "todo o Recife";
  if (t.length === 1) return t[0].tipo === "distrito" ? `o ${t[0].nome_exibicao}` : t[0].nome_exibicao;
  const bairros = t.filter((x) => x.tipo === "bairro").length;
  const distritos = t.length - bairros;
  return [
    bairros && `${bairros} bairro${bairros > 1 ? "s" : ""}`,
    distritos && `${distritos} distrito${distritos > 1 ? "s" : ""}`,
  ]
    .filter(Boolean)
    .join(" e ");
}

export function frase(s: Situacao): { nivel: ChaveNivel; titulo: string; apoio: string } {
  if (s.tipo === "carregando")
    return { nivel: "insuficiente", titulo: "Verificando os avisos…", apoio: "Um instante." };
  if (s.tipo === "erro")
    return {
      nivel: "insuficiente",
      titulo: "Não foi possível verificar os avisos agora.",
      apoio: "Isso não quer dizer que não há risco. Acompanhe a Defesa Civil e, em emergência, ligue 199.",
    };
  const { avisos_ativos: n, principal } = s.estado;
  if (n === 0 || !principal)
    return {
      nivel: "sem",
      titulo: "Nenhum aviso ativo publicado pela equipe.",
      apoio: "Isso não significa ausência de risco. Em chuva forte, evite áreas que costumam alagar.",
    };
  const mais = n > 1 ? ` E mais ${n - 1 === 1 ? "1 aviso" : `${n - 1} avisos`} em vigor.` : "";
  return {
    nivel: principal.nivel as ChaveNivel,
    titulo: `${ABERTURA[principal.nivel]} para ${onde(principal.territorios)} até ${quandoRelativo(
      principal.validade_fim,
    )}.`,
    apoio: `${principal.titulo}.${mais} Veja abaixo o que fazer.`,
  };
}

/** Landing pública (design §9.1): em 3 segundos, a pessoa sabe se existe aviso e o que fazer. */
export function PaginaInicial() {
  const situacao = useEstado();
  const avisos = useAvisos();
  const fontes = useConsulta<Esquemas["FontePublica"][]>("/publico/fontes", { staleTime: 10 * 60_000 });
  const f = frase(situacao);
  const niveis = situacao.tipo === "ok" ? situacao.estado.niveis_por_distrito : null;

  useEffect(() => {
    document.title = "ClimaSense: avisos de chuva e alagamento no Recife";
  }, []);

  return (
    <CascaPublica inicio>
      <section className={estilos.heroi} aria-labelledby="estado">
        <div className={estilos.rios} aria-hidden="true" dangerouslySetInnerHTML={{ __html: rios }} />
        <div className={estilos.heroiRegua}>
          <ReguaMare nivel={f.nivel} />
        </div>
        <div className={estilos.heroiTexto}>
          <div className={estilos.seloMovel}>
            <SeloNivel nivel={f.nivel} grande />
          </div>
          <h1 id="estado" className={estilos.frase} aria-live="polite">
            {f.titulo}
          </h1>
          <p className={estilos.apoio}>{f.apoio}</p>
          {situacao.tipo === "ok" && (
            <p className={estilos.verificacao}>
              Última verificação: {quandoRelativo(situacao.estado.atualizado_em)}.
            </p>
          )}
          <div className={estilos.buscaDesktop}>
            <BuscaBairro />
          </div>
        </div>
      </section>

      <FaixaEmergencia />
      <div className={estilos.buscaMovel}>
        <BuscaBairro />
      </div>

      <section id="avisos" className={estilos.vigor} aria-label="Avisos e mapa">
        <div>
          <h2 className={estilos.h2}>Avisos em vigor</h2>
          {avisos.isPending && <p className={estilos.lead}>Carregando os avisos…</p>}
          {avisos.isError && (
            <p className={estilos.lead}>
              Não foi possível carregar os avisos agora. Isso não quer dizer que não há risco: acompanhe a
              Defesa Civil.
            </p>
          )}
          {avisos.data &&
            (avisos.data.length ? (
              <ul className={estilos.cartoes}>
                {avisos.data.map((a) => (
                  <li key={a.id}>
                    <CartaoAviso aviso={a} ligarDetalhe />
                  </li>
                ))}
              </ul>
            ) : (
              <p className={estilos.lead}>
                Nenhum aviso ativo publicado pela equipe. Quando houver, ele aparece aqui com o que fazer e
                até quando vale.
              </p>
            ))}
        </div>
        <div>
          <h2 className={estilos.h2}>Onde há aviso agora</h2>
          <p className={estilos.lead}>O Recife é dividido em 8 distritos sanitários.</p>
          <MapaAvisos niveis={niveis} />
        </div>
      </section>

      <section id="como-funciona" className={estilos.faixaClara} aria-labelledby="como-h">
        <div className={estilos.secao}>
          <h2 id="como-h" className={estilos.h2}>
            Como um aviso chega até você
          </h2>
          <ol className={estilos.passos}>
            <li>
              <h3>Dados de chuva, maré e território</h3>
              <p>
                A chuva prevista, o nível do mar e o mapa oficial dos distritos são coletados de fontes
                públicas.
              </p>
            </li>
            <li>
              <h3>A equipe avalia</h3>
              <p>A Vigilância em Saúde analisa os territórios e escreve o aviso em linguagem simples.</p>
            </li>
            <li>
              <h3>Um responsável revisa e publica</h3>
              <p>Outra pessoa confere antes. Só avisos revisados aparecem aqui, sempre com a validade.</p>
            </li>
          </ol>
        </div>
      </section>

      <section id="sobre" className={estilos.secao} aria-labelledby="sobre-h">
        <h2 id="sobre-h" className={estilos.h2}>
          Sobre o ClimaSense
        </h2>
        <div className={estilos.sobre}>
          <div>
            <h3>O que é</h3>
            <p>
              Uma ferramenta feita para as equipes de Vigilância em Saúde do Recife anteciparem os efeitos da
              chuva e da maré na saúde da população e avisarem, com clareza, os bairros que precisam de
              cuidado.
            </p>
          </div>
          <div>
            <h3>O que não é</h3>
            <p>
              Não é alerta oficial e não substitui a Defesa Civil. Não prevê com certeza onde vai alagar. Na
              dúvida, siga a Defesa Civil e ligue 199.
            </p>
          </div>
        </div>
      </section>

      <section id="fontes" className={estilos.secao} aria-labelledby="fontes-h">
        <h2 id="fontes-h" className={estilos.h2}>
          De onde vêm os dados
        </h2>
        {fontes.data ? (
          <ul className={estilos.fontes}>
            {fontes.data.map((x) => (
              <li key={x.id} data-status={x.status}>
                <strong>{x.nome}</strong>
                <span>
                  {x.orgao}. {TIPOS_FONTE[x.tipo]}.
                </span>
                <span className={estilos.statusFonte}>
                  {x.status === "planejada"
                    ? "Planejada: ainda não gera dados."
                    : x.status === "atualizada"
                      ? `Atualizada ${x.ultima_atualizacao ? quandoRelativo(x.ultima_atualizacao) : ""}.`
                      : x.status === "desatualizada"
                        ? "Desatualizada."
                        : "Com falha na última carga."}
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <p className={estilos.lead}>Carregando as fontes…</p>
        )}
        <p className={estilos.nota}>
          Quando um dado falta, o ClimaSense mostra “Dados insuficientes”. Ele nunca preenche lacunas com
          valores inventados.
        </p>
      </section>

      <section id="equipe" className={estilos.secao} aria-labelledby="equipe-h">
        <h2 id="equipe-h" className={estilos.h2}>
          Equipe
        </h2>
        <p className={estilos.lead}>
          Feito por estudantes da CESAR School na disciplina de Análise e Visualização de Dados, em 2026. Os
          nomes e os critérios dos níveis de aviso ainda serão validados com a Vigilância em Saúde e a Defesa
          Civil.
        </p>
      </section>
    </CascaPublica>
  );
}
