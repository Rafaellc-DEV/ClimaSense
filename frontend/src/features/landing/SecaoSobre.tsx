import {
  CloudRain,
  Database,
  Gauge,
  HeartPulse,
  Phone,
  RefreshCw,
  ShieldAlert,
  Waves,
  type LucideIcon,
} from "lucide-react";
import rios from "@/assets/tracos/rios.svg?raw";
import { useConsulta } from "@/lib/consultas";
import { quandoRelativo } from "@/lib/formatos";
import type { Esquemas } from "@/lib/api";
import { TIPOS_FONTE } from "@/textos/glossario";
import estilos from "./SecaoSobre.module.css";

type Fonte = Esquemas["FontePublica"];

/** Ícone de cada tipo de fonte: o que se mede, o que se prevê e o que se calcula. */
const ICONE_TIPO: Record<string, LucideIcon> = {
  observada: Gauge,
  prevista: CloudRain,
  derivada: Waves,
};

function textoStatus(f: Fonte): string {
  if (f.status === "atualizada")
    return f.ultima_atualizacao ? `Atualizada ${quandoRelativo(f.ultima_atualizacao)}` : "Atualizada";
  if (f.status === "desatualizada") return "Desatualizada";
  return "Com falha na última carga";
}

/** Régua vazia e tracejada: o desenho de “Dados insuficientes” no guia de marca. */
function ReguaVazia() {
  return (
    <svg className={estilos.reguaVazia} viewBox="0 0 44 112" aria-hidden="true" focusable="false">
      <rect x="2" y="2" width="22" height="108" rx="0" className={estilos.reguaCorpo} />
      {[22, 46, 70, 94].map((y) => (
        <line key={y} x1="26" x2="40" y1={y} y2={y} className={estilos.reguaMarca} />
      ))}
    </svg>
  );
}

/** Rio que liga as fontes: desenha-se uma vez quando a lista entra na tela. */
function Rio() {
  return (
    <svg
      className={estilos.rio}
      viewBox="0 0 40 400"
      preserveAspectRatio="none"
      aria-hidden="true"
      focusable="false"
    >
      <path
        d="M20,0 C34,40 6,80 20,120 C34,160 6,200 20,240 C34,280 6,320 20,360 C27,380 20,392 20,400"
        pathLength={1}
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  );
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

  const emUso = fontes.data.filter((x) => x.status !== "planejada");
  const planejadas = fontes.data.length - emUso.length;

  return (
    <>
      {emUso.length ? (
        <div className={estilos.leito}>
          <Rio />
          <ul className={estilos.fontes}>
            {emUso.map((x) => {
              const Icone = ICONE_TIPO[x.tipo] ?? Database;
              return (
                <li key={x.id} className={estilos.fonte} data-status={x.status}>
                  <span className={estilos.estacao} aria-hidden="true">
                    <Icone size={22} strokeWidth={1.9} />
                  </span>
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
              );
            })}
          </ul>
        </div>
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

/** “Sobre o ClimaSense” na landing: o que é, o que não é e de onde vêm os dados. */
export function SecaoSobre() {
  return (
    <section id="sobre" className={estilos.secao} aria-labelledby="sobre-h">
      <div className={estilos.interno}>
        <h2 id="sobre-h" className={estilos.h2}>
          Sobre o ClimaSense
        </h2>

        <div className={estilos.par}>
          <article className={estilos.eh}>
            <div className={estilos.pontos} aria-hidden="true" />
            <div className={estilos.conteudo}>
              <span className={estilos.disco} aria-hidden="true">
                <HeartPulse size={28} strokeWidth={1.8} />
              </span>
              <h3>O que é</h3>
              <p>
                Uma ferramenta das equipes de Vigilância em Saúde do Recife para antecipar os efeitos da chuva
                e da maré na saúde e avisar, com clareza, os bairros que precisam de cuidado.
              </p>
            </div>
          </article>

          <article className={estilos.naoEh}>
            <div
              className={estilos.naoEhRios}
              aria-hidden="true"
              dangerouslySetInnerHTML={{ __html: rios }}
            />
            <svg
              className={estilos.linhaDagua}
              viewBox="0 0 400 24"
              preserveAspectRatio="none"
              aria-hidden="true"
              focusable="false"
            >
              <path
                d="M0,14 C60,2 110,2 170,12 C230,22 290,24 340,12 C370,5 390,6 400,9"
                vectorEffect="non-scaling-stroke"
              />
            </svg>
            <div className={estilos.conteudo}>
              <span className={estilos.disco} data-tom="mare" aria-hidden="true">
                <ShieldAlert size={28} strokeWidth={1.8} />
              </span>
              <h3>O que não é</h3>
              <p>
                Não é alerta oficial e não substitui a Defesa Civil. Não prevê com certeza onde vai alagar. Na
                dúvida, siga a Defesa Civil e ligue 199.
              </p>
              <a className={estilos.ligar} href="tel:199">
                <Phone aria-hidden="true" size={20} />
                Ligar para a Defesa Civil: 199
              </a>
            </div>
          </article>
        </div>

        <div className={estilos.dados}>
          <div className={estilos.dadosLado}>
            <h3 id="fontes" className={estilos.h3}>
              De onde vêm os dados
            </h3>
            <div className={estilos.insuficiente}>
              <ReguaVazia />
              <p>
                Quando um dado falta, o ClimaSense mostra <strong>“Dados insuficientes”</strong>. Ele nunca
                preenche lacunas com valores inventados.
              </p>
            </div>
          </div>
          <div className={estilos.dadosLista}>
            <Fontes />
          </div>
        </div>
      </div>
    </section>
  );
}
