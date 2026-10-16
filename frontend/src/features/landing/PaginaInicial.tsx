import { useEffect } from "react";
import { BellOff, Megaphone } from "lucide-react";
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

  const emUso = fontes.data?.filter((x) => x.status !== "planejada") ?? [];
  const planejadas = (fontes.data?.length ?? 0) - emUso.length;

  return (
    <CascaPublica inicio>
      <section className={estilos.heroi} aria-labelledby="estado">
        <div className={estilos.heroiInterno}>
          <div className={estilos.heroiRegua}>
            <ReguaMare nivel={f.nivel} />
          </div>
          <div className={estilos.heroiTexto}>
            <p className={estilos.sobrescrito}>Avisos de chuva e alagamento no Recife</p>
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
          </div>
        </div>
      </section>

      <FaixaEmergencia />

      <section className={estilos.secao} aria-labelledby="bairro-h">
        <div className={estilos.cartaoBusca}>
          <h2 id="bairro-h" className={estilos.h2}>
            Há aviso para o seu bairro?
          </h2>
          <BuscaBairro />
        </div>
      </section>

      <section id="comunicados" className={estilos.secao} aria-labelledby="comunicados-h">
        <div className={estilos.cabecalhoSecao}>
          <h2 id="comunicados-h" className={estilos.h2}>
            <Megaphone aria-hidden="true" /> Comunicados em vigor
          </h2>
          <p className={estilos.lead}>
            Publicados pela Vigilância em Saúde do Recife, com o que fazer e até quando valem. Cada comunicado
            sai daqui sozinho quando vence.
          </p>
        </div>
        {avisos.isPending && <p className={estilos.lead}>Carregando os comunicados…</p>}
        {avisos.isError && (
          <p className={estilos.vazio}>
            Não foi possível carregar os comunicados agora. Isso não quer dizer que não há risco: acompanhe a
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
            <div className={estilos.vazio}>
              <BellOff aria-hidden="true" size={28} />
              <div>
                <p className={estilos.vazioTitulo}>Nenhum comunicado em vigor agora.</p>
                <p>
                  Quando a equipe publicar um, ele aparece aqui com o que fazer e até quando vale. Isso não
                  significa ausência de risco.
                </p>
              </div>
            </div>
          ))}
      </section>

      <section className={estilos.faixaClara} aria-labelledby="mapa-h">
        <div className={estilos.secao}>
          <div className={estilos.cabecalhoSecao}>
            <h2 id="mapa-h" className={estilos.h2}>
              Onde há aviso agora
            </h2>
            <p className={estilos.lead}>O Recife é dividido em 8 distritos sanitários.</p>
          </div>
          <MapaAvisos niveis={niveis} />
        </div>
      </section>

      <section id="como-funciona" className={estilos.secao} aria-labelledby="como-h">
        <h2 id="como-h" className={estilos.h2}>
          Como um aviso chega até você
        </h2>
        <ol className={estilos.passos}>
          <li>
            <h3>Dados de chuva, maré e território</h3>
            <p>A chuva prevista, o nível do mar e o mapa oficial dos distritos vêm de fontes públicas.</p>
          </li>
          <li>
            <h3>A equipe avalia</h3>
            <p>A Vigilância em Saúde analisa os territórios e escreve o aviso em linguagem simples.</p>
          </li>
          <li>
            <h3>Outra pessoa revisa e publica</h3>
            <p>Só avisos revisados aparecem aqui, sempre com a validade.</p>
          </li>
        </ol>
      </section>

      <section id="sobre" className={estilos.faixaClara} aria-labelledby="sobre-h">
        <div className={estilos.secao}>
          <h2 id="sobre-h" className={estilos.h2}>
            Sobre o ClimaSense
          </h2>
          <div className={estilos.sobre}>
            <div>
              <h3>O que é</h3>
              <p>
                Uma ferramenta das equipes de Vigilância em Saúde do Recife para antecipar os efeitos da chuva
                e da maré na saúde e avisar, com clareza, os bairros que precisam de cuidado.
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

          <h3 id="fontes" className={estilos.h3}>
            De onde vêm os dados
          </h3>
          {fontes.data ? (
            <>
              <ul className={estilos.fontes}>
                {emUso.map((x) => (
                  <li key={x.id} data-status={x.status}>
                    <span>
                      <strong>{x.nome}</strong>
                      <small>
                        {x.orgao}. {TIPOS_FONTE[x.tipo]}.
                      </small>
                    </span>
                    <span className={estilos.statusFonte}>
                      {x.status === "atualizada"
                        ? `Atualizada ${x.ultima_atualizacao ? quandoRelativo(x.ultima_atualizacao) : ""}`
                        : x.status === "desatualizada"
                          ? "Desatualizada"
                          : "Com falha na última carga"}
                    </span>
                  </li>
                ))}
              </ul>
              {planejadas > 0 && (
                <p className={estilos.nota}>
                  Outras {planejadas} fontes públicas estão planejadas e ainda não geram dados.
                </p>
              )}
            </>
          ) : (
            <p className={estilos.lead}>Carregando as fontes…</p>
          )}
          <p className={estilos.nota}>
            Quando um dado falta, o ClimaSense mostra “Dados insuficientes”. Ele nunca preenche lacunas com
            valores inventados. Feito por estudantes da CESAR School em 2026; os critérios dos níveis ainda
            serão validados com a Vigilância em Saúde e a Defesa Civil.
          </p>
        </div>
      </section>
    </CascaPublica>
  );
}
