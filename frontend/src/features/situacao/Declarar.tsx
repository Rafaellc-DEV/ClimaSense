/** Declarar e retirar a situação de um território (F1) e os limiares que fazem o sistema sugerir. */
import { useState, type FormEvent } from "react";
import { SlidersHorizontal } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { useAviso } from "@/design-system/componentes/Aviso";
import { Botao } from "@/design-system/componentes/Botao";
import { AreaTexto, Campo } from "@/design-system/componentes/Campo";
import { Dialogo } from "@/design-system/componentes/Dialogo";
import { CarregandoLista } from "@/design-system/componentes/Esqueleto";
import { EstadoDados } from "@/design-system/componentes/EstadoDados";
import { Segmentado } from "@/design-system/componentes/Segmentado";
import { enviar, ErroApi } from "@/lib/api";
import { useConsulta } from "@/lib/consultas";
import { formatarDataHora, formatarNumero } from "@/lib/formatos";
import { useSessao } from "@/lib/sessao";
import { ESTAGIOS, ESTAGIOS_DECLARAVEIS, infoEstagio, rotuloLimiar } from "@/features/evento/estagios";
import { EstadoConsulta, invalidarPrefixo, SeloEstagio } from "@/features/evento/Evento";
import {
  autoriaParametros,
  limiaresDe,
  type Estagio,
  type ItemEstagio,
  type MensagemWhatsApp,
} from "@/features/evento/tipos";
import estilos from "./Situacao.module.css";

/** Sugestão acima do declarado (sem declaração conta como Observação). `sem_dados` nunca pede decisão. */
export function pedeDecisao(i: ItemEstagio) {
  const sug = infoEstagio(i.sugerido?.estagio).ordem;
  const dec = i.declarado ? infoEstagio(i.declarado.estagio).ordem : 0;
  return sug >= 1 && sug > dec;
}

export function DialogoDeclarar({
  territorios,
  aoFechar,
  aoDeclarar,
}: {
  territorios: ItemEstagio[];
  aoFechar: () => void;
  aoDeclarar: (m: MensagemWhatsApp | null) => void;
}) {
  const cliente = useQueryClient();
  const avisar = useAviso();
  const sugeridos = [...new Set(territorios.map((t) => t.sugerido?.estagio))];
  const inicial =
    sugeridos.length === 1 && ESTAGIOS_DECLARAVEIS.includes(sugeridos[0] as Estagio)
      ? (sugeridos[0] as Estagio)
      : "observacao";
  const [estagio, setEstagio] = useState<Estagio>(inicial);
  const [justificativa, setJustificativa] = useState("");
  const [erro, setErro] = useState<string>();
  const [ocupado, setOcupado] = useState(false);

  async function confirmar(e: FormEvent) {
    e.preventDefault();
    if (!justificativa.trim()) {
      setErro("Escreva em uma frase o motivo desta situação.");
      return;
    }
    const corpo = {
      territorio_ids: territorios.map((t) => t.territorio_id),
      estagio,
      justificativa: justificativa.trim(),
    };
    setOcupado(true);
    try {
      await enviar("/estagios", corpo);
    } catch (x) {
      setErro(x instanceof ErroApi ? x.message : "Não foi possível declarar. Tente de novo.");
      setOcupado(false);
      return;
    }
    void invalidarPrefixo(cliente, "/estagios");
    void invalidarPrefixo(cliente, "/boletim");
    avisar({ titulo: "Situação declarada.", texto: "Confira a mensagem pronta para o WhatsApp." });
    let m: MensagemWhatsApp | null = null;
    try {
      m = {
        ...(await enviar<MensagemWhatsApp>("/estagios/mensagem", corpo)),
        uso: { territorio_ids: corpo.territorio_ids, estagio: corpo.estagio },
      };
    } catch (x) {
      avisar({
        titulo: "A mensagem para o WhatsApp não foi gerada.",
        texto: x instanceof ErroApi ? x.message : undefined,
        tipo: "erro",
      });
    }
    aoDeclarar(m);
  }

  return (
    <Dialogo
      aberto
      aoMudar={(a) => !a && aoFechar()}
      titulo="Declarar situação"
      descricao="A declaração fica registrada com o seu nome e a hora. Depois, a mensagem para o WhatsApp fica pronta para copiar."
      acoes={
        <>
          <Botao variante="secundario" onClick={aoFechar}>
            Cancelar
          </Botao>
          <Botao type="submit" form="form-declarar" disabled={ocupado || territorios.length === 0}>
            {ocupado ? "Declarando…" : "Declarar situação"}
          </Botao>
        </>
      }
    >
      <form id="form-declarar" className={estilos.form} onSubmit={confirmar} noValidate>
        <div>
          <p className={estilos.rotulo}>Territórios ({territorios.length})</p>
          <ul className={estilos.escolhidos}>
            {territorios.map((t) => (
              <li key={t.territorio_id}>
                {t.territorio_nome}
                <small> · sugerido: {infoEstagio(t.sugerido?.estagio).rotulo}</small>
              </li>
            ))}
          </ul>
        </div>
        <Segmentado
          rotulo="Situação"
          opcoes={ESTAGIOS_DECLARAVEIS.map((v) => ({ valor: v, rotulo: ESTAGIOS[v].rotulo }))}
          valor={estagio}
          aoMudar={setEstagio}
        />
        <AreaTexto
          privacidade
          rotulo="Justificativa"
          ajuda="Uma frase curta. Ex.: chuva de 60 mm prevista e maré alta às 15h."
          value={justificativa}
          onChange={(e) => {
            setJustificativa(e.target.value);
            setErro(undefined);
          }}
          rows={3}
          maxLength={500}
          required
          erro={erro}
        />
      </form>
    </Dialogo>
  );
}

/** Tira a declaração do território: vira uma nova linha no histórico (quem, quando e por quê), nada é apagado. */
export function DialogoEncerrar({ item, aoFechar }: { item: ItemEstagio; aoFechar: () => void }) {
  const cliente = useQueryClient();
  const avisar = useAviso();
  const [justificativa, setJustificativa] = useState("");
  const [erro, setErro] = useState<string>();
  const [ocupado, setOcupado] = useState(false);

  async function confirmar(e: FormEvent) {
    e.preventDefault();
    if (!justificativa.trim()) {
      setErro("Escreva em uma frase por que a situação está sendo retirada.");
      return;
    }
    setOcupado(true);
    try {
      await enviar("/estagios", {
        territorio_ids: [item.territorio_id],
        estagio: "encerrado",
        justificativa: justificativa.trim(),
      });
    } catch (x) {
      setErro(x instanceof ErroApi ? x.message : "Não foi possível retirar a declaração. Tente de novo.");
      setOcupado(false);
      return;
    }
    void invalidarPrefixo(cliente, "/estagios");
    void invalidarPrefixo(cliente, "/boletim");
    avisar({
      titulo: "Declaração retirada.",
      texto: `${item.territorio_nome} voltou a mostrar só a situação sugerida.`,
    });
    aoFechar();
  }

  return (
    <Dialogo
      aberto
      aoMudar={(a) => !a && aoFechar()}
      titulo="Retirar a declaração"
      descricao="O território deixa de mostrar a situação declarada e volta a mostrar só a sugerida pelo sistema. O que foi declarado continua no histórico, com o seu nome e a hora."
      acoes={
        <>
          <Botao variante="secundario" onClick={aoFechar}>
            Cancelar
          </Botao>
          <Botao type="submit" form="form-encerrar" disabled={ocupado}>
            {ocupado ? "Retirando…" : "Retirar declaração"}
          </Botao>
        </>
      }
    >
      <form id="form-encerrar" className={estilos.form} onSubmit={confirmar} noValidate>
        <p>
          {item.territorio_nome}: <SeloEstagio estagio={item.declarado?.estagio} />
        </p>
        <AreaTexto
          privacidade
          rotulo="Justificativa"
          ajuda="Uma frase curta. Ex.: a chuva passou e o COP voltou à situação de observação."
          value={justificativa}
          onChange={(e) => {
            setJustificativa(e.target.value);
            setErro(undefined);
          }}
          rows={3}
          maxLength={500}
          required
          erro={erro}
        />
      </form>
    </Dialogo>
  );
}

export function Parametros() {
  const { pode } = useSessao();
  // permissão própria do backend (coordenação e administração); `publicar` cobre sessões antigas sem ela
  const podeEditar = pode("parametrizar") || pode("administrar") || pode("publicar");
  const cliente = useQueryClient();
  const avisar = useAviso();
  const r = useConsulta<unknown>("/estagios/parametros");
  const limiares = limiaresDe(r.data);
  const autoria = autoriaParametros(r.data);
  const [editando, setEditando] = useState<Record<string, string> | null>(null);
  const [erro, setErro] = useState<string>();
  const [motivo, setMotivo] = useState("");
  const padrao = (r.data as { dados?: unknown; padrao?: boolean } | undefined)?.padrao === true;
  const [ocupado, setOcupado] = useState(false);
  const chaves = Object.keys(limiares);

  async function salvar(e: FormEvent) {
    e.preventDefault();
    if (!editando) return;
    const novos: Record<string, number> = {};
    for (const k of chaves) {
      const n = Number(editando[k].replace(",", "."));
      if (editando[k].trim() === "" || !Number.isFinite(n) || n < 0) {
        setErro(`Confira “${rotuloLimiar(k)}”: use um número maior ou igual a zero.`);
        return;
      }
      novos[k] = n;
    }
    setOcupado(true);
    try {
      await enviar("/estagios/parametros", { limiares: novos, justificativa: motivo.trim() || null }, "PUT");
      avisar({ titulo: "Limiares salvos.", texto: "As próximas sugestões já usam os novos valores." });
      setEditando(null);
      void invalidarPrefixo(cliente, "/estagios");
    } catch (x) {
      setErro(x instanceof ErroApi ? x.message : "Não foi possível salvar. Tente de novo.");
    } finally {
      setOcupado(false);
    }
  }

  return (
    <div className={estilos.parametros}>
      <p className={estilos.detalhe}>
        O sistema compara a chuva medida e a prevista de cada distrito com estes limites. Passou do limite de
        Atenção, sugere Atenção, e assim por diante. Quem declara é sempre a equipe.
      </p>
      {podeEditar && chaves.length > 0 && !editando && (
        <Botao
          variante="secundario"
          icone={<SlidersHorizontal />}
          onClick={() => {
            setErro(undefined);
            setEditando(Object.fromEntries(chaves.map((k) => [k, String(limiares[k])])));
          }}
        >
          Editar limiares
        </Botao>
      )}
      {r.isPending && <CarregandoLista linhas={2} altura="2.5rem" texto="Carregando os limiares…" />}
      {r.isError && <EstadoConsulta erro={r.error} oQue="os limiares" aoTentar={() => r.refetch()} />}
      {r.isSuccess && chaves.length === 0 && (
        <EstadoDados tipo="insuficiente" titulo="Nenhum limiar configurado." />
      )}
      {chaves.length > 0 && !editando && (
        <dl className={estilos.limiares}>
          {chaves.map((k) => (
            <div key={k}>
              <dt>{rotuloLimiar(k)}</dt>
              <dd className="numeros">
                {formatarNumero(limiares[k], Number.isInteger(limiares[k]) ? 0 : 2)}
              </dd>
            </div>
          ))}
        </dl>
      )}
      {editando && (
        <form className={estilos.form} onSubmit={salvar} noValidate>
          <div className={estilos.camposLimiares}>
            {chaves.map((k) => (
              <Campo
                key={k}
                rotulo={rotuloLimiar(k)}
                inputMode="decimal"
                value={editando[k]}
                onChange={(e) => {
                  setEditando({ ...editando, [k]: e.target.value });
                  setErro(undefined);
                }}
              />
            ))}
          </div>
          <AreaTexto
            privacidade
            rotulo="Por que mudar (opcional)"
            rows={2}
            maxLength={500}
            value={motivo}
            onChange={(e) => setMotivo(e.target.value)}
          />
          {erro && (
            <p className={estilos.erro} role="alert">
              {erro}
            </p>
          )}
          <div className={estilos.botoesForm}>
            <Botao variante="secundario" onClick={() => setEditando(null)}>
              Cancelar
            </Botao>
            <Botao type="submit" disabled={ocupado}>
              {ocupado ? "Salvando…" : "Salvar limiares"}
            </Botao>
          </div>
        </form>
      )}
      {padrao && !editando && (
        <p className={estilos.detalhe}>Limiares padrão, propostos e ainda não validados com a equipe.</p>
      )}
      {(autoria.autor || autoria.em) && (
        <p className={estilos.detalhe}>
          Última mudança{autoria.autor ? ` por ${autoria.autor}` : ""}
          {autoria.em ? `, ${formatarDataHora(autoria.em)}` : ""}.
        </p>
      )}
    </div>
  );
}
