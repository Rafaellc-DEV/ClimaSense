import { CloudRain, Info, RefreshCw, ShieldAlert } from "lucide-react";
import { useConsulta } from "@/lib/consultas";
import { noProduto } from "@/lib/fontes";
import { quandoRelativo } from "@/lib/formatos";
import type { Esquemas } from "@/lib/api";
import { TIPOS_FONTE } from "@/textos/glossario";
import estilos from "./SecaoSobre.module.css";

type Fonte = Esquemas["FontePublica"];

function textoStatus(f: Fonte): string {
  if (f.status === "atualizada")
    return f.ultima_atualizacao ? `Atualizada ${quandoRelativo(f.ultima_atualizacao)}` : "Atualizada";
  if (f.status === "desatualizada") return "Desatualizada";
  return "Com falha na última carga";
}

function Fontes() {
  const fontes = useConsulta<Fonte[]>("/publico/fontes", { staleTime: 10 * 60_000 });

  if (fontes.isPending)
    return (
      <p className={estilos.estado} role="status">
        Carregando as fontes…
      </p>
    );

  if (fontes.isError)
    return (
      <div className={estilos.estado} role="status">
        <p>
          Não foi possível carregar a lista de fontes agora. Os avisos publicados continuam valendo. Tente de
          novo em alguns minutos.
        </p>
        <button
          type="button"
          className={estilos.tentar}
          onClick={() => void fontes.refetch()}
          disabled={fontes.isFetching}
        >
          <RefreshCw aria-hidden="true" size={18} />
          {fontes.isFetching ? "Carregando…" : "Tentar de novo"}
        </button>
      </div>
    );

  const doProduto = fontes.data.filter(noProduto);
  const emUso = doProduto.filter((x) => x.status !== "planejada");
  const planejadas = doProduto.length - emUso.length;

  return (
    <>
      {emUso.length ? (
        <ul className={estilos.fontes}>
          {emUso.map((x) => (
            <li key={x.id} className={estilos.fonte} data-status={x.status}>
              <span className={estilos.fonteTexto}>
                <strong>{x.nome}</strong>
                <span>
                  {x.orgao}. {TIPOS_FONTE[x.tipo] ?? x.tipo}.
                </span>
              </span>
              <span className={estilos.status} data-status={x.status}>
                {textoStatus(x)}
              </span>
            </li>
          ))}
        </ul>
      ) : (
        <p className={estilos.estado}>
          Nenhuma fonte está gerando dados neste momento. Enquanto isso, o ClimaSense mostra “Dados
          insuficientes” onde faltar informação.
        </p>
      )}
      {planejadas > 0 && (
        <p className={estilos.planejadas}>
          {planejadas === 1
            ? "Outra fonte pública está planejada e ainda não gera dados."
            : `Outras ${planejadas} fontes públicas estão planejadas e ainda não geram dados.`}
        </p>
      )}
    </>
  );
}

/** Conteúdo de “Quem somos e de onde vêm os dados” (aberto dentro do Recolhível da página inicial). */
export function SecaoSobre() {
  return (
    <div className={estilos.sobre}>
      <section aria-labelledby="desafio-h">
        <h3 id="desafio-h" className={estilos.h3}>
          <span className={estilos.disco}>
            <CloudRain aria-hidden="true" size={20} />
          </span>
          O desafio das chuvas no Recife
        </h3>
        <p>
          O Recife tem áreas baixas, morros, muitos rios e canais, e a maré alta dificulta o escoamento. Por
          isso, chuvas intensas podem causar alagamentos e deslizamentos, com riscos à saúde, como acidentes e
          doenças transmitidas pela água, entre elas a leptospirose.
        </p>
        <p>
          Desde 2022, a Portaria GM/MS nº 4.185 organiza no SUS a vigilância em saúde dos riscos de desastres,
          o Vigidesastres. O ClimaSense apoia esse trabalho no Recife, começando pela chuva.
        </p>
      </section>

      <section aria-labelledby="eh-h">
        <h3 id="eh-h" className={estilos.h3}>
          <span className={estilos.disco}>
            <Info aria-hidden="true" size={20} />
          </span>
          O que é
        </h3>
        <p>
          O ClimaSense é um projeto da CESAR School, feito a partir de um desafio da Vigilância em Saúde do
          Recife, para apoiar a preparação e a resposta às chuvas fortes. Ele reúne num só lugar a previsão de
          chuva, a previsão de maré e o mapa oficial dos distritos e bairros. Assim a equipe vê mais cedo onde
          pode precisar agir e avisa a população com clareza. Está em fase de teste.
        </p>
      </section>

      <section aria-labelledby="naoeh-h" className={estilos.naoEh}>
        <svg
          className={estilos.linhaDagua}
          viewBox="0 0 400 24"
          preserveAspectRatio="none"
          aria-hidden="true"
          focusable="false"
        >
          <path
            d="M0,12 C50,0 100,24 150,12 S250,0 300,12 S350,24 400,12"
            vectorEffect="non-scaling-stroke"
          />
        </svg>
        <h3 id="naoeh-h" className={estilos.h3}>
          <span className={estilos.disco}>
            <ShieldAlert aria-hidden="true" size={20} />
          </span>
          O que não é
        </h3>
        <p>
          Não é alerta oficial e não substitui a Defesa Civil. Não prevê com certeza onde vai alagar. Na
          dúvida, siga a Defesa Civil e ligue 199.
        </p>
      </section>

      <section aria-labelledby="fontes" className={estilos.dados}>
        <h3 id="fontes" className={estilos.h3}>
          De onde vêm os dados
        </h3>
        <p>
          Quando um dado falta, o ClimaSense mostra <strong>“Dados insuficientes”</strong>. Ele nunca preenche
          lacunas com valores inventados.
        </p>
        <Fontes />
      </section>
    </div>
  );
}
