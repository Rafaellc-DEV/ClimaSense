import { useEffect, type ReactNode } from "react";
import { AtualizadoAs } from "./EstadoDados";
import estilos from "./CabecalhoTela.module.css";

export interface CabecalhoTelaProps {
  /** Nome da tela, curto. Vira o <h1> e o título da aba. */
  titulo: string;
  /**
   * O que a tela responde, em uma frase de linguagem simples. Fica visível logo abaixo do título: quem chega com o
   * telefone tocando precisa saber em um segundo se está no lugar certo.
   */
  proposito?: ReactNode;
  /** Estado principal da tela (ex.: “3 aguardam a sua revisão”), em destaque logo abaixo da frase. */
  estado?: ReactNode;
  /** Botões e filtros da tela, à direita. */
  acoes?: ReactNode;
  /** Link discreto de retorno (“Voltar para avaliações”), em Outfit fina, acima do título. Passe um <Link>. */
  voltar?: ReactNode;
  /** Momento (ms) da última leitura dos dados: mostra “Atualizado às HH:MM” discreto (RF-10). */
  atualizadoEm?: number | null;
}

/**
 * Cabeçalho comum das telas da gestão, sempre na mesma ordem: título (o que a tela responde), uma frase de explicação,
 * o estado principal e, à direita, a ação primária. É o padrão de todas as telas da equipe.
 */
export function CabecalhoTela({
  titulo,
  proposito,
  estado,
  acoes,
  voltar,
  atualizadoEm,
}: CabecalhoTelaProps) {
  useEffect(() => {
    document.title = `${titulo} | ClimaSense`;
  }, [titulo]);
  return (
    <header className={estilos.cabecalho}>
      <div className={estilos.texto}>
        {voltar && <div className={estilos.voltar}>{voltar}</div>}
        <h1 className={estilos.titulo}>{titulo}</h1>
        {proposito && <p className={estilos.proposito}>{proposito}</p>}
        {estado && <div className={estilos.estado}>{estado}</div>}
        <AtualizadoAs em={atualizadoEm} />
      </div>
      {acoes && <div className={estilos.acoes}>{acoes}</div>}
    </header>
  );
}
