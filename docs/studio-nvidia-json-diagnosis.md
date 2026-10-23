# NVIDIA lesson: invalid_json e saída estruturada (#31 / PR #32)

Base: `88fdde76d1ebbdb64c509c427375dd458768da7d`.
Escopo: parser/diagnósticos NVIDIA, instrução privada, strict documentado,
testes e documentação. compact-v2-weighted preservado. Sem inferência real,
merge #32/#30, alteração do PR #34 ou trabalho do Agente 3.

## Evidência real informada e hipóteses

Terceiro smoke relatado pelo usuário: preparação simulada201 válida, revisão200,
NVIDIA200, 5.945 ms, corpo HTTP3.340 bytes, entrada916/saída822 tokens, none,
stream=false, compact-v2-weighted, phase=validation, outcome=invalid_json.
Matilda502/invalid_generation, uma chamada externa, sem retry.

A resposta textual não foi fornecida. Esses números não permitem identificar
sintaxe, duplicidade, raiz, constante inválida ou Unicode. Não atribuímos a falha
à alocação temporal: a validação JSON ocorre antes de `expand()`.

Hipóteses apresentadas antes da correção:

1. Saída com sintaxe inválida: Markdown, vírgula final, aspas não fechadas,
   objetos concatenados ou JSON incompleto. Predição: parsing falha antes do schema.
2. Chaves duplicadas em qualquer nível. Predição: rejeição pelo object_pairs_hook.
3. Constante não JSON ou raiz não objeto. Predição: diagnóstico específico após
   um envelope válido, antes de Pydantic.
4. Limite/representação do parser: inteiro excessivo, profundidade ou Unicode.
   Predição: falha diferente da gramática comum, sem modificar o texto.
5. Integração: modo estrito omitido ou característica não suportada pelo compilador
   hospedado. A inspeção comprova a omissão de strict; não comprova que causou o smoke.

## O que a base agrupava em invalid_json

`_parse()` primeiro decodifica o envelope HTTP e valida choices, finish_reason,
message.content textual, modelo e uso. Só depois chama json.loads(content) com
rejeição de duplicidades e constantes, exige dict e codifica o texto em UTF-8.
O bloco capturava ValueError, TypeError e RecursionError sem distinguir causas.

| Categoria | Como é reconhecida | Diagnóstico novo |
|---|---|---|
| Erro de sintaxe, incluindo Markdown, comentários, vírgula final e interrupção | JSONDecodeError | json_syntax_invalid |
| Chave repetida, também em objetos aninhados e escapes equivalentes | object_pairs_hook | json_duplicate_key |
| Array, string, número, booleano ou null na raiz | valor decodificado não é dict | json_root_not_object |
| NaN, Infinity ou -Infinity literais | parse_constant | json_nonfinite_constant |
| Inteiro acima do limite de dígitos do runtime | int() rejeita o token numérico | json_integer_too_large |
| Surrogate isolado no texto de content não codificável em UTF-8 | UnicodeEncodeError | json_unicode_invalid |
| Recursão excedida pelo decoder, quando o runtime a impõe | RecursionError | json_nesting_too_deep |

TypeError estava no handler, mas não há um caminho normal conhecido para ele
nesse ponto: content já é str e os hooks só recebem tipos do decoder.
undefined/None são sintaxe inválida; não são as constantes reconhecidas por
parse_constant. Números válidos em JSON continuam sujeitos a tipos/faixas do
schema e Pydantic; não são corrigidos pelo parser.

Profundidade merece uma distinção: no Python3.14 local, uma fixture com milhares
de arrays foi aceita pelo decoder e rejeitada por Pydantic. Não alegamos ter
reproduzido RecursionError nessa versão; o subcódigo é um tratamento defensivo da
exceção já capturada na base, para runtimes que a emitam.

Uma interrupção conhecida da fixture, mesmo com finish_reason=stop, recebe
json_syntax_invalid. A posição do erro não permite inferir a origem da interrupção
real. Se o upstream informa finish_reason=length, o resultado continua truncated,
antes do parsing do conteúdo. Nenhuma saída parcial é aceita.

## Separação de responsabilidades e segurança

`integrations/nvidia_json.py` concentra o decoder estrito e expõe `decode_object()`.
A mesma implementação decodifica envelope e conteúdo, sem reparo ou normalização.
`NVIDIAProvider` conserva a validação do protocolo, orçamentos e expansão da aula.

- Envelope JSON inválido: outcome=invalid_response, json_target=envelope e código
  do decoder. Envelope com forma/metadados inválidos conserva invalid_response.
- Conteúdo inválido: outcome=invalid_json, json_target=message_content e failure_code.
- Objeto JSON válido contrário ao contrato: pydantic_validation/lesson_schema_invalid.
- Saída válida: LessonDraft completo, LessonBundle, ciência, revisão e persistência.

Logs recebem apenas códigos constantes, content_chars, content_bytes quando UTF-8
é possível, posições/linha/coluna inteiras de erro e metadados já validados.
finish_reason usa uma lista fechada; valores desconhecidos viram unknown. Modelo
mantém a validação existente. Não há texto de exceção, nomes de chaves duplicadas,
valores, trechos, prompts, material, fontes privadas, cookies ou credenciais.
Posições são índices de caracteres do decoder, não offsets de bytes; podem variar
entre versões Python. response_bytes é o corpo HTTP; content_bytes é apenas a
string extraída, antes da expansão. Não devem ser comparados como a mesma medida.

## Endpoint hospedado: fatos e limite da evidência

A [referência oficial do modelo](https://docs.api.nvidia.com/nim/reference/nvidia-nemotron-3_5-super-vl-120b-a12b-infer)
expõe POST /v1/chat/completions no domínio integrate.api.nvidia.com e o modo
json_schema. O OpenAPI incorporado à página declara type no response_format e
name/schema obrigatórios dentro de json_schema; strict é um booleano opcional.
O payload da base já tinha o aninhamento correto, mas omitia strict. A leitura
foi apenas da documentação pública, sem chamada de inferência.
[Registro factual da referência e hash do fragmento](nvidia-hosted-structured-output-reference.json).

A mudança mínima é pedir strict=true **somente para lesson** e explicitar no
prompt um objeto JSON completo, sem cercas Markdown, texto externo, chaves
repetidas, vírgulas finais ou constantes não JSON. A prévia conserva seu schema,
flag omitida e prompt. O log json_schema_strict=true significa **modo solicitado**;
não prova que o decoder hospedado efetivamente o aplicou.

Não enviamos nvext, guided_json, guided_decoding, regex/grammar de containers,
parâmetros de backend ou SDK não declarados para esse endpoint. Nenhum fallback
para json_object/texto livre, nem retry novo, foi introduzido. Temperatura1,
top_p0,95, none, stream=false, limites12.000/8.000 e deadlines continuam.

## Contrato privado realmente enviado

[Snapshot do schema transmitido](../tests/fixtures/studio/nvidia/compact-v2-weighted.schema.json):
3.867 bytes de JSON compacto, oito definições em $defs. O schema integral é
idêntico ao da base88fdde7; o teste compara cada campo e resolve todos os refs locais.

- Raiz object, additionalProperties=false; prior_knowledge, materials, sections e
  limitations obrigatórios. Seções3–8; time_weight inteiro1–1000; slides e atividades
  aninhados, objetivos como arrays de índices inteiros não negativos.
- CompactSlide exige layout, title, content_blocks e speaker_notes. subtitle é
  opcional/nullable via anyOf, com default=null. Notas não vazias e limites mantidos.
- ContentBlock usa oneOf com cinco refs locais e discriminator.type. Cada ramo
  possui const distinto em type, seus campos obrigatórios e additionalProperties=false.
- Arrays conservam mínimos/máximos, strings conservam limites/patterns e layouts
  conservam enum. A remoção anterior de title afeta somente anotações, não campos.
- Limites agregados de4–12 slides/1–4 atividades são model_validators Pydantic:
  não são completamente expressos pelo JSON Schema. Objetivos, layouts, referências,
  50 minutos e autoridade científica continuam obrigatórios no servidor.

$defs/$ref, oneOf/discriminator, anyOf/default e constraints são pontos a observar
num compilador de saída estruturada. A referência hospedada não fornece uma matriz
por keyword nesse campo. Não há evidência de que algum deles tenha causado o
invalid_json; HTTP200 também não comprova que todos tenham sido aplicados. Por
isso não achatamos refs, trocamos uniões, tornamos campos obrigatórios, removemos
keywords ou reduzimos validações por tentativa. Essa mudança exigiria evidência
concreta do erro, equivalência de schema testada e novo gate.

Também não duplicamos o schema inteiro no prompt, nem alteramos sampling junto do
modo estrito. O pedido JSON explícito é um auxílio, não uma garantia medida.
Não se afirma que omitir strict foi a causa específica ou que ativá-lo resolveu
inferência real. O próximo smoke testará essa hipótese e terá diagnóstico preciso.

## TDD e evidências controladas

O primeiro tracer de chave duplicada reproduziu HTTP200 + invalid_json e ficou
vermelho por falta de failure_code; o subcódigo tornou-o verde. O tracer de sintaxe
ficou vermelho pelo mesmo motivo. A matriz de categorias ampliou o loop; posições
foram ajustadas à diferença legítima entre versões CPython. O teste de strict
ficou vermelho porque o campo não existia no payload, antes de sua ativação.

MockTransport cobre JSON completo, vírgula final, aspas não fechadas, duplicidade,
raiz array/escalar, Markdown, JSON interrompido, NaN/Infinity/-Infinity/undefined,
inteiro excessivo, Unicode inválido, envelope inválido e schema privado inválido.
Casos válidos preservam literalmente aspas, Unicode, novas linhas e até marcadores
Markdown dentro das strings. Não há regex, extração de bloco, preenchimento,
remoção silenciosa de campos ou reparo genérico.

Os11 casos pela API usam sessão, ciência, SQLite, revisão e materializador reais;
somente o HTTP upstream é controlado e limitado a uma chamada pelo mesmo guard do
smoke. Os inválidos retornam502, geração failed e nenhum last_lesson_bundle_id,
com sugestões, objetivos, revisão, material e configuração preservados. O válido
persiste50min, consulta o mesmo bundle, faz replay sem inferência e exporta Markdown.
O primeiro teste de revisão comparava também timestamps/status de operação; foi
corrigido para comparar a revisão e configuração, que são as invariantes pedidas.
Nenhuma mudança no produto foi feita para satisfazer essa asserção inadequada.

O smoke isolado controlado testa propagação dos subcódigos e tamanhos no relatório,
com uma única chamada em erro de sintaxe ou duplicidade. O guard de autorização
permanece antes da leitura de credenciais/rede. Testes não certificam compilação
NVIDIA, qualidade pedagógica ou funcionamento real do modo estrito.

## Validação e próximo passo

Backend completo: **760 passed**, 11,48s. Contratos **7/40/4**, TypeScript/build
aprovados. Avisos existentes de dependências e chunk520,42kB permanecem.
Playwright completo e Standards/Spec: registrar os resultados finais após execução.

O checkout temporário desapareceu durante atualização de ambiente; as alterações
não commitadas foram reconstituídas no checkout persistente .runtime/nvidia-json-worktree.
Os51 testes focados foram repetidos e passaram antes da suíte completa acima.
O reinício posterior interrompeu a coleta do Playwright; a suíte integrada foi
retomada com log persistente, sem repetir chamadas reais.

Próximo smoke, **somente após autorização explícita posterior**:

```sh
.venv/bin/python scripts/smoke_studio_nvidia_lesson.py --env-file /caminho/local/.env --allow-paid-nvidia
```

Executar no checkout atualizado de feat/nvidia-studio. Teto uma chamada NVIDIA,
100s totais/backend75s/reserva5s. Preparação simulada identificada, ciência real
em cache, revisão normal; geração exige referências autorizadas, bundle válido,
leitura, replay e Markdown. Sem retry pago, sem conteúdo bruto no relatório.
full_flow_proven=false continua. Não executar nem fazer merge #32/#30 nesta tarefa.
