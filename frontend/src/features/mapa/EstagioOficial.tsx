/** Informar o estágio oficial da cidade dado pelo COP (RF-01): botão e diálogo. A leitura do estágio fica no cartão
 *  "Situação agora" (dashboards/Kpis). */
import { useState, type FormEvent } from "react";
import { Radio } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { useAviso } from "@/design-system/componentes/Aviso";
import { Botao } from "@/design-system/componentes/Botao";
import { AreaTexto, Campo } from "@/design-system/componentes/Campo";
import { Dialogo } from "@/design-system/componentes/Dialogo";
import { Segmentado } from "@/design-system/componentes/Segmentado";
import { enviar, ErroApi } from "@/lib/api";
import { ESTAGIOS, ESTAGIOS_DECLARAVEIS } from "@/features/evento/estagios";
import { invalidarPrefixo } from "@/features/evento/Evento";
import { desembrulhar, type Estagio } from "@/features/evento/tipos";
import type { EstagioOficial } from "./tipos";
import estilos from "./Mapa.module.css";

interface Consulta {
  isPending: boolean;
  isError: boolean;
  error: Error | null;
  data?: unknown;
}

/** Valor de um `<input type="datetime-local">` com a hora de agora no fuso do navegador. */
function agoraLocal(): string {
  const d = new Date();
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
  return d.toISOString().slice(0, 16);
}

/** "Informar" ou "Atualizar" o estágio do COP; só aparece para quem pode editar e se a rota existe. */
export function BotaoInformarCop({ oficial, podeInformar }: { oficial: Consulta; podeInformar: boolean }) {
  const [aberto, setAberto] = useState(false);
  const dados = desembrulhar<EstagioOficial | null>(oficial.data) ?? null;
  const indisponivel = oficial.isError && oficial.error instanceof ErroApi && oficial.error.status === 404;
  if (!podeInformar || indisponivel || oficial.isPending) return null;
  return (
    <>
      <Botao
        variante="secundario"
        icone={<Radio />}
        aria-label="Informar estágio do COP"
        className={estilos.botaoCop}
        onClick={() => setAberto(true)}
      >
        {dados?.estagio ? "Atualizar" : "Informar"}
      </Botao>
      {aberto && <DialogoOficial aoFechar={() => setAberto(false)} />}
    </>
  );
}

function DialogoOficial({ aoFechar }: { aoFechar: () => void }) {
  const cliente = useQueryClient();
  const avisar = useAviso();
  const [estagio, setEstagio] = useState<Estagio>("observacao");
  const [hora, setHora] = useState(agoraLocal);
  const [observacao, setObservacao] = useState("");
  const [erro, setErro] = useState<string>();
  const [ocupado, setOcupado] = useState(false);

  async function confirmar(e: FormEvent) {
    e.preventDefault();
    const momento = new Date(hora);
    if (!hora || Number.isNaN(momento.getTime())) {
      setErro("Informe a hora em que o COP definiu o estágio.");
      return;
    }
    if (momento.getTime() > Date.now() + 60_000) {
      setErro("A hora informada não pode estar no futuro.");
      return;
    }
    setOcupado(true);
    try {
      await enviar("/estagios/oficial", {
        estagio,
        informado_em: momento.toISOString(),
        observacao: observacao.trim() || null,
      });
    } catch (x) {
      setErro(x instanceof ErroApi ? x.message : "Não foi possível registrar. Tente de novo.");
      setOcupado(false);
      return;
    }
    void invalidarPrefixo(cliente, "/estagios");
    avisar({ titulo: "Estágio do COP registrado.", texto: "Fica com o seu nome e a hora informada." });
    aoFechar();
  }

  return (
    <Dialogo
      aberto
      aoMudar={(a) => !a && aoFechar()}
      titulo="Informar estágio do COP"
      descricao="Registre o estágio que o COP definiu para a cidade. Fica com o seu nome e a hora em que o COP informou."
      acoes={
        <>
          <Botao variante="secundario" onClick={aoFechar}>
            Cancelar
          </Botao>
          <Botao type="submit" form="form-oficial" disabled={ocupado}>
            {ocupado ? "Registrando…" : "Registrar estágio"}
          </Botao>
        </>
      }
    >
      <form id="form-oficial" className={estilos.form} onSubmit={confirmar} noValidate>
        <Segmentado
          rotulo="Estágio definido pelo COP"
          opcoes={ESTAGIOS_DECLARAVEIS.map((v) => ({ valor: v, rotulo: ESTAGIOS[v].rotulo }))}
          valor={estagio}
          aoMudar={setEstagio}
        />
        <Campo
          rotulo="Hora informada pelo COP"
          type="datetime-local"
          value={hora}
          max={agoraLocal()}
          onChange={(e) => {
            setHora(e.target.value);
            setErro(undefined);
          }}
          required
          erro={erro}
        />
        <AreaTexto
          privacidade
          rotulo="Observação (opcional)"
          rows={3}
          maxLength={500}
          value={observacao}
          onChange={(e) => setObservacao(e.target.value)}
        />
      </form>
    </Dialogo>
  );
}
