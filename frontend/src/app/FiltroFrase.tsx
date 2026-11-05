import { useMemo, useState, type FormEvent } from "react";
import { CalendarRange, MapPin } from "lucide-react";
import { Botao } from "@/design-system/componentes/Botao";
import { Campo } from "@/design-system/componentes/Campo";
import { Dialogo } from "@/design-system/componentes/Dialogo";
import type { Esquemas } from "@/lib/api";
import { useConsulta } from "@/lib/consultas";
import { diaNoRecife } from "@/lib/formatos";
import { normalize } from "@/map/model";
import { PREDEFINICOES, useRecorte } from "@/lib/recorte";
import estilos from "./FiltroFrase.module.css";

type Territorio = Esquemas["Territorio"];

export function useTerritorios() {
  return useConsulta<Territorio[]>("/territorios", { staleTime: 60 * 60_000 });
}

export function nomeTerritorio(lista: Territorio[] | undefined, id: string): string {
  if (id === "recife") return "Recife inteiro";
  return lista?.find((t) => t.id === id)?.nome_exibicao ?? id;
}

/** "1 jan" ou "15 out 2026", sem passar por fuso. */
function diaCurto(dia: string, comAno: boolean): string {
  const data = new Date(`${dia}T00:00:00Z`);
  const t = new Intl.DateTimeFormat("pt-BR", {
    day: "numeric",
    month: "short",
    ...(comAno ? { year: "numeric" } : {}),
    timeZone: "UTC",
  }).format(data);
  return t.replace(/\./g, "").replace(/ de /g, " ");
}

/**
 * Filtro global compacto: dois botões em pílula, território e período. O estado fica na URL (RF-05.3).
 * Antes era a frase (design §8.2, RF-05.3): “Mostrando Recife inteiro, de 1º de janeiro a 15 de outubro
 * de 2026.” Cada parte em destaque é um botão grande que abre a escolha. O estado fica na URL.
 */
export function FiltroFrase() {
  const { recorte, mudar } = useRecorte();
  const territorios = useTerritorios();
  const [aberto, setAberto] = useState<"territorio" | "periodo" | null>(null);
  const mesmoAno = recorte.inicio.slice(0, 4) === recorte.fim.slice(0, 4);

  return (
    <div className={estilos.frase} role="group" aria-label="Recorte de território e período">
      <button type="button" className={estilos.parte} onClick={() => setAberto("territorio")}>
        <MapPin aria-hidden="true" size={18} />
        <span className="so-leitor">Território: </span>
        {nomeTerritorio(territorios.data, recorte.territorio)}
      </button>
      <button type="button" className={estilos.parte} onClick={() => setAberto("periodo")}>
        <CalendarRange aria-hidden="true" size={18} />
        <span className="so-leitor">Período: </span>
        {diaCurto(recorte.inicio, !mesmoAno)} a {diaCurto(recorte.fim, true)}
      </button>

      <EscolhaTerritorio
        aberto={aberto === "territorio"}
        aoMudar={(a) => setAberto(a ? "territorio" : null)}
        lista={territorios.data ?? []}
        atual={recorte.territorio}
        aoEscolher={(t) => {
          mudar({ territorio: t });
          setAberto(null);
        }}
      />
      <EscolhaPeriodo
        aberto={aberto === "periodo"}
        aoMudar={(a) => setAberto(a ? "periodo" : null)}
        inicio={recorte.inicio}
        fim={recorte.fim}
        aoEscolher={(inicio, fim) => {
          mudar({ inicio, fim });
          setAberto(null);
        }}
      />
    </div>
  );
}

function EscolhaTerritorio({
  aberto,
  aoMudar,
  lista,
  atual,
  aoEscolher,
}: {
  aberto: boolean;
  aoMudar: (a: boolean) => void;
  lista: Territorio[];
  atual: string;
  aoEscolher: (id: string) => void;
}) {
  const [q, setQ] = useState("");
  const filtrados = useMemo(() => {
    const agulha = normalize(q);
    return lista.filter((t) => !agulha || normalize(t.nome_exibicao).includes(agulha));
  }, [lista, q]);
  const grupos = [
    { titulo: "Município", itens: filtrados.filter((t) => t.tipo === "municipio") },
    { titulo: "Distritos sanitários", itens: filtrados.filter((t) => t.tipo === "distrito") },
    { titulo: "Bairros", itens: filtrados.filter((t) => t.tipo === "bairro") },
  ];
  return (
    <Dialogo
      aberto={aberto}
      aoMudar={aoMudar}
      titulo="Escolha o território"
      descricao="Recife inteiro, um dos 8 distritos sanitários ou um bairro. Vale para todas as telas de análise."
    >
      <Campo
        rotulo="Procurar"
        type="search"
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder="Ex.: Distrito Sanitário IV, Afogados"
        autoComplete="off"
      />
      <div className={estilos.lista}>
        {grupos
          .filter((g) => g.itens.length)
          .map((g) => (
            <section key={g.titulo} aria-label={g.titulo}>
              <h3 className={estilos.grupo}>{g.titulo}</h3>
              <ul>
                {g.itens.map((t) => (
                  <li key={t.id}>
                    <button
                      type="button"
                      className={estilos.opcao}
                      aria-pressed={t.id === atual}
                      onClick={() => aoEscolher(t.id)}
                    >
                      {t.id === "recife" ? "Recife inteiro" : t.nome_exibicao}
                    </button>
                  </li>
                ))}
              </ul>
            </section>
          ))}
        {!filtrados.length && (
          <p>Nenhum território com esse nome. Confira a grafia ou procure pelo distrito.</p>
        )}
      </div>
    </Dialogo>
  );
}

function EscolhaPeriodo({
  aberto,
  aoMudar,
  inicio,
  fim,
  aoEscolher,
}: {
  aberto: boolean;
  aoMudar: (a: boolean) => void;
  inicio: string;
  fim: string;
  aoEscolher: (inicio: string, fim: string) => void;
}) {
  const hoje = diaNoRecife();
  const [erro, setErro] = useState<string>();
  function aplicar(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const d = new FormData(e.currentTarget);
    const i = String(d.get("inicio")),
      f = String(d.get("fim"));
    if (!i || !f) return setErro("Preencha as duas datas.");
    if (i > f) return setErro("A data de início precisa ser antes da data de fim.");
    setErro(undefined);
    aoEscolher(i, f);
  }
  return (
    <Dialogo
      aberto={aberto}
      aoMudar={aoMudar}
      titulo="Escolha o período"
      descricao="As datas seguem o horário do Recife."
    >
      <div className={estilos.predefinicoes}>
        {PREDEFINICOES.map((p) => {
          const r = p.periodo(hoje);
          return (
            <button
              key={p.rotulo}
              type="button"
              className={estilos.chip}
              aria-pressed={r.inicio === inicio && r.fim === fim}
              onClick={() => aoEscolher(r.inicio, r.fim)}
            >
              {p.rotulo}
            </button>
          );
        })}
      </div>
      <form onSubmit={aplicar} className={estilos.datas} key={`${inicio}-${fim}`}>
        <Campo
          rotulo="De"
          name="inicio"
          type="date"
          defaultValue={inicio}
          min="2021-01-01"
          max={hoje}
          required
        />
        <Campo rotulo="Até" name="fim" type="date" defaultValue={fim} min="2021-01-01" max={hoje} required />
        {erro && (
          <p role="alert" className={estilos.erro}>
            {erro}
          </p>
        )}
        <Botao type="submit">Usar este período</Botao>
      </form>
    </Dialogo>
  );
}
