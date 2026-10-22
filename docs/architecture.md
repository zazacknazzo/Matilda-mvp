# Arquitetura

React + TypeScript + Vite → proxy `/api` → FastAPI + Pydantic → OpenAlex.
O catálogo editorial em JSON complementa os metadados bibliográficos. SQLite
persiste o cache e as investigações por sete dias, sem cadastro.

## Fluxo e contratos

1. `GET /api/papers/{doi:path}` normaliza o DOI e consulta o cache ou OpenAlex.
2. A ficha apresenta o registro real e suas limitações antes da investigação.
3. `POST /api/analyses` recebe `{ "doi": "10.1126/science.1231143" }`.
4. Termos específicos do catálogo são encontrados no título, resumo, tópicos e
   palavras-chave; cada conceito registra a procedência.
5. O motor recupera contribuições com identidade revisada e documento específico.
6. A comparação usa IDs OpenAlex correspondentes aos DOIs dos trabalhos curados.
7. O construtor consolida nós por ID e produz arestas estáveis por hash da relação.
8. O resultado é persistido e enviado ao grafo, à alternativa textual e ao dossiê.

Documentação interativa do contrato: `http://localhost:8000/docs`.

| Endpoint | Resultado |
|---|---|
| `GET /api/health` | Estado do processo; não atesta saúde do OpenAlex |
| `GET /api/papers/{doi}` | Paper, conceitos, procedência, cache e limitações |
| `POST /api/analyses` | Analysis síncrona, HTTP 201 |
| `GET /api/analyses/{id}` | Resultado persistido ou 404 |
| `GET /api/analyses/{id}/graph` | Nós, arestas, raiz e limites |
| `GET /api/evidence/{id}` | Documento e afirmação sustentada |
| `GET /api/analyses/{id}/export?format=markdown` | Download Markdown |
| `GET /api/analyses/{id}/export?format=json` | Download JSON |

O esquema completo é gerado em `/openapi.json` e está tipado em
`backend/app/schemas/models.py`. Opções desconhecidas da análise são rejeitadas.

## Resiliência e segurança

Somente um domínio acadêmico fixo recebe chamadas. O DOI é validado e codificado
como segmento de URL; URLs arbitrárias não são buscadas. O cliente não segue
redirecionamentos. Timeout HTTP de seis segundos; até duas tentativas para
429/502/503/504, com pausa de 500 ms e teto total de 15 segundos.
Erros 404 não são substituídos por cache antigo. Em falhas transitórias, o cache
anterior pode ser usado com `cache_stale=true`, data de recuperação e aviso.

A chave do OpenAlex fica no backend. Respostas upstream e suas URLs completas
não são registradas pelo código da aplicação; evite habilitar logs HTTP em debug
com credenciais. SQL usa parâmetros. A interface renderiza strings como texto
React, sem HTML externo. CORS aceita apenas as origens configuradas.

O cache é local e persistente. Investigações expiram após sete dias; a limpeza
ocorre ao abrir o banco. O cache bibliográfico não contém contas ou dados
pessoais de usuários e pode ser apagado removendo `.runtime/matilda.db`.
O armazenamento é adequado para demonstração de processo único; não há filas,
login ou serviço de IA. A implantação pública exige configurar proxy HTTPS,
limitação de requisições, retenção de cache e origens de produção.

## Visualização

React Flow: zoom, pan, seleção e movimentação dos nós. As camadas filtram
bibliografia, contribuições ou ambas. As setas são direcionais e rotuladas;
arestas temáticas são tracejadas. O caminho conceitual da contribuição selecionada
recebe destaque. A lista textual exibe todas as arestas com seus significados.
O grafo mostra até 12 referências e 12 autores; o contrato mantém todos os dados
recuperados e a comparação considera todas as referências disponíveis.


## Catálogo automático (v0.2)

`POST /api/analyses/{id}/discovery` executa um fluxo separado, limitado a 18s,
com consultas concorrentes ao OpenAlex e Europe PMC, resolução no Wikidata e
persistência de candidatos. `external_discovery` na Analysis é opcional para
compatibilidade com investigações anteriores. O retorno é `complete`, `partial`
ou `unavailable`, com fontes, consultas sem segredos, datas e limitações.

As tabelas `external_cache`, `catalog_candidates` e `catalog_revisions` são
criadas automaticamente. Os endpoints `/api/catalog/candidates` e
`/api/catalog/candidates/{id}` permitem inspecionar o catálogo e suas versões.
O frontend oferece ação de ampliação, filtro de identidade documentada e fontes,
sem transformar candidatos pendentes em nós verificados. A exportação inclui
os resultados e todas as limitações. Não há endpoint de aprovação editorial.


## Studio — T05

`api/studio_preview.py` compõe somente POST `/api/studio/preview` e GET
`/api/studio/previews/{id}` em `main.py`. A leitura do corpo é limitada em
streaming antes do Pydantic; erros usam StudioError. Os schemas M0 permanecem
inalterados. A composição T10 abaixo conecta revisão, geração, consulta e exportação às
portas existentes, sem substituir os contratos ou renderizadores.

`services/studio/preview.py` usa `build_scientific_context` e
`search_context_contributions` de T04. O planner recebe documentos e IDs
permitidos; o servidor materializa pesquisadores, explicação e afirmação
histórica canônica. A resposta passa pelo schema interno e por
`EnrichmentPreview.validate_scientific_authority` antes de publicar.

`integrations/gemini_client.py` implementa StudioProvider com o SDK oficial,
JSON Schema, contagem de tokens, ferramentas desabilitadas e deadline comum.
A construção é preguiçosa: importar/iniciar o Forensics não requer chave.

`services/studio/repository.py` implementa a fatia de prévia das portas M0,
com migração transacional aditiva e foreign keys apenas nas novas entidades.
Inclui as cinco tabelas Studio e tabelas auxiliares de sessão, admissão e cota;
não modifica tabelas Forensics. Admissão/publicação são transações curtas,
sem transação na chamada externa. Ownership é um hash do token opaco HttpOnly.
Operações abandonadas liberam a admissão após 45 + 15 s. GET não renova o prazo.
A composição inicial T05 usava limpeza horária; a T13 conecta o lifespan T12
descrito abaixo, sem depender de um acesso Studio. Nova tentativa mantém o último projeto utilizável até publicar, e GET
materializa o erro corrente separado dos originais/snapshots anteriores.
O bloqueio persistido impede duas operações ativas da mesma sessão. A chave
idempotente de geração pertence ao futuro endpoint `/generate`; T05 não cria
semântica concorrente para POST de prévia.

O frontend mantém os modos montados ao alternar. StudioWorkspace usa o cliente
HTTP real e navegação por hash para retomar a prévia. ReviewWorkspace e
LessonWorkspace existentes permanecem módulos independentes, sem mocks em
produção ou botões que aparentem executar revisão/geração ainda não integradas.


## Studio — integração T10

`api/studio_runtime.py` compõe POST de revisão, o router de geração T09, GET
lesson e o router Markdown T11. `get_repository` fornece `StudioRepository`,
que estende a persistência T05 no mesmo banco; `get_provider` seleciona
o adaptador real NVIDIA por padrão ou Gemini explicitamente; permite substituição
explícita somente nos testes. Não há fallback automático.

`services/studio/runtime_repository.py` grava revisão e operações de geração em
transações curtas, com comparação da revisão, ownership, expiração e idempotência.
Prévia e geração compartilham admissão/capacidade. Nenhuma transação atravessa
uma chamada de rede. O fingerprint comum mora em `generation_identity.py`;
o adaptador isolado T09 permanece exclusivo dos testes/harnesses.

A publicação da prévia grava um snapshot científico separado e validado no
servidor. A geração reutiliza esse snapshot, incluindo Papers e evidências,
sem consultar novamente uma investigação que pode ter expirado. A migração é
aditiva. Prévias anteriores sem snapshot permanecem consultáveis; precisam de
nova prévia para gerar com autoridade verificável.

`StudioWorkspace` conecta os componentes T05/T07/T09/T08 a APIs reais. As rotas
hash de revisão, geração e aula retomam o estado persistido da sessão; a entrega
consulta o bundle imutável retornado pela geração. Campos científicos e contratos
M0 permanecem inalterados. Detalhes de verificação em `studio-flow-t10.md`.


## Studio — composição T13

A prévia delega a resolução DOI/analysis_id ao resolvedor T06, reutilizando T04
e preservando o snapshot da investigação. A configuração recebe o ID do
Forensics; o servidor resolve e persiste a autoridade, sem confiar em ciência
enviada pelo cliente. O dossiê integrado renderiza a prévia canônica M0, sem
criar Paper/grafo/classificação para material textual. Editor e visualizador
continuam montados ao explorar evidências. Com analysis_id, o host consulta a
investigação existente e seleciona a contribuição; em indisponibilidade/expiração,
usa o dossiê canônico retido. Cada contribuição usada pela aula tem ação própria.
Respostas de uma operação anterior
não substituem uma nova origem selecionada.

`api/studio_lifecycle.py` compõe `studio_maintenance_lifespan` T12: varredura
inicial e a cada 15 s, reconciliação de operações abandonadas, falhas de storage
sanitizadas e encerramento da tarefa. `StudioMetrics` vive no estado do app e é
compartilhado com o serviço de geração; nenhuma rota pública de métricas é criada.

`services/studio/timings.py` mede as seis etapas de prévia com relógio monotônico
e eventos sem material/chave. Não altera deadlines, schemas, validação ou retries.
Os routers de exportação T11 e persistência/autorização T10 são reutilizados
integralmente; os testes T13 verificam sua composição no host real.
Ver `integrated-demo-t13.md` para evidências e limitações.


## Studio — NVIDIA NIM (#31)

`integrations/nvidia_client.py` implementa as mesmas portas sem mudar API, schemas,
tabelas ou catálogo. HTTPX envia `response_format.json_schema` com o schema privado
integral: PreviewPlan na prévia e LessonDraft na geração. O serviço materializa e
valida LessonBundle contra a revisão e o snapshot científico existentes. O provedor
não recebe autoridade para inventar referências ou identidades.

NVIDIA_API_KEY vem exclusivamente do ambiente do backend. AI_PROVIDER seleciona
nvidia (padrão) ou gemini (explícito); valor desconhecido falha dentro da operação,
preservando material/revisão. Nenhum SDK realiza retries ocultos no adaptador NVIDIA.
A admissão SQLite continua impondo uma operação por sessão e duas globais, comuns
à prévia e geração; limites HTTPX não substituem essa admissão persistida.

Contagem NVIDIA é estimada conservadoramente antes da rede, sem endpoint de
inferência adicional. Payload completo UTF-8 + reserva de 1.024 tokens; nunca
chars/4 nem tokenizer de outro modelo. Uso efetivo é verificado no retorno e
registrado junto da estimativa e diferença. Ver [guia NVIDIA](studio-nvidia.md).
