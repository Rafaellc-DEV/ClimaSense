# ADR 0013 — Hospedagem: nuvem gerenciada para dados públicos agora; decisão definitiva antes de dado não público

- **Situação:** hipótese (decisão definitiva depende do cliente: `docs/perguntas-abertas.md`, P-07)
- **Data:** 06/11/2026
- **Requisitos:** RNF-02, RNF-07, RNF-12, RNF-03
- **Mantém:** ADR 0001 (API e ETL separados), ADR 0003 (Atlas na bronze, Postgres/Neon em silver e gold)

## Contexto

O cliente relatou que uma falha em PHP deixou todos sem acesso aos sistemas da prefeitura. A plataforma precisa
funcionar de forma independente desses sistemas, sem PHP exposto (RNF-02), disponível nos eventos de chuva (RNF-07).
O RNF-12 diz que Atlas e Neon são serviços de terceiros adequados a dados públicos, e que a hospedagem definitiva deve
ser decidida **antes de qualquer dado não público do cliente**. Hoje a API roda localmente; os bancos estão no Atlas e
no Neon.

## Decisão

1. **Enquanto só houver dado público e registros da equipe (ADR 0010):** manter Atlas e Neon e publicar a API +
   frontend num único contêiner (hoje a API NÃO serve o build do frontend: não há `StaticFiles`/`mount` no backend; servir o build é tarefa a fazer), sem PHP e
   sem servidor Node, com HTTPS e HSTS. **O Neon atual está nos EUA (AWS `us-east-2`) e serve só para dados públicos**; a região do Atlas ainda não foi
   conferida. Para a hospedagem definitiva, preferir região no Brasil (AWS `sa-east-1`). O ETL roda agendado no mesmo provedor ou no GitHub Actions, com segredos no
   cofre do provedor (nunca no repositório).
2. **Portabilidade obrigatória:** configuração só por variáveis de ambiente; Postgres padrão sem recurso exclusivo do
   Neon; imagem de contêiner reproduzível. Mudar para a infraestrutura da prefeitura (Emprel) ou outro provedor é troca
   de ambiente, não de código.
3. **Isolamento dos sistemas da prefeitura:** a plataforma só **lê** fontes externas (APIs públicas, arquivos
   exportados, importação manual). Não depende de login, sessão nem servidor PHP da prefeitura. Fonte bloqueada aparece
   como desatualizada, e a equipe importa o dado à mão (RNF-04).
4. **Gatilho da decisão definitiva:** antes do primeiro dado não público (extrato da vigilância, Assistência Social,
   cadastros), o cliente e o encarregado de dados da Prefeitura aprovam onde ficam os dados. Se exigirem infraestrutura
   própria, o Postgres vai junto, e a bronze do Atlas precisa de ADR próprio (sair do Atlas muda o ADR 0003).
5. **Disponibilidade (proposta para RNF-07):** 99,5% no mês; monitor externo em `GET /api/v1/health` a cada minuto
   durante estágio Alerta ou Crítico; backup do esquema `app` (ações, abrigos, estágios declarados, cenários) diário e
   fora do Neon, além do PITR do Neon.

## Alternativas consideradas

- **Servidor da prefeitura já**: depende de acesso hoje bloqueado; atrasaria o Gate 1.
- **Continuar só local**: sem disponibilidade nem HTTPS; serve só ao desenvolvimento.

## Consequências

- A demonstração às usuárias pode acontecer antes da resposta sobre hospedagem.
- Fica proibido carregar dado não público até esta ADR virar "aceita" com a hospedagem definitiva.
- O `arquiteto` escreve o `Dockerfile` de produção em `infra/` quando o dono aprovar esta hipótese.
