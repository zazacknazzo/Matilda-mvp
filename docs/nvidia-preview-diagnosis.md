# Diagnóstico da primeira prévia NVIDIA — PR #32 / Issue #31

Documento histórico da primeira correção. A geração livre e os exemplos de
âncoras descritos aqui foram substituídos por [seleção canônica](studio-canonical-anchors.md).

Base da investigação: `d42432b` (cabeça do PR #32 antes desta correção).
Nenhuma nova inferência NVIDIA/Gemini foi executada nesta investigação.

## Evidência real disponível e limite do diagnóstico

O usuário informou: HTTP NVIDIA 200; modelo reportado
`private/nvidia/nemotron-3.5-super-120b-a12b`; inferência de 2.254 ms; entrada de
1.330 tokens e saída de 96 tokens; structured_generation OK; validation FAILED
com scientific_validation; HTTP Matilda 502 / invalid_generation. Foi feita uma
inferência; a correção foi bloqueada pelo orçamento do smoke.

Esses números são o relato do smoke real, não medições repetidas por esta sessão.
O alias reportado difere do nome solicitado. O adaptador aceita e registra esse
identificador como metadado; a diferença textual não é uma regra de rejeição
científica. A equivalência dos modelos no servidor não foi certificada aqui.
O smoke agora fixa o modelo **solicitado** exatamente em
`nvidia/nemotron-3.5-super-vl-120b-a12b`, independentemente de NVIDIA_MODEL.

Foram encontrados dois SQLite locais de smoke, abertos somente para leitura.
Ambos guardam uma entrada, dois documentos e invalid_generation, sem prévia
publicada. **Nenhum guarda o JSON rejeitado.** Também não foi encontrado arquivo
local da resposta. A captura privada foi solicitada ao usuário apenas por caminho,
sem pedir conteúdo ou credencial na conversa.

No código dessa versão, PreviewPlan inválido gera ValidationError e é registrado
como pydantic_validation. Após a leitura limitada do adaptador, o ramo de tamanho
excessivo anterior ao PreviewPlan não é alcançável: o envelope HTTP inteiro já foi
limitado a 128 KiB. Com a sequência de eventos relatada, **PreviewPlan passou na
validação estrutural**, e a falha ocorreu numa regra semântica posterior. Isso é
inferência pelo fluxo do código e pelos eventos, não inspeção de um JSON recuperado.

O rótulo antigo scientific_validation não distingue cobertura, contribuição,
evidência ou demais regras posteriores. **Não é possível provar qual delas
rejeitou essa resposta específica nem quantas sugestões ela continha.** Os 96
tokens de saída não comprovam suggestions vazio. A hipótese coverage_mismatch
não foi promovida a fato observado no endpoint real.

## Contexto reconstruído sem rede

As entradas dos dois bancos foram reprocessadas pela API/SQLite em bancos
temporários, com HTTPX impedindo qualquer saída de rede e inferência substituída
por transporte controlado. Em ambos:

- quatro contribuições autorizadas;
- dois documentos (texto e metadados reais do artigo);
- conteúdo dos documentos idêntico ao preservado nos bancos;
- cada contribuição com concept_ids e evidence_ids disponíveis;
- source_documents com id e content completos, suficientes para uma âncora literal.

Essas são contagens de **reconstrução offline** com o catálogo preservado. O
snapshot de autorização do primeiro instante não foi persistido na prévia falha.
A quantidade de sugestões da resposta real continua desconhecida.

## Loop e causa comprovada no contrato

Comando determinístico, sem rede:

```sh
.venv/bin/python -m pytest backend/tests/test_studio_preview_diagnostics.py -q
```

O caso mínimo fornece pelo MockTransport um objeto PreviewPlan válido com um
objetivo e suggestions vazio, diante de cobertura CRISPR autorizada. O adaptador
aceita HTTP/JSON e o servidor rejeita a ciência com HTTP 502. O teste inicial
ficou vermelho porque não havia código nem contagens de diagnóstico; com a
instrumentação, identifica **coverage_mismatch**, plan_pydantic_valid=true,
authorized_contributions=4 e returned_suggestions=0. Esses valores de retorno
são da resposta sintética, não do JSON original perdido.

Também ficou vermelho o teste do contrato enviado ao provedor: o schema permitia
suggestions vazio embora a regra científica exigisse ao menos uma sugestão quando
há contribuições. **Essa divergência entre o schema enviado e a validação posterior
é um defeito comprovado e corrigido.** O prompt já mencionava cobertura, mas o
schema de decodificação ainda permitia a alternativa rejeitada pelo servidor.
Não se afirma que essa era a única causa possível do primeiro smoke real.

Hipóteses verificadas isoladamente por transporte controlado: ausência de
sugestões apesar de cobertura; ID de contribuição inexistente/evidência de outra
contribuição; conceito inválido; documento/trecho/ocorrência não literal. Cada
mutação mantém falha, com diagnóstico específico. Identidade não elegível foi
verificada pela interface pública validate_scientific_authority, usando autoridade
controlada independente. Nenhuma hipótese foi testada com nova inferência paga.

## Correção e segurança

- PreviewPlan permanece o schema Pydantic estrutural comum. O schema enviado ao
  provedor agora **refina** a política já existente: minItems=1/maxItems=20 com
  cobertura; minItems=0/maxItems=0 sem cobertura. Não inventa uma sugestão vazia
  nem transforma ausência de cobertura em atribuição.
- Enums restringem contribution_id, concept_ids, evidence_ids e documento da
  âncora aos IDs resolvidos. As relações entre contribuição/conceito/evidência
  continuam verificadas no servidor; enums globais não autorizam misturar IDs.
- Prompt studio-preview-v2 explica que cobertura é resolvida pelo servidor e
  exige selecionar todos os IDs de uma mesma entrada. Não autoriza novos nomes,
  fontes, fatos ou ferramentas.
- source_anchor_examples contém apenas id de documento real, substring literal
  de até 160 caracteres e occurrence=0. É exemplo de **estrutura**, sem sugestão
  completa pronta e sem alegação histórica fabricada. Os trechos são dados não
  confiáveis; instruções neles continuam proibidas.
- Regras científicas continuam nos mesmos validadores. PydanticCustomError
  acrescenta códigos tipados sem alterar campos, schema público ou autorização.
  Não há classificação por comparação de mensagens brutas.
- O relatório do smoke captura studio_preview_validation, inclusive antes de
  uma tentativa corretiva local ser bloqueada. BudgetedNVIDIA mantém uma chamada
  por operação e três totais; é testado com o próprio script e MockTransport.
  Também impede uma segunda inferência em 202, 401, 429 e 503.
- Deadlines, tamanho máximo, orçamento de tokens, revisão docente, evidências,
  participantes e persistência idempotente permanecem obrigatórios. Não houve
  mudança de catálogo, frontend, contrato HTTP ou banco.

## Diagnósticos sanitizados

Evento studio_preview_validation contém somente códigos, contagens, número da
tentativa, outcome e os três resultados: plan_pydantic_valid,
preview_pydantic_valid, scientific_authority_valid. true=passou; false=falhou;
null=não chegou a executar. returned_suggestions é null se o plano não passou;
nunca se conta uma lista não validada como sucesso. Nem IDs, trechos, nomes,
objetivos, prompts, resposta bruta, mensagens Pydantic ou chave entram nesse evento.

| Código | Regra que falhou |
|---|---|
| coverage_mismatch | Presença/ausência de sugestões diverge da cobertura autorizada |
| unknown_contribution | Contribuição fora do conjunto autorizado |
| unauthorized_evidence | Evidência não pertence à contribuição selecionada |
| invalid_concept | Conceito fora do contexto/contribuição autorizados |
| invalid_source_anchor | Documento, trecho ou ocorrência literal inválidos |
| invalid_identity | Identidade não verificada ou pesquisadores incompatíveis |
| ineligible_contribution | Contribuição sem verificação exigida |
| pydantic_validation | Forma/tipos/campos do plano ou da prévia inválidos |
| provider_response_invalid | Falha do payload antes de executar PreviewPlan |
| scientific_validation | Outra regra científica não coberta por código específico |
| ok | Plano, prévia e autoridade passaram; persistência é etapa separada |

A classificação não muda StudioError: o cliente continua recebendo o envelope
seguro invalid_generation. O reporte antigo studio_validation foi mantido para
compatibilidade. Mensagens originais dos validadores são estáticas e seus valores
não são serializados nos diagnósticos.

## Repetição real — somente após nova autorização

No checkout atualizado do PR #32, com dependências instaladas e chave apenas no
ambiente/.env local do backend:

```sh
.venv/bin/python scripts/smoke_studio_nvidia.py --allow-paid-nvidia --env-file /caminho/local/.env
```

São no máximo duas prévias (CRISPR/RNA) e uma aula, uma inferência por operação,
180 s totais supervisionados. O comando acima **não foi executado** contra a
NVIDIA nesta investigação. Falha continua interrompendo o roteiro; não há novas
tentativas pagas automáticas, fallback ou merge. O próximo relatório permitirá
identificar a rejeição sem reter/expor o JSON bruto. Sucesso live ainda não foi
comprovado após a correção; revisão pedagógica humana continua necessária.

## Verificação desta correção

- Backend: **635 passed**, 8,57 s, incluindo 16 testes de diagnóstico/contrato/budget.
- Contratos: 7 fixtures científicas, 40 payloads Studio e 4 LessonBundle TS.
- TypeScript/build: aprovado; permanece o aviso Vite de chunk acima de 500 kB.
- Playwright: **87 casos aprovados** — integrado T13/Forensics 20, revisão 19,
  slides 14, geração/operações 18, ponte 5 e exportação 11.
- O harness de geração teve uma falha inicial de ciclo de vida de transporte de
  teste (`apiResponse.json: Response has been disposed`). O teste isolado passou
  na reprodução seguinte, e o harness completo passou 18/18 sem alteração de
  produto/teste. O resultado inicial não foi descartado nem contado como aprovado.
- MockTransport reproduz a rejeição preservada e confirma uma chamada externa
  controlada por operação; simulação não comprova melhoria de inferência live.
- Não foi alterado GeminiProvider, smoke Gemini, evidências/catálogo ou deadlines.

Revisões independentes: [Standards e Spec](reviews/nvidia-preview-diagnosis-code-review.md). Standards teve uma sugestão P3 de manutenção corrigida; nenhum achado técnico permanece aberto nos dois eixos. A falta do JSON original continua sendo limite da investigação real.
