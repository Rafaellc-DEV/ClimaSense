import { useEffect, useMemo, useRef } from "react";
import { Link } from "react-router-dom";
import { distritoPorExtenso } from "@/textos/glossario";
import { SeloNivel } from "@/design-system/componentes/SeloNivel";
import { NIVEIS, type ChaveNivel } from "@/design-system/niveis";
import { quandoRelativo } from "@/lib/formatos";
import { CartaoAbrigo } from "./CartaoAbrigo";
import { formatarDistancia, maisPertoDe, pertoDoBairro } from "./abrigosPublicos";
import type { Bairro, Busca } from "./useBusca";
import type { Abrigos } from "./useAbrigos";
import type { AvisoPublico } from "./useEstado";
import estilos from "./ResultadoBusca.module.css";

const ABERTURA: Record<string, string> = {
  informativo: "Aviso preventivo",
  atencao: "Atenção",
  alerta: "Alerta",
  critico: "Situação crítica",
};

/** Mais longe que isto, a pessoa está fora do Recife: nenhum abrigo cadastrado é “perto”. */
const LONGE_KM = 40;

function CartaoDoBairro({ bairro, aviso }: { bairro: string; aviso: AvisoPublico }) {
  const nivel = (aviso.nivel in NIVEIS ? aviso.nivel : "informativo") as ChaveNivel;
  return (
    <article className={estilos.aviso} data-nivel={nivel}>
      <SeloNivel nivel={nivel} />
      <h3 className={estilos.titulo}>
        {ABERTURA[nivel]} para {bairro} até {quandoRelativo(aviso.validade_fim)}.
      </h3>
      <p className={estilos.assunto}>{aviso.titulo}</p>
      {aviso.orientacoes.length > 0 ? (
        <div className={estilos.fazer}>
          <h4>O que fazer</h4>
          <ul>
            {aviso.orientacoes.slice(0, 3).map((o, i) => (
              <li key={i}>{o}</li>
            ))}
          </ul>
        </div>
      ) : (
        <p className={estilos.assunto}>{NIVEIS[nivel].acao}</p>
      )}
      <p className={estilos.fonte}>
        Fonte: {aviso.emitido_por.replace(/^A /, "")}
        {aviso.publicado_em ? `, publicado ${quandoRelativo(aviso.publicado_em)}` : ""}.
      </p>
      <Link to={`/avisos/${aviso.id}`} className={estilos.ler}>
        Ler o comunicado completo<span className="so-leitor">: {aviso.titulo}</span>
      </Link>
    </article>
  );
}

function ListaAbrigos({
  titulo,
  nota,
  abrigos,
  itens,
  aoVerTodos,
  vazio = "Nenhum local de abrigo cadastrado ainda.",
}: {
  titulo: string;
  vazio?: string;
  nota?: string;
  abrigos: Abrigos;
  itens: { abrigo: Abrigos["itens"][number]; nota?: string }[];
  aoVerTodos: () => void;
}) {
  return (
    <section className={estilos.abrigos} aria-labelledby="abrigos-perto">
      <h3 id="abrigos-perto" className={estilos.h3}>
        {titulo}
      </h3>
      {nota && <p className={estilos.nota}>{nota}</p>}
      {abrigos.carregando && <p className={estilos.nota}>Verificando os abrigos…</p>}
      {abrigos.indisponivel && (
        <p className={estilos.nota}>A lista de abrigos ainda não está disponível. Ligue 0800 081 3400.</p>
      )}
      {abrigos.erro && (
        <p className={estilos.nota}>
          Não foi possível carregar a lista de abrigos agora. Isso não quer dizer que não há abrigo. Ligue
          0800 081 3400.{" "}
          <button type="button" className={estilos.link} onClick={abrigos.refazer}>
            Tentar de novo
          </button>
        </p>
      )}
      {!abrigos.carregando && !abrigos.indisponivel && !abrigos.erro && itens.length === 0 && (
        <p className={estilos.nota}>{vazio}</p>
      )}
      {itens.length > 0 && (
        <>
          <ul className={estilos.cartoes}>
            {itens.map((x) => (
              <CartaoAbrigo key={x.abrigo.id} a={x.abrigo} compacto nota={x.nota} />
            ))}
          </ul>
          <button type="button" className={estilos.link} onClick={aoVerTodos}>
            Ver todos os abrigos
          </button>
        </>
      )}
    </section>
  );
}

/**
 * O resultado da busca, no mesmo lugar do campo. É a única região viva da página: o leitor de tela anuncia só
 * esta, e só quando ela muda. Cada estado diz o que se sabe, o que não se sabe e o que fazer.
 */
export function ResultadoBusca({
  busca,
  abrigos,
  irParaAba,
}: {
  busca: Busca;
  abrigos: Abrigos;
  irParaAba: (aba: "comunicados" | "abrigos" | "mapa") => void;
}) {
  const { resultado: r, localizacao: loc } = busca;
  const caixa = useRef<HTMLDivElement>(null);

  // quando o resultado chega, garante que ele esteja à vista (sem rolar à toa se já está)
  useEffect(() => {
    if (r.tipo === "ocioso" || r.tipo === "curto") return;
    caixa.current?.scrollIntoView?.({ block: "nearest" });
  }, [r.tipo]);

  const bairro: Bairro | null = r.tipo === "ok" || r.tipo === "erro" ? r.bairro : null;
  const proximos = useMemo(() => {
    if (!bairro) return [];
    const dist = bairro.distrito_id ? distritoPorExtenso(bairro.distrito_id) : null;
    return pertoDoBairro(abrigos.itens, bairro.nome, dist)
      .slice(0, 3)
      .map((x) => ({
        abrigo: x.abrigo,
        nota:
          x.grupo === "bairro"
            ? `No bairro ${bairro.nome}`
            : x.grupo === "distrito"
              ? "Mesmo distrito"
              : undefined,
      }));
  }, [bairro, abrigos.itens]);

  const perto = useMemo(
    () => (loc.tipo === "ok" ? maisPertoDe(abrigos.itens, { lat: loc.lat, lon: loc.lon }) : []),
    [loc, abrigos.itens],
  );

  let conteudo = null;
  if (r.tipo === "carregando") {
    conteudo = (
      <div className={estilos.painel} aria-busy="true">
        <h2 className={estilos.h2}>Verificando os avisos…</h2>
        <div className={estilos.esqueleto} aria-hidden="true">
          <i />
          <i />
        </div>
      </div>
    );
  } else if (r.tipo === "naoEncontrado") {
    conteudo = (
      <div className={estilos.painel}>
        <h2 className={estilos.h2}>Bairro não encontrado</h2>
        <p>Não achamos esse bairro. Confira a escrita (sem acento funciona) ou escolha no mapa.</p>
        <button type="button" className={estilos.botao} onClick={() => irParaAba("mapa")}>
          Escolher no mapa
        </button>
      </div>
    );
  } else if (r.tipo === "escolher") {
    conteudo = (
      <div className={estilos.painel}>
        <h2 className={estilos.h2}>Qual destes é o seu bairro?</h2>
        <ul className={estilos.opcoes}>
          {r.opcoes.map((b) => (
            <li key={b.id}>
              <button type="button" onClick={() => busca.escolher(b)}>
                <strong>{b.nome}</strong>
                {b.distrito_id && <span>{distritoPorExtenso(b.distrito_id)}</span>}
              </button>
            </li>
          ))}
        </ul>
      </div>
    );
  } else if (r.tipo === "erro") {
    conteudo = (
      <>
        <div className={estilos.painel} data-tom="erro">
          <h2 className={estilos.h2}>Não foi possível verificar os avisos agora.</h2>
          <p>Isso não quer dizer que não há risco. Em emergência, ligue 199.</p>
          <button type="button" className={estilos.botao} onClick={busca.tentarDeNovo}>
            Tentar de novo
          </button>
        </div>
        <ListaAbrigos
          titulo={`Abrigos perto de ${r.bairro.nome}`}
          abrigos={abrigos}
          itens={proximos}
          aoVerTodos={() => irParaAba("abrigos")}
        />
      </>
    );
  } else if (r.tipo === "ok") {
    const semDados = r.bairro.id === "";
    conteudo = (
      <>
        <div className={estilos.painel} data-tom={r.avisos.length ? "aviso" : "sem"}>
          <h2 className={estilos.h2}>
            {r.avisos.length ? `Avisos para ${r.bairro.nome}` : `Sem aviso publicado para ${r.bairro.nome}`}
          </h2>
          {r.avisos.length > 0 ? (
            <div className={estilos.avisos}>
              {r.avisos.map((a) => (
                <CartaoDoBairro key={a.id} bairro={r.bairro.nome} aviso={a} />
              ))}
            </div>
          ) : semDados ? (
            <p>
              Ainda não há dados suficientes para este bairro. Em dúvida, ligue{" "}
              <a href="tel:08000813400">0800 081 3400</a> (Defesa Civil, 24 h, grátis).
            </p>
          ) : (
            <p>
              Nenhum aviso ativo publicado pela equipe para {r.bairro.nome}. Isso não significa ausência de
              risco. Em chuva forte, evite áreas que alagam e acompanhe a Defesa Civil.
            </p>
          )}
        </div>
        <ListaAbrigos
          titulo={`Abrigos perto de ${r.bairro.nome}`}
          abrigos={abrigos}
          itens={proximos}
          aoVerTodos={() => irParaAba("abrigos")}
        />
      </>
    );
  } else if (loc.tipo === "pedindo") {
    conteudo = (
      <div className={estilos.painel} aria-busy="true">
        <h2 className={estilos.h2}>Procurando a sua localização…</h2>
        <p>Aceite o pedido do navegador. Se preferir, digite o nome do bairro acima.</p>
      </div>
    );
  } else if (loc.tipo === "negada") {
    conteudo = (
      <div className={estilos.painel}>
        <h2 className={estilos.h2}>Localização não usada</h2>
        <p>Sem problema. Digite o nome do bairro acima.</p>
      </div>
    );
  } else if (loc.tipo === "indisponivel" || loc.tipo === "falhou") {
    conteudo = (
      <div className={estilos.painel}>
        <h2 className={estilos.h2}>Não foi possível obter a localização</h2>
        <p>Digite o nome do bairro acima para ver os avisos.</p>
      </div>
    );
  } else if (loc.tipo === "imprecisa") {
    conteudo = (
      <div className={estilos.painel}>
        <h2 className={estilos.h2}>A localização está imprecisa</h2>
        <p>
          Ela não serve para dizer o seu bairro, e por isso não afirmamos nada sobre avisos. Digite o nome do
          bairro acima.
        </p>
      </div>
    );
  } else if (loc.tipo === "ok") {
    const longe = perto.length > 0 && perto[0].km > LONGE_KM;
    conteudo = (
      <>
        <div className={estilos.painel}>
          <h2 className={estilos.h2}>Localização encontrada</h2>
          <p>
            Pela localização não dá para saber o seu bairro, nem se há aviso nele. Digite o nome do bairro
            acima para ver os avisos.
          </p>
        </div>
        {longe ? (
          <section className={estilos.abrigos}>
            <h3 className={estilos.h3}>Abrigos perto de você</h3>
            <p className={estilos.nota}>
              Sua localização está longe dos abrigos cadastrados no Recife. Digite o bairro acima ou ligue
              0800 081 3400.
            </p>
          </section>
        ) : (
          <ListaAbrigos
            titulo="Abrigos mais perto de você"
            nota="Distância em linha reta. A rota real pode ser maior."
            vazio="Nenhum abrigo cadastrado tem localização no mapa. Ligue 0800 081 3400."
            abrigos={abrigos}
            itens={perto.map((x) => ({ abrigo: x.abrigo, nota: `a ${formatarDistancia(x.km)} de você` }))}
            aoVerTodos={() => irParaAba("abrigos")}
          />
        )}
      </>
    );
  }

  return (
    <div ref={caixa} className={estilos.regiao} aria-live="polite">
      {conteudo}
    </div>
  );
}
