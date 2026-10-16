import { useEffect, useId, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { Search } from "lucide-react";
import { api } from "@/lib/api";
import { NIVEIS, type ChaveNivel } from "@/design-system/niveis";
import { distritoPorExtenso } from "@/textos/glossario";
import type { AvisoPublico } from "./useEstado";
import estilos from "./PaginaInicial.module.css";

interface Bairro {
  id: string;
  nome: string;
  distrito_id: string | null;
}

/** Busca sem acento (“brasilia” encontra “Brasília Teimosa”) e mostra os avisos em vigor para o bairro. */
export function BuscaBairro() {
  const id = useId();
  const [q, setQ] = useState("");
  const [sugestoes, setSugestoes] = useState<Bairro[] | null>(null);
  const [resultado, setResultado] = useState<{ bairro: string; avisos: AvisoPublico[] } | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    if (q.trim().length < 2) return setSugestoes(null);
    const t = setTimeout(() => {
      api<Bairro[]>(`/publico/territorios/busca?q=${encodeURIComponent(q.trim())}`)
        .then(setSugestoes)
        .catch(() => setSugestoes(null));
    }, 250);
    return () => clearTimeout(t);
  }, [q]);

  async function ver(nome: string) {
    setErro(null);
    setSugestoes(null);
    try {
      setResultado({
        bairro: nome,
        avisos: await api<AvisoPublico[]>(`/publico/avisos?bairro=${encodeURIComponent(nome)}`),
      });
    } catch {
      setErro("Não foi possível consultar agora. Tente de novo em instantes.");
    }
  }
  function enviar(e: FormEvent) {
    e.preventDefault();
    if (q.trim().length < 2) return setErro("Digite pelo menos duas letras do nome do bairro.");
    const exato = sugestoes?.length === 1 ? sugestoes[0].nome : q.trim();
    setQ(exato);
    void ver(exato);
  }

  return (
    <form className={estilos.busca} onSubmit={enviar} role="search">
      <label htmlFor={id}>Digite o seu bairro</label>
      <div className={estilos.buscaLinha}>
        <input
          id={id}
          type="search"
          value={q}
          onChange={(e) => {
            setQ(e.target.value);
            setResultado(null);
          }}
          placeholder="Ex.: Brasília Teimosa"
          autoComplete="off"
          aria-describedby={`${id}-ajuda`}
        />
        <button type="submit">
          <Search aria-hidden="true" size={20} /> Ver avisos do bairro
        </button>
      </div>
      <p id={`${id}-ajuda`} className={estilos.buscaNota}>
        Pode escrever sem acento.
      </p>
      {sugestoes && sugestoes.length > 0 && !resultado && (
        <ul className={estilos.sugestoes} aria-label="Bairros encontrados">
          {sugestoes.map((b) => (
            <li key={b.id}>
              <button
                type="button"
                onClick={() => {
                  setQ(b.nome);
                  void ver(b.nome);
                }}
              >
                <strong>{b.nome}</strong>
                {b.distrito_id && <span>{distritoPorExtenso(b.distrito_id)}</span>}
              </button>
            </li>
          ))}
        </ul>
      )}
      <div aria-live="polite">
        {erro && <p className={estilos.buscaNota}>{erro}</p>}
        {sugestoes?.length === 0 && !resultado && (
          <p className={estilos.buscaNota}>Nenhum bairro com esse nome.</p>
        )}
        {resultado &&
          (resultado.avisos.length ? (
            <div className={estilos.resultado}>
              <p>
                {resultado.avisos.length === 1 ? "Há 1 aviso" : `Há ${resultado.avisos.length} avisos`} em
                vigor para {resultado.bairro}:
              </p>
              <ul>
                {resultado.avisos.map((a) => (
                  <li key={a.id}>
                    <Link to={`/avisos/${a.id}`}>
                      {NIVEIS[a.nivel as ChaveNivel].rotulo}: {a.titulo}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ) : (
            <p className={estilos.resultado}>
              Nenhum aviso ativo publicado pela equipe para {resultado.bairro}. Em chuva forte, evite as áreas
              que costumam alagar.
            </p>
          ))}
      </div>
    </form>
  );
}
