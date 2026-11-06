/** Controle e legenda das camadas do mapa (RF-02, RF-03, RF-19, RF-26). A lógica fica em `useCamadas`. */
import { useId } from "react";
import { token } from "@/charts/tema";
import { EstadoDados, LegendaFonte, SeloDesatualizado } from "@/design-system/componentes/EstadoDados";
import { EstadoConsulta } from "@/features/evento/Evento";
import { formatarHoraMinuto, formatarNumero } from "@/lib/formatos";
import {
  AVISO_DEFICIENCIA,
  INDICADORES,
  ROTULO_CAMADA,
  TIPOS_EQUIP,
  rotuloTipoRisco,
  textoCobertura,
  type IdCamada,
} from "./modeloCamadas";
import { TOKENS_POPULACAO, tokenTipoRisco, type Camadas, type EstadoCamada } from "./usarCamadas";
import estilos from "./Camadas.module.css";

type Dependentes = Exclude<IdCamada, "base">;
const ORDEM: Dependentes[] = ["populacao", "areas", "equipamentos", "abrigos"];

const AJUDA: Record<Dependentes, string> = {
  populacao: "Quantas pessoas moram em cada bairro",
  areas: "Onde há risco de deslizamento ou alagamento",
  equipamentos: "Hospitais, UPAs e unidades básicas",
  abrigos: "Abertos em destaque",
};

/** Texto curto do estado de uma camada ligada. `ok` não escreve nada. */
function MensagemEstado({
  estado,
  nome,
  aoTentar,
}: {
  estado: EstadoCamada;
  nome: string;
  aoTentar: () => void;
}) {
  if (estado.tipo === "carregando")
    return (
      <p className={estilos.estado} role="status">
        Carregando {nome.toLowerCase()}…
      </p>
    );
  if (estado.tipo === "indisponivel")
    return (
      <EstadoDados tipo="insuficiente" titulo="Ainda não disponível">
        O servidor ainda não oferece {nome.toLowerCase()}.
      </EstadoDados>
    );
  if (estado.tipo === "insuficiente")
    return (
      <EstadoDados tipo="insuficiente" titulo="Dados insuficientes">
        Falta a fonte {estado.falta}. Isso não quer dizer que não haja.
      </EstadoDados>
    );
  if (estado.tipo === "erro")
    return <EstadoConsulta erro={estado.erro} oQue={nome.toLowerCase()} aoTentar={aoTentar} />;
  return null;
}

/** Caixas de seleção das camadas. Estágio (ou a classe do cenário) vem ligado; as demais, desligadas. */
export function ControleCamadas({ c, rotuloBase }: { c: Camadas; rotuloBase: string }) {
  const grupoIndicador = useId();
  const aviso = useId();
  return (
    <fieldset className={estilos.camadas}>
      <legend>Camadas do mapa</legend>
      <ul className={estilos.lista}>
        <li>
          <label className={estilos.camada}>
            <input type="checkbox" checked={c.ligadas.base} onChange={() => c.alternar("base")} />
            <span>
              {rotuloBase}
              <small>Cor de cada bairro</small>
            </span>
          </label>
        </li>
        {ORDEM.map((id) => (
          <li key={id}>
            <label className={estilos.camada}>
              <input type="checkbox" checked={c.ligadas[id]} onChange={() => c.alternar(id)} />
              <span>
                {ROTULO_CAMADA[id]}
                <small>{AJUDA[id]}</small>
              </span>
            </label>
          </li>
        ))}
      </ul>
      {c.ligadas.populacao && (
        <fieldset className={estilos.indicadores}>
          <legend>População a mostrar</legend>
          <div className={estilos.chips}>
            {INDICADORES.map((i) => (
              <label key={i.valor} data-marcado={c.indicador === i.valor}>
                <input
                  type="radio"
                  name={grupoIndicador}
                  checked={c.indicador === i.valor}
                  onChange={() => c.setIndicador(i.valor)}
                />
                <span>{i.rotulo}</span>
              </label>
            ))}
            <label data-desabilitado="true">
              <input type="radio" name={grupoIndicador} disabled aria-describedby={aviso} />
              <span>Pessoas com deficiência</span>
            </label>
          </div>
          <p id={aviso} className={estilos.avisoDeficiencia}>
            Pessoas com deficiência: {AVISO_DEFICIENCIA}.
          </p>
        </fieldset>
      )}
      {c.ligadas.populacao && (
        <p className={estilos.nota}>
          A população substitui a cor do estágio. Desligue-a para voltar a ver o estágio.
        </p>
      )}
    </fieldset>
  );
}

/** Rótulo permanente sobre o mapa quando a cobertura das áreas de risco é parcial (RN-01). */
export function CoberturaNoMapa({ c }: { c: Camadas }) {
  if (c.estados.areas.tipo !== "ok") return null;
  const t = textoCobertura(c.risco.cobertura);
  if (!t) return null;
  return (
    <p className={estilos.rotuloMapa} data-testid="cobertura-parcial">
      {t}
    </p>
  );
}

function Fonte({ c, id }: { c: Camadas; id: Dependentes }) {
  const f = c.fontes[id];
  if (f.fontes.length > 0) return <LegendaFonte fontes={f.fontes} />;
  return (
    <p className={estilos.fonte}>
      Fonte: {f.padrao}
      {f.consultadoEm ? `, consultado às ${formatarHoraMinuto(f.consultadoEm)}` : ""}.
    </p>
  );
}

function Amostra({ cor, hachura, nome }: { cor?: string; hachura?: "supr" | "sem"; nome: string }) {
  return (
    <li>
      <i
        className={[
          estilos.amostra,
          hachura === "sem" ? estilos.semDado : "",
          hachura === "supr" ? estilos.supr : "",
        ].join(" ")}
        style={cor ? { background: cor } : undefined}
        aria-hidden="true"
      />
      {nome}
    </li>
  );
}

/** Legenda e fonte com hora de cada camada ligada, em texto (RF-19). */
export function LegendaCamadas({ c }: { c: Camadas }) {
  const ligadas = ORDEM.filter((id) => c.ligadas[id]);
  if (ligadas.length === 0) return null;
  return (
    <div className={estilos.legendas} role="group" aria-label="Legenda das camadas">
      {ligadas.map((id) => {
        const estado = c.estados[id];
        const venceu = c.fontes[id].fontes.some((f) => f.desatualizado === true);
        return (
          <section key={id} className={estilos.legenda} aria-label={`Legenda: ${ROTULO_CAMADA[id]}`}>
            <h3>{ROTULO_CAMADA[id]}</h3>
            <MensagemEstado estado={estado} nome={ROTULO_CAMADA[id]} aoTentar={c.tentar[id]} />
            {estado.tipo === "ok" && (
              <>
                {id === "populacao" && <LegendaPopulacao c={c} />}
                {id === "areas" && <LegendaAreas c={c} />}
                {id === "equipamentos" && (
                  <>
                    <p className={estilos.resumoCamada}>
                      {formatarNumero(c.totais.equipamentos)} equipamentos. Toque em um ícone para ver o nome
                      e o tipo.
                    </p>
                    <ul className={estilos.itens}>
                      {TIPOS_EQUIP.map((t) => (
                        <li key={t.chave}>
                          <b className={estilos.pinoLegenda} aria-hidden="true">
                            {t.glifo}
                          </b>
                          {t.rotulo}
                        </li>
                      ))}
                    </ul>
                  </>
                )}
                {id === "abrigos" && <LegendaAbrigos c={c} />}
                {venceu && (
                  <p className={estilos.estado} data-aviso="desatualizado">
                    <SeloDesatualizado /> Fonte vencida: confira antes de decidir.
                  </p>
                )}
              </>
            )}
            {(estado.tipo === "ok" || estado.tipo === "insuficiente") && <Fonte c={c} id={id} />}
          </section>
        );
      })}
    </div>
  );
}

function LegendaPopulacao({ c }: { c: Camadas }) {
  const { rotulos, meta } = c.populacao;
  const rotulo = INDICADORES.find((i) => i.valor === c.indicador)?.rotulo ?? "";
  const ano = typeof meta.ano === "number" || typeof meta.ano === "string" ? ` (${meta.ano})` : "";
  const deficiencia = typeof meta.deficiencia === "string" && meta.deficiencia ? meta.deficiencia : null;
  const tokens = TOKENS_POPULACAO.slice(0, rotulos.length);
  return (
    <>
      <p className={estilos.resumoCamada}>
        {rotulo}: pessoas residentes por bairro{ano}. Contagem, não percentual. O IBGE publica por bairro só
        até 70 anos ou mais.
      </p>
      <ul className={estilos.itens}>
        {rotulos.map((r, i) => (
          <Amostra key={r} cor={token(tokens[i])} nome={r} />
        ))}
        <Amostra hachura="supr" nome="< 5 (valor oculto para proteger a privacidade)" />
        <Amostra hachura="sem" nome="Dados insuficientes" />
      </ul>
      <p className={estilos.avisoDeficiencia}>
        Pessoas com deficiência: {deficiencia ?? `${AVISO_DEFICIENCIA}.`}
      </p>
    </>
  );
}

function LegendaAreas({ c }: { c: Camadas }) {
  const { tipos, total } = c.risco;
  const cobertura = textoCobertura(c.risco.cobertura);
  return (
    <>
      <p className={estilos.resumoCamada}>{formatarNumero(total)} áreas de risco mapeadas.</p>
      <ul className={estilos.itens}>
        {tipos.map((t) => (
          <Amostra key={t} cor={token(tokenTipoRisco(t))} nome={rotuloTipoRisco(t)} />
        ))}
      </ul>
      {cobertura && (
        <p className={estilos.alertaCobertura}>
          {cobertura}.{" "}
          {c.risco.cobertura?.texto ?? "Bairro sem área desenhada não quer dizer bairro sem risco."}
        </p>
      )}
    </>
  );
}

function LegendaAbrigos({ c }: { c: Camadas }) {
  const abertos = c.totais.abrigos.filter((a) => a.aberto === true).length;
  return (
    <>
      <p className={estilos.resumoCamada}>
        {formatarNumero(c.totais.abrigos.length)} abrigos com localização, {formatarNumero(abertos)} abertos
        agora.
      </p>
      <ul className={estilos.itens}>
        <li>
          <b className={`${estilos.pinoLegenda} ${estilos.abrigoAberto}`} aria-hidden="true">
            A
          </b>
          Aberto (em destaque)
        </li>
        <li>
          <b className={`${estilos.pinoLegenda} ${estilos.abrigoFechado}`} aria-hidden="true">
            a
          </b>
          Fechado ou situação não informada
        </li>
      </ul>
    </>
  );
}
