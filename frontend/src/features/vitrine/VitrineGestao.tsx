import { useEffect, useState } from "react";
import { Download, Moon, Sun } from "lucide-react";
import { Botao } from "@/design-system/componentes/Botao";
import { CabecalhoTela } from "@/design-system/componentes/CabecalhoTela";
import { Dica, DicaFonte } from "@/design-system/componentes/Dica";
import { EstadoDados } from "@/design-system/componentes/EstadoDados";
import { CarregandoLista, Esqueleto, EsqueletoIndicador } from "@/design-system/componentes/Esqueleto";
import { Indicador } from "@/design-system/componentes/Indicador";
import { Marca } from "@/design-system/componentes/Marca";
import { Painel } from "@/design-system/componentes/Painel";
import { Pilula, type TomPilula } from "@/design-system/componentes/Pilula";
import { ItemRanking, Ranking } from "@/design-system/componentes/Ranking";
import { Tabela, semDado } from "@/design-system/componentes/Tabela";
import { NIVEIS, type ChaveNivel } from "@/design-system/niveis";
import estilos from "./Vitrine.module.css";

const GRUPOS_COR: [string, [string, string][]][] = [
  [
    "Marca",
    [
      ["--cs-mare", "títulos, ação principal"],
      ["--cs-mare-forte", "hover da ação principal"],
      ["--cs-mangue", "links"],
      ["--cs-sol", "acento: item ativo, contador"],
      ["--cs-espuma", "etiquetas claras"],
    ],
  ],
  [
    "Neutros",
    [
      ["--cs-papel", "cartões"],
      ["--cs-nevoa", "fundo da página"],
      ["--cs-tinta", "texto"],
      ["--cs-tinta-2", "texto de apoio"],
      ["--cs-linha", "fios"],
      ["--cs-linha-forte", "bordas de campo"],
    ],
  ],
  [
    "Superfície de marca (não inverte)",
    [
      ["--sup-mare", "menu lateral"],
      ["--sup-mare-forte", "faixa escura"],
      ["--sup-sobre", "texto sobre o azul"],
      ["--sup-sobre-2", "texto secundário"],
      ["--sup-sol", "acento sobre o azul"],
    ],
  ],
  [
    "Níveis de aviso",
    ["sem", "info", "atencao", "alerta", "critico", "insuf"].map((n) => [`--n-${n}`, "só para nível"]),
  ],
  ["Gráficos", [1, 2, 3, 4, 5, 6].map((n) => [`--g-${n}`, `série ${n}`])],
];

const TONS: TomPilula[] = [
  "neutro",
  "marca",
  "sucesso",
  "info",
  "atencao",
  "alerta",
  "critico",
  "insuficiente",
];
const NIVEIS_LISTA: ChaveNivel[] = ["sem", "informativo", "atencao", "alerta", "critico", "insuficiente"];
const FONTE = [{ nome: "APAC, pluviômetros", atualizadoEm: "2026-10-15T20:40:00Z" }];

const LINHAS = [
  { id: "ds5", nome: "Distrito Sanitário 5", chuva: 62.4, casos: 18 },
  { id: "ds3", nome: "Distrito Sanitário 3", chuva: 41.0, casos: null },
  { id: "ds8", nome: "Distrito Sanitário 8", chuva: 12.8, casos: 4 },
];

/** Seção da vitrine para a plataforma de gestão: paleta, forma e o kit de componentes, em claro e escuro. */
export function VitrineGestao() {
  const [escuro, setEscuro] = useState(() => document.documentElement.dataset.tema === "escuro");
  useEffect(() => {
    if (escuro) document.documentElement.dataset.tema = "escuro";
    else delete document.documentElement.dataset.tema;
    return () => {
      delete document.documentElement.dataset.tema;
    };
  }, [escuro]);

  return (
    <section className={estilos.secao} aria-labelledby="s-gestao">
      <h2 id="s-gestao">Plataforma de gestão</h2>
      <p>Paleta, formas e o kit das telas da equipe. Use o botão para alternar entre claro e escuro.</p>
      <div className={estilos.linha}>
        <Botao
          variante="secundario"
          aria-pressed={escuro}
          icone={escuro ? <Sun /> : <Moon />}
          onClick={() => setEscuro((e) => !e)}
        >
          {escuro ? "Ver no tema claro" : "Ver no tema escuro"}
        </Botao>
      </div>

      <div className={estilos.bloco}>
        <h3>Paleta por grupo</h3>
        {GRUPOS_COR.map(([grupo, itens]) => (
          <div key={grupo}>
            <h4 className={estilos.subtitulo}>{grupo}</h4>
            <div className={estilos.grade}>
              {itens.map(([token, uso]) => (
                <div key={token} className={estilos.cor}>
                  <div style={{ background: `var(${token})` }} />
                  <p>
                    <code>{token}</code>
                    {uso}
                  </p>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      <div className={estilos.bloco}>
        <h3>Formas</h3>
        <div className={estilos.linha}>
          {[
            ["Campo · 4 px", "var(--r-campo)"],
            ["Ícone · 10 px", "var(--r-icone)"],
            ["Painel · 14 px", "var(--r-painel)"],
            ["Pílula", "var(--r-pilula)"],
          ].map(([nome, raio]) => (
            <div key={nome} className={estilos.forma} style={{ borderRadius: raio }}>
              {nome}
            </div>
          ))}
          <div
            className={estilos.forma}
            style={{ borderRadius: "var(--r-painel)", boxShadow: "var(--sombra-cartao)" }}
          >
            Sombra do cartão
          </div>
          <div
            className={estilos.forma}
            style={{ borderRadius: "var(--r-painel)", boxShadow: "var(--sombra-cartao-alta)" }}
          >
            Sombra em foco
          </div>
        </div>
      </div>

      <div className={estilos.bloco}>
        <h3>Menu lateral (superfície de marca)</h3>
        <div className={estilos.amostraMenu}>
          <Marca decorativa />
          <Pilula tom="neutro">Branco sobre azul, nos dois temas</Pilula>
        </div>
      </div>

      <div className={estilos.bloco}>
        <h3>CabecalhoTela</h3>
        <CabecalhoTela
          titulo="Cenários"
          proposito="Simule a chuva e veja quais territórios precisam de atenção primeiro."
          voltar={<a href="#s-gestao">Voltar para o painel</a>}
          acoes={<Botao icone={<Download />}>Exportar</Botao>}
        />
      </div>

      <div className={estilos.bloco}>
        <h3>Indicador</h3>
        <div className={estilos.indicadores}>
          <Indicador
            rotulo="Chuva em 24 h"
            valor="62,4"
            unidade="mm"
            nivel="alerta"
            tendencia={{ sentido: "sobe", texto: "+18 mm vs. ontem", efeito: "ruim" }}
            explicacao="Soma da chuva medida nas últimas 24 horas, na média dos pluviômetros do território."
            fonte={FONTE}
          />
          <Indicador
            rotulo="Casos de dengue"
            valor="148"
            tendencia={{ sentido: "desce", texto: "-6% na semana", efeito: "bom" }}
            fonte={FONTE}
          />
          <Indicador
            rotulo="Maré agora"
            valor="1,9"
            unidade="m"
            tendencia={{ sentido: "estavel", texto: "sem mudança" }}
          />
          <Indicador rotulo="Sem valor" valor={null} fonte={FONTE} />
          <Indicador rotulo="Chuva em 24 h" valor={null} insuficiente nivel="insuficiente" />
          <EsqueletoIndicador />
        </div>
      </div>

      <div className={estilos.bloco}>
        <h3>Pilula</h3>
        <div className={estilos.linha}>
          {TONS.map((t) => (
            <Pilula key={t} tom={t}>
              {t}
            </Pilula>
          ))}
        </div>
        <div className={estilos.linha}>
          {NIVEIS_LISTA.map((n) => (
            <Pilula key={n} nivel={n}>
              {NIVEIS[n].rotulo}
            </Pilula>
          ))}
          <Pilula tom="marca" pequena semMarca>
            pequena
          </Pilula>
        </div>
      </div>

      <div className={estilos.bloco}>
        <h3>Ranking (territórios em atenção)</h3>
        <Ranking rotulo="Territórios em atenção">
          <ItemRanking
            posicao={1}
            nome="Afogados"
            contexto="Distrito Sanitário 5"
            nivel="critico"
            motivos={["chuva 62 mm", "maré alta", "histórico de alagamento", "solo saturado"]}
            confianca="alta"
            explicacaoConfianca="Quantas fontes confirmam a leitura e quão recentes são."
            aoAbrir={() => undefined}
          />
          <ItemRanking
            posicao={2}
            nome="Mustardinha"
            contexto="Distrito Sanitário 5"
            nivel="alerta"
            motivos={["chuva 41 mm"]}
            confianca="media"
            aoAbrir={() => undefined}
          />
          <ItemRanking
            posicao={3}
            nome="Ibura"
            nivel="insuficiente"
            motivos={["sem leitura há 6 h"]}
            confianca="baixa"
          />
        </Ranking>
      </div>

      <div className={estilos.bloco}>
        <h3>Painel e Tabela</h3>
        <Painel
          id="v-painel"
          titulo="Chuva por distrito"
          dica="Total medido no período escolhido no topo da tela."
          acoes={<DicaFonte fontes={FONTE} />}
        >
          <Tabela
            legenda="Chuva e casos por distrito"
            legendaVisivel={false}
            chaveLinha={(l) => l.id}
            linhas={LINHAS}
            colunas={[
              { chave: "nome", titulo: "Distrito", celula: (l) => l.nome },
              {
                chave: "chuva",
                titulo: "Chuva (mm)",
                numerica: true,
                celula: (l) => l.chuva.toLocaleString("pt-BR"),
              },
              { chave: "casos", titulo: "Casos", numerica: true, celula: (l) => semDado(l.casos) },
            ]}
          />
        </Painel>
      </div>

      <div className={estilos.bloco}>
        <h3>EstadoDados, Dica e esqueletos</h3>
        <div className={estilos.empilha}>
          <EstadoDados tipo="insuficiente">Faltam leituras nas últimas 6 horas.</EstadoDados>
          <EstadoDados tipo="desatualizado" acao={<Botao variante="secundario">Ver fontes</Botao>}>
            A última leitura é de ontem.
          </EstadoDados>
          <EstadoDados tipo="falha" acao={<Botao variante="secundario">Tentar de novo</Botao>}>
            Confira a conexão.
          </EstadoDados>
          <div className={estilos.linha}>
            <span>Ajuda ao lado de um rótulo</span>
            <Dica texto="O (i) abre ao passar o mouse, focar ou tocar. Esc fecha." />
            <Dica texto="Abre para baixo e à esquerda." lado="abaixo" alinhar="fim" />
          </div>
          <div className={estilos.linha}>
            <Esqueleto largura="8rem" />
            <Esqueleto forma="circulo" />
            <Esqueleto largura="12rem" altura="2.4rem" forma="bloco" />
          </div>
          <CarregandoLista linhas={2} />
        </div>
      </div>
    </section>
  );
}
