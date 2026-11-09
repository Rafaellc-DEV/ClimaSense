import { useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import { distritoPorExtenso } from "@/textos/glossario";
import { SeloNivel } from "@/design-system/componentes/SeloNivel";
import { NIVEIS, type ChaveNivel } from "@/design-system/niveis";
import { quandoRelativo } from "@/lib/formatos";
import type { Busca } from "./useBusca";
import type { AvisoPublico } from "./useEstado";
import estilos from "./ResultadoBusca.module.css";

const ABERTURA: Record<string, string> = {
  informativo: "Aviso preventivo",
  atencao: "Atenção",
  alerta: "Alerta",
  critico: "Situação crítica",
};

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

/**
 * O resultado da busca, no mesmo lugar do campo. É a única região viva da página: o leitor de tela anuncia só
 * esta, e só quando ela muda. Cada estado diz o que se sabe, o que não se sabe e o que fazer.
 */
export function ResultadoBusca({
  busca,
  irParaAba,
}: {
  busca: Busca;
  irParaAba: (aba: "comunicados" | "mapa") => void;
}) {
  const { resultado: r, localizacao: loc } = busca;
  const caixa = useRef<HTMLDivElement>(null);

  // quando o resultado chega, garante que ele esteja à vista (sem rolar à toa se já está)
  useEffect(() => {
    if (r.tipo === "ocioso" || r.tipo === "curto") return;
    caixa.current?.scrollIntoView?.({ block: "nearest" });
  }, [r.tipo]);

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
    conteudo = (
      <>
        <div className={estilos.painel}>
          <h2 className={estilos.h2}>Localização encontrada</h2>
          <p>
            Pela localização não dá para saber o seu bairro, nem se há aviso nele. Digite o nome do bairro
            acima para ver os avisos.
          </p>
        </div>
      </>
    );
  }

  return (
    <div ref={caixa} className={estilos.regiao} aria-live="polite">
      {conteudo}
    </div>
  );
}
