# Geração NVIDIA — timeout, contrato compacto e smoke isolado (#31 / PR #32)

Registro histórico do compact-v1. O contrato vigente e os diagnósticos de validação
estão em [compact-v2-weighted](studio-nvidia-lesson-validation.md).

Base: `394d109`. Não houve inferência real NVIDIA/Gemini nesta correção.
A prévia e os contratos públicos permanecem. PR #34/UI não foi alterado.

## Evidência e o que ela permite concluir

Smoke real **relatado pelo usuário** na base: CRISPR 201, seis sugestões, ciência
aprovada, 3,83 s; RNA 201, seis sugestões, ciência aprovada, 2,95 s; revisão 200.
Lesson falhou com 504/generation_timeout após 70.001 ms na tentativa NVIDIA,
http_status=null, outcome=unavailable e sem metadados de conclusão. O smoke usou
três chamadas. Estes números não foram medidos novamente nesta sessão.

GenerationService inicia um prazo absoluto de 75 s antes da leitura/validação e
admissão. _run_provider usa deadline menos os 5 s reservados à persistência.
Contagem e inferência compartilham o restante desses aproximadamente 70 s; preparo
já consumido e retries não renovam a janela. O limite externo também cancela o
adapter. Como asyncio.CancelledError não era capturado, finally podia registrar
o valor inicial unavailable. Esse **defeito de classificação foi reproduzido**
por cancelamento controlado e corrigido, sem aumentar nenhum prazo.

A ausência de headers não identifica a fase interna NVIDIA: pode incluir conexão,
envio, fila, compilação do schema, raciocínio ou a geração monolítica inteira.
Não há conclusão, finish_reason ou tokens finais para calcular throughput ou
provar que o limite de saída foi atingido. Não se atribui o incidente a fila,
raciocínio ou transporte como causa comprovada. O fato comprovado é a expiração
do prazo local sem resposta HTTP final observada; a origem da latência continua
pendente de medição live.

Hipóteses: (1) cancelamento externo explica a classificação unavailable —
reproduzido; (2) raciocínio low e elaboração longa elevam latência — mitigação
experimental none/compactação, sem comprovação de ganho live; (3) espera por
headers pode ser rede/fila/inferência — agora distinguível da leitura de corpo,
ainda sem atribuição ao servidor; (4) saída incompleta/limite de tokens — testada
como falha, mas sem evidência de ter ocorrido no smoke real.

Loops vermelhos antes das correções: teste do cancelamento observou unavailable;
HTTP504 preservava revisão, mas faltava failure_phase; teste da aula compacta
falhou no esforço/schema antigo; teste de notas vazias detectou plano incompleto
que passava. Os loops finais estão nos testes test_nvidia_lesson_deadline,
test_nvidia_compact_lesson e test_nvidia_lesson_smoke, sempre com MockTransport.

## Transporte e telemetria

nvidia_attempt agora registra fase, orçamento restante no início da tentativa,
limites de tokens, tempo até headers, primeiro bloco do corpo, bytes recebidos e
duração total. Mantém HTTP, uso efetivo/diferença e modelo quando informados.
Timeout/deadline gera timeout/deadline_exceeded; cancelamento antes do deadline
é cancelled/caller_cancelled; falha HTTPX de transporte é unavailable/transport_error.
A fase identifica preflight, waiting_headers, reading_body ou validation. Não há
prompt, texto de chunk, raciocínio, resposta bruta, chave ou mensagem de exceção.

O primeiro bloco HTTP **não é o primeiro token do modelo**. A leitura continua
limitada antes do parsing; JSON inteiro, finish_reason=stop, metadados e validações
são necessários. Nenhum byte parcial é publicado. O cancelamento é propagado,
preservando o mecanismo de falha/reconciliação e a revisão existente.

## Raciocínio e SSE

A [referência do endpoint hospedado](https://docs.api.nvidia.com/nim/reference/nvidia-nemotron-3_5-super-vl-120b-a12b-infer)
documenta reasoning_effort none/low/high; none desliga tokens de raciocínio.
A geração passa a none, mantendo temperature=1, top_p=.95 e teto 8.000. A prévia
já usava none e não teve seu contrato alterado. A alteração é uma mitigação
a validar no próximo smoke, não prova de que low causou o timeout.

A mesma referência documenta stream SSE, stream_options e response_format
json_schema, sem demonstrar especificamente o schema deste Matilda em SSE.
Essa combinação não foi testada live. Mantém-se stream=false nesta correção:
SSE permitiria medir deltas, mas não reduz por si o trabalho total, não renova o
prazo e adicionaria outro protocolo/regras de conclusão e uso. O transporte HTTP
já lê blocos com limites; instrumentá-los não transforma a requisição em SSE.
Nenhuma resposta parcial é aceita. O [exemplo oficial](https://build.nvidia.com/nvidia/nemotron-3.5-super-vl-120b-a12b)
com stream=true não foi tratado como comprovação de JSON Schema + SSE para esta aula.

## Module privado de elaboração

nvidia_lesson concentra uma interface pequena: preparar o contrato do adapter e
expandir sua saída para LessonDraft. O schema compacto aninha slides e atividades
na seção; a IA escreve títulos, conceitos, blocos, notas, atividades, critérios,
objetivos semânticos e duração de cada seção. Seções devem somar exatamente os
50 minutos; o backend **não corrige** um total errado.

O servidor cria chaves locais e ambos os lados dos vínculos pela estrutura
aninhada. Divide os minutos inteiros de cada seção igualmente entre seus slides,
atribuindo o resto aos primeiros slides (25/2 = 13+12). A IA deve fornecer ao
menos um minuto por slide; não há atividades fora da duração da seção.
Objetivos são escolhas pedagógicas, portanto seus índices não são inventados
pelo servidor. O plano reutiliza blocos e speaker_notes escritos uma única vez;
notas não vazias são obrigatórias no contrato compacto. Não há texto pedagógico
pronto ou atribuição científica fabricada para completar uma resposta ausente.

A expansão passa pelo **LessonDraft original completo**, depois pela materialização
T09, LessonBundle, revisão congelada e autoridade científica existentes. Globais
3–8 seções, 4–12 slides, 1–4 atividades, objetivos válidos, duração e todos os
vínculos permanecem obrigatórios. EvidenceClaimBlock continua usando apenas IDs
autorizados; fontes/participantes e afirmações históricas são resolvidos pelo
servidor. IDs científicos desconhecidos, tempo errado, notas vazias, excesso de
slides e objetivos inválidos falham, nunca são reparados automaticamente.

Compactação é exclusiva do adapter NVIDIA. Gemini permanece com LessonDraft
original, sem fallback. A instrução genérica T09 agora manda seguir o schema do
adapter em vez de exigir chaves locais; versão da instrução studio-lesson-v2.
Metadados de transporte identificam lesson_contract=compact-v1. Documentos chegam
uma vez sem UUIDs/títulos administrativos, sugestões aceitas sem IDs de UI. O
schema omite somente títulos de anotação; o campo real title e todas as restrições
permanecem. Não há remoção de validações públicas nem alteração de SQLite.

A divisão uniforme do tempo dentro da seção é uma limitação pedagógica explícita:
o professor precisa conferir o ritmo e as notas. A qualidade docente não é
certificada por testes estruturais. O agrupamento escolhido pela IA continua
responsável pela coerência dos conteúdos, e nenhuma melhora de latência live foi
comprovada nesta sessão.

## Medição offline

Mesma preparação textual/revisão controlada na base e após a correção. Não é o
payload do smoke real, que usou artigo por DOI, nem medição de tokens NVIDIA.

| Métrica | Antes → depois |
|---|---:|
| Payload completo UTF-8 | 8.735 → 7.020 bytes (-19,63%) |
| JSON Schema UTF-8 | 6.011 → 3.885 bytes |
| Entradas declaradas em required | 37 → 28 |
| Material UTF-8 | 1.188 → 815 bytes |
| Instruções UTF-8 | 1.111 → 1.923 bytes |
| Estimativa conservadora | 9.759 → 8.044 |
| Saída exemplo controlado (6 slides) | 3.799 → 2.898 bytes (-23,72%) |

A instrução adicional explica o contrato compacto e suas obrigações; o saldo do
payload ainda diminui. A saída de exemplo é fixture de teste explicitamente
simulada, **nunca usada como resposta no smoke real lesson**. O teto 8.000 não foi
reduzido nem ampliado para mascarar falhas; conta raciocínio conforme uso upstream.
A estimativa continua bytes do payload completo +1.024, sem caracteres/4.
[Registro de números](nvidia-lesson-payload-comparison.json).

```sh
.venv/bin/python scripts/measure_studio_lesson_payload.py
```

## Smoke lesson isolado — somente após autorização

```sh
.venv/bin/python scripts/smoke_studio_nvidia_lesson.py --env-file /caminho/local/.env --allow-paid-nvidia
```

Opcional: --scenario rna. Sem flag, termina explicit_authorization_required antes
de carregar chave/iniciar o roteiro. Sem NVIDIA_API_KEY local, termina
nvidia_key_missing; não se deve compartilhar a chave. Supervisor de 100 s, prazo
backend de 75 s com reserva de 5 s, **uma única inferência lesson**, modelo fixo
nvidia/nemotron-3.5-super-vl-120b-a12b e endpoint hospedado fixo. Nenhuma segunda
chamada é permitida, inclusive em erro HTTP/schema ou correção. O contador reserva
uma tentativa; preflight pode consumir a reserva sem enviar HTTP.

Antes da preparação, um preflight exige fonte em cache com validade suficiente
para a janela de recuperação científica. Sem cache fresco, falha como
preparation_cache_unavailable, sem consulta bibliográfica nem inferência. O teste
com cache ausente bloqueia qualquer HTTP externo e confirma zero chamadas.

Preparação usa seleção pedagógica determinística identificada como
simulated-preparation, com material científico público e ciência real do cache.
Cria prévia e aprova objetivos/sugestões pelas rotas normais, com sessão/cookie e
snapshot/autoridade reais. Não injeta fixtures de ciência, revisão ou aula na
persistência. Somente após a revisão troca o provider para NVIDIA real na etapa
lesson. A resposta passa por todos os validadores e persistência normais.

O relatório exige geração, leitura idêntica persistida, replay idempotente HTTP200
sem inferência extra e Markdown. Inclui tempos/status, tokens/modelo efetivo se
houver conclusão, fases/limites/erros sanitizados, contagens e marca preparação
simulada/full_flow_proven=false. Não emite conteúdo, stderr, cookie ou chave.
Em erro interrompe e preserva o estado; não repete a geração automaticamente.
Este ensaio isolado **não comprova o fluxo inteiro com prévias reais na mesma
execução**. Nenhuma chamada live deste comando foi feita nesta correção.

## Verificação

Backend: **670 passed**, 9,56 s, incluindo Forensics, limites, retry/recuperação,
idempotência, timeout pré-header/durante corpo, truncamento/JSON incompleto,
LessonDraft inválido, persistência e Markdown. Contratos: **7/40/4**. TypeScript/
build aprovado (aviso Vite de chunk >500 kB permanece). **87 Playwright aprovados** nas execuções finais: integrado T13/Forensics 20
(24,5 s), revisão 19 (10,3 s), slides 14 (5,4 s), geração/operações 18 (9,5 s),
ponte 5 (4,3 s), exportação 11 (4,8 s). As falhas iniciais são registradas abaixo.

Revisões independentes: Standards **0 achados pendentes**, Spec **0**. Spec
reexecutou 50 testes do commit principal; ambos revisaram o incremento de cache.
O responsável executou o novo teste e a suíte backend completa final.
[Relatório por eixo](reviews/nvidia-lesson-timeout-code-review.md).

O primeiro E2E integrado passou 19/20: o mock BrowserProvider do cenário de falha
única ainda exigia um ID administrativo removido do payload. O identificador de
teste foi adaptado ao conteúdo recebido (somente harness, sem alterar frontend).
A reprodução isolada passou após a correção; o rerun completo passou **20/20**.

O primeiro harness de geração/operações passou 17/18; o caso de polling em
andamento falhou em route.fetch/response.json com `Response has been disposed`,
antes da leitura pelo mock do navegador. A reprodução isolada passou e o rerun
completo passou **18/18** sem alteração de produto ou frontend. Esse problema de
ciclo de vida do transporte do Playwright já estava registrado no diagnóstico
anterior; permanece uma limitação do harness, não uma prova de erro NVIDIA.
