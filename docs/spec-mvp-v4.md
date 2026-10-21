# Matilda v4 — Especificação técnica do MVP do hackathon

Status: especificação aprovada pelo usuário, incorporando os ajustes finais de escopo e organização. Autoriza-se a publicação como uma única GitHub Issue; a implementação não foi iniciada.

Origem: PRD v4.0, lido integralmente, instruções aprovadas para agentes e implementação local. Base de código inspecionada: commit `273ced944fc31593fa753d87bf01c02a1adb5516`. Data: 21/10/2026. Apresentação prevista no PRD: 22/10/2026.

Destino de publicação: GitHub Issues de `zazacknazzo/Matilda-mvp`, label `ready-for-agent`. O repositório e o deploy diferentes citados no PRD são referências do documento, não destinos autorizados desta especificação.

As escolhas de limites, estados, controle de sessão e extensões de API abaixo fecham lacunas do PRD. A aprovação estabiliza as decisões da especificação; o marco M0 ainda exige materializar e conferir os contratos compartilhados antes da implementação paralela. Não representa implementação ou validação já realizadas.

## Problem Statement

Professores precisam transformar conteúdos científicos em aulas que expliquem contribuições femininas com contexto e fontes conferíveis. Hoje o Forensics investiga artigos por DOI, apresenta contribuições documentadas, grafo e evidências, mas não produz uma sequência pedagógica ou apresentação.

O prazo do hackathon exige demonstrar uma jornada integrada e estável. A equipe precisa desenvolver o Studio em paralelo sem reconstruir o Forensics, duplicar o catálogo ou alterar contratos compartilhados de forma incompatível.

## Solution

Entregar o fluxo: texto, conceitos ou DOI → contexto científico compartilhado → sugestões fundamentadas → revisão do professor → LessonBundle validado → slides, plano imprimível e Markdown.

O Forensics permanece operacional. A ação **Transformar em aula** reaproveita uma investigação existente. O Studio oferece **Explorar descoberta** para conferir a contribuição, seus participantes e documentos na investigação ou no dossiê científico correspondente.

O MVP usa React, FastAPI, Pydantic, SQLite e Gemini no backend. O LessonBundle é a única representação dos materiais gerados; slides e plano são duas renderizações dos mesmos dados. A revisão humana permanece visível, inclusive quando a estrutura e os identificadores passam na validação automática.

## User Stories

As 36 histórias descrevem necessidades e rastreabilidade do produto. Não equivalem a 36 tickets obrigatórios nem autorizam sua criação automática. A unidade de entrega do hackathon é o fluxo P0 integrado definido abaixo, organizado nas quatro frentes; melhorias de profundidade não bloqueiam esse fluxo.

1. Como professor, quero escolher entre Forensics e Studio, para iniciar pela investigação ou pelo planejamento da aula.
2. Como usuário do Forensics, quero continuar recuperando artigos por DOI, para preservar o fluxo já disponível.
3. Como usuário do Forensics, quero continuar usando grafo, lista, dossiês, comparação bibliográfica e exportações, para conferir as investigações existentes.
4. Como usuário do Forensics, quero manter a descoberta automática separada do catálogo verificado, para distinguir candidatos de contribuições revisadas.
5. Como professor, quero transformar uma investigação em aula, para reaproveitar artigo, conceitos, contribuições e evidências sem preencher tudo novamente.
6. Como professor, quero iniciar uma aula com texto livre, para trabalhar a partir do material que já utilizo.
7. Como professor, quero iniciar com conceitos ou um DOI, para preparar uma aula mesmo sem texto pronto.
8. Como professor, quero informar tema, disciplina, nível e duração, para adequar o resultado à turma.
9. Como professor, quero fornecer objetivos de aprendizagem, para orientar a organização pedagógica.
10. Como professor, quero revisar objetivos sugeridos quando não os informar, para conservar a decisão sobre o que ensinar.
11. Como professor, quero conhecer quais partes do material serão enviadas ao provedor de IA, para decidir se posso utilizar esse conteúdo.
12. Como professor, quero conservar o material original separado do conteúdo gerado, para identificar as intervenções propostas.
13. Como professor, quero ver conceitos identificados e sua procedência, para entender a relação entre meu conteúdo e a pesquisa científica.
14. Como professor, quero receber contribuições do mesmo motor do Forensics, para consultar fontes e classificações consistentes.
15. Como professor, quero entender o que inserir, onde inserir e por que inserir, para avaliar cada enriquecimento.
16. Como professor, quero abrir a evidência e a afirmação sustentada, para conferir a atribuição científica.
17. Como professor, quero ver todos os participantes documentados da publicação, para evitar atribuições exclusivas de trabalho coletivo.
18. Como professor, quero distinguir correspondência temática de citação e influência histórica, para explicar corretamente a relação científica.
19. Como professor, quero aceitar ou rejeitar sugestões individualmente, para controlar o conteúdo da aula.
20. Como professor, quero editar a proposta pedagógica preservando o trecho científico documentado, para adaptar a abordagem sem alterar a evidência.
21. Como professor, quero conservar minhas decisões após uma falha ou recarregamento, para tentar novamente sem refazer a revisão.
22. Como professor, quero gerar a aula apenas após revisar objetivos e sugestões, para impedir inclusões automáticas não aprovadas.
23. Como professor, quero receber uma aula mesmo sem enriquecimentos aceitos, para utilizar o planejamento sem inserir atribuições indesejadas.
24. Como professor, quero ser informado quando faltar cobertura documental, para não confundir ausência no catálogo com ausência de contribuições femininas.
25. Como professor, quero um plano com objetivos, conhecimentos prévios, materiais, sequência, atividades e avaliação, para conduzir a aula.
26. Como professor, quero que a sequência respeite a duração escolhida, para organizar o tempo em sala.
27. Como professor, quero slides com diferentes layouts e fontes identificáveis, para apresentar o conteúdo com clareza.
28. Como professor, quero notas separadas dos slides projetados, para consultar orientações sem exibi-las aos alunos.
29. Como professor, quero navegar por teclado e usar tela cheia, para conduzir a apresentação no projetor.
30. Como professor, quero consultar referências e limitações no plano e nos slides relevantes, para conferir o que estou ensinando.
31. Como professor, quero imprimir o plano ou salvá-lo como PDF pelo navegador, para utilizá-lo fora do Matilda.
32. Como professor, quero exportar Markdown com fontes, para editar ou guardar uma versão textual.
33. Como usuário, quero mensagens claras de limite, falha ou indisponibilidade, para decidir quando corrigir a entrada ou tentar novamente.
34. Como usuário, quero operar a interface no celular e por teclado, para acessar o fluxo sem depender exclusivamente de mouse, grafo ou cor.
35. Como professor, quero que meus materiais sejam acessíveis apenas na minha sessão e tenham retenção definida, para evitar exposição desnecessária.
36. Como integrante da equipe, quero contratos e dependências definidos antes da implementação paralela, para integrar as quatro branches com segurança.

## Implementation Decisions

### 1. Escopo P0 e preservação do Forensics

- P0: texto, conceitos e DOI; navegação entre modos; análise pedagógica; sugestões revisáveis; geração estruturada real; seis layouts; plano e notas; impressão do plano; Markdown; rastreabilidade; tratamento de erros; regressão e demonstração.
- Manter contexto único e a infraestrutura atual. Acrescentar serviços Studio e adaptadores explícitos, sem migrar framework, banco ou catálogo.
- Preservar os contratos de artigo, investigação, grafo, evidência, candidatos e exportações, incluindo formatos, códigos de sucesso e classificações. A criação de investigação continua síncrona com HTTP 201.
- Preservar IDs científicos, autoria coletiva, ranking determinístico, cache identificado, tratamento de DOI inválido e distinção entre catálogo editorial e candidatos pendentes.
- O Studio não precisa executar descoberta externa adicional para gerar uma aula. Os candidatos automáticos continuam disponíveis no Forensics e nunca entram no conjunto de atribuições elegíveis do Studio.
- A disponibilidade da chave Gemini afeta apenas o Studio. Importar ou iniciar o backend e usar o Forensics deve continuar possível sem essa chave.

**P0 rigoroso para demonstrar até 22/10/2026:** todos os critérios abaixo devem funcionar na mesma versão integrada. Não há aceite por telas isoladas, mocks apresentados como produção ou partes de uma jornada ainda desconectadas.

| Entrega indispensável | Corte mínimo e critério de pronto | Responsáveis |
|---|---|---|
| P0-1 — ciência preservada | regressão Forensics aprovada; um único motor/catálogo; texto/conceitos e DOI produzem contexto rastreável sem Paper fictício | A, com B como consumidor |
| P0-2 — entrada e prévia | configurar aula e preservar material; recuperar contribuições elegíveis; cada sugestão informa o que, onde, por que e fonte; sem cobertura, aviso explícito | A + B + C |
| P0-3 — decisão docente | aceitar/rejeitar individualmente, ajustar a abordagem pedagógica e aprovar objetivos; salvar e retomar revisão; nenhuma evidência histórica é editável | C + B |
| P0-4 — geração real | Gemini retorna LessonBundle validado baseado apenas na revisão aprovada; erro preserva material e decisões; nenhum sucesso fictício | B, com validação científica de A |
| P0-5 — aula utilizável | mesmo bundle produz slides navegáveis em 16:9 e plano com sequência, duração, objetivos, atividade avaliativa, notas e fontes; seis layouts simples, sem editor livre | D |
| P0-6 — entrega do material | Markdown e impressão do plano/salvar PDF pelo navegador; nenhuma nova chamada de IA para exportar | D, com endpoint mantido por B |
| P0-7 — integração dos modos | Transformar em aula e Explorar descoberta funcionam preservando a investigação e o estado do Studio; teclado e tela pequena utilizáveis | A + C + D |
| P0-8 — demonstração estável | duas aulas de 50 minutos ensaiadas, CRISPR e RNA, mais caso sem cobertura e falha controlada; E2E integrado, backend/build aprovados, configuração reproduzível | A/B/C testam sua frente; D mantém E2E e coordena o ensaio |

O recorte de apresentação são duas aulas e uma sessão docente por navegador, com tipos de atividade já definidos, armazenamento local/persistente de demonstração e interface mínima funcional. Não exige biblioteca de projetos, editor de slides, novos domínios científicos, upload, exportações adicionais ou infraestrutura distribuída. Os limites gerais do contrato não ampliam os cenários obrigatórios do pitch. O fluxo **entrada de material → recuperação científica → sugestões verificáveis → aprovação docente → geração estruturada → slides e plano de aula** é indivisível e não pode ser removido por corte de prazo.

### 2. Contratos comuns e regras de representação

- Contrato Studio inicial: `schema_version = 1`. JSON em snake_case; datas UTC em ISO 8601; durações em minutos inteiros; listas vazias quando não houver elementos. Campos opcionais e sua nulabilidade devem constar no OpenAPI.
- Novos modelos Pydantic rejeitam campos desconhecidos, tipos incompatíveis, referências cruzadas inválidas e limites excedidos. Não alterar retroativamente a política dos modelos antigos do Forensics.
- O contrato HTTP publicado pelo backend é a referência para os tipos TypeScript. A primeira integração deve incluir exemplos válidos e inválidos compartilhados, usados pelo frontend, backend e testes.
- IDs de projeto, documento, contexto, prévia, sugestão e aula são gerados pelo servidor. O modelo pode selecionar IDs científicos autorizados; não cria pesquisadores, documentos, evidências ou URLs canônicas.
- Componentes gerados pela IA usam chaves locais apenas dentro de sua resposta; o servidor valida os vínculos e atribui os IDs finais. O cliente não precisa interpretar IDs de forma especial.

| Estrutura | Campos e regras do contrato inicial |
|---|---|
| LessonProject | `id`, `title`, `subject`, `education_level`, `duration_minutes`, `learning_objectives`, `scientific_context_id`, `status`, `created_at`, `updated_at`, `last_teacher_activity_at`, `expires_at`; pertencimento à sessão mantido apenas no servidor |
| SourceDocument | `id`, `project_id`, `type` em `text`, `concept_list`, `paper_metadata`; `title`, `content`, `doi` opcional, `extraction_status = ready`; conteúdo original imutável por prévia, separado das saídas |
| ScientificContext | `id`, `origin_type` em `doi`, `material`, `mixed`; `paper_ids`, `concept_ids`, `concept_labels`, `source_document_ids`, `provenance`, `limitations`; labels alinhados por posição aos IDs; `analysis_id` opcional |
| Provenance | `source_document_id`, `concept_id` opcional, `method` em `teacher_input`, `editorial_alias`, `openalex_metadata`, `ai_suggested`; `quote` opcional e literal; `retrieved_at`, `from_cache` e `source_url` quando originada em consulta científica |
| SourceAnchor | `source_document_id`, `quote` literal não vazia, `occurrence` inteiro a partir de zero; o backend confirma a ocorrência no documento; sem material textual, ancorar no documento de conceitos ou nos metadados reais do DOI |
| EnrichmentSuggestion | `id`, `project_id`, `concept_ids`, `source_anchor`, `researcher_ids`, `contribution_id`, `evidence_ids`, `scientific_explanation`, `historical_claim`, `pedagogical_rationale`, `suggested_content`, `status` em `pending`, `accepted`, `rejected`; o trecho histórico é preenchido pelo servidor a partir da evidência |
| EnrichmentPreview | `preview_id`, `project_id`, `schema_version`, `scientific_context`, `concepts`, `suggested_objectives`, `suggestions`, `evidence_references`, `limitations`, `review_revision`, `expires_at`, `generation_metadata`, `generation_status`, `last_lesson_bundle_id` opcional; prazo é o prazo corrente do projeto, não um snapshot desatualizado |
| EvidenceReference | evidência canônica com ID, contribuição associada, afirmação sustentada, título, URL, localização, tipo e estado de verificação; snapshot conferido no servidor; mantém participantes e limitações da contribuição associada |
| LessonMetadata | título, disciplina, nível, duração, objetivos aprovados, conhecimentos prévios e materiais necessários; valores configurados pelo professor prevalecem sobre sugestões do modelo |
| LessonBundle | `lesson_bundle_id`, `project_id`, `preview_id`, `schema_version`, `review_revision`, `metadata`, `sections`, `slides`, `activities`, `references`, `limitations`, `generation_metadata` |
| GenerationMetadata | provedor, modelo efetivo, versão do prompt, versão do contrato, instante, duração e contagem de tokens quando disponível; sem chave, prompt completo ou material original em logs |

As listas de conceitos podem conter labels adicionais sugeridos pela IA, apresentados separadamente como sugestões pedagógicas. Somente IDs resolvidos pelo catálogo ou pela fonte científica entram em `ScientificContext.concept_ids`; a IA não cria correspondências editoriais por similaridade livre.

### 3. ScientificContext e recuperação compartilhada

- Criar um ponto de entrada de recuperação que aceite contexto e referências bibliográficas reais opcionais. Reutilizar seleção, elegibilidade e ordenação do motor atual; manter o ponto de entrada por artigo como adaptador compatível.
- Resolver termos de texto e conceitos pelos mesmos aliases, normalização e limites de palavra do catálogo existente. Guardar a origem de cada correspondência. O título pode contribuir como tema; objetivos gerados pela IA não se tornam evidência científica.
- Preservar o filtro específico de RNA: imunogenicidade isolada não basta; é necessária correspondência editorial com RNA mensageiro ou modificação de nucleosídeos.
- Para DOI, reutilizar normalização, recuperação, cache, conceitos e referências atuais. Para uma investigação existente, reutilizar os objetos já recuperados, sem nova chamada obrigatória ao OpenAlex.
- Para texto sem DOI, não criar Paper, DOI, autor ou referências fictícias. A relação continua `RELATED_TO`; a comparação bibliográfica é `UNKNOWN` por falta de artigo comparável, ou `THEMATIC_ONLY` quando a própria contribuição não tem publicação associada, conforme a semântica atual.
- Para origem mista, a comparação bibliográfica se refere exclusivamente ao artigo vinculado; conceitos adicionais do material têm procedência distinta. Não apresentar a bibliografia do artigo como se fosse a bibliografia do material docente.
- São elegíveis apenas contribuições verificadas, pesquisadores com identidade verificada e evidências verificadas de tipo documental ou histórico, corretamente ligadas à contribuição. Preservar coautores e limitações.
- Sem cobertura, retornar contexto válido, lista vazia de sugestões científicas e limitação explícita. A aula pode ser gerada sem enriquecimento histórico, com conteúdos pedagógicos identificados como gerados por IA.

### 4. Pipeline Gemini e controle das atribuições

- Executar workflow controlado pela aplicação: resolver entrada e recuperar ciência → analisar material e planejar sugestões → revisão humana → gerar aula → validar → persistir → renderizar.
- Primeira chamada de IA: análise pedagógica, seções, objetivos sugeridos e propostas de enriquecimento, já com o conjunto científico autorizado. Segunda chamada: LessonBundle baseado na revisão persistida. Esta ordem escolhe explicitamente o fluxo de duas chamadas sugerido no PRD.
- Usar SDK Python `google-genai`, chave `GEMINI_API_KEY` e modelo configurável por `GEMINI_MODEL`, inicialmente `gemini-3.8-flash`. Fixar a versão do SDK compatível durante a implementação e registrar o modelo efetivo em cada resultado.
- O identificador e o suporte a saídas estruturadas constam na [documentação oficial do Gemini 3.8 Flash](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash). A integração deve usar o mecanismo de JSON Schema/Pydantic descrito em [saídas estruturadas](https://ai.google.dev/gemini-api/docs/structured-output), mantendo validação própria de domínio no servidor. Disponibilidade e quota da chave da equipe precisam de ensaio real.
- O material é dado não confiável, delimitado do comando do sistema. Desabilitar ferramentas, navegação, execução de código e ações autônomas do modelo neste fluxo. Instruções existentes no material não alteram o conjunto autorizado nem as regras de geração.
- A IA produz decisões pedagógicas e referências a IDs permitidos. Nomes de pesquisadores, participantes, URLs, estados de verificação e afirmações históricas são resolvidos pelo servidor.
- Representar inserções históricas como blocos `evidence_claim` contendo um ID de evidência permitido. O renderizador e o exportador resolvem o texto exato de `claim_supported` no snapshot canônico. O modelo não fornece uma paráfrase histórica a ser marcada como verificada.
- Separar texto pedagógico, conteúdo original e afirmação documental. Edições do professor podem alterar proposta de inserção, justificativa e abordagem; campos de evidência e o trecho histórico permanecem bloqueados. Alterar a evidência exige uma nova prévia.
- Validar em toda sugestão e aula: contribuição elegível; evidência existente e pertencente à contribuição; pesquisadores associados; conceitos correspondentes; referência no conjunto autorizado; sugestão aceita na revisão usada.
- Rejeitar referências novas, IDs estranhos ao contexto e conteúdo de sugestões rejeitadas. Não buscar referências sugeridas pelo modelo para tentar legitimar uma saída inválida.
- Validação estrutural não garante correção semântica de texto livre. Proibir novas atribuições históricas nos campos pedagógicos por instrução, manter os blocos históricos controlados e exigir revisão humana do material completo antes de uso ou pitch. Não prometer detecção automática infalível de alegações inventadas.

### 5. API Studio

Todos os endpoints Studio exigem a sessão proprietária, exceto a criação inicial de sessão durante a primeira prévia. Respostas bem-sucedidas são objetos JSON com os campos definidos abaixo; o exportador retorna arquivo. Erros mantêm `detail` textual e acrescentam `code`, `retryable` e, quando disponível e pertencente à sessão, `project_id`.

| Operação | Entrada e comportamento | Saída |
|---|---|---|
| `POST /api/studio/preview` | campos pedagógicos, `objectives`, `concepts`, `material_text`, `doi` opcional ou `analysis_id` opcional; `project_id` opcional para nova prévia do mesmo projeto | HTTP 201 com EnrichmentPreview; persiste projeto e documentos originais antes da IA; prévia só fica disponível após validação |
| `GET /api/studio/previews/{id}` | sessão proprietária | HTTP 200 com EnrichmentPreview, decisões e configuração/documentos originais necessários para retomar o formulário; sem chamar IA |
| `POST /api/studio/previews/{id}/review` | `review_revision` esperada, lista `decisions` com `suggestion_id`, `status` e edição pedagógica opcional; `approved_objectives` | HTTP 200 com prévia revisada, revisão incrementada e decisões persistidas; sem chamar IA |
| `POST /api/studio/generate` | `preview_id`, `review_revision`, `accepted_suggestion_ids`; cabeçalho `Idempotency-Key` obrigatório | HTTP 201 com LessonBundle validado; repetição concluída da mesma operação retorna o mesmo bundle com HTTP 200 |
| `GET /api/studio/lessons/{id}` | sessão proprietária | HTTP 200 com LessonBundle persistido, sem nova geração |
| `GET /api/studio/lessons/{id}/export?format=markdown` | sessão proprietária; único formato P0 | HTTP 200, arquivo Markdown UTF-8 e nome de download seguro; demais formatos retornam 422 |

Os endpoints de consulta da prévia e gravação da revisão complementam o PRD para preservar decisões, oferecer retomada e separar revisão de chamadas cobradas de IA. A consulta também informa `generation_status` em `idle`, `generating`, `ready` ou `failed` e o último bundle, quando houver, permitindo recuperar conclusão após falha de conexão. Não acrescentar CRUD completo de projetos ao MVP.

Regras de entrada:

- `title`: obrigatório, 1–160 caracteres após remover espaços externos. Disciplina e nível: até 80 caracteres cada; formulário mostra defaults editáveis `Ciências` e `Ensino Médio`. Duração: 10–120 minutos, default visível de 50.
- `objectives`: 0–10 textos de até 300 caracteres; `concepts`: 0–20 textos de até 100 caracteres; `material_text`: até 20.000 caracteres; corpo HTTP total: até 128 KiB. Valores acima do limite de corpo retornam 413; violações de campo retornam 422.
- Exigir ao menos uma origem: texto não vazio, conceitos, DOI ou investigação. Tema isolado não substitui uma origem, mas pode ser copiado explicitamente pelo professor para a lista de conceitos.
- DOI usa o validador atual, inclusive seu limite efetivo e proibição de URLs arbitrárias. `doi` e `analysis_id` são alternativas: enviar ambos retorna 422. Uma investigação inexistente ou expirada retorna 404; nenhuma investigação é criada artificialmente para texto.
- `approved_objectives`: 1–10 objetivos após revisão, mesmo se a entrada original não os informou. Objetivos originais são preservados e exibidos; sugestões nunca os substituem silenciosamente.
- Revisões rejeitam IDs repetidos, sugestões de outra prévia e alterações de campos históricos. A interface marca sugestões ainda não decididas como pendentes; gerar exige todas decididas e objetivos aprovados. Aceitar zero sugestões é permitido.
- Os IDs aceitos enviados a `generate` devem coincidir exatamente com a revisão persistida. Alterar texto original, DOI ou configuração pedagógica cria uma nova prévia e exige nova revisão; a anterior permanece recuperável até expirar.
- Revisão obsoleta retorna 409. Prévia expirada ou recurso de outra sessão retorna 404 com mensagem genérica. Falta de chave/configuração Gemini retorna 503; entrada inválida não é tratada como falha do provedor.

Erros operacionais Studio:

| HTTP | `code` | Comportamento |
|---|---|---|
| 422 | `invalid_input` | indicar campos inválidos; nenhuma chamada de IA |
| 404 | `not_found` | recurso não encontrado, expirado ou não acessível à sessão |
| 409 | `review_conflict` ou `generation_in_progress` | atualizar revisão ou aguardar; não duplicar geração |
| 413 | `input_too_large` | reduzir material; nenhuma chamada de IA |
| 429 | `session_limit` | informar espera/quota; incluir `Retry-After` quando temporal |
| 502 | `invalid_generation` | JSON ou conteúdo fora do contrato; não persistir bundle inválido |
| 503 | `provider_unavailable` ou `studio_not_configured` | preservar estado e permitir tentativa quando cabível |
| 504 | `generation_timeout` | encerrar a operação dentro do prazo e preservar revisão |

Erros do OpenAlex reutilizam os status do serviço existente, adaptando apenas o envelope Studio sem alterar o Forensics. O frontend nunca exibe erro bruto do provedor nem detalhes com credenciais.

### 6. LessonBundle, plano e slides

- `metadata` contém os campos do plano, incluindo objetivos aprovados, conhecimentos prévios e materiais necessários. Todas as visualizações usam esses mesmos valores.
- Cada seção possui `id`, `title`, `duration_minutes`, `objective_indexes` referentes à lista de objetivos, `explanation_blocks`, `slide_ids` e `activity_ids`. A sequência é a ordem da lista; duração estritamente positiva.
- Cada slide possui `id`, `section_id`, `layout`, `title`, `subtitle` opcional, `content_blocks`, `speaker_notes`, `duration_minutes`, `contribution_ids` e `evidence_ids`. Notas incluem objetivo, orientação, perguntas e exemplos, com texto pedagógico claramente separado dos blocos documentais.
- Blocos P0: `text`, `bullets`, `steps`, `question`, `evidence_claim`. Texto e itens são strings simples; `evidence_claim` referencia uma evidência autorizada. Imagens remotas e HTML da IA não fazem parte do contrato.
- Layouts: `TITLE` para abertura; `CONCEPT` para texto ou bullets; `PROCESS` com 2–6 etapas; `SCIENTIST_SPOTLIGHT` com contribuição aceita e bloco documental obrigatório; `QUESTION` com pergunta; `SUMMARY` para síntese. Renderização e identidade visual pertencem aos componentes React/CSS.
- Cada atividade possui `id`, `section_id`, `type` em `comprehension` ou `discussion`, `prompt`, `teacher_guidance`, `objective_indexes` e `assessment_criteria`. Toda aula inclui ao menos uma atividade avaliativa ligada a objetivo aprovado.
- Cada slide pertence a exatamente uma seção e é referenciado uma vez; atividades também têm vínculo válido. Toda seção possui ao menos um slide. A duração de uma atividade integra a seção correspondente, sem ser somada novamente ao total.
- A soma das durações das seções deve ser exatamente a duração da aula, tolerância zero. A soma dos slides de cada seção deve coincidir com a duração da seção, incluindo o tempo de atividades orientadas por esses slides.
- Limites iniciais: 3–8 seções, 4–12 slides, 1–4 atividades, até 6 blocos por slide; título de slide até 100 caracteres; até 600 caracteres visíveis de texto pedagógico por slide; até 1.500 caracteres de notas por slide. Afirmações canônicas têm limite próprio de 1.500 caracteres e não são truncadas para mudar seu sentido. Resposta gerada com no máximo 128 KiB. Aulas de 50 minutos devem preferir 6–12 slides, sem tornar isso requisito universal.
- Respostas com conteúdo excessivo ou tempo inválido são rejeitadas ou corrigidas na tentativa controlada, nunca cortadas silenciosamente ou normalizadas alterando o significado.
- `references` é montado no servidor a partir das evidências efetivamente utilizadas nas sugestões aceitas e nos blocos do bundle, com deduplicação por ID e snapshot de procedência. O artigo de origem pode aparecer separado como material de base; não confundir fonte de entrada com evidência de atribuição.
- Os conjuntos de contribuição/evidência declarados por cada slide devem coincidir com seus blocos documentais. Quando nenhuma sugestão foi aceita, não criar spotlight ou referência histórica; informar que a aula foi gerada sem enriquecimentos científicos aprovados.
- Imprimir e exportar inclui objetivos, cronologia, atividades, avaliação, notas, fontes e limitações. Conteúdo original do professor não é anexado integralmente por padrão. O exportador usa o bundle validado, sem nova chamada de IA.

### 7. Persistência, revisão e idempotência

- Acrescentar as entidades propostas no PRD: `lesson_projects`, `source_documents`, `enrichment_previews`, `enrichment_suggestions`, `lesson_bundles`. Persistir revisões, metadados de geração e resultados validados nessas entidades; manter documentos originais separados.
- Usar migração aditiva e transacional. Não apagar ou reescrever tabelas de cache, investigações, candidatos ou histórico existentes. Ativar integridade referencial nas novas relações.
- Estados do projeto: `draft`, `preview_ready`, `reviewed`, `generating`, `ready`. Registrar falha da última operação separadamente; uma tentativa malsucedida não apaga o último estado utilizável nem bundles anteriores.
- Transições: prévia válida leva `draft` a `preview_ready`; todas as sugestões decididas e objetivos aprovados levam a `reviewed`; geração reclamada leva a `generating`; bundle validado leva a `ready`. Falha de geração devolve a `reviewed`, preservando eventual bundle anterior. Editar revisão de projeto pronto volta a `reviewed`; nova prévia válida volta a `preview_ready` e exige nova revisão. Só promover estado após a operação correspondente concluir de forma transacional.
- Salvar material e configuração antes de iniciar a prévia; salvar revisão antes da geração. Uma falha mantém o material no formulário e no projeto; o erro pode devolver o `project_id` próprio para repetição. A consulta da prévia permite retomar decisões após recarregamento.
- Operações de revisão usam incremento atômico de `review_revision`. Ao iniciar geração, congelar essa revisão e seus conteúdos; revisão paralela durante a operação retorna 409. Um bundle concluído é imutável e registra a revisão utilizada.
- Idempotência vinculada à sessão, prévia, revisão e chave. Mesma chave com entrada diferente retorna 409; chamada repetida concluída retorna o bundle existente; chamada em andamento retorna 409. Persistir e reclamar a operação atomicamente antes da IA, sem manter transação SQLite aberta durante a chamada externa.
- Após falha, uma tentativa explícita pode reutilizar a chave sem duplicar um bundle concluído. Uma falha de rede antes de gravar a resposta pode ainda ter consumido tokens no provedor; não prometer cobrança exatamente uma vez.
- Em reinício do processo, operações sem conclusão expiram após o prazo da etapa mais 15 segundos, liberando repetição. Persistência da revisão e idempotência não podem depender só de locks em memória.

### 8. Interface e integração bidirecional

- Manter a entrada Forensics já acessível na raiz e adicionar seleção clara de modo na interface. O Studio pode usar navegação por hash para evitar dependência de reescrita de rotas no hosting.
- Encapsular a navegação sem remontar ou descartar a investigação ao alternar de modo. O editor Studio conserva sua prévia revisada ao voltar do dossiê.
- **Transformar em aula** envia apenas `analysis_id` da investigação real; título e campos pedagógicos são apresentados para confirmação. O servidor resolve os dados científicos, não confia em objetos reenviados pelo cliente.
- **Explorar descoberta** abre a análise existente e a contribuição selecionada quando houver `analysis_id`. Na origem somente textual, abre um dossiê dos mesmos registros científicos; não cria grafo ou artigo raiz fictícios.
- Workspace de enriquecimento apresenta material original, sugestões e evidências; em tela pequena, empilhar ou usar abas acessíveis. Aceitar/rejeitar e editar a abordagem persistem pela operação de revisão.
- A aula possui visualizações de apresentação e plano. Slides em 16:9, anterior/próximo, progresso, setas de teclado, Home/End e Escape para sair; atalhos não capturam digitação em campos editáveis. Tela cheia depende de gesto do usuário e tem alternativa dentro da página.
- Notas ficam no plano ou painel separado e ocultas no modo projetado. Referências continuam consultáveis nos slides documentais. Não construir sistema de dois monitores no MVP.
- Preservar foco visível, rótulos, mensagens anunciáveis e navegação por teclado; respeitar redução de movimento. Informações científicas incluem texto, não apenas cor. Validar desktop e viewport de 390 × 844 sem rolagem horizontal da página.
- O plano usa estilos de impressão com quebras legíveis e exclusão dos controles. Salvar PDF é a função do navegador; não há endpoint de PDF binário P0.

### 9. Limites operacionais, privacidade e deploy

- Manter os timeouts do Forensics, inclusive a política atual de recuperação bibliográfica. O teto de 22 segundos do cliente existente não pode ser aplicado às operações Studio.
- Separar metas de desempenho e tetos de execução: prévia em até 30 segundos e geração em até 45 segundos são metas do PRD, medidas em cenário controlado. Tetos operacionais P0: backend 45 segundos para prévia e 75 para geração; cliente 55 e 85 segundos; proxy/hosting com no mínimo 100 segundos. O backend deve responder antes do cliente e do proxy, inclusive em erro.
- O orçamento da prévia de 45 segundos inclui admissão, até 15 segundos da recuperação DOI, preparação, chamada(s) Gemini, validação e persistência. O orçamento de geração de 75 segundos inclui todas as tentativas, validação e gravação do bundle; reservar ao menos 5 segundos para validação/persistência. Não somar um novo timeout completo a cada etapa ou retry. Contabilizar a duração total com relógio monotônico desde a entrada na operação; não manter fila de espera ilimitada.
- A UI indica a etapa real em andamento e conserva material/revisão durante a espera, sem porcentagens fictícias. Ao exceder a meta de 30/45 segundos, informa que a operação continua dentro do limite de 45/75; ao atingir o teto, exibe falha recuperável. Não disparar nova geração automaticamente por impaciência ou erro de conexão: consultar a prévia e reutilizar a chave de idempotência. Usar `generation_status`/`last_lesson_bundle_id` para recuperar resultado já concluído, sem reiniciar a contagem do prazo da operação original.
- Os limites operacionais não são promessa de qualidade nem substituem a medição das metas. Registrar ambiente/cache/modelo e duração no ensaio. Artigo em até 5 segundos continua meta em condição normal; manter o fallback atual. Se o hosting não suportar 100 segundos, usar o ambiente controlado ensaiado; não reduzir apenas o timeout do cliente e chamar isso de compatibilidade.
- Até duas tentativas do provedor por operação, incluindo correção de saída inválida ou retry transitório, sempre dentro do mesmo prazo total. Não repetir 401/403, nem continuar em segundo plano após timeout. Uma resposta bloqueada pelo provedor retorna falha explícita.
- Limite inicial por sessão: uma operação de IA ativa, 5 prévias e 5 gerações em janela móvel de uma hora. Contabilizar a operação antes da chamada e limitar retries. Limite global inicial: duas operações de IA concorrentes no backend de demonstração; excesso retorna erro de capacidade sem bloquear o Forensics.
- Configurar teto total de 12.000 tokens de entrada por chamada e 8.000 de saída, incluindo o contexto autorizado; contar com o mecanismo do provedor antes da geração ou rejeitar entradas acima de estimativa conservadora documentada. Nunca truncar silenciosamente o material. O teto de saída inclui o raciocínio quando aplicável; saída incompleta é inválida. Metas e limites são ajustáveis pela configuração após medição, com exemplos de contrato preservados.
- Criar sessão anônima opaca em cookie HttpOnly, SameSite=Lax e Secure em HTTPS; associar projetos e registros a essa sessão. IDs aleatórios não substituem verificação de propriedade. Não listar projetos de outras sessões, nem expor material em URLs ou analytics.
- A sessão tem validade de 7 dias renovada por ação explícita válida do professor que crie prévia, salve revisão ou inicie geração. O projeto usa a mesma janela de 7 dias após sua última ação docente válida, permitindo preparar no dia 21 e retomar no dia 22 sem expiração arbitrária de 24 horas. Consultas, polling, impressão e download não renovam a janela. Exibir o `expires_at` corrente e informar que apagar cookies ou usar outro navegador impede a recuperação. Não oferecer compartilhamento por URL de aula no MVP.
- Preferir frontend e API sob a mesma origem, com encaminhamento de `/api` ao backend. O Vite cobre desenvolvimento; o ambiente publicado deve ter encaminhamento equivalente, incluindo exports, cookie e timeout. A configuração de destino da API deve ser explícita no ambiente de hosting.
- Se forem necessárias origens diferentes, configurar base da API no frontend, credenciais no fetch, CORS com origens exatas, métodos/cabeçalhos Studio e política de cookies compatível; validar o percurso completo antes do pitch. Para P0, escolher a origem única para reduzir dependências.
- Validar Origin nas escritas Studio. Aceitar o cabeçalho de idempotência e preservar os métodos atuais do Forensics. Usar consultas SQL parametrizadas e escapar texto em React; nenhuma saída da IA é executada como HTML, JavaScript ou URL buscada pelo servidor.
- Informar antes do primeiro envio que o material será enviado ao Gemini. Não exigir dados pessoais de alunos. Uploads e busca de URLs arbitrárias ficam fora do MVP.
- Retenção Matilda: documentos originais, prévias, decisões e bundles compartilham o prazo do projeto, de 7 dias após a última ação explícita válida descrita acima. Renovar de forma atômica o prazo e o cookie antes de admitir a geração; assim a retenção não interrompe uma operação já aceita de até 75 segundos. Sessão e projeto devem estar válidos na admissão; erro de IA mantém a revisão e o prazo já concedido. Repetição idempotente de resultado concluído equivale a leitura e não renova retenção. Expiração impede nova operação e leitura, com mensagem orientando recomeçar sem fingir recuperar dados apagados.
- Verificar expiração antes de todo acesso e executar limpeza periódica/no início do processo, removendo em cascata todas as entidades filhas e os registros de idempotência daquele projeto. A limpeza não remove uma geração admitida e ainda em prazo; operações abandonadas seguem a regra de recuperação de prazo mais 15 segundos. A retenção de 7 dias é recuperação temporária do MVP, não histórico permanente. A retenção de investigações Forensics permanece como implementada, sem estender automaticamente a validade de seu `analysis_id`; o Studio conserva o contexto e as evidências já capturados mesmo que o link da investigação expire. A política do provedor é distinta e precisa ser conferida e comunicada conforme a conta usada.
- Evitar logs do material e das respostas completas. Registrar apenas IDs internos, status, modelo, latência e uso agregado. Chaves e variáveis de servidor não entram no bundle frontend, nos exports ou em respostas de erro.
- Backend de demonstração: processo único com SQLite em armazenamento persistente, HTTPS e orçamento de execução compatível. Manter um ambiente local controlado como alternativa ensaiada. Não considerar o frontend publicado prova de que o backend, o armazenamento ou a integração Gemini funcionam.
- Não escolher ou contratar novo serviço de hosting nesta especificação. B confirma execução e persistência do backend, C a entrada/navegação do frontend e D o percurso de entrega e E2E no ambiente já disponível; se não houver backend público compatível, a entrega do hackathon é demonstrada no ambiente controlado, com limitação declarada.

### 10. Quatro frentes, dependências e integração

As frentes são responsabilidades de desenvolvimento para quatro pessoas e suas sessões Codex. Cada uma usa branch e checkout próprios; este documento não dispara agentes ou cria branches.

| Frente | Responsabilidade principal | Pode começar em paralelo | Depende de |
|---|---|---|---|
| A — Scientific Core | motor científico e Forensics; ScientificContext, resolução conceitual, recuperação, classificação, elegibilidade e evidências; regressão científica | após M0, adaptador e testes de contexto com os dados existentes | contrato científico acordado; B/C/D consomem IDs e evidências de A sem alterá-los |
| B — AI Engineering | Gemini, orquestração, análise, planner, geração e validação do LessonBundle; API Studio, sessão, persistência, revisão e idempotência necessárias ao fluxo | após M0, integração Gemini e rotas Studio com fixtures científicas acordadas | ScientificContext/evidências de A; contratos de revisão com C e LessonBundle com D |
| C — Studio Experience | seleção de modos, entrada de material/configuração, cliente Studio de prévia/revisão, sugestões, evidências e aprovação docente; preservação do estado | após M0, workspace com fixtures fiéis à API e revisão persistida | prévia/revisão de B e dossiê científico de A; entrega o bundle à experiência de D |
| D — Lesson Delivery | slides, apresentação, notas, plano, impressão, Markdown, renderizadores e testes E2E do fluxo completo; coordenação do ensaio | após M0, renderizar LessonBundle de referência e preparar E2E | bundle validado e endpoint de exportação de B; navegação de C e fontes canônicas de A |

**M0 é uma condição obrigatória de início da implementação paralela, não uma tarefa a resolver enquanto contratos concorrentes já são codificados.** A aprovação deste texto libera preparar M0; as quatro frentes só começam a implementação simultânea quando os artefatos abaixo estiverem conferidos e acordados.

| Contrato compartilhado a estabilizar | Responsável por consolidar | Consumidores que precisam concordar | Evidência de estabilidade em M0 |
|---|---|---|---|
| ScientificContext, conceitos, contribuições, evidências e classificações Forensics | A | B, C e D | modelos com IDs/enums/procedência e fixtures DOI, texto e sem cobertura; compatibilidade anterior verificada |
| API Studio, Pydantic/OpenAPI, erros, sessão, revisão, idempotência, retenção e timeouts | B | A, C e D | operações e campos definidos, exemplos de sucesso/erro, estados e prazos consistentes |
| Configuração pedagógica, SourceAnchor, sugestões e decisões de revisão | B + C | A e D | exemplos de pendente/aceito/rejeitado, edição permitida, revisão obsoleta e objetivos aprovados |
| LessonBundle, layouts, blocos, referências, notas, tempos e formato da exportação | B + D | A e C | bundle válido renderizável por D e contraexemplos temporais/documentais rejeitados |
| Tipos TypeScript e fixtures correspondentes aos schemas Pydantic | C para prévia/revisão; D para entrega; B mantém schema de origem | A/B/C/D | nomes, enums, nulos e limites equivalentes; fixture HTTP consumível pelas duas experiências frontend |

- M0 encerra somente quando os quatro integrantes registrarem o acordo na Issue da especificação, com versões/revisões dos contratos e exemplos. Nenhum integrante cria uma variante local incompatível para avançar mais rápido. Fixtures são dados de teste, sem substituir geração real no aceite.
- API, schemas Pydantic, tipos TypeScript e estruturas de dados compartilhadas não podem ser alterados unilateralmente. Mudança exige proposta de impacto, aprovação explícita dos responsáveis afetados, atualização de fixtures/testes e ordem de integração combinada.
- A mantém os contratos científicos e endpoints Forensics; B mantém os novos contratos/rotas Studio e persistência. C mantém navegação, cliente de prévia/revisão e estilos de preparação; D mantém visualizações, exportação e estilos de aula. A lógica de Markdown pertence a D; B integra sua resposta na rota de exportação combinada. Contratos, dependências e pontos de entrada têm um editor por vez, combinado entre os envolvidos.
- Cada frente entrega seus testes de comportamento: A científicos/regressão, B API/IA/persistência, C interação/revisão e D renderização/exportação/E2E. D não concentra todas as correções ou toda a qualidade do projeto.
- D coordena o ensaio integrado; B integra mudanças de backend, C/D integram seus módulos frontend por meio do ponto de navegação mantido por C. Usar PRs pequenos com revisão por outro integrante. Correções em outra frente são combinadas com seu responsável; não depender de commits diretos na branch principal.

| Marco | Entrega verificável | Dependências e gate |
|---|---|---|
| M0 — contratos estabilizados antes do paralelo | os cinco conjuntos de contrato acima, versões, fixtures e aceite A/B/C/D registrados; baseline Forensics e ensaio mínimo Gemini | requisito de entrada para implementar em paralelo; texto aprovado não dispensa conferir schemas e exemplos |
| M1 — primeiro fluxo completo | texto/conceitos de CRISPR → recuperação A → sugestões B → revisão C → Gemini/bundle B → slides e plano básicos D | A/B/C/D integrados; E2E de D atravessa todas as etapas; fixtures não contam como geração real |
| M2 — integração científica e revisão | DOI e Transformar em aula; fontes/dossiê; aceitar, rejeitar, editar pedagogia; retomada após erro | M1 e compatibilidade preservada; nenhum catálogo paralelo |
| M3 — entrega pedagógica | D completa seis layouts, notas, plano, impressão e Markdown; B integra exportação e A confere rastreabilidade | M1/M2 e contrato LessonBundle estável; C mantém a continuidade da experiência |
| M4 — estabilização até 22/10/2026 | P0-1–P0-8, CT-01–CT-16, regressão, segurança essencial e dois cenários ensaiados | cada frente corrige sua área; D coordena E2E/ensaio; revisão científica com A e pedagógica pela equipe |

M0 libera as quatro frentes simultaneamente. M1 é o primeiro ponto de integração obrigatório; não aguardar todas as telas ou serviços ficarem completos isoladamente. O prazo de demonstração é 22/10/2026, sem inventar uma hora de apresentação ausente do contexto. Os marcos não atribuem estimativas de horas sem conhecer a disponibilidade da equipe. As histórias são agrupadas por esse fluxo, não desdobradas automaticamente em tickets; esta publicação contém somente a Issue da especificação.

## Testing Decisions

### Pontos de teste aprovados

- Fronteira principal: API HTTP FastAPI, exercitada com TestClient e SQLite temporário. Verificar entrada, saída, persistência, autorização e invariantes de uma jornada completa, sem acoplar testes à divisão interna dos serviços.
- Fronteira de experiência: Playwright no navegador com frontend e backend reais, substituindo apenas o provedor Gemini e fontes externas por respostas controladas nos testes repetíveis. Usar o cliente HTTP real do Studio, incluindo cookie, revisão e downloads.
- Simular a dependência externa no adaptador de transporte/provedor; não criar uma interface de teste diferente para cada componente ou função. Respostas inválidas do provedor devem alcançar o validador real.
- Manter poucos testes diretos dos validadores determinísticos quando cobrirem invariantes difíceis de diagnosticar pela jornada HTTP, como soma temporal e relações de evidência. Não testar chamadas privadas, nomes de funções ou detalhes de CSS como objetivos por si próprios.
- Ensaio real separado com a chave da equipe confirma modelo, quota, latência, payload estruturado e ambiente. Não depender de chamadas pagas ou dados variáveis para a suíte automatizada.

Esses pontos aproveitam os precedentes existentes: TestClient com banco temporário, snapshots bibliográficos, HTTPX MockTransport para falhas e testes Playwright de DOI, dossiê, celular, teclado e exportação. Foram incluídos na direção técnica aprovada; M0 materializa os exemplos que A/B/C/D usarão.

### Matriz de aceite rastreável ao PRD

| Caso | Critério de aceite observável | Evidência planejada |
|---|---|---|
| CT-01 — texto livre | texto contendo CRISPR cria prévia com documento original preservado e ao menos uma sugestão elegível ligada a trecho literal | HTTP e jornada navegador |
| CT-02 — DOI | DOI real válido produz contexto com Paper/IDs/procedência originais; Transformar em aula reutiliza investigação selecionada | HTTP com snapshots e E2E |
| CT-03 — conceitos | conceitos e texto produzem IDs editoriais rastreáveis; termos desconhecidos não inventam IDs; nível e objetivos originais não são substituídos silenciosamente | HTTP; fixture com objetivos vazios exige aprovação dos sugeridos |
| CT-04 — motor comum | mesmo contexto de DOI devolve mesmas contribuições, IDs, evidências e classificações do Forensics; RNA preserva filtro específico | comparação pelos endpoints; teste de texto sem Paper artificial |
| CT-05 — sugestões | cada proposta informa conceito, local de inserção, contribuição, participantes, justificativa e fonte válida | HTTP e inspeção visual dos três painéis |
| CT-06 — rejeição | rejeitar persiste e sobrevive a recarregamento; IDs/conteúdo documental daquela sugestão não entram na aula | HTTP e E2E |
| CT-07 — aprovação e edição | aceitar e editar abordagem persiste; histórico canônico permanece bloqueado; sugestão pendente impede gerar | HTTP e E2E; revisão obsoleta retorna 409 |
| CT-08 — geração | somente sugestões aceitas e objetivos aprovados aparecem; zero aceitas gera aula sem atribuições; tempos, vínculos e pelo menos uma avaliação são válidos | HTTP, bundle válido e contraexemplos |
| CT-09 — layouts | os seis layouts renderizam com dados válidos; 16:9, teclado, progresso e tela cheia/alternativa funcionam; notas não aparecem na projeção | E2E com fixture cobrindo os seis layouts e verificação no projetor |
| CT-10 — evidências | toda atribuição verificada resolve evidência autorizada da contribuição correta, com afirmação canônica, participantes e limites; explorar preserva o editor | HTTP e E2E de dossiê para DOI e texto |
| CT-11 — Markdown | download contém a mesma aula, fontes e limitações; não reexecuta IA nem incorpora material original integralmente | HTTP e download no navegador |
| CT-12 — imprimir/PDF | plano imprimível inclui sequência, atividades, notas e referências legíveis, sem controles cortando texto | estilos print em E2E e salvar PDF manualmente no navegador do pitch |
| CT-13 — falha de IA | timeout, 429, 401/403, bloqueio, JSON inválido e resposta incompleta não geram sucesso fictício; estado revisado permanece recuperável | falhas no transporte do provedor, HTTP e E2E de nova tentativa |
| CT-14 — referência inválida | ID desconhecido, evidência de outra contribuição, ID real fora da prévia, candidato pendente e afirmação histórica inventada pelo modelo não são aceitos como evidência verificada | HTTP com respostas maliciosas; bloco documental usa sempre texto canônico |
| CT-15 — fora da cobertura | lista científica vazia e aviso de cobertura; geração sem enriquecimento é possível; nenhuma cientista é inventada para preencher a aula | HTTP e E2E com material sem correspondência |
| CT-16 — regressão | DOI, grafo, camadas/lista, evidências, exportações, cache, descoberta e estados vazios do Forensics permanecem funcionais, inclusive sem Gemini configurado ou com Gemini indisponível | suíte existente mais regressão da navegação e nova fronteira de contexto |

### Casos transversais obrigatórios

- Limites de campo/corpo/tokens e configurações inválidas são rejeitados antes da chamada cobrada. Nenhuma espera ilimitada ou loop de correção.
- Material contendo prompt injection, HTML e URLs arbitrárias continua dado textual; não habilita ferramentas, execução, busca SSRF ou IDs fora do conjunto permitido. Testar resultado observável, sem afirmar proteção perfeita contra toda injeção.
- Sessão B não lê, revisa, gera ou exporta registros da sessão A; recurso expirado não retorna conteúdo. Com relógio controlado, testar retomada após mais de 24 horas e antes de 7 dias, renovação por revisão/geração explícita, ausência de renovação em GET/export e expiração após 7 dias sem ação válida. Cookie e prazo do projeto precisam permanecer coerentes; a limpeza não apaga uma geração válida em andamento.
- Requisições simultâneas com mesma chave produzem no máximo um bundle persistido; conflitos de revisão e de chave/entrada são explícitos. Reinício não apaga revisão nem libera duplicação de resultado concluído.
- Migração sobre banco com investigação, cache e candidato existentes preserva os registros e permite consultá-los pelos endpoints antigos.
- Vazamento de chave é testado em erro, resposta, metadados, exportação e bundle de produção. Logs não contêm material do professor nem respostas completas.
- Contrato compartilhado: contexto científico de A, API/prévia de B e bundle acordado por B/D são consumidos pelos tipos/clientes de C/D e pela jornada E2E de D, incluindo enums, nulos, erros e referências. Build TypeScript e OpenAPI devem concordar antes da integração das frentes.
- Medir metas de prévia até 30 segundos e geração até 45 em cenário controlado, registrando ambiente, modelo, cache e limites. Simular ultrapassagem da meta sem cancelamento precoce, timeout total do backend em 45/75, cliente em 55/85 e proxy com no mínimo 100; retries compartilham o orçamento e não duplicam bundle. Navegação de slides deve responder sem requisição de IA ou travamento perceptível.

### Gate de entrega e demonstração

- Executar a suíte backend existente e nova, build de produção TypeScript/Vite e Playwright com as dependências externas controladas. Registrar comandos, versões e resultados reais; contagens históricas não substituem a execução da versão integrada.
- A documentação existente registra 59 testes backend, 6 de navegador e build aprovados em validação anterior. Esta etapa de especificação não executou nem confirmou novamente esses resultados.
- Ensaiar duas jornadas completas: CRISPR-Cas9 com `10.1126/science.1231143` e RNA com `10.1056/NEJMoa2034577`, incluindo fonte, decisão docente, geração real, slides e exportação. Ensaiar adicionalmente o caso sem cobertura e falha do provedor.
- Revisar manualmente as atribuições, preservação de autoria coletiva e adequação pedagógica; verificar leitura no projetor, foco, teclado e impressão. Sem alegar revisão independente por especialistas se ela não ocorreu.
- Se for usado um bundle previamente gerado como alternativa de demonstração, identificá-lo como aula recuperada, com modelo e data reais. Nunca apresentá-lo como uma chamada ao vivo ou inventar retorno de sucesso em falha.
- Aceite final exige fluxo P0 completo, regressão Forensics aprovada, ausência de credenciais expostas, ambiente de demonstração testado e instruções reproduzíveis. Zero erros críticos é o objetivo do ensaio, não um resultado presumido.

## Out of Scope

- Upload PDF, OCR, DOCX, PPTX ou imagens; URLs externas arbitrárias e extração de conteúdo protegido. Testes de upload não se aplicam enquanto essa entrada não existir.
- Exportação PPTX editável, DOCX, PDF binário no backend e PDF dos slides. O PDF P0 é exclusivamente a impressão do plano pelo navegador.
- Editor livre de slides, edição avançada por bloco, animações elaboradas e imagens científicas geradas automaticamente.
- Autenticação institucional, contas docentes, colaboração simultânea no mesmo projeto, compartilhamento entre professores, biblioteca e histórico permanente. Sessão e persistência curta para retomar o MVP permanecem P0.
- Novo catálogo científico independente, curadoria automática de candidatos, inferência de gênero por nome, influência histórica derivada de similaridade e investigação recursiva.
- Ampliação quantitativa do catálogo para cumprir quotas, novos provedores científicos ou reestruturação do grafo durante a construção do Studio.
- Monetização, planos comerciais, validação de mercado e alegações de economia de tempo não medidas.
- Migração do Forensics, troca de stack, filas distribuídas, múltiplos workers e implantação de produção em grande escala.

## Further Notes

- Ordem de corte para o hackathon: manter os itens fora de escopo cortados; estabilizar o primeiro fluxo completo antes de ampliar. Se o P0 ainda não estiver estável, registrar a limitação em vez de declarar o MVP concluído ou enfraquecer validação de evidências.
- Lacunas fechadas por esta proposta: contratos de seções/slides/atividades; revisão de objetivos; edição pedagógica com histórico bloqueado; ausência de comparação bibliográfica em texto; persistência da revisão; idempotência; sessão; retenção; limites e timeout; dossiê sem artigo raiz; configuração da API em produção.
- Dependências externas de execução: chave/quota Gemini, configuração OpenAlex conforme o ambiente, backend Python acessível, armazenamento SQLite adequado e navegador/projetor. A equipe deve confirmar essas condições em M0/M4; esta especificação não as declara disponíveis.
- A documentação local e o remoto aprovado prevalecem para determinar o destino de publicação. O deploy informado no PRD não foi auditado como parte desta síntese.
- Revisão concluída pelo usuário: direção técnica aprovada com frentes A Scientific Core, B AI Engineering, C Studio Experience e D Lesson Delivery; estabilização prévia dos contratos; P0 rigoroso para 22/10/2026; retenção e timeouts revisados; fluxo completo preservado. A aprovação autoriza publicar esta especificação como uma única Issue.
- Publicação exclusivamente desta especificação no rastreador configurado, com `ready-for-agent`. As 36 histórias e os critérios de aceite são parte do corpo da mesma Issue; não criar tickets de implementação, sub-issues ou funcionalidades nesta etapa. M0 e os marcos seguintes são trabalho futuro, não resultados já concluídos.
