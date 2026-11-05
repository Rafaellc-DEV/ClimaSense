import { useId, type FormEvent, type ReactNode } from "react";
import { LocateFixed, Search } from "lucide-react";
import rios from "@/assets/tracos/rios.svg?raw";
import { distritoPorExtenso } from "@/textos/glossario";
import { TELEFONES } from "./telefones";
import { Onda } from "./Onda";
import type { Busca } from "./useBusca";
import estilos from "./HeroiBusca.module.css";

/**
 * O herói é a pergunta da página: “Há aviso no meu bairro?”. O campo, o botão e a localização ficam na primeira tela;
 * o resultado aparece logo abaixo, no mesmo lugar. O fundo (malha e rios) é estático. Havendo aviso ativo, um banner
 * fino (`aviso`) fica no topo; sem aviso ele não existe.
 */
export function HeroiBusca({
  busca,
  resultado,
  aviso,
}: {
  busca: Busca;
  resultado: ReactNode;
  aviso: ReactNode;
}) {
  const id = useId();
  const curto = busca.resultado.tipo === "curto";
  const pedindo = busca.localizacao.tipo === "pedindo";

  function enviar(e: FormEvent) {
    e.preventDefault();
    busca.buscar();
  }

  return (
    <section className={estilos.heroi} aria-labelledby="pergunta">
      <div className={estilos.malha} aria-hidden="true" />
      <div className={estilos.rios} aria-hidden="true" dangerouslySetInnerHTML={{ __html: rios }} />
      <div className={estilos.interno}>
        <div className={estilos.aviso}>{aviso}</div>

        <div className={estilos.texto}>
          <h1 id="pergunta" className={estilos.h1}>
            Há aviso no meu bairro?
          </h1>
          <p className={estilos.apoio}>Veja os avisos de chuva e alagamento publicados para o Recife.</p>

          <form className={estilos.form} onSubmit={enviar} role="search" noValidate>
            <label htmlFor={id} className={estilos.rotulo}>
              Digite o nome do seu bairro
            </label>
            <div className={estilos.linha}>
              <input
                id={id}
                name="bairro"
                type="search"
                value={busca.q}
                onChange={(e) => busca.digitar(e.target.value)}
                placeholder="Ex.: Brasília Teimosa"
                autoComplete="off"
                spellCheck={false}
                enterKeyHint="search"
                aria-describedby={`${id}-ajuda`}
                aria-invalid={curto || undefined}
              />
              <button type="submit" className={estilos.ver}>
                <Search aria-hidden="true" size={22} /> Ver avisos do bairro
              </button>
            </div>
            <p id={`${id}-ajuda`} className={estilos.ajuda} data-erro={curto}>
              {curto ? "Digite pelo menos duas letras do nome do bairro." : "Pode escrever sem acento."}
            </p>
            {busca.sugestoes.length > 0 && (
              <ul className={estilos.sugestoes} aria-label="Bairros encontrados">
                {busca.sugestoes.map((b) => (
                  <li key={b.id}>
                    <button type="button" onClick={() => busca.escolher(b)}>
                      <strong>{b.nome}</strong>
                      {b.distrito_id && <span>{distritoPorExtenso(b.distrito_id)}</span>}
                    </button>
                  </li>
                ))}
              </ul>
            )}
            <button
              type="button"
              className={estilos.local}
              onClick={busca.usarLocalizacao}
              disabled={pedindo}
            >
              <LocateFixed aria-hidden="true" size={22} />
              {pedindo ? "Pedindo a localização…" : "Usar minha localização"}
            </button>
          </form>

          <p className={estilos.emergencia}>
            <span>Em emergência, ligue:</span>
            {TELEFONES.map((t) => (
              <a
                key={t.numero}
                href={`tel:${t.numero}`}
                aria-label={`Ligar para ${t.nome === "SAMU" ? "o" : "a"} ${t.nome}, ${t.numero}`}
              >
                <b>{t.numero}</b> <span className={estilos.nomeTel}>{t.nome}</span>
              </a>
            ))}
          </p>
        </div>

        <div className={estilos.resultado}>{resultado}</div>
      </div>
      <Onda cor="var(--cs-papel)" linha />
    </section>
  );
}
