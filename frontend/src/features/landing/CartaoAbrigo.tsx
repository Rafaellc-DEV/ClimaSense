import { ExternalLink, MapPin, Navigation, Phone } from "lucide-react";
import { formatarNumero, quandoRelativo } from "@/lib/formatos";
import {
  abertoConfirmado,
  linkComoChegar,
  linkOsm,
  linkSeguro,
  quemInformou,
  rotuloTipo,
  type AbrigoPublico,
} from "./abrigosPublicos";
import estilos from "./CartaoAbrigo.module.css";

export const TEL_DEFESA_CIVIL = "tel:08000813400";

/**
 * Um local de abrigo. “Aberto agora” só com confirmação de quem opera (COP ou equipe); o padrão é “local de apoio
 * cadastrado”. No cartão compacto (resultado da busca) ficam o essencial e as duas ações: ligar e ir.
 */
export function CartaoAbrigo({
  a,
  destaque = false,
  compacto = false,
  nota,
}: {
  a: AbrigoPublico;
  destaque?: boolean;
  compacto?: boolean;
  /** Onde fica em relação à busca: “No bairro Afogados”, “a 1,2 km de você”. Só o que foi calculado de verdade. */
  nota?: string;
}) {
  const aberto = abertoConfirmado(a);
  const rota = linkComoChegar(a);
  const osm = linkOsm(a);
  const fonte = linkSeguro(a.fonte_url);
  const Titulo = compacto ? "h4" : "h3";
  return (
    <li id={`abrigo-${a.id}`} className={estilos.cartao} data-aberto={aberto} data-destaque={destaque}>
      <p className={estilos.estado} data-aberto={aberto}>
        {aberto ? (
          <>
            <b>Aberto agora</b>, {quemInformou(a)}.
          </>
        ) : a.tipo === "cras" ? (
          "Atendimento de assistência social. Não é abrigo."
        ) : (
          "Local de apoio cadastrado. Confirme a abertura com a Defesa Civil."
        )}
      </p>
      <Titulo className={estilos.nome}>{a.nome}</Titulo>
      <p className={estilos.tipo}>
        {rotuloTipo(a.tipo)}
        {nota && <span className={estilos.nota}> · {nota}</span>}
      </p>
      <p className={estilos.endereco}>
        <MapPin aria-hidden="true" size={18} />
        <span>
          {a.endereco ?? "Endereço não informado"}
          {a.bairro_nome && (
            <>
              <br />
              <b>{a.bairro_nome}</b>
              {a.distrito_nome && `, ${a.distrito_nome}`}
            </>
          )}
        </span>
      </p>
      {!compacto && typeof a.capacidade === "number" && (
        <p className={estilos.detalhe}>Capacidade: {formatarNumero(a.capacidade)} pessoas</p>
      )}
      <div className={estilos.acoes}>
        <a
          href={TEL_DEFESA_CIVIL}
          className={estilos.ligar}
          aria-label={`Ligar para confirmar a abertura de ${a.nome}: Defesa Civil do Recife, 0800 081 3400`}
        >
          <Phone aria-hidden="true" size={20} /> Ligar para confirmar
        </a>
        {rota && (
          <a href={rota} target="_blank" rel="noopener noreferrer" className={estilos.rota}>
            <Navigation aria-hidden="true" size={20} /> Como chegar
            <span className="so-leitor"> a {a.nome} (Google Maps, abre em nova aba)</span>
          </a>
        )}
        {!compacto && osm && (
          <a href={osm} target="_blank" rel="noopener noreferrer" className={estilos.linkDiscreto}>
            Ver no OpenStreetMap<span className="so-leitor"> (abre em nova aba)</span>
          </a>
        )}
      </div>
      <p className={estilos.origem}>
        {a.atualizado_em ? `Informação de ${quandoRelativo(a.atualizado_em)}` : "Sem data da informação"}
        {a.origem && (
          <>
            . Fonte:{" "}
            {fonte ? (
              <a href={fonte} target="_blank" rel="noopener noreferrer">
                {a.origem}
                <ExternalLink aria-hidden="true" size={14} />
                <span className="so-leitor"> (abre em nova aba)</span>
              </a>
            ) : (
              a.origem
            )}
          </>
        )}
        .
      </p>
    </li>
  );
}
