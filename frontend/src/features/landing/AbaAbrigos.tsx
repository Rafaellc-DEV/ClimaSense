import { useId, useMemo, useState } from "react";
import { formatarNumero, quandoRelativo } from "@/lib/formatos";
import { distritoPorExtenso } from "@/textos/glossario";
import { CartaoAbrigo } from "./CartaoAbrigo";
import {
  abertoConfirmado,
  filtrar,
  pertoDoBairro,
  type AbrigoPublico,
  type FiltroTipo,
} from "./abrigosPublicos";
import type { Abrigos } from "./useAbrigos";
import type { Busca } from "./useBusca";
import estilos from "./AbasLanding.module.css";

const POR_PAGINA = 12;

/**
 * Aba “Abrigos”: a resposta primeiro (há abrigo aberto agora?), depois a lista completa com filtros. Quando há um
 * bairro na busca da página, a lista começa pelos abrigos dele. Nada é inventado: sem confirmação de quem opera o
 * abrigo, o local aparece como “local de apoio cadastrado”.
 */
export function AbaAbrigos({ abrigos, busca }: { abrigos: Abrigos; busca: Busca }) {
  const [tipo, setTipo] = useState<FiltroTipo>("abrigos");
  const [soAbertos, setSoAbertos] = useState(false);
  const [quantos, setQuantos] = useState(POR_PAGINA);
  const idTipo = useId();

  const todos = abrigos.itens;
  const abertos = todos.filter((a) => abertoConfirmado(a) && a.tipo !== "cras");
  const bairro = busca.resultado.tipo === "ok" ? busca.resultado.bairro : null;

  const itens = useMemo(() => {
    const base = filtrar(todos, tipo, soAbertos);
    if (!bairro || tipo === "cras") return base.map((a) => ({ a, nota: undefined as string | undefined }));
    const dist = bairro.distrito_id ? distritoPorExtenso(bairro.distrito_id) : null;
    return pertoDoBairro(base, bairro.nome, dist).map((x) => ({
      a: x.abrigo as AbrigoPublico,
      nota:
        x.grupo === "bairro"
          ? `No bairro ${bairro.nome}`
          : x.grupo === "distrito"
            ? "Mesmo distrito"
            : undefined,
    }));
  }, [todos, tipo, soAbertos, bairro]);
  const visiveis = itens.slice(0, quantos);

  return (
    <div className={estilos.painel}>
      {abrigos.carregando && <p className={estilos.frase}>Verificando os abrigos…</p>}
      {!abrigos.carregando && !abrigos.indisponivel && !abrigos.erro && (
        <div>
          {abertos.length > 0 ? (
            <>
              <p className={estilos.frase} data-aberto="true">
                {abertos.length === 1 ? "1 abrigo aberto agora." : `${abertos.length} abrigos abertos agora.`}
              </p>
              <p className={estilos.lead}>
                Eles aparecem primeiro, com “Aberto agora” e quem informou. Se puder, ligue antes de ir.
              </p>
            </>
          ) : (
            <>
              <p className={estilos.frase}>Nenhum abrigo ativo neste momento.</p>
              <p className={estilos.lead}>
                {todos.length > 0
                  ? "Abaixo estão os locais que podem ser abertos em emergência. Em caso de alagamento ou deslizamento, ligue para a Defesa Civil: ela diz qual local está recebendo pessoas."
                  : "Em caso de alagamento ou deslizamento, ligue para a Defesa Civil: ela diz qual local está recebendo pessoas."}
              </p>
            </>
          )}
        </div>
      )}
      {abrigos.indisponivel && (
        <div>
          <p className={estilos.frase}>A lista de abrigos ainda não está disponível. Ligue 0800 081 3400.</p>
          <p className={estilos.lead}>
            Isso não quer dizer que não há abrigo: a Defesa Civil diz qual local está recebendo pessoas.
          </p>
        </div>
      )}
      {abrigos.erro && (
        <div>
          <p className={estilos.frase}>Não foi possível carregar a lista de abrigos agora.</p>
          <p className={estilos.lead}>
            Isso não quer dizer que não há abrigo. Ligue 0800 081 3400.{" "}
            <button type="button" className={estilos.link} onClick={abrigos.refazer}>
              Tentar de novo
            </button>
          </p>
        </div>
      )}

      {!abrigos.carregando && !abrigos.indisponivel && !abrigos.erro && todos.length === 0 && (
        <p className={estilos.vazio}>
          Nenhum local de abrigo cadastrado ainda. Quando a Prefeitura ou a equipe informar, os locais
          aparecem aqui com endereço e rota.
        </p>
      )}

      {todos.length > 0 && (
        <>
          <div className={estilos.filtros}>
            <div className={estilos.campo}>
              <label htmlFor={idTipo}>Tipo de local</label>
              <select
                id={idTipo}
                value={tipo}
                onChange={(e) => {
                  setTipo(e.target.value as FiltroTipo);
                  setQuantos(POR_PAGINA);
                }}
              >
                <option value="abrigos">Abrigos e pontos de apoio</option>
                <option value="cras">Assistência social (CRAS), não é abrigo</option>
                <option value="todos">Todos os locais</option>
              </select>
            </div>
            {abertos.length > 0 && (
              <label className={estilos.marcar}>
                <input type="checkbox" checked={soAbertos} onChange={(e) => setSoAbertos(e.target.checked)} />
                Só os abertos agora
              </label>
            )}
          </div>
          {tipo === "cras" && (
            <p className={estilos.nota}>
              O CRAS é um serviço de assistência social, não um abrigo. Procure-o para cadastro, benefícios e
              orientação depois do evento.
            </p>
          )}
          <p className={estilos.total} role="status">
            {itens.length === 0
              ? "Nenhum local encontrado com esse filtro."
              : `${formatarNumero(itens.length)} ${itens.length === 1 ? "local" : "locais"}${
                  abertos.length === 0 && tipo !== "cras" ? " que podem ser abertos em emergência" : ""
                }${bairro ? `, começando por ${bairro.nome}` : ""}`}
          </p>
          <ul className={estilos.abrigos} aria-label="Locais de abrigo">
            {visiveis.map((x) => (
              <CartaoAbrigo key={x.a.id} a={x.a} nota={x.nota} />
            ))}
          </ul>
          {itens.length > quantos && (
            <button type="button" className={estilos.mais} onClick={() => setQuantos((q) => q + POR_PAGINA)}>
              Mostrar mais {Math.min(POR_PAGINA, itens.length - quantos)} de {itens.length - quantos}
            </button>
          )}
        </>
      )}

      {(abrigos.aviso || abrigos.atualizadoEm) && (
        <p className={estilos.nota}>
          {abrigos.aviso}
          {abrigos.aviso && abrigos.atualizadoEm ? " " : ""}
          {abrigos.atualizadoEm && `Lista atualizada ${quandoRelativo(abrigos.atualizadoEm)}.`}
        </p>
      )}
    </div>
  );
}
