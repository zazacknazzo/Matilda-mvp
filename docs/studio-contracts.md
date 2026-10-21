# Studio v1 — T03 / Issue #4

Contrato de preparação de M0, baseado em main `c089a67` e na
[Issue #1](https://github.com/zazacknazzo/Matilda-mvp/issues/1), com a atualização
de dependências/ensaio da [Issue #4](https://github.com/zazacknazzo/Matilda-mvp/issues/4).
Importa ScientificContext/SourceDocument/SourceAnchor do PR #15 e
LessonBundle/LessonReference/LessonGenerationMetadata do PR #17. Não redefine
essas estruturas, não instala endpoints, não acessa Gemini e não implementa banco/UI.

[Proposta e impactos registrados antes da edição](https://github.com/zazacknazzo/Matilda-mvp/issues/4#issuecomment-6327293881).
Responsável pela consolidação: B; C consome/consolida tipos de preparação e revisão;
A confere ciência e D o vínculo à entrega. O aceite humano continua pendente.

## Artefatos e consumo

- `backend/app/schemas/studio.py`: requests, prévia, revisão, erros, projeto e
  vínculos determinísticos. Tipos estritos, extras proibidos, snake_case.
- `frontend/src/types/studio.ts`: os mesmos nomes/enums/nulos e tipos importados
  dos contratos científico e de aula. Requests com defaults podem omitir campos;
  respostas materializam defaults e nulos explicitamente. O gerador OpenAPI local
  marca esses campos como obrigatórios, inclusive nos modelos T01/T02 importados,
  sem mudar os modelos originais ou a opcionalidade dos requests.
- `backend/app/studio/contracts.py`: `studio_openapi()` produz OpenAPI 3.1
  independente com schemas derivados do Pydantic, seis operações, segurança,
  cabeçalhos, códigos e formatos. Não registrar esse documento no app Forensics.
- `backend/app/studio/ports.py`: portas de repositório/provedor, política e tipos
  internos; implementações são trabalho dos próximos tickets.
- `tests/fixtures/studio/api/`: payloads reais de contrato, intercâmbios HTTP
  declarativos, casos inválidos e casos do transporte simulado. São fixtures,
  nunca um caminho de sucesso de produção. Não duplicam LessonBundle.

Uso antes de publicar uma prévia: validar EnrichmentPreview; chamar
`preview.validate_scientific_authority(matches, allowed_references,
concepts=editorial, papers=reais)` com autoridade resolvida **pelo servidor**.
Esse método reutiliza `ScientificContext.validate_references`, preserva a âncora
literal e compara evidência, afirmação, autoria coletiva e snapshots autorizados.
Nunca construir a autoridade a partir do payload enviado pelo cliente/provedor.
A seleção/ranking e o adaptador científico continuam pertencendo a A/T04.

`Concept` continua sendo o modelo Forensics importado; somente a fronteira nova
de `EnrichmentPreview.concepts` rejeita extras/coerções que o legado tolerava.
Validators relacionais não são expressos integralmente por JSON Schema: produtores
também precisam executar os validadores Python e não apenas conferir o OpenAPI.

## Seis operações

Todos os retornos abaixo são futuros contratos, não rotas já executáveis.

| Operação | Entrada | Sucesso |
|---|---|---|
| POST `/api/studio/preview` | PreviewRequest + Origin, cookie opcional somente para criar sessão inicial | 201 EnrichmentPreview |
| GET `/api/studio/previews/{id}` | cookie proprietário | 200 EnrichmentPreview com estado/documentos originais |
| POST `/api/studio/previews/{id}/review` | ReviewRequest + Origin + cookie | 200 EnrichmentPreview revisado, revisão incrementada |
| POST `/api/studio/generate` | GenerateRequest + Origin + cookie + Idempotency-Key | 201 LessonBundle; replay concluído retorna o mesmo bundle com 200 |
| GET `/api/studio/lessons/{id}` | cookie proprietário | 200 LessonBundle existente |
| GET `/api/studio/lessons/{id}/export?format=markdown` | cookie proprietário | 200 `text/markdown; charset=utf-8`, attachment com nome seguro |

O exportador recebe o bundle persistido e não chama IA. `ExportQuery` rejeita
outros formatos e parâmetros desconhecidos com 422. IDs de path são opacos;
nenhum recurso é compartilhável por conhecer a URL. `GenerationHeaders` faz o
binding de `Origin` e `Idempotency-Key` (nome HTTP com alias explícito); não são
campos do corpo. A chave é opaca, não vazia, até 128 caracteres, sem normalização.

`PreviewRequest`: title aparado 1–160; subject/education_level aparados até 80,
defaults visíveis Ciências/Ensino Médio; duração inteira 10–120, default 50.
Objectives 0–10 de até 300; concepts 0–20 de até 100; material_text até 20.000,
preservado literalmente. Ao menos texto não vazio, conceitos, DOI ou analysis_id.
DOI usa normalizador Forensics; doi/analysis_id são alternativas. Tema isolado não
é origem. Project_id opcional permite repetir/nova prévia de projeto próprio.
Ausente/expirado/outro proprietário: 404 genérico; sem fabricar investigação.

Corpo bruto tem teto 128 KiB em UTF-8, antes da desserialização/chamada cobrada.
`validate_request_bytes` materializa essa regra para os modelos. O adaptador HTTP
deverá limitar também a leitura em streaming, sem primeiro carregar corpo arbitrário.
Erro de campo é 422; exceder bytes é 413. Forensics mantém sua política atual.

## Prévia, revisão e recuperação

EnrichmentPreview contém os campos da #1 e, para retomada, `project`,
`source_documents`, `approved_objectives` e `last_error`. Project conserva
`learning_objectives` originais; os aprovados são uma lista separada. Material,
DOI, configuração ou contexto alterados exigem nova prévia e nova revisão;
prévia anterior continua recuperável até expirar. GET nunca chama IA.

`schema_version` é inteiro 1 (true, float e string não são versões válidas).
Listas não aceitam null. IDs de projeto/contexto/documento/prévia/sugestão/aula
são atribuídos pelo servidor. Sugestões e documentos pertencem ao mesmo projeto;
conceitos coincidem com o contexto. Referências da prévia correspondem exatamente
às evidências das sugestões, inclusive as posteriormente rejeitadas, para revisão.
Somente referências usadas pela aula aceita chegam ao LessonBundle.

Cada sugestão informa o que inserir, onde (SourceAnchor), por que (justificativa)
e fonte. `historical_claim` é preenchido pelo servidor: concatenação literal dos
`claim_supported` na ordem `evidence_ids`, separados por duas quebras de linha.
`scientific_explanation`, contribuição, pesquisadores, conceitos, âncora,
evidências, participantes e URLs não são campos editáveis pelo professor/modelo.
O trecho canônico e as limitações científicas permanecem preservados.

ReviewDecision aceita somente suggestion_id, status accepted/rejected e edições
opcionais de `pedagogical_rationale`/`suggested_content` (null/ausência = sem edição).
Não há status pending na decisão enviada: pending pertence à sugestão ainda não
decidida. Uma gravação pode decidir parte das sugestões; IDs devem ser únicos e
pertencer à prévia. ReviewRequest exige revisão esperada e 1–10 objetivos aprovados.
`validate_preview` rejeita revisão obsoleta, sugestão alheia e revisão durante
generating. O repositório aplica as mesmas condições atomicamente e incrementa
review_revision uma vez; o validador não executa a gravação.

GenerateRequest exige mesma preview_id/review_revision, todas as sugestões
decididas, objetivos aprovados e conjunto de accepted_suggestion_ids exatamente
igual ao persistido. Zero aceitas é válido; zero sugeridas também. IDs repetidos
ou sugestões rejeitadas/pendentes não passam. `validate_lesson_response` confere
IDs da revisão, título/disciplina/nível/duração e objetivos docentes, e chama o
`LessonBundle.validate_authorized_references` existente com o conjunto aceito.
Validação estrutural não comprova a semântica de texto pedagógico livre; revisão
humana do material integral continua necessária conforme #1.

| Projeto | generation_status | Regra |
|---|---|---|
| draft | sem prévia publicada | salvar original/configuração antes da IA; falha não apaga |
| preview_ready | idle | prévia válida, decisões/objetivos ainda incompletos |
| reviewed | idle | todos decididos, objetivos aprovados; revisão pronta para gerar |
| generating | generating | revisão congelada; outra revisão/geração concorrente retorna 409 |
| ready | ready | last_lesson_bundle_id obrigatório, bundle imutável consultável |
| reviewed após falha | failed | last_error sanitizado; conservar revisão, material e eventual bundle anterior |

Editar revisão de ready volta a reviewed/idle, conservando bundle anterior;
nova prévia válida volta a preview_ready. Publish/completion só promovem estado
após validação e transação concluídas. Consulta expõe o prazo **corrente** do
projeto; igualdade é validada, sem snapshot de expiração desatualizado.

## Sessão, retenção, idempotência e orçamentos

Cookie `matilda_studio_session`: token aleatório opaco, HttpOnly, SameSite=Lax,
Secure em HTTPS, Path=/api/studio, validade de 7 dias renovada em ação docente.
Gerar token seguro e vincular ownership somente no servidor; não expor session_id
no projeto, erros ou exportação. Limpar cookie/outro navegador impede retomada.
Validar Origin em toda escrita contra a origem configurada. Preferir mesma origem
com proxy /api; configuração alternativa deve tratar cookies/CORS explicitamente.

Sessão/projeto devem estar válidos na admissão. Criar prévia, salvar revisão ou
admitir geração válida renova ambos atomicamente para 7 dias; o cookie acompanha
o prazo concedido. `LessonProject` valida expires_at = last_teacher_activity_at +
7 dias e cronologia UTC. Polling/GET/download/impressão/replay concluído não renovam.
Falha da IA mantém a retenção já concedida. O servidor lê o projeto corrente ao
montar a resposta; uma operação longa admitida não é removida pela limpeza.
Referências/contexto capturados sobrevivem à expiração independente de analysis_id.

Idempotência persistida por sessão + prévia + revisão + chave + fingerprint da
entrada aprovada. Mesma operação concluída retorna mesmo bundle/200 sem custo ou
renovação; entrada diferente com a mesma chave é 409, inclusive revisão diferente.
Reclamar trabalho atomicamente antes da IA, sem transação SQLite aberta na rede.
GenerationClaim contém claim_id ativo **ou** completed_bundle, exclusivamente.
Falha admite repetição explícita da mesma chave sem duplicar resultado concluído.
Reinício recupera operações abandonadas após prazo da etapa + 15 s. Não prometer
cobrança exatamente uma vez se o provedor respondeu antes de falha de gravação.

| Limite | Prévia | Geração |
|---|---|---|
| Meta de experiência | 30 s | 45 s |
| Teto total backend | 45 s, incluindo recuperação DOI de até 15 s | 75 s |
| Cliente | 55 s | 85 s |
| Proxy | >=100 s | >=100 s |

Relógio monotônico desde a admissão; retries compartilham deadline. Reservar ao
menos 5 s para validar/persistir geração. Até 2 tentativas totais, inclusive
correção; não repetir 401/403 nem continuar após timeout. Exceder meta informa
espera real, sem porcentagem fictícia nem cancelamento precoce. Timeout encerra
trabalho e permite consulta/repetição explícita. Campos em POLICY congelam os
valores acordados: 12.000 tokens de entrada e 8.000 de saída por chamada (inclui
raciocínio), sem truncamento; contar tokens antes de chamar. Uma operação ativa
por sessão, duas globais, cinco prévias e cinco gerações por hora móvel/sessão.
Admissão/cotas são atômicas antes da chamada; não manter fila ilimitada.

## Erros

Envelope StudioError: detail textual seguro, code enumerado, retryable booleano,
project_id opcional/null somente se próprio e disponível. Não devolver corpo bruto,
chave, prompt, material ou erro do provedor; logs somente IDs, status, modelo,
latência e uso agregado. 404 não distingue inexistente/expirado/outra sessão.

| HTTP | code |
|---|---|
| 422 | invalid_input |
| 404 | not_found |
| 409 | review_conflict, generation_in_progress |
| 413 | input_too_large |
| 429 | session_limit; Retry-After obrigatório se temporal |
| 502 | invalid_generation |
| 503 | provider_unavailable, studio_not_configured |
| 504 | generation_timeout |

`retryable` depende da causa: recusa 401/403 não tem retry automático; timeout ou
falha transitória podem permitir tentativa explícita. Capacidade global retorna
503 sem bloquear Forensics. Erros OpenAlex preservam os status do serviço atual;
adaptar somente o envelope (ex.: 404/not_found, 422/invalid_input,
502/invalid_generation para registro inválido, 503/provider_unavailable).

## Portas e propriedade dos arquivos

StudioRepository deve verificar ownership/expiração em cada acesso, fazer migração
aditiva/transacional e preservar tabelas Forensics. Não é implementação nesta fatia.

| Método | Garantia da implementação futura |
|---|---|
| save_material | admitir/quota/renovar sessão e projeto, persistir request/configuração e documentos antes da IA; draft pode guardar DOI ainda não resolvido, sem Paper fictício |
| publish_preview / fail_preview | validar/promover ou registrar falha e liberar admissão; manter material/decisões e prazo admitido |
| get_preview / get_lesson | ownership/expiração; prazo e estado correntes; sem IA ou renovação |
| save_review | comparar revisão/estado atomicamente, aplicar só campos permitidos, incrementar e renovar |
| claim_generation | conferir revisão/IDs/ownership, idempotência, quota e estado atomicamente; congelar revisão e renovar somente se nova operação |
| complete_generation | validar bundle/revisão/snapshots, finalizar claim e estado em uma transação; resultado imutável |
| fail_generation | marcar falha e liberar operação, preservar revisão e último bundle; sem segunda renovação |
| cleanup_expired | remover filhos/idempotência em cascata; não remover execução admitida válida; recuperar abandonadas após prazo + 15 s |

StudioProvider oferece count_input_tokens e complete. ProviderRequest separa
system_instruction, material não confiável e response_schema; stage preview/lesson,
deadline monotônico absoluto e budgets acompanham a chamada. T09 fornece o schema
de JSON estruturado com chaves locais dos componentes; servidor resolve IDs finais.
ProviderResult carrega bytes UTF-8 **não confiáveis** e LessonGenerationMetadata
efetivos. O consumidor limita bytes antes de parsear e aplica validação estrutural,
científica e da revisão; o port não faz esse parse nem valida uma resposta inválida
como sucesso. Desabilitar ferramentas, busca, código e execução de material no adapter.

ProviderFailure expõe somente razões timeout/rate_limited/unauthorized/blocked/
truncated/unavailable; RepositoryConflict contém StudioError sanitizado. JSON
inválido ou fora do schema alcança a validação real de T09. O double em
backend/tests/studio_provider_double.py cobre esses casos sem rede, chave ou SDK;
provider=fixture/model=not-generated nunca é sucesso de produção.

A Issue #4 autoriza liberar T09 com Gemini simulado após M0; não exige chave/quota
real neste gate. Ensaio real fica em T05/T10 e não é declarado concluído por fixtures.
Autorização, Origin, validação e testes essenciais nascem com cada rota real em T05;
T12 acrescenta retomada/refinamentos, não adia esses controles obrigatórios.

| Frente/tickets | Editor exclusivo e composição proposta |
|---|---|
| A / T04–T06 | motor/catálogo e adaptador científico; não editar schemas Studio de B |
| B / T05, T09, T12 | schemas/ports Studio; futuros api/studio.py, studio/repository.py, studio/provider.py e orquestração; B conecta router em main.py, sem alterar rotas Forensics |
| C / T07, T10 | types/studio.ts após aceite, services/studio-api.ts, entrada/revisão e navegação App.tsx; B/C serializam mudanças de contrato antes de editar |
| D / T08, T11 | types/lesson.ts, componentes de aula/plano, estilos de entrega, exportador Markdown e E2E; B integra a função de exportação de D na rota acordada |

Sequência: artefatos T03 → revisão A/B/C/D e registro de versões/exemplos → integração
na base comum e fechamento M0 → T04/T07/T09. T08 tem somente a antecipação já
autorizada por T02. Depois, T05/T06 e T10 integram ciência, API e consumidores reais;
T11/T12 completam entrega/retomada. Um editor por arquivo compartilhado; alterações
posteriores exigem proposta, impactos, acordo e sequência na Issue #4.

## Verificação e aceite

```sh
.venv/bin/python -m pytest backend/tests/test_studio_contracts.py -q
.venv/bin/python scripts/check_studio_contract.py
.venv/bin/python scripts/check_scientific_contract.py
node scripts/check_lesson_types.mjs
make test
make build
```

O OpenAPI pode ser consultado sem instalar rotas:
`PYTHONPATH=backend .venv/bin/python -c 'from app.studio.contracts import studio_openapi; import json; print(json.dumps(studio_openapi()))'`.
Fixtures HTTP usam ponteiros para os mesmos payloads; o export é somente amostra
de transporte, não um exportador implementado. Testes/checadores usam os bytes/JSON
reais, sem casts TS. Datas/IDs fictícios de projeto são namespace de testes; fontes
científicas e participantes vêm dos registros reais versionados de T01/T02.

Aceite a registrar **nesta Issue #4**, referenciando #1 sem alterá-la:

| Frente | O que conferir | Estado |
|---|---|---|
| A | fontes/IDs/âncoras, conjunto autorizado, ausência de artigo fictício | pendente |
| B | schemas, OpenAPI, portas, sessão/revisão/idempotência e geração simulada | pendente |
| C | requests/responses, null/defaults, retomada, campos editáveis e tipos | pendente |
| D | LessonBundle importado, referências aceitas, export/renderer e estados | pendente |

Informar commit/revisão v1 e os exemplos conferidos em cada resposta. Não atribuir
aprovações a pessoas não consultadas. Revisão técnica automatizada/por agentes e
PR preparado não representam esses aceites, integração ou M0 fechado. Manter a
Issue #4 aberta até o registro e a integração; #1 não é editada/fechada por T03.

Verificação desta revisão em 21/10/2026: **366 testes backend aprovados** (241
existentes + 125 T03), **40 payloads HTTP Studio**, **7 fixtures científicas** e
**4 fixtures de aula** validados/compilados contra TypeScript, build TypeScript/Vite
aprovado e **6 testes Playwright Forensics aprovados**. Ambiente: Python 3.14.7,
Pydantic 2.13.4, Node 26.10.0, Vite 6.4.5 e Chromium 156.0.8078.4. Sem alterar
dependências ou chamar fontes/Gemini externos; aviso preexistente TestClient/HTTPX.
Executar os verificadores antigos e build em sequência: o verificador científico
usa temporários dentro de src; o novo verificador Studio usa .runtime, fora da
varredura do build. Estes resultados comprovam contratos/regressão, não endpoints
Studio, persistência, autorização em execução ou geração real já entregues.
