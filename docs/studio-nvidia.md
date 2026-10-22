# Studio com NVIDIA NIM — Issue #31

Atualização lesson: [timeout, contrato compacto e smoke isolado](studio-nvidia-lesson-timeout.md).

Histórico da prévia: [candidatos científicos e compactação](studio-scientific-candidates.md).

Histórico estrutural de âncoras: [seleção canônica pelo servidor](studio-canonical-anchors.md).

Histórico após o primeiro smoke relatado pelo usuário: ver
[diagnóstico da prévia e limites da evidência](nvidia-preview-diagnosis.md).
A correção não realizou novas inferências reais. O registro de validação abaixo
refere-se à implementação inicial da migração.

Migração baseada na T13 `a88698e` / PR #30, com PR dirigido à branch
`feat/issue-14-integrated-demo`. API, schemas Pydantic públicos, tipos TypeScript,
FastAPI, SQLite, snapshots e catálogo científico permanecem os da T13.

## Configuração e transporte

```dotenv
AI_PROVIDER=nvidia
NVIDIA_API_KEY=
NVIDIA_MODEL=nvidia/nemotron-3.5-super-vl-120b-a12b
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
```

Copiar `.env.example` para `.env`, preencher a chave no backend e reiniciar a API.
A chave é lida exclusivamente de NVIDIA_API_KEY no ambiente; não é parâmetro de
construtor nem configuração de frontend. O carregamento local de `.env` segue o
host existente. Não habilitar logs HTTP de debug com material real.

Sem chave, Studio falha explicitamente e Forensics continua disponível. Para a
alternativa, definir AI_PROVIDER=gemini, GEMINI_API_KEY e GEMINI_MODEL. O adaptador
Gemini e seu script smoke não foram modificados. Nenhuma falha NVIDIA provoca
chamada a Gemini ou a outro modelo.

HTTPX AsyncClient usa POST `/chat/completions`, HTTPS, sem redirects e sem proxies
implícitos do ambiente. O timeout absoluto inclui conexão, resposta e leitura do
corpo. Respostas são lidas em blocos com teto de 128 KiB **antes** do parsing.
O deadline é o mesmo nas duas tentativas controladas pelos serviços: 45 s na
prévia, 75 s na aula, com os 5 s de reserva de persistência existentes na geração.
A admissão SQLite mantém uma operação por sessão e duas globais, entre os estágios.
O adaptador não tem retries próprios. HTTP 202 já é trabalho aceito: falha como
resposta pendente, sem iniciar outro POST. A página do endpoint menciona polling
por requestId, mas não especifica nela a rota/protocolo de consulta; não se
inventa uma URL, não se segue Location arbitrário e não se aumenta o deadline.
Polling/reconciliação de uma operação NVIDIA pendente continua uma limitação
explícita; o estado docente local é preservado para consulta/tentativa explícita.

| Estágio | reasoning_effort | stream | temperature | top_p | Saída |
|---|---|---|---|---|---|
| Prévia | none | false | 1 | 0.95 | PreviewPlan completo |
| Aula | none | false | 1 | 0.95 | CompactLessonDraft → LessonDraft completo → LessonBundle validado |

## JSON e autoridade científica

O endpoint específico documenta `response_format.json_schema.schema`. O envelope
usado é `{"type":"json_schema","json_schema":{"name":"PreviewPlan ou LessonDraft","schema":{...}}}`.
Não são enviados `strict`, `nvext`, parâmetros de SDK não documentados ou um
schema vazio como alternativa. O `model_json_schema()` existente é enviado com refinamentos de cobertura e enums de IDs autorizados na prévia,
incluindo `$defs`, `$ref`, limites, campos obrigatórios, uniões e
`additionalProperties=false`. Não há adaptação que retire validações. O schema da prévia agora exige sugestões com cobertura e proíbe sugestões sem cobertura, mantendo a validação científica independente.

A API do modelo não recebe LessonBundle diretamente: a fronteira T09 existente
é LessonDraft, preservada para Gemini e para a validação central. O adapter
NVIDIA usa elaboração compacta aninhada, expandida deterministicamente para esse
LessonDraft integral antes da materialização. IDs finais, metadados, evidências, participantes e referências
canônicas são acrescentados e conferidos pelo servidor. Exigir LessonBundle do
modelo permitiria que ele escrevesse campos que pertencem ao servidor. A prévia
usa PreviewPlan privado com candidate_id; o servidor resolve toda a associação
(contribuição, conceitos, evidências e âncora) para
o SourceAnchor público original antes de validar EnrichmentPreview. Não aceita
source_anchor escrito pelo modelo. A aula continua recebendo a prévia pública completa.

O contrato compacto da aula ainda precisa ser aceito pelo endpoint live: testes de
transporte validam o payload, mas não executam o compilador de schema da NVIDIA.
Se o schema for recusado, 400/422 falha sem repetição automática. Não há downgrade
para JSON livre. Uma adaptação futura exige reproduzir o erro sanitizado, manter
o schema original como validação obrigatória no servidor e documentar a diferença.
Não se afirma aqui que todo keyword Pydantic já foi comprovado no endpoint live.

Conteúdo vazio, finish_reason ausente/diferente de stop, tool calls, recusa,
JSON malformado, chaves duplicadas e constantes não JSON falham. JSON com formato
válido ainda precisa passar pelos schemas Pydantic e pela autoridade científica.
Âncoras literais, IDs autorizados, autoria coletiva, revisão docente, vínculo de
slides/seções, duração e ausência de referências inventadas continuam obrigatórios.

## Contagem conservadora

A referência do Chat Completions hospedado não documenta equivalente ao
`countTokens` do Gemini. Não se presume que `/tokenize` de um container NIM seja
oferecido por `integrate.api.nvidia.com`. Não há chamada de contagem cobrada.

A implementação soma os **bytes UTF-8 do payload JSON completo e compacto**
(instrução, material serializado, schema integral, wrappers de mensagens e
configuração) e acrescenta **1.024** como reserva de tokens para o template.
É um teto operacional deliberadamente conservador para tokenização textual por
bytes/subpalavras, em vez de uma razão média de caracteres por token. Escapes e
schema também entram no orçamento. Unicode e textos pouco compressíveis não são
divididos por quatro. Pode rejeitar entradas que caberiam no tokenizer exato;
reduza a entrada quando a estimativa ultrapassar 12.000. A correção da segunda
tentativa é recontada e não ganha orçamento adicional.

A reserva é uma hipótese operacional explícita sobre overhead não publicado pelo
endpoint hospedado, e não uma promessa sobre o template interno da NVIDIA. Não
foi alegada contagem exata nem usado tokenizer de outro modelo. Alterar modelo ou
servidor exige revalidar essa hipótese. O smoke registra dados para essa conferência.
Se o uso informado exceder 12.000 ou o orçamento de saída de 8.000 (incluindo
raciocínio contabilizado em completion_tokens), a resposta falha; não publica
sucesso acima do limite. A validação do uso efetivo complementa a admissão,
sem afirmar que evita retroativamente o custo de uma requisição já enviada.

Eventos `nvidia_attempt` incluem etapa, HTTP externo, duração, estimativa,
`actual_input_tokens`, `output_tokens`, modelo efetivo e
`input_token_delta = actual_input_tokens - estimated_input_tokens` quando disponíveis.
Metadados persistidos continuam guardando os tokens **efetivos**, não a estimativa.
Não se registra prompt, resposta, chave, material, URLs com segredos ou erro bruto.
O outcome completed no adaptador significa transporte/JSON válidos; o sucesso da
prévia/aula depende também da validação Pydantic/científica e persistência.

## Falhas e recuperação

A classificação interna usa os motivos já existentes de StudioProvider e o
envelope HTTP M0, sem alterar contratos públicos. Telemetria mantém a distinção:

| Situação | Classificação sanitizada | Envelope e repetição |
|---|---|---|
| 400/422, redirects/outro HTTP incompatível | invalid_request | invalid_generation, sem retry |
| 401/403 | unauthorized | provider_unavailable, sem retry |
| 429 | rate_limited | provider_unavailable, até 2 tentativas |
| 5xx, rede | unavailable | provider_unavailable, até 2 tentativas |
| 202 aceito/pendente | pending_response | invalid_generation, sem novo POST automático |
| Timeout/deadline | timeout | generation_timeout, sem prazo novo |
| JSON inválido/duplicado/não objeto | invalid_json | invalid_generation após até 2 tentativas |
| Envelope/metadados incompatíveis | invalid_response | invalid_generation após até 2 tentativas |
| Sem conteúdo | empty_content | invalid_generation, falha incompleta |
| Finish incompleto/limite de saída | truncated | invalid_generation, sem sucesso parcial |
| Corpo acima de 128 KiB | response_too_large | invalid_generation após até 2 tentativas |
| Schema Pydantic inválido | pydantic_validation | invalid_generation após até 2 tentativas |
| Ciência/vínculos incompatíveis | scientific_validation | invalid_generation após até 2 tentativas |

Recusa/blocked preserva a política anterior: prévia invalid_generation; geração
provider_unavailable sem retry. Mensagens de HTTP upstream nunca são propagadas.
Em erro ficam preservados material e decisões; tentativa explícita pode recuperar
a operação. Repetição de geração concluída retorna o mesmo bundle, sem IA extra.

## Smoke NVIDIA e gates live

**Nenhuma chamada NVIDIA live foi executada nesta implementação.** O status
produção depende de uma prévia e uma aula completas comprovadas no endpoint real.
Também permanece o ensaio pedagógico/humano e no equipamento de apresentação.

Sem flag, o script termina com exit 2, sem carregar chave nem chamar serviços.
Só executar após autorização explícita, reconhecendo até **3 chamadas / 180 s**:

```sh
.venv/bin/python scripts/smoke_studio_nvidia.py --allow-paid-nvidia
# Alternativamente, gerar a aula RNA depois das mesmas duas prévias:
.venv/bin/python scripts/smoke_studio_nvidia.py --allow-paid-nvidia --lesson-scenario rna
```

Cada invocação usa novo SQLite `.runtime/nvidia-smoke-<uuid>.sqlite`, prévias CRISPR
e RNA com 50 minutos, revisão explícita via API e uma geração de aula. Usa fontes
reais em cache datado; inferência real, sem respostas prontas. A aprovação de teste
aceita a primeira sugestão e rejeita as demais; não equivale à revisão humana do
conteúdo para uso em sala. O limite permite uma tentativa externa por operação;
uma correção/retry cobrado não é iniciado. Contagem é local, exportação e leitura
não chamam IA. O processo supervisor interrompe após 180 s; não aumenta os
45/75 s do backend. O argumento interno worker é exclusivo do supervisor. O modelo solicitado pelo smoke é fixo no Nemotron escolhido; NVIDIA_MODEL não o substitui.

O relatório só passa após duas prévias válidas, aula LessonBundle de 50 minutos
com referências, leitura idêntica persistida e Markdown. Registra HTTP/tempo por
etapa, modelo/tokens efetivos, diferença da estimativa, JSON validado, slides e
seções. Falha continua failed; não promove prévia isolada a ensaio completo.
O campo external_calls é o número máximo de tentativas reservadas pelo limite,
inclusive uma tentativa impedida pelo preflight. stderr nunca é retransmitido
pelo supervisor. Não anexar o banco, `.env` ou material docente a um PR.

## Validação simulada

Comandos na raiz, salvo Playwright/build na pasta frontend:

```sh
.venv/bin/python -m pytest backend/tests -q
.venv/bin/python scripts/check_scientific_contract.py
.venv/bin/python scripts/check_studio_contract.py
node scripts/check_lesson_types.mjs
cd frontend
npm run build
node node_modules/@playwright/test/cli.js test --config playwright.studio.config.ts
```

Resultado desta versão: **619 backend**, **7 fixtures científicas**, **40 payloads
Studio**, **4 fixtures LessonBundle**, TypeScript/build e **20 E2E integrados**
aprovados. MockTransport exercita ambos os estágios, erros HTTP, limite de
entrada/saída/corpo, deadline, credenciais ausentes, URL insegura, ausência de
fallback, JSON/metadata inválidos, retry, recuperação, idempotência e smoke.
O E2E T13 agora substitui somente o transporte externo NVIDIA, executando o
adaptador real junto de FastAPI/SQLite, frontend e validadores reais. Modelo
controlado sempre se identifica como controlled. Regressão Forensics incluída.

## Referências primárias consultadas em 22/10/2026

- [Endpoint específico Nemotron 3.5 Super VL](https://docs.api.nvidia.com/nim/reference/nvidia-nemotron-3_5-super-vl-120b-a12b-infer): formato response_format, estágios de raciocínio, HTTP e amostragem.
- [Playground/modelo NVIDIA](https://build.nvidia.com/nvidia/nemotron-3.5-super-vl-120b-a12b): endpoint hospedado, chave e exemplo de chamada.
- [Model card NVIDIA](https://docs.api.nvidia.com/nim/reference/nvidia-nemotron-3_5-super-vl-120b-a12b): amostragem de texto e características do modelo.
- [Structured Generation NIM 1.8](https://docs.nvidia.com/nim/large-language-models/1.8.0/structured-generation.html): usa nvext em containers de outros modelos; não é tratado como contrato deste endpoint hospedado.

A estimativa byte a byte e a reserva são decisões conservadoras do Matilda,
não uma fórmula de contagem exata publicada pela NVIDIA.

Também passaram os harnesses Playwright existentes: revisão **19**, slides **14**,
geração/operações **18**, ponte Forensics/Studio **5** e exportação **11**.
Total de navegador: **87**, somando os **20** integrados. Esses harnesses isolados
usam seus provedores/fixtures declarados e não contam como inferência live.
