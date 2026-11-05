import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { normalizar } from "./abrigosPublicos";
import type { AvisoPublico } from "./useEstado";

export interface Bairro {
  id: string;
  nome: string;
  distrito_id: string | null;
}

/** Resultado da busca por bairro: um só para a página inteira (hero, resultado, abas e mapa). */
export type Resultado =
  | { tipo: "ocioso" }
  | { tipo: "curto" }
  | { tipo: "carregando"; consulta: string }
  | { tipo: "naoEncontrado"; consulta: string }
  | { tipo: "erro"; bairro: Bairro }
  | { tipo: "ok"; bairro: Bairro; avisos: AvisoPublico[] }
  | { tipo: "escolher"; consulta: string; opcoes: Bairro[] };

/** A localização só é pedida depois do toque. Imprecisa ou negada nunca vira “sem aviso”. */
export type Localizacao =
  | { tipo: "ocioso" }
  | { tipo: "pedindo" }
  | { tipo: "negada" }
  | { tipo: "indisponivel" }
  | { tipo: "falhou" }
  | { tipo: "imprecisa" }
  | { tipo: "ok"; lat: number; lon: number };

/** Acima disto (metros), a posição não serve nem para sugerir abrigos próximos. */
export const PRECISAO_MAXIMA_M = 1500;

export interface Busca {
  q: string;
  /** A pessoa digitou: o resultado antigo sai, para não ficar um aviso de outro bairro na tela. */
  digitar: (q: string) => void;
  sugestoes: Bairro[];
  resultado: Resultado;
  localizacao: Localizacao;
  buscar: (texto?: string) => void;
  escolher: (b: Bairro) => void;
  tentarDeNovo: () => void;
  usarLocalizacao: () => void;
  limpar: () => void;
}

/** Estado único da busca por bairro. Quem digita, quem toca no mapa e quem usa a localização falam com o mesmo lugar. */
export function useBusca(): Busca {
  const [q, setQ] = useState("");
  const [sugestoes, setSugestoes] = useState<Bairro[]>([]);
  const [resultado, setResultado] = useState<Resultado>({ tipo: "ocioso" });
  const [localizacao, setLocalizacao] = useState<Localizacao>({ tipo: "ocioso" });
  const rodada = useRef(0);
  const ultimo = useRef<Bairro | null>(null);

  // autocompletar: só enquanto a pessoa digita e ainda não há resultado
  useEffect(() => {
    const t = q.trim();
    if (t.length < 2 || (resultado.tipo !== "ocioso" && resultado.tipo !== "curto")) return setSugestoes([]);
    const espera = setTimeout(() => {
      api<Bairro[]>(`/publico/territorios/busca?q=${encodeURIComponent(t)}`)
        .then(setSugestoes)
        .catch(() => setSugestoes([]));
    }, 250);
    return () => clearTimeout(espera);
  }, [q, resultado.tipo]);

  const avisosDe = useCallback(async (b: Bairro, minha: number) => {
    ultimo.current = b;
    try {
      const avisos = await api<AvisoPublico[]>(`/publico/avisos?bairro=${encodeURIComponent(b.nome)}`);
      if (rodada.current === minha) setResultado({ tipo: "ok", bairro: b, avisos });
    } catch {
      if (rodada.current === minha) setResultado({ tipo: "erro", bairro: b });
    }
  }, []);

  const escolher = useCallback(
    (b: Bairro) => {
      const minha = ++rodada.current;
      setQ(b.nome);
      setSugestoes([]);
      setLocalizacao({ tipo: "ocioso" });
      setResultado({ tipo: "carregando", consulta: b.nome });
      void avisosDe(b, minha);
    },
    [avisosDe],
  );

  const buscar = useCallback(
    (texto?: string) => {
      const t = (texto ?? q).trim();
      if (texto !== undefined) setQ(texto);
      if (t.length < 2) return setResultado({ tipo: "curto" });
      const minha = ++rodada.current;
      setSugestoes([]);
      setLocalizacao({ tipo: "ocioso" });
      setResultado({ tipo: "carregando", consulta: t });
      api<Bairro[]>(`/publico/territorios/busca?q=${encodeURIComponent(t)}`)
        .then((achados) => {
          if (rodada.current !== minha) return;
          const exato = achados.find((b) => normalizar(b.nome) === normalizar(t));
          const unico = achados.length === 1 ? achados[0] : undefined;
          const escolhido = exato ?? unico;
          if (escolhido) {
            setQ(escolhido.nome);
            return void avisosDe(escolhido, minha);
          }
          setResultado(
            achados.length
              ? { tipo: "escolher", consulta: t, opcoes: achados }
              : { tipo: "naoEncontrado", consulta: t },
          );
        })
        .catch(() => {
          if (rodada.current !== minha) return;
          // a busca do nome falhou: sem o nome oficial, tenta o texto digitado, para a rede ruim não esconder avisos
          void avisosDe({ id: "", nome: t, distrito_id: null }, minha);
        });
    },
    [q, avisosDe],
  );

  const tentarDeNovo = useCallback(() => {
    if (ultimo.current) {
      const minha = ++rodada.current;
      setResultado({ tipo: "carregando", consulta: ultimo.current.nome });
      void avisosDe(ultimo.current, minha);
    } else buscar();
  }, [avisosDe, buscar]);

  const usarLocalizacao = useCallback(() => {
    rodada.current++;
    setResultado({ tipo: "ocioso" });
    if (typeof navigator === "undefined" || !navigator.geolocation)
      return setLocalizacao({ tipo: "indisponivel" });
    setLocalizacao({ tipo: "pedindo" });
    navigator.geolocation.getCurrentPosition(
      (p) =>
        setLocalizacao(
          p.coords.accuracy > PRECISAO_MAXIMA_M
            ? { tipo: "imprecisa" }
            : { tipo: "ok", lat: p.coords.latitude, lon: p.coords.longitude },
        ),
      (e) => setLocalizacao({ tipo: e.code === 1 ? "negada" : "falhou" }),
      { enableHighAccuracy: false, timeout: 10_000, maximumAge: 60_000 },
    );
  }, []);

  const digitar = useCallback((texto: string) => {
    setQ(texto);
    setResultado((r) => (r.tipo === "carregando" ? r : { tipo: "ocioso" }));
  }, []);

  const limpar = useCallback(() => {
    rodada.current++;
    ultimo.current = null;
    setQ("");
    setSugestoes([]);
    setResultado({ tipo: "ocioso" });
    setLocalizacao({ tipo: "ocioso" });
  }, []);

  return {
    q,
    digitar,
    sugestoes,
    resultado,
    localizacao,
    buscar,
    escolher,
    tentarDeNovo,
    usarLocalizacao,
    limpar,
  };
}
