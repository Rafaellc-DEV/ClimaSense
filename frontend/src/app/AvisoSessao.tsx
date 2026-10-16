import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Botao } from "@/design-system/componentes/Botao";
import { Dialogo } from "@/design-system/componentes/Dialogo";
import { momentoUltimaAtividade } from "@/lib/api";
import { MOTIVO_INATIVIDADE, useSessao } from "@/lib/sessao";

const AVISO_ANTES_MS = 2 * 60_000;

/**
 * RF-02.5: 2 minutos antes de a sessão expirar por inatividade, um diálogo grande pergunta se a pessoa continua.
 * “Continuar conectado” renova a sessão no servidor; sem resposta, a interface sai sozinha.
 */
export function AvisoSessao() {
  const { usuario, renovar, sair } = useSessao();
  const navegar = useNavigate();
  const [restante, setRestante] = useState<number | null>(null);
  const limite = (usuario?.inatividade_min ?? 60) * 60_000;

  useEffect(() => {
    const verificar = () => {
      const falta = limite - (Date.now() - momentoUltimaAtividade());
      if (falta <= 0) {
        void sair(MOTIVO_INATIVIDADE).then(() => navegar("/entrar"));
      } else setRestante(falta <= AVISO_ANTES_MS ? falta : null);
    };
    const t = setInterval(verificar, 1000);
    return () => clearInterval(t);
  }, [limite, sair, navegar]);

  const segundos = restante === null ? 0 : Math.ceil(restante / 1000);
  const texto = segundos > 60 ? `${Math.ceil(segundos / 60)} minutos` : `${segundos} segundos`;
  return (
    <Dialogo
      aberto={restante !== null}
      aoMudar={() => undefined}
      modalEstrito
      titulo="Você continua aí?"
      descricao={`Por segurança, vamos sair em ${texto}.`}
      acoes={
        <>
          <Botao variante="secundario" onClick={() => void sair().then(() => navegar("/"))}>
            Sair agora
          </Botao>
          <Botao grande onClick={() => void renovar().then(() => setRestante(null))}>
            Continuar conectado
          </Botao>
        </>
      }
    />
  );
}
