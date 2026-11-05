import { useId, type ReactNode } from "react";
import { ChevronDown, CircleAlert, Footprints } from "lucide-react";
import { Dica } from "@/design-system/componentes/Dica";
import estilos from "./Pecas.module.css";

/** Um dado com rótulo: “Período”, “Versão”, “Licença”. Nada de texto solto na tela. */
export function Fato({ rotulo, dica, children }: { rotulo: string; dica?: ReactNode; children: ReactNode }) {
  return (
    <div className={estilos.fato}>
      <dt>
        {rotulo}
        {dica && <Dica texto={dica} rotulo={`Sobre ${rotulo}`} />}
      </dt>
      <dd>{children}</dd>
    </div>
  );
}

/** Faixa de fatos lado a lado; no celular vira uma coluna. */
export function Fatos({ children, colunas }: { children: ReactNode; colunas?: "duas" }) {
  return (
    <dl className={estilos.fatos} data-colunas={colunas}>
      {children}
    </dl>
  );
}

/**
 * O próximo passo da pessoa, em primeiro lugar na tela: uma frase curta e os botões que a API liberou.
 * `tom="espera"` quando não há nada a fazer agora.
 */
export function CartaoDecisao({
  titulo = "Próximo passo",
  tom = "agir",
  children,
  acoes,
}: {
  titulo?: string;
  tom?: "agir" | "espera";
  children?: ReactNode;
  acoes?: ReactNode;
}) {
  const id = useId();
  return (
    <section className={estilos.decisao} data-tom={tom} aria-labelledby={id}>
      <span className={estilos.disco} aria-hidden="true">
        {tom === "agir" ? <Footprints size={22} /> : <CircleAlert size={22} />}
      </span>
      <div className={estilos.decisaoTexto}>
        <h2 id={id}>{titulo}</h2>
        {children && <p>{children}</p>}
      </div>
      {acoes && <div className={estilos.decisaoAcoes}>{acoes}</div>}
    </section>
  );
}

/** “Ver detalhes”: o que é longo ou de apoio fica recolhido até a pessoa pedir. */
export function Recolher({
  titulo,
  contagem,
  aberto,
  children,
}: {
  titulo: string;
  contagem?: number;
  aberto?: boolean;
  children: ReactNode;
}) {
  return (
    <details className={estilos.recolher} open={aberto}>
      <summary>
        <span>{titulo}</span>
        {contagem !== undefined && <span className={estilos.contagem}>{contagem}</span>}
        <ChevronDown aria-hidden="true" size={20} />
      </summary>
      <div className={estilos.recolherCorpo}>{children}</div>
    </details>
  );
}

/** Bloco de conteúdo com rótulo (h3) — o par rótulo/valor de texto longo, como justificativa e limitações. */
export function Bloco({ titulo, children }: { titulo: string; children: ReactNode }) {
  return (
    <div className={estilos.bloco}>
      <h3>{titulo}</h3>
      {children}
    </div>
  );
}

/** Seção de formulário com título curto, para agrupar campos sem criar um muro de campos. */
export function SecaoForm({
  titulo,
  children,
  dica,
}: {
  titulo: string;
  children: ReactNode;
  dica?: ReactNode;
}) {
  return (
    <section className={estilos.secao}>
      <h3>
        {titulo}
        {dica && <Dica texto={dica} rotulo={`Sobre ${titulo}`} lado="abaixo" />}
      </h3>
      {children}
    </section>
  );
}

/** “37 de 120 caracteres.” em um chip; fica vermelho-escuro (com texto) ao encher. */
export function Contador({ atual, max }: { atual: number; max: number }) {
  return (
    <span className={estilos.contador} data-cheio={atual >= max}>
      {atual} de {max} caracteres.
    </span>
  );
}
