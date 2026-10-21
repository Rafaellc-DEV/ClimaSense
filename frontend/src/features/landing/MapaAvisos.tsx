import { Fragment, useMemo, useState, type CSSProperties, type PointerEvent, type ReactNode } from "react";
import { ChevronDown } from "lucide-react";
import tracos from "@/assets/tracos/distritos.json";
import { NIVEIS, type ChaveNivel } from "@/design-system/niveis";
import type { AvisoPublico } from "./useEstado";
import estilos from "./PaginaInicial.module.css";

interface Props {
  /** distrito → nível do aviso mais alto nele; null = não foi possível verificar */
  niveis: Record<string, string> | null;
  /** avisos em vigor, para marcar na lista de bairros os que são citados em cada um */
  avisos?: AvisoPublico[];
  /** título e texto da seção, acima da legenda */
  children?: ReactNode;
}

type Distrito = (typeof tracos.distritos)[number];

/** Na landing o distrito vai em número arábico (“Distrito Sanitário 5”), mais fácil de ler que o romano. */
const nomeDe = (d: Distrito) => `Distrito Sanitário ${d.codigo}`;

/** “Boa Viagem, Pina e mais 3”: bairros conhecidos, para quem não sabe o número do seu distrito. */
function exemplos(d: Distrito): string {
  const resto = d.bairros.length - d.referencias.length;
  if (resto <= 1) return d.bairros.map((b) => b.nome).join(", ");
  return `${d.referencias.join(", ")} e mais ${resto}`;
}

const corNivel = (n: ChaveNivel | null) =>
  n
    ? ({
        "--cor-nivel": NIVEIS[n].cor,
        "--fundo-nivel": NIVEIS[n].fundo,
        "--texto-nivel": NIVEIS[n].texto,
      } as CSSProperties)
    : undefined;

/**
 * “Onde há aviso agora” (design §8.8): os 8 distritos desenhados das geometrias oficiais, cada um com uma bolinha
 * numerada. Uma única etiqueta, ligada à bolinha por uma reta, mostra o distrito em foco com bairros conhecidos dele:
 * por padrão o de aviso mais alto. A legenda ao lado diz o mesmo em texto (RN-17) e abre a lista completa de bairros.
 * O aviso vale para os bairros citados nele, não para o distrito inteiro (RN-07).
 */
export function MapaAvisos({ niveis, avisos, children }: Props) {
  const [ativo, setAtivo] = useState<string | null>(null);
  const [aberto, setAberto] = useState<string | null>(null);

  const nivelDe = (id: string): ChaveNivel | null =>
    ((niveis?.[id] ?? niveis?.recife) as ChaveNivel | undefined) ?? null;
  const afetados = tracos.distritos
    .filter((d) => nivelDe(d.id))
    .sort((a, b) => NIVEIS[nivelDe(b.id)!].marcas - NIVEIS[nivelDe(a.id)!].marcas);
  const situacao = (id: string) => {
    const n = nivelDe(id);
    return niveis === null ? "Não verificado" : n ? NIVEIS[n].rotulo : "Sem aviso publicado";
  };

  /** bairro → nível do aviso mais alto que o cita (um aviso de distrito ou do Recife vale para todos os bairros). */
  const nivelBairro = useMemo(() => {
    const m = new Map<string, ChaveNivel>();
    const marcar = (id: string, n: ChaveNivel) => {
      const atual = m.get(id);
      if (!atual || NIVEIS[n].marcas > NIVEIS[atual].marcas) m.set(id, n);
    };
    for (const a of avisos ?? []) {
      const n = a.nivel as ChaveNivel;
      for (const t of a.territorios) {
        if (t.tipo === "bairro") marcar(t.id, n);
        else
          tracos.distritos
            .filter((d) => t.tipo === "municipio" || d.id === t.id)
            .forEach((d) => d.bairros.forEach((b) => marcar(b.id, n)));
      }
    }
    return m;
  }, [avisos]);

  const foco = ativo ?? aberto ?? afetados[0]?.id ?? null;
  const emFoco = tracos.distritos.find((d) => d.id === foco);
  const alternar = (id: string) => {
    setAtivo(null);
    setAberto((a) => (a === id ? null : id));
  };
  /** Passar por cima só acende com mouse; no toque o estado de hover ficaria preso. */
  const sobre = (id: string | null) => (e: PointerEvent) => {
    if (e.pointerType === "mouse") setAtivo(id);
  };

  return (
    <div className={estilos.mapa}>
      <div className={estilos.mapaCabecalho}>{children}</div>

      <figure className={estilos.mapaFigura} onPointerLeave={sobre(null)}>
        <svg
          viewBox={`0 0 ${tracos.largura} ${tracos.altura}`}
          role="img"
          aria-labelledby="mapa-titulo mapa-desc"
        >
          <title id="mapa-titulo">Mapa dos 8 distritos sanitários do Recife</title>
          <desc id="mapa-desc">
            {afetados.length
              ? `Distritos com aviso: ${afetados
                  .map((d) => `${nomeDe(d)}, ${NIVEIS[nivelDe(d.id)!].rotulo}`)
                  .join("; ")}.`
              : "Nenhum distrito com aviso publicado."}
          </desc>
          {tracos.distritos.map((d) => {
            const n = nivelDe(d.id);
            return (
              <g
                key={d.id}
                className={estilos.distritoG}
                data-afetado={!!n}
                data-nivel={n ?? undefined}
                data-foco={foco === d.id}
                style={corNivel(n)}
                onPointerEnter={sobre(d.id)}
                onClick={() => alternar(d.id)}
              >
                <path d={d.d} className={estilos.distrito} />
              </g>
            );
          })}
          {tracos.distritos.map((d) => {
            const n = nivelDe(d.id);
            return (
              <g
                key={d.id}
                className={estilos.bolinha}
                data-com-aviso={!!n}
                data-foco={foco === d.id}
                style={corNivel(n)}
              >
                {n && <circle cx={d.x} cy={d.y} r={16} className={estilos.ondulacao} />}
                <circle cx={d.x} cy={d.y} r={16} className={estilos.bolinhaDisco} />
                <text x={d.x} y={d.y} textAnchor="middle" dominantBaseline="central">
                  {d.codigo}
                </text>
              </g>
            );
          })}
        </svg>
        {emFoco && (
          <div
            key={emFoco.id}
            className={estilos.rotuloFoco}
            data-lado={emFoco.x > tracos.largura / 2 ? "dir" : "esq"}
            style={{
              left: `${(emFoco.x / tracos.largura) * 100}%`,
              top: `${(emFoco.y / tracos.altura) * 100}%`,
              ...corNivel(nivelDe(emFoco.id)),
            }}
            aria-hidden="true"
          >
            <strong>{nomeDe(emFoco)}</strong>
            <span>{exemplos(emFoco)}</span>
            <span className={estilos.rotuloFocoSituacao} data-com-aviso={!!nivelDe(emFoco.id)}>
              {situacao(emFoco.id)}
            </span>
          </div>
        )}
      </figure>

      <div className={estilos.legenda}>
        <p className={estilos.notaMapa}>
          {niveis === null
            ? "Não foi possível verificar os avisos agora."
            : afetados.length
              ? `${
                  afetados.length === 1 ? "1 distrito tem" : `${afetados.length} distritos têm`
                } aviso. Ele vale para os bairros citados, marcados na lista.`
              : "Nenhum distrito com aviso publicado."}
        </p>
        <ul className={estilos.listaDistritos}>
          {tracos.distritos.map((d) => {
            const n = nivelDe(d.id);
            return (
              <li key={d.id} data-afetado={!!n} data-foco={foco === d.id} style={corNivel(n)}>
                <button
                  type="button"
                  aria-expanded={aberto === d.id}
                  aria-controls={`bairros-${d.id}`}
                  onClick={() => alternar(d.id)}
                  onPointerEnter={sobre(d.id)}
                  onPointerLeave={sobre(null)}
                  onFocus={() => setAtivo(d.id)}
                  onBlur={() => setAtivo(null)}
                >
                  <span className={estilos.marcador} aria-hidden="true">
                    {d.codigo}
                  </span>
                  <span className={estilos.distritoTexto}>
                    <span className={estilos.nomeDistrito}>{nomeDe(d)}</span>
                    <span className={estilos.exemplosDistrito}>{exemplos(d)}</span>
                  </span>
                  {(n || niveis === null) && (
                    <span className={estilos.situacaoDistrito}>{situacao(d.id)}</span>
                  )}
                  <ChevronDown aria-hidden="true" size={20} className={estilos.seta} />
                </button>
                {aberto === d.id && (
                  <p id={`bairros-${d.id}`} className={estilos.bairros}>
                    {d.bairros.length} bairros:{" "}
                    {d.bairros.map((b, i) => {
                      const nb = nivelBairro.get(b.id);
                      return (
                        <Fragment key={b.id}>
                          {i > 0 && ", "}
                          {nb ? (
                            <strong>
                              {b.nome} ({NIVEIS[nb].rotulo})
                            </strong>
                          ) : (
                            b.nome
                          )}
                        </Fragment>
                      );
                    })}
                    .
                  </p>
                )}
              </li>
            );
          })}
        </ul>
      </div>
    </div>
  );
}
