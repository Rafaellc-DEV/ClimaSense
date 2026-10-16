import { useEffect } from "react";
import { Link, useParams } from "react-router-dom";
import { CartaoAviso } from "@/design-system/componentes/CartaoAviso";
import { EstadoDados } from "@/design-system/componentes/EstadoDados";
import { Carregando } from "@/design-system/componentes/Painel";
import { useConsulta } from "@/lib/consultas";
import { CascaPublica, FaixaEmergencia } from "./CascaPublica";
import type { AvisoPublico } from "./useEstado";
import estilos from "./PaginaInicial.module.css";

/** Detalhe de um aviso publicado (RF-01.3). Um aviso vencido ou encerrado não aparece mais (RN-14). */
export function DetalheAviso() {
  const { id = "" } = useParams();
  const r = useConsulta<AvisoPublico>(`/publico/avisos/${id}`, { retry: false });
  useEffect(() => {
    if (r.data) document.title = `${r.data.titulo} | ClimaSense`;
  }, [r.data]);
  return (
    <CascaPublica>
      <FaixaEmergencia />
      <div className={estilos.detalhe}>
        <p className={estilos.voltar}>
          <Link to="/">Voltar à página inicial</Link>
        </p>
        {r.isPending && <Carregando />}
        {r.isError && (
          <EstadoDados tipo="desatualizado" titulo="Este aviso não está mais em vigor.">
            Ele pode ter vencido ou sido encerrado pela equipe. Veja os avisos atuais na página inicial.
          </EstadoDados>
        )}
        {r.data && <CartaoAviso aviso={r.data} nivelTitulo={2} />}
      </div>
    </CascaPublica>
  );
}
