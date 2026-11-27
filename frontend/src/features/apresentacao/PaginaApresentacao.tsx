import { ArrowRight, BrainCircuit, Database, Layers3, Map, Workflow } from "lucide-react";
import styles from "./PaginaApresentacao.module.css";

const pipeline = [
  {
    etapa: "01 · ORIGEM",
    titulo: "Fontes de dados",
    texto: "Open-Meteo, APAC, dados abertos do Recife e fontes de saúde.",
    codigo: "backend/climasense/etl/conectores/",
  },
  {
    etapa: "02 · EXTRAIR",
    titulo: "Conectores ETL",
    texto: "Cada conector busca uma fonte e registra a execução. O lote é identificado para rastreio.",
    codigo: "backend/climasense/etl/conectores/base.py",
  },
  {
    etapa: "03 · BRONZE",
    titulo: "MongoDB Atlas",
    texto: "Guarda os documentos originais da coleta e os dados geográficos do território.",
    codigo: "backend/climasense/etl/load.py · data/territorio/",
  },
  {
    etapa: "04 · TRANSFORMAR",
    titulo: "Limpeza e validação",
    texto: "O ETL relê o lote da Bronze, normaliza campos, valida e carrega os dados tratados.",
    codigo: "backend/climasense/etl/conectores/ · load.py",
  },
  {
    etapa: "05 · SILVER → GOLD",
    titulo: "PostgreSQL / Neon",
    texto: "Silver guarda dados estruturados; Gold contém agregações SQL prontas para consulta.",
    codigo: "backend/migrations/versions/ · backend/climasense/etl/gold.py",
  },
  {
    etapa: "06 · CONSUMO",
    titulo: "API e aplicação",
    texto: "FastAPI consulta os dados e entrega respostas ao frontend React.",
    codigo: "backend/climasense/api/routers/ · backend/climasense/servicos/",
  },
];

const funcionalidades = [
  "Mapa de bairros e distritos",
  "Situação de chuva, previsão e alertas",
  "Séries históricas e dashboards",
  "Simulador de impacto e prioridades",
  "Indicadores de saúde como contexto",
  "Fontes, qualidade, usuários e auditoria",
];

function LinhaPipeline({ etapa }: { etapa: (typeof pipeline)[number] }) {
  return (
    <article className={styles.passo}>
      <span className={styles.etapa}>{etapa.etapa}</span>
      <div>
        <h3>{etapa.titulo}</h3>
        <p>{etapa.texto}</p>
        <code>{etapa.codigo}</code>
      </div>
    </article>
  );
}

export function PaginaApresentacao() {
  return (
    <main className={styles.pagina}>
      <header className={styles.topo}>
        <span className={styles.marca}>
          CLIMASENSE <span>/</span> VISÃO TÉCNICA
        </span>
        <h1>Do dado à decisão</h1>
        <p>Como os dados percorrem o backend — e onde encontrar cada parte no código.</p>
      </header>

      <section className={styles.secao} aria-labelledby="pipeline">
        <div className={styles.tituloSecao}>
          <Workflow size={19} />
          <div>
            <span>01 / CAMINHO DO DADO</span>
            <h2 id="pipeline">Pipeline: origem → consumo</h2>
          </div>
        </div>
        <div className={styles.trilho}>
          {pipeline.map((etapa, i) => (
            <div className={styles.parada} key={etapa.etapa}>
              <LinhaPipeline etapa={etapa} />
              {i < pipeline.length - 1 && <ArrowRight className={styles.seta} size={16} aria-hidden="true" />}
            </div>
          ))}
        </div>
        <p className={styles.nota}>
          Regra de qualidade: dado ausente permanece ausente — não é convertido em zero.
        </p>
      </section>

      <section className={styles.secao} aria-labelledby="bancos">
        <div className={styles.tituloSecao}>
          <Database size={19} />
          <div>
            <span>02 / PERSISTÊNCIA</span>
            <h2 id="bancos">Dois bancos, responsabilidades diferentes</h2>
          </div>
        </div>
        <div className={styles.duasColunas}>
          <article className={styles.bloco}>
            <span className={styles.etiqueta}>DOCUMENTOS + GEOGRAFIA</span>
            <h3>MongoDB Atlas</h3>
            <p>
              <b>Bronze:</b> cópia original das coletas, preservada para rastreabilidade.
            </p>
            <p>
              <b>Território:</b> arquivos oficiais de bairros, distritos e faixas hídricas.
            </p>
            <code>etl/load.py · territorio/carga.py · data/territorio/</code>
          </article>
          <article className={styles.bloco}>
            <span className={styles.etiqueta}>RELACIONAL + INTEGRIDADE</span>
            <h3>PostgreSQL / Neon</h3>
            <p>
              <b>Silver:</b> dados limpos, tipados e ligados a estação e território.
            </p>
            <p>
              <b>Gold:</b> agregações derivadas por SQL. <b>App:</b> usuários, fontes e execuções.
            </p>
            <code>migrations/versions/ · infra/modelos_sql.py · etl/gold.py</code>
          </article>
        </div>
        <div className={styles.resumoCamadas}>
          <span>
            BRONZE <small>original</small>
          </span>
          <ArrowRight size={15} />
          <span>
            SILVER <small>tratado</small>
          </span>
          <ArrowRight size={15} />
          <span>
            GOLD <small>agregado</small>
          </span>
        </div>
      </section>

      <section className={`${styles.secao} ${styles.ml}`} aria-labelledby="ml">
        <div className={styles.tituloSecao}>
          <BrainCircuit size={19} />
          <div>
            <span>03 / MACHINE LEARNING</span>
            <h2 id="ml">Árvore de decisão para risco de alagamento</h2>
          </div>
        </div>
        <div className={styles.duasColunas}>
          <div className={styles.bloco}>
            <p>
              Escolhemos <b>DecisionTreeClassifier</b> por ser interpretável: dá para explicar quais condições
              levaram a cada classe. A avaliação usa separação e validação temporal.
            </p>
            <p>Usa chuva em 1, 3 e 7 dias, maré máxima, mês e histórico de ocorrências do bairro.</p>
            <code>ml/alagamento/base.py · ml/alagamento/modelo.py</code>
          </div>
          <div className={styles.blocoResultado}>
            <span className={styles.etiqueta}>VERSÃO 0.2.0 · EXPERIMENTAL</span>
            <div className={styles.metricas}>
              <b>
                80,1%<small>recall</small>
              </b>
              <b>
                3,4%<small>precisão</small>
              </b>
              <b>
                0,046<small>AUC-PR</small>
              </b>
            </div>
            <p>
              Não está validado para uso operacional: a precisão é baixa e a AUC-PR ficou abaixo da referência
              simples de chuva.
            </p>
            <code>docs/ml/risco-alagamento.md</code>
          </div>
        </div>
      </section>

      <section className={styles.secao} aria-labelledby="ferramentas">
        <div className={styles.tituloSecao}>
          <Layers3 size={19} />
          <div>
            <span>04 / APLICAÇÃO E FERRAMENTAS</span>
            <h2 id="ferramentas">O que construímos</h2>
          </div>
        </div>
        <div className={styles.duasColunas}>
          <article className={styles.bloco}>
            <h3>
              <Map size={16} /> Funcionalidades
            </h3>
            <ul className={styles.lista}>
              {funcionalidades.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
            <code>frontend/src/features/ · dashboards (ECharts) · mapa (Leaflet)</code>
          </article>
          <article className={styles.bloco}>
            <h3>
              <Map size={16} /> Visualização
            </h3>
            <p>
              Mapas territoriais usam Leaflet; os dashboards usam ECharts para apresentar indicadores e
              séries.
            </p>
            <p>O frontend consome a API FastAPI, que consulta os dados preparados no PostgreSQL.</p>
            <code>frontend/src/features/mapa/ · frontend/src/features/dashboards/</code>
          </article>
        </div>
      </section>

      <footer className={styles.rodape}>
        <span>Execução do ETL é independente da API.</span>
        <code>python -m climasense.etl atualizar</code>
        <span>ClimaSense · CESAR School</span>
      </footer>
    </main>
  );
}
