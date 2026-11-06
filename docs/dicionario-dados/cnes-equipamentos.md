# CNES — equipamentos de saúde do Recife

- **Identificador:** `cnes-equipamentos`
- **Situação:** Implementada (06/11/2026). RF-04, RF-02.
- **Órgão:** Ministério da Saúde (Cadastro Nacional de Estabelecimentos de Saúde, API de dados abertos).
- **Acesso:** `GET https://apidadosabertos.saude.gov.br/cnes/estabelecimentos?codigo_municipio=261160&limit=20&offset=N`.
  Sem chave. O servidor devolve no máximo 20 por página (ignora `limit` maior); a carga percorre as páginas até uma
  página curta (cerca de 240 páginas, 2 a 3 minutos).
- **Licença:** dados abertos do Governo Federal, acesso público sem autenticação; o endpoint não declara licença
  própria. Conferir antes de redistribuir o cadastro bruto (aqui só o recorte público/SUS é guardado).
- **Granularidade:** estabelecimento (um por código CNES). **Atualização:** o CNES é atualizado pelos gestores o tempo
  todo e a API reflete a base mensal; o campo `data_atualizacao` de cada unidade vai à bronze.
- **Cadência no ETL:** `python -m climasense.etl run cnes-equipamentos` (mensal).

## O que a API devolve e o que fica

A resposta traz os **4.740** estabelecimentos do município (06/11/2026): 2.049 clínicas/centros (tipo 36), 1.628
consultórios isolados (22), 261 laboratórios (39), 222 farmácias (43), 181 centros de saúde (2) e o resto. Cada linha
tem razão social, CNPJ, telefone, e-mail e endereço. **Atenção:** `descricao_esfera_administrativa` é a esfera de
**gestão** (clínicas privadas aparecem como "MUNICIPAL"); a esfera gravada vem da natureza jurídica.

Filtro (em `extrair`, antes da bronze), na ordem:

| Regra | Efeito |
|---|---|
| `codigo_motivo_desabilitacao_estabelecimento` preenchido | descarta (`desabilitado`) |
| tipo 22 (consultório isolado, em geral pessoa física) | descarta (`consultorio_isolado`) |
| tipo fora da lista abaixo (farmácia 43, unidades móveis 40/42, academia da saúde 74, home care 77, etc.) | descarta (`tipo_fora_do_escopo`) |
| tipos 36 e 39 (clínica, laboratório) | só se natureza jurídica 1244 (município) ou 1023 (estado) |
| demais tipos | só se **público** (natureza 1xxx, empresa pública 2011 ou economia mista 2038) |
| tipos hospitalares e de urgência (5, 7, 15, 20, 21, 62, 73) | também entram se `estabelecimento_faz_atendimento_ambulatorial_sus = SIM` (filantrópico/privado conveniado), com esfera `privada-sus` |

Tipos mantidos (código CNES → rótulo): 1 posto de saúde; 2 centro de saúde/UBS/USF; 4 policlínica; 5 hospital geral;
7 hospital especializado (inclui maternidades, que o CNES não separa); 15 unidade mista; 20 pronto-socorro geral; 21
pronto-socorro especializado; 36 clínica/centro de especialidades (UPAE, CEO, NDI); 39 laboratório/apoio diagnóstico;
62 hospital-dia; 69 hemocentro; 70 CAPS; 71 centro de apoio à saúde da família; 73 UPA/pronto atendimento; 76 central de
regulação das urgências (SAMU); 80 laboratório central de saúde pública; 85 centro de imunização.

Resultado sobre a resposta de 06/11/2026: **271 equipamentos** (UBS/USF 164, hospital geral 33, clínica/centro de
especialidades 20, CAPS 18, hospital especializado 14, policlínica 10, UPA 5, laboratório central 4, laboratório 1,
pronto-socorro especializado 1, SAMU 1); esfera: municipal 205, estadual 40, privada-sus 20, federal 5, pública 1.

## Campos descartados (LGPD, RN-13, RNF-03)

Nunca chegam à bronze: `nome_razao_social`, `numero_cnpj`, `numero_cnpj_entidade`, `numero_telefone_estabelecimento`,
`endereco_email_estabelecimento`, `endereco_estabelecimento`, `numero_estabelecimento`, CEP e todos os `estabelecimento_possui_*`.
Consultórios de pessoa física são descartados por inteiro. A lista de campos mantidos é fechada (`so_o_necessario`).

## Camadas

| Camada | Onde | Conteúdo |
|---|---|---|
| Bronze | Atlas `bronze.cnes_equipamentos` | um documento `registro = consulta` (páginas, lidos, mantidos, descartes por motivo, `amostra`) e um `registro = estabelecimento` por unidade mantida: `codigo_cnes`, `nome_fantasia`, `codigo_tipo_unidade`, `natureza_juridica`, `atende_sus`, `bairro_cnes`, `latitude`, `longitude`, `data_atualizacao` |
| Silver | `silver.equipamentos_saude` | `cnes` (pk), `nome`, `tipo`, `esfera` (`municipal`, `estadual`, `federal`, `publica`, `privada-sus`), `bairro_id`, `distrito_id`, `latitude`, `longitude`, `fonte_id`, `execucao_id` |

Carga completa: upsert por `cnes` e remoção de quem saiu do cadastro ou foi desabilitado. `--limite N` lê só N páginas:
é **amostra** (RN-10), rotulada na bronze (`amostra = true`) e a silver só recebe upsert, sem remoção.

## Território

1. Coordenada do CNES → ponto-em-polígono na malha de bairros (`data/territorio/bairros-do-recife.geojson`); 260 de
   271 acertaram. Coordenada fora do Recife é descartada (duvidosa).
2. Sem coordenada válida → nome do bairro escrito no CNES, normalizado (sem acento, caixa) e casado com os 94 bairros
   oficiais: 11 unidades. Resultado: todas as 271 com bairro; 8 sem coordenada (aparecem na lista, não no mapa).
3. Senão `bairro_id` nulo.

A rede municipal do CKAN (`rede-de-saude-municipal`, 132 polígonos, GeoJSON de 04/03/2026) **não traz código CNES**,
só nome, tipo e endereço; por isso não completa coordenada por CNES (pergunta P-26 em `docs/perguntas-abertas.md`).

## Limitações

- Cadastro, não situação: **fechado, danificado ou sem energia não existe em fonte pública**; entra por registro da
  equipe (nunca inferido).
- O CNES não diz se a unidade é abrigo nem se tem gerador; só tipo, natureza e atendimento SUS.
- Coordenada do CNES é digitada pelo estabelecimento; pode estar deslocada.
- Hospital privado conveniado ao SUS entra por ser relevante a desastres, com esfera `privada-sus`; a lista não é o
  cadastro oficial de leitos.

## Frescor

- Limite: 744 h (31 dias) (configurado em `backend/climasense/etl/frescor.toml`, chave `cnes-equipamentos`; lido por `climasense.etl.frescor`).
- Motivo: base do CNES atualizada todo mês.
- Sem dado registrado, o indicador mostra "Dados insuficientes", nunca "em dia" (RN-01).
