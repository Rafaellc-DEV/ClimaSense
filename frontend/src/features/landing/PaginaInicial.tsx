import { useEffect, useRef } from "react";
import {
  ArrowLeft,
  ArrowRight,
  BellOff,
  CloudRain,
  Map,
  Megaphone,
  RefreshCw,
  Route,
  Search,
} from "lucide-react";
import rios from "@/assets/tracos/rios.svg?raw";
import { CartaoAviso } from "@/design-system/componentes/CartaoAviso";
import { ReguaMare } from "@/design-system/componentes/ReguaMare";
import type { ChaveNivel } from "@/design-system/niveis";
import { quandoRelativo } from "@/lib/formatos";
import type { Esquemas } from "@/lib/api";
import { BuscaBairro } from "./BuscaBairro";
import { CascaPublica, FaixaEmergencia, Onda } from "./CascaPublica";
import { MapaAvisos } from "./MapaAvisos";
import { SecaoSobre } from "./SecaoSobre";
import { useAvisos, useEstado, type Situacao } from "./useEstado";
import { useHolofote } from "./useHolofote";
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
    return {
      nivel: "insuficiente",
      titulo: "Verificando os avisos…",
      apoio: s.tentandoDeNovo
        ? "A primeira tentativa não respondeu. Tentando de novo…"
        : "Consultando os avisos da equipe e as estações de chuva…",
    };
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

/** Os rios do herói se desenham uma vez, junto com a subida da água na régua (pathLength normaliza o traço). */
const riosTracados = rios.replace('<path class="agua"', '<path pathLength="1" class="agua"');

/** Atalhos em círculo logo abaixo do herói: levam às partes da página que respondem às dúvidas mais comuns. */
const ATALHOS = [
  { href: "#bairro", rotulo: "Buscar meu bairro", Icone: Search },
  { href: "#comunicados", rotulo: "Ver comunicados", Icone: Megaphone },
  { href: "#mapa", rotulo: "Ver o mapa", Icone: Map },
  { href: "#como-funciona", rotulo: "Entender os avisos", Icone: Route },
];

/** Landing pública (design §9.1): em 3 segundos, a pessoa sabe se existe aviso e o que fazer. */
export function PaginaInicial() {
  const situacao = useEstado();
  const avisos = useAvisos();
  const trilho = useRef<HTMLUListElement>(null);
  const heroi = useRef<HTMLElement>(null);
  useHolofote(heroi);
  const f = frase(situacao);
  const niveis = situacao.tipo === "ok" ? situacao.estado.niveis_por_distrito : null;

  useEffect(() => {
    document.title = "ClimaSense: avisos de chuva e alagamento no Recife";
  }, []);

  const rolar = (sentido: 1 | -1) =>
    trilho.current?.scrollBy({
      left: sentido * trilho.current.clientWidth * 0.85,
      behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth",
    });

  return (
    <CascaPublica inicio>
      <section ref={heroi} className={estilos.heroi} aria-labelledby="estado">
        <div className={`${estilos.malha} ${estilos.heroiMalha}`} aria-hidden="true" />
        <div className={`${estilos.malha} ${estilos.heroiHolofote}`} aria-hidden="true" />
        <div
          className={estilos.heroiRios}
          aria-hidden="true"
          dangerouslySetInnerHTML={{ __html: riosTracados }}
        />
        <div className={estilos.heroiInterno}>
          <div className={estilos.heroiTexto}>
            <p className={estilos.sobrescrito}>
              <CloudRain aria-hidden="true" size={18} />
              Avisos de chuva e alagamento no Recife
            </p>
            {/* o h1 fica (é a região viva); só o texto troca, com uma entrada suave em vez de um corte seco */}
            <h1 id="estado" className={estilos.frase} aria-live="polite">
              <span key={f.titulo} className={estilos.entrada}>
                {f.titulo}
              </span>
            </h1>
            <p className={estilos.apoio}>
              {situacao.tipo === "carregando" && (
                <RefreshCw aria-hidden="true" size={18} className={estilos.girando} />
              )}
              <span key={f.apoio} className={estilos.entrada}>
                {f.apoio}
              </span>
            </p>
            {situacao.tipo === "ok" && (
              <p className={`${estilos.verificacao} ${estilos.entrada}`}>
                Última verificação: {quandoRelativo(situacao.estado.atualizado_em)}.
              </p>
            )}
          </div>
          <div className={estilos.heroiRegua}>
            <ReguaMare nivel={f.nivel} carregando={situacao.tipo === "carregando"} />
          </div>
          {/* no celular, o medidor dá lugar à faixa com marcador, que cabe na largura da tela */}
          <div className={estilos.heroiFaixa}>
            <ReguaMare nivel={f.nivel} carregando={situacao.tipo === "carregando"} formato="faixa" />
          </div>
        </div>
        <Onda cor="var(--cs-papel)" linha />
      </section>

      <div className={estilos.atalhos}>
        <FaixaEmergencia />
        <nav className={estilos.atalhosNav} aria-labelledby="atalhos-h">
          <h2 id="atalhos-h" className={estilos.etiqueta} data-tom="claro">
            Quero…
          </h2>
          <ul className={estilos.circulos}>
            {ATALHOS.map(({ href, rotulo, Icone }) => (
              <li key={href}>
                <a href={href} className={estilos.circulo}>
                  <span className={estilos.disco} data-tom="claro">
                    <Icone aria-hidden="true" size={30} strokeWidth={1.8} />
                  </span>
                  <span className={estilos.rotuloCirculo}>{rotulo}</span>
                </a>
              </li>
            ))}
          </ul>
        </nav>
      </div>

      <section id="bairro" className={estilos.secaoBusca} aria-labelledby="bairro-h">
        <h2 id="bairro-h" className={estilos.h2}>
          Há aviso para o seu bairro?
        </h2>
        <BuscaBairro />
      </section>

      <section id="mapa" className={estilos.secaoMapa} aria-labelledby="mapa-h">
        <div className={estilos.secao}>
          <MapaAvisos niveis={niveis} avisos={avisos.data}>
            <h2 id="mapa-h" className={estilos.h2}>
              Onde há aviso agora
            </h2>
            <p className={estilos.lead}>
              O Recife é dividido em 8 distritos sanitários. Escolha um para ver os bairros que fazem parte
              dele.
            </p>
          </MapaAvisos>
        </div>
      </section>

      <section id="comunicados" className={estilos.secao} aria-labelledby="comunicados-h">
        <div className={estilos.cabecalhoTrilho}>
          <div>
            <h2 id="comunicados-h" className={estilos.h2}>
              Comunicados em vigor
            </h2>
            <p className={estilos.lead}>
              Publicados pela Vigilância em Saúde do Recife, com o que fazer e até quando valem. Cada
              comunicado sai daqui sozinho quando vence.
            </p>
          </div>
          {(avisos.data?.length ?? 0) > 1 && (
            <div className={estilos.setas}>
              <button type="button" onClick={() => rolar(-1)} aria-label="Comunicados anteriores">
                <ArrowLeft aria-hidden="true" size={22} />
              </button>
              <button type="button" onClick={() => rolar(1)} aria-label="Próximos comunicados">
                <ArrowRight aria-hidden="true" size={22} />
              </button>
            </div>
          )}
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
            <ul id="avisos" ref={trilho} className={estilos.cartoes} tabIndex={0} aria-label="Comunicados">
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

      <section id="como-funciona" className={estilos.faixaClara} aria-labelledby="como-h">
        <div className={estilos.secao}>
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
        </div>
      </section>

      <SecaoSobre />
    </CascaPublica>
  );
}
