import { Link } from "react-router-dom";
import { CabecalhoTela } from "@/app/AppShell";
import { Carregando, FalhaCarga, Painel } from "@/design-system/componentes/Painel";
import { Tabela } from "@/design-system/componentes/Tabela";
import type { Esquemas } from "@/lib/api";
import { useConsulta } from "@/lib/consultas";
import { formatarDataHora } from "@/lib/formatos";
import { TIPOS_FONTE } from "@/textos/glossario";
import { StatusFonte } from "./StatusFonte";
import estilos from "./Fontes.module.css";

type Fonte = Esquemas["Fonte"];

/** O que cada fonte planejada vai trazer quando o conector existir (resumo de docs/dicionario-dados). */
export const PLANOS: Record<string, string> = {
  "ana-telemetria":
    "Chuva e nível dos rios medidos nas estações telemétricas da ANA. Exige cadastro e credenciais.",
  "apac-chuva": "Chuva acumulada em 24 h nos pluviômetros da APAC, a agência estadual de águas e clima.",
  inmet: "Medições da estação automática do INMET no Recife (A301): chuva, temperatura e umidade.",
  cemaden: "Pluviômetros automáticos do Cemaden espalhados pelos bairros.",
  "mare-marinha":
    "Tábua de maré oficial da Marinha para o Porto do Recife, para comparar com o nível previsto.",
  "recife-alagamento":
    "Ocorrências de alagamento registradas pela Defesa Civil nos Dados Abertos do Recife, marcadas como não confirmadas.",
};

export function TelaFontes() {
  const f = useConsulta<Fonte[]>("/fontes");
  const ativas = f.data?.filter((x) => x.status !== "planejada") ?? [];
  const planejadas = f.data?.filter((x) => x.status === "planejada") ?? [];
  return (
    <>
      <CabecalhoTela
        titulo="Fontes de dados"
        proposito="De onde vem cada dado do ClimaSense, quando foi atualizado e se está em dia. Todas as fontes são reais."
      />
      {f.isPending && <Carregando />}
      {f.isError && <FalhaCarga erro={f.error} aoTentar={() => f.refetch()} />}
      {f.data && (
        <div className={estilos.pilha}>
          <Painel titulo="Em uso" id="f-uso">
            <Tabela
              legenda="Fontes em uso, com status e última atualização"
              legendaVisivel={false}
              linhas={ativas}
              chaveLinha={(x) => x.id}
              colunas={[
                {
                  chave: "nome",
                  titulo: "Fonte",
                  celula: (x) => (
                    <span className={estilos.nomeFonte}>
                      <Link to={`/app/fontes/${x.id}`}>{x.nome}</Link>
                      <span>{x.orgao}</span>
                    </span>
                  ),
                },
                { chave: "tipo", titulo: "Tipo", celula: (x) => TIPOS_FONTE[x.tipo] ?? x.tipo },
                { chave: "status", titulo: "Status", celula: (x) => <StatusFonte status={x.status} /> },
                {
                  chave: "quando",
                  titulo: "Última atualização",
                  celula: (x) =>
                    x.ultima_atualizacao ? formatarDataHora(x.ultima_atualizacao) : "Nunca carregada",
                },
                {
                  chave: "limite",
                  titulo: "Fica desatualizada após",
                  numerica: true,
                  celula: (x) => limiteTexto(x.limite_desatualizacao_h),
                },
              ]}
            />
          </Painel>
          <Painel titulo="Planejadas" id="f-planejadas">
            <p className={estilos.explicacao}>
              Estas fontes já foram escolhidas, mas ainda não têm conector. Enquanto isso, elas não geram
              nenhum dado, e as telas que dependem delas mostram “Dados insuficientes”.
            </p>
            <ul className={estilos.planejadas}>
              {planejadas.map((x) => (
                <li key={x.id}>
                  <div>
                    <h3>
                      <Link to={`/app/fontes/${x.id}`}>{x.nome}</Link>
                    </h3>
                    <p>{PLANOS[x.id] ?? x.orgao}</p>
                  </div>
                  <StatusFonte status="planejada" />
                </li>
              ))}
            </ul>
          </Painel>
        </div>
      )}
    </>
  );
}

export function limiteTexto(horas: number) {
  if (horas % (24 * 365) === 0) return `${horas / (24 * 365)} ano${horas > 24 * 365 ? "s" : ""}`;
  if (horas % 24 === 0) return `${horas / 24} dia${horas > 24 ? "s" : ""}`;
  return `${horas} h`;
}
