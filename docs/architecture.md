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
inalterados. Revisão, geração e exportação Studio continuam reservadas às
portas/consumidores dos tickets posteriores.

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
O bloqueio persistido impede duas operações ativas da mesma sessão. A chave
idempotente de geração pertence ao futuro endpoint `/generate`; T05 não cria
semântica concorrente para POST de prévia.

O frontend mantém os modos montados ao alternar. StudioWorkspace usa o cliente
HTTP real e navegação por hash para retomar a prévia. ReviewWorkspace e
LessonWorkspace existentes permanecem módulos independentes, sem mocks em
produção ou botões que aparentem executar revisão/geração ainda não integradas.
