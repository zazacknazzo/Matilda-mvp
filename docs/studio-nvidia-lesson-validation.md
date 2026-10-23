# NVIDIA lesson: validação temporal (#31 / PR #32)

Base investigada: `8051fbd4c55848e637acfe18c3780a035eada4f1`.
Nenhuma inferência real foi executada nesta correção; nenhum merge #32/#30.

## Evidência real informada

O usuário informou preparação simulada HTTP201 válida, revisão HTTP200 e NVIDIA
lesson HTTP200 em aproximadamente 11,47 s: 3.097 bytes, 849 tokens de entrada e
743 de saída, reasoning_effort=none, lesson_contract=compact-v1, phase=validation,
outcome=invalid_lesson_draft. Matilda retornou HTTP502/invalid_generation, uma
chamada externa sem retry. O timeout anterior não ocorreu nesse ensaio.

## Causa reproduzida e limite da conclusão

Na base, `_parse()` valida envelope/uso/JSON antes de chamar `expand()` com a
configuração aprovada. `expand()` valida CompactLessonDraft, exige soma exata dos
minutos e constrói LessonDraft. O adapter classificava qualquer ValueError/KeyError
não Pydantic desse bloco como invalid_lesson_draft. Isso ocultava a causa.

| Condição na base | Resultado reproduzido por MockTransport |
|---|---|
| Seções 11+25+15, duração aprovada 50 | ValueError / invalid_lesson_draft, phase=validation |
| Campo ausente/tipo inválido/notas vazias/limites agregados ou slides sem minutos mínimos | ValidationError / pydantic_validation |
| configuration ausente ou sem duration_minutes | KeyError / invalid_lesson_draft |
| Duração configurada como string, nula, bool ou float diferente do total | comparação rejeita / invalid_lesson_draft; float50 podia comparar igual |
| Falha ValueError/KeyError ao expandir | invalid_lesson_draft; reproduzida com falha injetada em LessonDraft |
| ValidationError no LessonDraft expandido | pydantic_validation; não há caminho conhecido com CompactLessonDraft válido e configuração normal |
| Saída expandida maior que 128 KiB | response_too_large, preservado pelo handler; não invalid_lesson_draft |

Essas são as condições do handler da base. Erros anteriores têm outros outcomes:
invalid_response, invalid_json, bloqueio/truncamento, limites de tokens etc.
TypeError da configuração não era classificado como invalid_lesson_draft no adapter.
Falhas científicas/objetivos/layouts no materializador ocorrem depois do adapter,
portanto também não explicam esse outcome no log NVIDIA.

A causa de projeto reproduzida é exigir que o modelo satisfaça uma igualdade
aritmética global, apesar de as seções serem individualmente válidas. A mutação
mínima 10→11 reproduz exatamente HTTP200 NVIDIA + falha local de validação.
No fluxo normal, GenerationService fornece configuration/duration_minutes da
revisão persistida; soma incorreta é a principal hipótese compatível com o log.
**Não foi recebida a saída real; não é possível afirmar que ela somava 51 nem
excluir categoricamente um defeito interno de expansão/configuração.**

Hipóteses classificadas antes da correção: soma temporal; configuração ausente;
defeito na expansão; erro estrutural Pydantic (menos compatível com o outcome).
Não se atribui a falha a latência, NVIDIA, tokenização ou conteúdo científico.

## Reprodução e ciclos vermelho/verde

Na base, harness temporário usando `NVIDIAProvider.complete()` + MockTransport
reproduziu cada linha principal da tabela; nenhum HTTP externo. Os testes de
subcódigos ficaram **6 failed**, todos por ausência de failure_code. O commit
`0ac4f20` adiciona diagnósticos ao compact-v1 e mantém o teste específico 51/50:
**6 passed**. É uma reprodução histórica executável sem inferência:

```sh
.venv/bin/python -m pytest backend/tests/test_nvidia_lesson_validation.py -q
```

Execute esse comando no commit de diagnóstico para observar o contrato antigo.
No head, o teste correspondente exige rejeição explícita do contrato antigo,
com total 50 ou 51; não existe aceitação legada ou reparo silencioso.

O próximo teste exigiu pesos/schema novo no seam do provedor: ficou vermelho
porque o schema ainda expunha duration_minutes. Passou após compact-v2-weighted.
A suíte final cruza MockTransport, serviço, LessonDraft, LessonBundle e SQLite;
não testa apenas um algoritmo isolado ou duplica sua fórmula no valor esperado.

## Contrato privado compact-v2-weighted

Cada seção exige `time_weight`: inteiro estrito entre 1 e 1000. Booleanos, strings,
frações, zero, negativos e valores acima de 1000 são inválidos. Não há
`duration_minutes` na saída NVIDIA. Campos desconhecidos continuam proibidos.
Gemini conserva LessonDraft e a revisão persistida conserva a duração aprovada.

O servidor realiza a alocação como propriedade explícita do contrato:

1. Reserva um minuto por slide em sua seção. Se o total aprovado for menor que
   esse mínimo, rejeita o orçamento; não remove seções, slides ou atividades.
2. Distribui o tempo restante proporcionalmente aos pesos. Usa divisão inteira
   e maiores restos; empates seguem a ordem original das seções. Sem floats.
3. Divide os minutos da seção por seus slides, com os minutos de resto nos
   primeiros slides. As atividades já estão incluídas no tempo da seção.

Exemplos independentes, todos com 50 minutos:

| Slides por seção | Pesos | Minutos resultantes |
|---|---|---|
| 1/2/1 | 1/1/1 | 17/17/16; slides 17/9/8/16 |
| 1/1/1/1 | 1/2/3/4 | 6/10/15/19 |
| 2/1/3/1/1 | 1/1/1/1/1 | 11/10/11/9/9 |
| 1/1/10 | 1000/1/1 | 39/1/10, mínimo por slide preservado |

O peso expressa **tempo adicional** após os mínimos, não uma proporção exata do
total final. A ordem só decide empates de arredondamento. O modelo escolhe a
estrutura, intenção pedagógica e pesos; o servidor só constrói tempos/vínculos.
Pesos extremos podem produzir uma seção de um minuto: estruturalmente válido,
mas ritmo e qualidade continuam exigindo avaliação docente.

Permanecem 3–8 seções, 4–12 slides e 1–4 atividades. Notas docentes não vazias,
blocos, atividades, orientação, critérios e índices semânticos são fornecidos
pelo modelo. Nada é gerado pelo servidor para completar pedagogia ausente.
O teste de ausência de evidências autoriza uma aula sem referências após rejeitar
todas as sugestões; não inventa claims/participantes. IDs não autorizados
continuam falhando nos validadores existentes.

LessonDraft completo e LessonBundle continuam validando estrutura, layouts,
conteúdo visível, objetivos, vínculos, tempos, revisão e autoridade científica.
A expansão também permanece limitada a 128 KiB. Nenhuma mudança em contratos
públicos/Pydantic compartilhado/TS, ciência, SQLite, Gemini ou componentes UI.

## Diagnósticos sanitizados

`nvidia_attempt` identifica lesson_contract=compact-v2-weighted. Os novos códigos
são constantes, sem mensagens de exceção, inputs/paths Pydantic, resposta bruta,
material docente, fontes privadas, cookies ou credenciais:

| failure_code | Significado |
|---|---|
| lesson_schema_invalid | Pydantic do contrato privado, incluindo pesos/conteúdo/contagens |
| lesson_configuration_missing | Configuração ou duração ausente |
| lesson_configuration_invalid | Forma/tipo/faixa de duração inválidos (10–120 inteiros) |
| lesson_time_budget_infeasible | Minutos aprovados insuficientes para mínimo de um por slide |
| lesson_expansion_invalid | Falha posterior ao parsing privado na expansão para LessonDraft |
| lesson_expanded_response_too_large | LessonDraft expandido ultrapassa 128 KiB |

`lesson_duration_mismatch` existe apenas no commit de diagnóstico compact-v1,
com approved_minutes/section_minutes; o novo contrato elimina essa condição.
Orçamento inviável registra somente approved_minutes/minimum_minutes inteiros.
Erro estrutural mantém outcome=pydantic_validation; expansão/configuração/orçamento
usam invalid_lesson_draft com subcódigo; excesso mantém response_too_large.
Os envelopes públicos e políticas comuns de erro/retry não mudam.

## Validação

- Backend: **716 passed**, 9,49 s; inclui contratos, Forensics, Gemini controlado,
  revisão persistida, limites, transporte, idempotência, consulta e Markdown.
- Contratos: **40 HTTP / 7 científicos / 4 aulas** aprovados.
- TypeScript/build aprovado; avisos existentes de dependências e chunk 520,42 kB.
- Cobertura nova: 50 minutos/3/4/5/8 seções, 4–12 slides, mínimos,
  arredondamento/desempate, pesos iguais/diferentes/extremos/inválidos, contagens,
  campos pedagógicos ausentes, expansão/bytes, evidências ausentes/não autorizadas.
- **90 Playwright passaram**: integrado T13/Forensics/UI23 (23,4 s), revisão19
  (6,7 s), slides14 (4,5 s), geração/operações18 (8,6 s), ponte5 (3,0 s),
  exportação11 (3,8 s). O sandbox inicialmente bloqueou bind nas portas locais; as
  execuções com a permissão necessária passaram sem falha funcional.
- Revisões independentes: **Standards0 / Spec0**, cada revisor reexecutou **57
  testes focados**. [Relatórios por eixo](reviews/nvidia-lesson-validation-code-review.md).
- Diff confirmado sem mudanças em schemas públicos, frontend/src, Gemini,
  serviço de geração, persistência, ciência ou política de deadlines/retry.

## Próximo smoke — somente após nova autorização

```sh
.venv/bin/python scripts/smoke_studio_nvidia_lesson.py --env-file /caminho/local/.env --allow-paid-nvidia
```

Execute no checkout atualizado de feat/nvidia-studio. O smoke isolado mantém teto
**uma chamada NVIDIA / 100 s totais**, backend75 s/reserva5 s, none/stream=false,
limites 12.000/8.000 e cache científico obrigatório. Sem retry pago. Nenhum prazo
foi aumentado nem houve otimização de latência nesta tarefa.

Preparação pedagógica é simulada e identificada; revisão/sessão/ciência são reais.
Aula exige validação, referências autorizadas, persistência, replay sem inferência
e Markdown. Relatório identifica o contrato novo, subcódigos e, em sucesso, somas
de minutos aprovados/seções/slides. full_flow_proven=false permanece explícito.
O comando **sem** --allow-paid-nvidia foi executado e recusou com
explicit_authorization_required/exit2 antes de ler credenciais ou iniciar rede.
O smoke com MockTransport passou e casos inválidos comprovaram uma única chamada.

Gate real de geração completa permanece pendente; qualidade pedagógica não é
certificada por testes estruturais. Não fazer merge de #32 nem #30 nesta tarefa.
