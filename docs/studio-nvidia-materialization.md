# Materialização NVIDIA: autoridade, contratos e diagnósticos (#31 / PR #32)

Base: `e2acbc717199dcbb6ff44eaa85a0a8311ad73b3c`. Responsável: Codex do Mac,
branch feat/nvidia-studio, checkout separado .runtime/nvidia-json-worktree.
Nenhuma inferência real nesta tarefa; sem merge #32/#30, mudança na main,
PR #34 ou branch do Agente 3.

## O que o smoke real prova

[Relatório real anterior](https://github.com/zazacknazzo/Matilda-mvp/pull/32#issuecomment-6370275103):
preparação simulada201, revisão200, NVIDIA200/completed em29,845s, stop,
strict=true, compact-v2-weighted. JSON, contrato privado e expansão LessonDraft
passaram; Matilda502/invalid_generation com scientific_validation. SQLite não
publicou aula; revisão e configuração50min preservadas.

Não foi retido JSON gerado nem mensagem de exceção. Uma referência não autorizada
reproduz esse padrão offline, mas **não prova a causa específica da resposta real**.
A etapa seguinte ao provider também podia falhar por metadados, chaves/vínculos,
conformidade com a revisão ou erro interno. A nova instrumentação distingue essas
classes sem precisar registrar conteúdo ou pagar por tentativas exploratórias.

## Diagnóstico exaustivo do caminho da base

A classificação antiga scientific_validation era emitida pelo except
ValueError/KeyError/TypeError de _run_provider quando a exceção não era
ValidationError. Não significava necessariamente uma falha científica.

| Região da base | Exceções/condições | Relação com o smoke |
|---|---|---|
| provider.complete | JSON, schema privado, configuração, expansão, transporte | excluída como origem da rejeição deste caso pelo evento completed |
| Prazo depois do provider | ProviderFailure(timeout), TimeoutError, cancelamento | limites e classes separados; não scientific_validation |
| Metadados | model_dump/model_validate; prompt_version divergente; uso acima do orçamento | divergência/budget eram ValueError; Pydantic era outra classificação; AttributeError/RuntimeError iam ao fallback503 |
| Conteúdo e LessonDraft | tipo/bytes, JSON inválido/duplicado/não finito/Unicode/profundidade, campos/tipos/listas | erros JSON/tipo podiam cair no bucket genérico; ValidationError era pydantic_validation |
| Chaves locais | repetição em seções/slides/atividades | ValueError; NVIDIA compacto já constrói chaves únicas |
| Vínculos locais | section.slide_keys/activity_keys e section_key inexistentes | KeyError na consulta aos mapas; vínculos compactos já são construídos pelo servidor |
| Evidências | bloco de seção/slide com ID fora da revisão aceita | ValueError explícito; causa reproduzida, hipótese do caso real |
| LessonBundle | campos, layouts, limites, objetivos, grafo, tempos, referências | ValidationError, portanto normalmente pydantic_validation, distinto do log real |
| validate_lesson_response | request/revisão, IDs do bundle, configuração/objetivos, referência não autorizada ou snapshot divergente | ValueError; construídos da revisão no fluxo normal, mas precisavam de defesa e diagnóstico |
| Exceção não prevista no trecho | qualquer ValueError/KeyError/TypeError não catalogado | também recebia scientific_validation; outras exceções iam ao fallback seguro503 |
| Publicação SQLite | claim, deadline, frozen/request persistidos, fingerprint, revalidação, SQL/commit | fora do handler scientific_validation; conflito/timeout ou fallback503 |
| Leitura depois do commit | preview/expiração ou erro de leitura | podia responder503 apesar de já haver aula válida persistida; replay deve recuperá-la |
| Registro de falha | fail_generation/rollback/reconciliação | falha secundária podia substituir o erro original; lifecycle já recupera claims abandonadas |

Hipóteses apresentadas antes da correção: evidência fora da revisão; metadados;
vínculos/chaves; layout/objetivos/schema; falha interna/persistência. O tracer
mínimo de evidência confirmou provider completed +502 e ficou vermelho pela
falta de subcódigo. Tracers de vínculo e prompt_version também ficaram vermelhos
antes de seus códigos específicos. Não se transformou a hipótese do smoke em fato.

Foram lidos integralmente GenerationService, materialize_lesson,
validate_lesson_response, LessonDraft, LessonBundle, seções/slides/atividades/
referências, contrato/expand NVIDIA e publicação do repositório.

## Decisão para referências científicas

| Critério | A: IDs canônicos limitados no schema | B: aliases locais resolvidos no servidor |
|---|---|---|
| Formato de saída | mantém evidence_id | exige alias e novo mapa de resolução |
| Escolhas | enum dos IDs aprovados | enum de aliases e vínculo alias→snapshot |
| Custo de implementação | patch local do schema e conferência de pertença | emissão/escopo/estabilidade/expansão de aliases e testes adicionais |
| Payload | repete IDs no enum; incluído no orçamento | aliases podem encurtar IDs longos, com mapa/instruções adicionais |
| Falha desconhecida | rejeição explícita | rejeição explícita no resolvedor |
| Compatibilidade | enum já usado em layouts do contrato | enum também, mas novo campo/protocolo privado |

**Escolhida A.** É a menor mudança e preserva a referência canônica já usada pelo
materializador. O conjunto enviado é exatamente authorized_evidence, formado pelo
servidor a partir das sugestões aceitas e referências do snapshot. Não há seleção
fuzzy, abreviação, truncamento do conjunto ou substituição de ID.

A [referência hospedada](https://docs.api.nvidia.com/nim/reference/nvidia-nemotron-3_5-super-vl-120b-a12b-infer)
documenta response_format/json_schema. Isso não publica uma garantia por keyword
ou demonstra que o decoder aplica cada restrição. Mantemos strict=true e a
conferência no servidor mesmo quando o upstream ignora o enum. Não presumimos
parâmetros exclusivos de containers ou suporte novo a grammar/regex.

O contrato privado agora se identifica como **compact-v3-authorized**:

- Mantém pesos1–1000 e a alocação determinística de50min do v2; não aceita minutos
  legados na saída nem repara tempos fornecidos pelo modelo.
- EvidenceClaimBlock.evidence_id recebe enum literal dos IDs autorizados. Sem
  autoridade, o schema omite esse ramo, seu ref/discriminator e o layout
  SCIENTIST_SPOTLIGHT. Um retorno que ignore isso é rejeitado, não apagado.
- Índices de objetivos de seções e atividades recebem enum da lista aprovada.
  O backend também rejeita índices não aprovados e duplicados, sem remapeamento.
- Layout e conteúdo visível são validados antes do provider concluir, pela mesma
  função usada em LessonSlide. TITLE/CONCEPT/PROCESS/QUESTION/SUMMARY/SPOTLIGHT
  mantêm as regras existentes; títulos não podem ser só espaços.
- Notas, atividades, orientação e critérios continuam sendo escritos pelo modelo.
  Não há texto de preenchimento, atividades artificiais ou troca automática de layout.
- Chaves, vínculos, minutos, contribuições e referências finais continuam do
  servidor. evidence_claim contém somente uma referência; a afirmação histórica,
  fonte e autoria são materializadas literalmente do snapshot canônico escolhido.
  Uma fonte aprovada não pode receber claim_supported/participantes inventados.

O custo completo de material+instruções+schema entra na estimativa UTF-8+1.024.
Conjuntos extensos falham em input_too_large antes do HTTP; não retiramos opções
para caber no teto. Limites12.000/8.000 e128KiB,75s/reserva5s permanecem.

## Pontos de rejeição e novos códigos

O módulo `app/studio/lesson_diagnostics.py` concentra a allowlist e o evento
studio_lesson_validation. Os pontos de rejeição usam LessonRejected ou tipos
PydanticCustomError constantes. Pydantic usa somente type em allowlist; msg, input,
loc, ctx, URLs de erro, nomes de modelos e mensagens livres nunca são registrados.
Tipos desconhecidos viram other. Métricas do adapter também têm nomes/tipos fechados.

| Ponto/condição | failure_code |
|---|---|
| Referência fora do conjunto aceito | lesson_evidence_not_authorized |
| Tipo/bytes do draft | lesson_draft_type_invalid / lesson_draft_size_invalid |
| JSON do draft inválido, repetido, não finito ou não decodificável | lesson_draft_json_invalid |
| Campos/tipos/contagens de LessonDraft | lesson_draft_schema_invalid + validation_types |
| Chaves locais repetidas | lesson_duplicate_local_key |
| Slide/atividade da seção inexistente ou dono incompatível | lesson_section_slide_link_invalid / lesson_section_activity_link_invalid |
| section_key de slide/atividade inexistente | lesson_slide_section_link_invalid / lesson_activity_section_link_invalid |
| Identificadores/índices duplicados | lesson_duplicate_identifier |
| Objetivo fora da lista / contexto sem objetivos | lesson_objective_not_approved / lesson_objectives_missing |
| Layout incompatível com blocos | lesson_slide_layout_invalid |
| Conteúdo visível acima de600 | lesson_slide_content_too_large |
| Evidências do slide diferentes de seus blocos | lesson_evidence_binding_mismatch |
| Contribuições diferentes das referências dos blocos | lesson_contribution_binding_mismatch |
| Duração global / duração da seção | lesson_duration_mismatch / lesson_section_duration_mismatch |
| Slide/atividade órfão ou vínculo global repetido | lesson_slide_ownership_invalid / lesson_activity_ownership_invalid |
| Seção/evidência desconhecida no slide final | lesson_slide_reference_invalid |
| Referências finais diferentes das efetivamente usadas | lesson_reference_usage_mismatch |
| Bundle maior que128KiB | lesson_bundle_too_large |
| Bundle/section/slide/activity/reference incompatível estruturalmente | lesson_bundle_schema_invalid + validation_types |
| URL / timestamp / versão inválidos | lesson_reference_url_invalid / lesson_timestamp_invalid / lesson_schema_version_invalid |
| Identidade/revisão/request divergentes | lesson_review_mismatch |
| Configuração / objetivos divergentes | lesson_configuration_mismatch / lesson_objectives_mismatch |
| Mesma referência com snapshot adulterado | lesson_reference_snapshot_mismatch |
| Tipo/estrutura de metadados, inclusive UTC/versão | lesson_metadata_invalid + validation_types |
| Prompt_version / orçamento informado divergente | lesson_metadata_prompt_mismatch / lesson_metadata_budget_invalid |
| Claim ausente/não ativo na publicação | lesson_generation_claim_missing |
| Fingerprint/revisão atual diferentes | lesson_persistence_review_mismatch |
| Frozen/request persistidos corrompidos | lesson_persistence_snapshot_invalid |
| Outra validação Pydantic na persistência / leitura final / prévia | lesson_persistence_schema_invalid / lesson_completion_schema_invalid / lesson_review_schema_invalid |
| SQLite, inclusive falha de INSERT/commit/leitura | lesson_storage_failure |
| Não foi possível registrar a falha | lesson_failure_recording_failed |
| Exceção bruta de transporte / outra exceção do provider | lesson_provider_transport_failure / lesson_provider_internal_failure |
| Outra saída inválida do provider | lesson_provider_output_invalid; diagnóstico do adapter permanece no nvidia_attempt |
| Prazo / cancelamento | lesson_deadline_exceeded / lesson_cancelled |
| Falha interna não antecipada | lesson_internal_failure, com a fase constante |

Os códigos JSON e de configuração/expansão do adapter anterior continuam ativos.
A lista integral de códigos e tipos permitidos está no módulo, sem dados gerados.

O evento informa validation_phase (provider, metadata, draft, materialization,
bundle, review, persistence ou completion), failure_code, outcome=rejected ou
pydantic_validation e, quando aplicável, validation_types. O nome genérico
scientific_validation não é usado para novas rejeições. Recorder captura esse JSON
no relatório do smoke e mantém leitura do formato legado para registros antigos.
Não há IDs de evidência, material, prompts, credenciais ou dados pessoais.

Erros de geração continuam HTTP502/invalid_generation. Conflitos de revisão,
timeout e indisponibilidade/armazenamento preservam os envelopes existentes
409/504/503. Em falha de registro, conserva-se o erro seguro original e o lifecycle
recupera a operação abandonada na janela75+15s. Depois de commit válido, uma falha
de leitura não apaga a aula; replay recupera o resultado sem nova inferência.
Encerramento forçado do processo não garante entrega de logs; não é uma nova
rejeição científica. Nenhum retry ou deadline adicional foi introduzido; o teto
comum já existente é preservado e o smoke continua com guard de uma chamada.

## Causas reproduzidas e matriz de testes

[Diagnósticos mínimos](../backend/tests/test_lesson_materialization_diagnostics.py):
evidência não autorizada, link inexistente e prompt_version divergente. Três ciclos
vermelho/verde por falta de subcódigo; Recorder passou a capturá-los.

[Matriz de materialização](../backend/tests/test_lesson_materialization_matrix.py):
falhas após o provider real com MockTransport: chaves, links, ownership, objetivos,
JSON/tipos/bytes, layouts, tamanho, metadados, referência/contribuição, snapshot,
configuração, revisão, contagens, versão, falha interna e leitura após commit.

[Matriz do repositório](../backend/tests/test_lesson_repository_guards.py): claim,
deadline, operação/fingerprint corrompidos, frozen inválido, INSERT SQLite que
aborta, falha secundária e tipos Pydantic desconhecidos. Corrupção e aborto são
injetados somente no SQLite temporário; as asserções usam a API. Esses cenários
não sugerem que o modelo possa editar armazenamento ou chaves construídas.

[Escolhas autorizadas](../backend/tests/test_nvidia_authorized_lesson.py): enum,
autoridade ausente, fonte de outra chamada, retorno que ignore o schema, índices
não aprovados/duplicados, layout e orçamento sem truncamento. Os tracers de enum,
objetivos e PROCESS ficaram vermelhos antes da implementação.

[Matriz positiva](../backend/tests/test_nvidia_bundle_matrix.py): **48 combinações**
de3–8 seções,4–12 slides e1/4 atividades, com e sem evidências. Todos os seis layouts
são exercitados; cada caso valida50min, fonte/contribuição canônicas, revisão
congelada, conteúdo/notas do modelo, SQLite, leitura, replay200 e Markdown. Uma
única chamada MockTransport por geração; nenhuma inferência real.

O smoke isolado controlado comprova captura de subcódigos posteriores ao provider
(link e metadados), sem segunda chamada HTTP. As outras regressões cobrem ausência
de pedagogia, pesos inválidos/extremos, arredondamento, schema, JSON e falhas do
provider. Conflitos e indisponibilidade mantêm os erros públicos originais.

Uma falha isolada no primeiro run completo detectou mudança indevida de503 para502
em exceção bruta de transporte. O código foi corrigido, preservando o teste
original e o comportamento anterior; não se adaptou a expectativa para ocultar a
regressão. Novas categorias não transformam transporte em rejeição de conteúdo.

## Compatibilidade, validação e riscos

Os seis JSON Schemas públicos foram comparados ao código de e2acbc7 e são idênticos:
[hashes e resultado](lesson-materialization-public-schemas.json). Tipos internos de
ValidationError recebem novos códigos, mas campos, condições de aceitação e
mensagens públicas existentes permanecem. Gemini conserva o contrato LessonDraft;
seus erros de transporte e política limitada existente foram verificados.
Não mudaram API, TS, UI/UX, catálogo, motor científico, tabelas ou idempotência.

Backend final: **894 passed**,27,28s. Contratos **7/40/4** e TypeScript/build
aprovados. **90 Playwright finais passaram**: integrado/Forensics/UI23 (31,0s),
revisão19 (10,0s), slides14 (8,5s), geração/operações18 (11,0s), ponte5 (6,3s),
exportação11 (5,0s).

O primeiro run de geração passou17/18: o mock route.fetch/response.json recebeu
Response has been disposed em operations.spec.ts:89 durante fechamento do teste.
O caso isolado passou1/1 e o rerun completo passou18/18, sem mudar frontend/harness.
Esse comportamento já estava registrado no histórico; permanece uma limitação
do transporte de teste, não uma falha NVIDIA comprovada.

Revisões independentes: **Standards0 / Spec0**, cada revisor reexecutou **143 testes
focados** em checkout separado. [Relatórios por eixo](reviews/nvidia-materialization-code-review.md).
A única limpeza posterior foi retirar um import duplicado, sem mudança funcional.
Avisos existentes de dependências e chunk520,42kB permanecem.
[Registro estruturado das verificações](lesson-materialization-validation.json).

O comando sem autorização recusou explicit_authorization_required/exit2 antes
de ler credenciais ou iniciar rede. Nenhuma inferência real foi executada.

Riscos remanescentes: compilação do schema dinâmico e geração real NVIDIA ainda
precisam de novo smoke autorizado; enum não dispensa a conferência local. Semântica
de texto livre, relevância didática, escolha de objetivos e ritmo requerem revisão
docente. Layout/conteúdo inválidos são rejeitados cedo, não reescritos. Payload
excessivo ou armazenamento indisponível continuam falhas explícitas, diagnosticadas.
A causa específica da resposta real anterior continua desconhecida.

## Próximo smoke — não executado nesta tarefa

Após nova autorização explícita, no checkout atualizado de feat/nvidia-studio:

```sh
.venv/bin/python scripts/smoke_studio_nvidia_lesson.py --env-file /caminho/local/.env --allow-paid-nvidia
```

Preparação pedagógica simulada identificada, ciência real em cache, uma chamada
lesson, máximo100s/backend75s/reserva5s, nenhum retry pago. Deve comprovar
LessonBundle,50min, fontes autorizadas, SQLite, replay e Markdown. Relatório inclui
compact-v3-authorized e novos códigos, sem conteúdo. full_flow_proven=false
permanece: o ensaio isolado não comprova prévias reais na mesma execução.
Nenhum merge autorizado dos PRs32/30 e nenhuma inferência real nesta tarefa.
