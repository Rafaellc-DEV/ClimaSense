/**
 * Os quatro números que respondem "onde decidir, quanto falta, onde já choveu, quem está exposto" (RF-09, RF-19, RF-20).
 * Usados no topo do Dashboards e do Mapa. Sem dado, cada um diz "Dados insuficientes" e a fonte que falta (RN-01).
 */
import type { ReactNode } from "react";
import { Esqueleto } from "@/design-system/componentes/Esqueleto";
import { Experimental } from "@/design-system/componentes/Pilula";
import { infoEstagio } from "@/features/evento/estagios";
import { formatarHoraMinuto, formatarNumero } from "@/lib/formatos";
import type { FonteMeta } from "@/lib/frescor";
import { ROTULO_INSUMO, type Janela } from "./indicadores";
import type { DadosDecisao } from "./usarDadosDecisao";
import estilos from "./Dashboards.module.css";

const mm = (v: number) => formatarNumero(v, v < 10 && !Number.isInteger(v) ? 1 : 0);

function Rodape({
  padrao,
  ids,
  consultadoEm,
  fontes,
}: {
  padrao: string;
  ids: string[];
  consultadoEm: number;
  fontes: FonteMeta[];
}) {
  const achadas = fontes.filter((f) => ids.includes(f.id));
  if (achadas.length > 0)
    return (
      <p className={estilos.fonte}>
        Fonte:{" "}
        {achadas.map((f, i) => (
          <span key={f.id}>
            {i > 0 && "; "}
            {f.nome}
            {f.atualizado_em ? ` · ${formatarHoraMinuto(f.atualizado_em)}` : " · sem hora de atualização"}
          </span>
        ))}
      </p>
    );
  return (
    <p className={estilos.fonte}>
      Fonte: {padrao}
      {consultadoEm ? `, consultado às ${formatarHoraMinuto(consultadoEm)}` : ""}
    </p>
  );
}

function Cartao({
  rotulo,
  experimental,
  carregando,
  insuficiente,
  children,
  rodape,
}: {
  rotulo: string;
  experimental?: boolean;
  carregando: boolean;
  /** Texto do que falta: mostra "Dados insuficientes" no lugar do valor. */
  insuficiente: string | null;
  children?: ReactNode;
  rodape: ReactNode;
}) {
  return (
    <li className={estilos.numero}>
      <h3 className={estilos.rotulo}>
        {rotulo}
        {experimental && <Experimental />}
      </h3>
      {carregando ? (
        <div role="status" aria-busy="true">
          <Esqueleto largura="6rem" altura="1.75rem" forma="bloco" />
          <span className="so-leitor">Carregando {rotulo}…</span>
        </div>
      ) : insuficiente ? (
        <>
          <p className={estilos.semDado}>Dados insuficientes</p>
          <p className={estilos.detalhe}>Falta: {insuficiente}.</p>
        </>
      ) : (
        children
      )}
      {rodape}
    </li>
  );
}

export function NumerosChave({
  d,
  janela,
  compacto = false,
}: {
  d: DadosDecisao;
  janela: Janela;
  compacto?: boolean;
}) {
  const { pendencias: p, gatilhos: g, maior, pessoas } = d;
  const falhaEstagios = d.distritos.isError && d.bairros.isError;
  const semEstagios = !p || p.avaliados === 0 || p.semDados === p.avaliados;
  const topo = g?.itens[0];
  const nomeTerritorio = p?.itens[0]?.nivel === "distrito" ? "distritos" : "bairros";

  return (
    <ul className={estilos.numeros} aria-label="Números principais" data-compacto={compacto}>
      <Cartao
        rotulo="Decisões pendentes"
        experimental
        carregando={d.distritos.isPending && d.bairros.isPending}
        insuficiente={
          falhaEstagios || semEstagios ? "os estágios sugeridos (previsão de chuva e maré)" : null
        }
        rodape={
          <Rodape
            padrao="estágios sugeridos e declarados (ClimaSense)"
            ids={[]}
            consultadoEm={d.bairros.dataUpdatedAt || d.distritos.dataUpdatedAt}
            fontes={d.fontes}
          />
        }
      >
        {p && (
          <>
            <p className={estilos.valor}>
              {p.total}
              <span> {p.total === 1 ? nomeTerritorio.replace(/s$/, "") : nomeTerritorio}</span>
            </p>
            <p className={estilos.detalhe}>
              {p.total === 0
                ? "Nenhuma sugestão acima do declarado."
                : `Sugestão acima do declarado, em ${p.distritos} ${p.distritos === 1 ? "distrito" : "distritos"}.`}
              {p.semDados > 0 && ` Sem dados em ${p.semDados}.`}
            </p>
          </>
        )}
      </Cartao>

      <Cartao
        rotulo="Próximo gatilho"
        experimental
        carregando={d.distritos.isPending}
        insuficiente={
          !g || (!topo && g.noTopo === 0) ? "a previsão de chuva por distrito (Open-Meteo)" : null
        }
        rodape={
          <Rodape
            padrao="previsão de chuva por distrito e limiares dos estágios"
            ids={["open-meteo-previsao"]}
            consultadoEm={d.distritos.dataUpdatedAt}
            fontes={d.fontes}
          />
        }
      >
        {topo ? (
          <>
            <p className={estilos.valor}>
              {mm(topo.falta)}
              <span> mm</span>
            </p>
            <p className={estilos.detalhe}>
              {topo.nome}: falta de {ROTULO_INSUMO[topo.insumo]} para {infoEstagio(topo.proximo).rotulo}.
            </p>
          </>
        ) : (
          <p className={estilos.detalhe}>Todos os distritos já estão no estágio mais alto.</p>
        )}
      </Cartao>

      <Cartao
        rotulo={`Maior chuva em ${janela} h`}
        carregando={d.situacao.isPending}
        insuficiente={maior ? null : "nenhum pluviômetro com leitura (APAC)"}
        rodape={
          <Rodape
            padrao="pluviômetros (APAC)"
            ids={["apac-chuva"]}
            consultadoEm={d.situacao.dataUpdatedAt}
            fontes={d.fontes}
          />
        }
      >
        <p className={estilos.valor}>
          {maior ? mm(maior.mm) : ""}
          <span> mm</span>
        </p>
        <p className={estilos.detalhe}>
          {maior?.nome}
          {maior?.estacoes ? ` · ${maior.estacoes}` : ""}
        </p>
      </Cartao>

      <Cartao
        rotulo="Pessoas em bairros em alerta"
        experimental
        carregando={d.impacto.isPending}
        insuficiente={pessoas ? null : "a previsão de chuva e maré (Open-Meteo)"}
        rodape={
          <Rodape
            padrao="IBGE, Censo 2022, e estágios sugeridos"
            ids={["ibge-censo-2022-bairro"]}
            consultadoEm={d.impacto.dataUpdatedAt}
            fontes={d.fontes}
          />
        }
      >
        {pessoas && pessoas.bairros === 0 ? (
          <>
            <p className={estilos.valor}>0</p>
            <p className={estilos.detalhe}>Nenhum bairro com sugestão de Alerta ou mais.</p>
          </>
        ) : (
          pessoas && (
            <>
              <p className={estilos.valor}>
                {pessoas.bairros}
                <span> {pessoas.bairros === 1 ? "bairro" : "bairros"}</span>
              </p>
              <p className={estilos.detalhe}>
                {pessoas.idosos === null || pessoas.criancas === null
                  ? "Dados insuficientes: contagem de moradores sem dado ou omitida."
                  : `${pessoas.parcial ? "Pelo menos " : ""}${formatarNumero(pessoas.idosos)} idosos e ${formatarNumero(pessoas.criancas)} crianças que moram lá.`}
              </p>
            </>
          )
        )}
      </Cartao>
    </ul>
  );
}
