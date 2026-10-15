import { useState } from "react";
import { Send, Trash2 } from "lucide-react";
import { Botao } from "@/design-system/componentes/Botao";
import { AreaTexto, Campo } from "@/design-system/componentes/Campo";
import { Selecao } from "@/design-system/componentes/Selecao";
import { Confirmacao, Dialogo } from "@/design-system/componentes/Dialogo";
import { useAviso } from "@/design-system/componentes/Aviso";
import { Abas } from "@/design-system/componentes/Abas";
import { Tabela } from "@/design-system/componentes/Tabela";
import { VazioConvidativo } from "@/design-system/componentes/VazioConvidativo";
import { ReguaMare } from "@/design-system/componentes/ReguaMare";
import { SeloNivel } from "@/design-system/componentes/SeloNivel";
import { EstadoDados, LegendaFonte } from "@/design-system/componentes/EstadoDados";
import { NIVEIS, type ChaveNivel } from "@/design-system/niveis";
import { QuadroGrafico } from "@/charts/QuadroGrafico";
import { formatarNumero } from "@/lib/formatos";
import distritos from "@/assets/tracos/distritos.json";
import rios from "@/assets/tracos/rios.svg?raw";
import { DISTRITOS_REAIS, FONTE_DISTRITOS, type DistritoReal } from "./dadosReais";
import estilos from "./Vitrine.module.css";

const CORES = [
  ["Maré", "--cs-mare", "#0F4C75"],
  ["Mangue", "--cs-mangue", "#0B6F6C"],
  ["Sol", "--cs-sol", "#EDB105"],
  ["Tinta", "--cs-tinta", "#0E2433"],
  ["Névoa", "--cs-nevoa", "#F2F6F8"],
  ["Papel", "--cs-papel", "#FFFFFF"],
];
const ESTADOS_REGUA: ChaveNivel[] = ["sem", "informativo", "atencao", "alerta", "critico", "insuficiente"];
const FONTES = [FONTE_DISTRITOS];

export function Vitrine() {
  const [nivel, setNivel] = useState<ChaveNivel>("alerta");
  const [territorio, setTerritorio] = useState("recife");
  const [dialogo, setDialogo] = useState(false);
  const [confirmar, setConfirmar] = useState(false);
  const avisar = useAviso();

  const maior = [...DISTRITOS_REAIS].sort((a, b) => b.areaKm2 - a.areaKm2)[0];

  return (
    <main className={estilos.pagina}>
      <header className={estilos.topo}>
        <img src="/brand/logo.png" alt="ClimaSense" width={1059} height={280} />
        <a href="/">Voltar ao início</a>
      </header>
      <h1 className={estilos.titulo}>Vitrine do design system</h1>
      <p className={estilos.lead}>
        Todos os componentes e estados do ClimaSense em um só lugar. Os números desta página são reais:
        distritos sanitários e bairros do Recife, a partir dos arquivos oficiais. Esta rota só existe em
        desenvolvimento.
      </p>

      <section className={estilos.secao} aria-labelledby="s-marca">
        <h2 id="s-marca">Marca</h2>
        <p>Logo limpa, versão negativa para fundos escuros, símbolo vetorial e ícone do aplicativo.</p>
        <div className={estilos.marca}>
          <figure>
            <img src="/brand/logo.png" alt="Logo ClimaSense sobre fundo claro" />
            <figcaption>Logo principal, sobre fundos claros</figcaption>
          </figure>
          <figure className={estilos.escuro}>
            <img src="/brand/logo-negativo.png" alt="Logo ClimaSense sobre fundo escuro" />
            <figcaption>Logo negativa, sobre o azul maré</figcaption>
          </figure>
          <figure>
            <div className={estilos.linha}>
              <img src="/brand/simbolo.svg" alt="Símbolo ClimaSense" width={72} height={72} />
              <img src="/brand/icone.svg" alt="Ícone do aplicativo ClimaSense" width={72} height={72} />
              <img src="/brand/icone.svg" alt="" width={32} height={32} />
              <img src="/brand/icone.svg" alt="" width={16} height={16} />
            </div>
            <figcaption>Símbolo vetorial e ícone (72, 32 e 16 px)</figcaption>
          </figure>
        </div>
      </section>

      <section className={estilos.secao} aria-labelledby="s-cores">
        <h2 id="s-cores">Cores</h2>
        <p>Tiradas da logo. O amarelo-sol aparece só na marca e na linha d’água, nunca como texto.</p>
        <div className={estilos.grade}>
          {CORES.map(([nome, token, hex]) => (
            <div key={token} className={estilos.cor}>
              <div style={{ background: `var(${token})` }} />
              <p>
                {nome}
                <code>{hex}</code>
              </p>
            </div>
          ))}
        </div>
      </section>

      <section className={estilos.secao} aria-labelledby="s-regua">
        <h2 id="s-regua">Régua de maré e selos de nível</h2>
        <p>
          A régua mostra o nível do aviso mais alto em vigor. O selo é a mesma régua em tamanho pequeno,
          sempre com o nome do nível.
        </p>
        <div className={estilos.regua}>
          <ReguaMare key={nivel} nivel={nivel} />
          <div className={estilos.empilha}>
            <Selecao
              rotulo="Nível exibido na régua"
              valor={nivel}
              aoMudar={(v) => setNivel(v as ChaveNivel)}
              opcoes={ESTADOS_REGUA.map((c) => ({ valor: c, rotulo: NIVEIS[c].rotulo }))}
            />
            <div className={estilos.linha}>
              {ESTADOS_REGUA.map((c) => (
                <SeloNivel key={c} nivel={c} />
              ))}
            </div>
            <div className={estilos.linha}>
              <SeloNivel nivel="alerta" grande />
              <SeloNivel nivel="insuficiente" rotulo="Sem dado neste distrito" />
            </div>
          </div>
        </div>
      </section>

      <section className={estilos.secao} aria-labelledby="s-tipo">
        <h2 id="s-tipo">Tipografia</h2>
        <p>
          Atkinson Hyperlegible Next, criada para leitores com baixa visão. A hierarquia vem do peso e do
          tamanho.
        </p>
        <div className={estilos.tipo}>
          <p>
            <span>Estado 72</span>
            <span
              style={{
                fontSize: "var(--t-estado)",
                fontWeight: 800,
                lineHeight: 1.04,
                letterSpacing: "-0.02em",
              }}
            >
              Nenhum aviso ativo
            </span>
          </p>
          <p>
            <span>Título 44</span>
            <span style={{ fontSize: "var(--t-1)", fontWeight: 750, lineHeight: 1.1 }}>
              Como um aviso chega até você
            </span>
          </p>
          <p>
            <span>Tela 35</span>
            <span style={{ fontSize: "var(--t-2)", fontWeight: 700 }}>Onde precisamos agir primeiro?</span>
          </p>
          <p>
            <span>Painel 22</span>
            <span style={{ fontSize: "var(--t-4)", fontWeight: 650 }}>Territórios em atenção</span>
          </p>
          <p>
            <span>Corpo 18</span>
            <span>
              O {maior.nome} tem {maior.bairros} bairros e {formatarNumero(maior.areaKm2, 1)} km², a maior
              área do Recife.
            </span>
          </p>
          <p>
            <span>Apoio 16</span>
            <span style={{ fontSize: "var(--t-apoio)", color: "var(--cs-tinta-2)" }}>
              Fonte: Dados Abertos do Recife, distritos sanitários.
            </span>
          </p>
        </div>
      </section>

      <section className={estilos.secao} aria-labelledby="s-botoes">
        <h2 id="s-botoes">Botões</h2>
        <p>O texto diz o que acontece. O retorno usa o mesmo verbo.</p>
        <div className={estilos.linha}>
          <Botao
            icone={<Send size={20} />}
            onClick={() =>
              avisar({ titulo: "Enviado para revisão.", texto: "A coordenação foi notificada." })
            }
          >
            Enviar para revisão
          </Botao>
          <Botao variante="secundario" onClick={() => avisar({ titulo: "Rascunho salvo." })}>
            Salvar rascunho
          </Botao>
          <Botao variante="discreto" onClick={() => setDialogo(true)}>
            Ver detalhes
          </Botao>
          <Botao variante="perigo" icone={<Trash2 size={20} />} onClick={() => setConfirmar(true)}>
            Encerrar aviso
          </Botao>
          <Botao grande>Ver avisos do bairro</Botao>
          <Botao disabled>Publicar</Botao>
        </div>
        <Dialogo
          aberto={dialogo}
          aoMudar={setDialogo}
          titulo="Sobre os dados"
          descricao="Os limites oficiais dos distritos são relacionados ao CSV de bairros pelo código oficial."
        />
        <Confirmacao
          aberto={confirmar}
          aoMudar={setConfirmar}
          titulo="Encerrar este aviso?"
          consequencia="O aviso sai da página inicial agora e fica guardado no histórico. Ninguém mais o verá como vigente."
          rotuloConfirmar="Encerrar aviso"
          perigo
          aoConfirmar={() => {
            setConfirmar(false);
            avisar({ titulo: "Aviso encerrado." });
          }}
        />
      </section>

      <section className={estilos.secao} aria-labelledby="s-campos">
        <h2 id="s-campos">Campos</h2>
        <p>Rótulo sempre visível acima. Erros dizem o que fazer.</p>
        <div className={estilos.formulario}>
          <Campo
            rotulo="E-mail"
            type="email"
            placeholder="nome@recife.pe.gov.br"
            ajuda="Use o e-mail cadastrado pela coordenação."
          />
          <Campo
            rotulo="Senha"
            type="password"
            erro="E-mail ou senha incorretos. Confira e tente de novo."
            defaultValue="12345"
          />
          <Selecao
            rotulo="Território"
            valor={territorio}
            aoMudar={setTerritorio}
            opcoes={[
              { valor: "recife", rotulo: "Recife inteiro" },
              { valor: "ds-4", rotulo: "Distrito Sanitário IV" },
              { valor: "ds-5", rotulo: "Distrito Sanitário V" },
            ]}
          />
          <AreaTexto
            rotulo="Texto do comunicado"
            ajuda="Frases curtas. No máximo 1.200 caracteres."
            placeholder="Escreva o que a população precisa saber e o que fazer."
          />
        </div>
      </section>

      <section className={estilos.secao} aria-labelledby="s-dados">
        <h2 id="s-dados">Estados dos dados</h2>
        <p>
          Falta de informação nunca vira zero nem “risco baixo”. Abaixo, exemplos das mensagens de cada
          estado.
        </p>
        <div className={estilos.formulario}>
          <EstadoDados tipo="insuficiente">
            A estação de referência não envia dados desde ontem, às 14h.
          </EstadoDados>
          <EstadoDados tipo="desatualizado">
            Última atualização há 3 dias. O limite desta fonte é de 24 horas.
          </EstadoDados>
          <EstadoDados tipo="falha">
            A fonte não respondeu às 14h. Tente de novo em alguns minutos.
          </EstadoDados>
        </div>
      </section>

      <section className={estilos.secao} aria-labelledby="s-graficos">
        <h2 id="s-graficos">Gráficos e tabelas</h2>
        <p>
          Barras na cor da primeira série, resumo em frase, fonte com data e tabela alternativa. Dados reais
          dos 8 distritos sanitários do Recife.
        </p>
        <div className={estilos.duas}>
          <QuadroGrafico
            titulo="Bairros por distrito sanitário"
            resumo={`O Recife tem 94 bairros em 8 distritos. O Distrito Sanitário II reúne mais bairros (18); o VIII, menos (3).`}
            fontes={FONTES}
            opcao={{
              xAxis: {
                type: "category",
                data: DISTRITOS_REAIS.map((d) => d.nome.replace("Distrito Sanitário ", "DS ")),
              },
              yAxis: { type: "value", name: "bairros", minInterval: 1 },
              tooltip: { trigger: "item" },
              series: [{ name: "Bairros", type: "bar", data: DISTRITOS_REAIS.map((d) => d.bairros) }],
            }}
            tabela={{
              colunas: ["Distrito", "Bairros"],
              linhas: DISTRITOS_REAIS.map((d) => [d.nome, d.bairros]),
            }}
          />
          <div className={estilos.empilha}>
            <Tabela
              legenda="Área dos distritos sanitários (km²)"
              colunas={[
                { chave: "d", titulo: "Distrito", celula: (l: DistritoReal) => l.nome },
                { chave: "b", titulo: "Bairros", numerica: true, celula: (l) => l.bairros },
                {
                  chave: "a",
                  titulo: "Área (km²)",
                  numerica: true,
                  celula: (l) => formatarNumero(l.areaKm2, 1),
                },
              ]}
              linhas={DISTRITOS_REAIS}
              chaveLinha={(l) => String(l.codigo)}
            />
            <LegendaFonte fontes={FONTES} />
          </div>
        </div>
      </section>

      <section className={estilos.secao} aria-labelledby="s-abas">
        <h2 id="s-abas">Abas e estado vazio</h2>
        <p>Abas com contagem. Ainda não há avaliações registradas, então a tela vazia convida a agir.</p>
        <Abas
          rotulo="Avaliações por estado"
          itens={[
            {
              valor: "rascunho",
              rotulo: "Rascunhos",
              contagem: 0,
              conteudo: (
                <VazioConvidativo
                  titulo="Nenhuma avaliação ainda."
                  texto="Comece pelo mapa e registre a primeira."
                  acao={<Botao variante="secundario">Abrir o mapa</Botao>}
                />
              ),
            },
            {
              valor: "revisao",
              rotulo: "Em revisão",
              contagem: 0,
              conteudo: (
                <VazioConvidativo
                  titulo="Nada aguardando revisão."
                  texto="Quando alguém enviar uma avaliação, ela aparece aqui."
                />
              ),
            },
          ]}
        />
      </section>

      <section className={estilos.secao} aria-labelledby="s-traco">
        <h2 id="s-traco">Traço cartográfico</h2>
        <p>Rios e distritos desenhados a partir dos arquivos oficiais do Recife, sem mapa de fundo.</p>
        <div className={estilos.traco}>
          <figure
            className={estilos.rios}
            aria-label="Faixas marginais dos rios do Recife"
            dangerouslySetInnerHTML={{ __html: rios }}
          />
          <figure>
            <svg
              viewBox={`0 0 ${distritos.largura} ${distritos.altura}`}
              role="img"
              aria-label="Os 8 distritos sanitários do Recife"
            >
              {distritos.distritos.map((d) => (
                <path
                  key={d.id}
                  d={d.d}
                  className={estilos.distrito}
                  style={
                    d.codigo === 5
                      ? { fill: "var(--n-alerta)", stroke: "var(--cs-tinta)", strokeWidth: 2 }
                      : undefined
                  }
                />
              ))}
              {distritos.distritos.map((d) => (
                <text key={d.id} x={d.x} y={d.y} className={estilos.distritoRotulo} aria-hidden="true">
                  {d.rotulo}
                </text>
              ))}
            </svg>
          </figure>
        </div>
      </section>
    </main>
  );
}
