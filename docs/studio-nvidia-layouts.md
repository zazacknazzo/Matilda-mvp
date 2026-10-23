# NVIDIA: slides válidos por construção (#31 / PR #32)

Sexta etapa sobre `eda296952c5a397a843ff512d6488fcdf377f1c1`.
Responsável: Codex do Mac, `feat/nvidia-studio`, checkout isolado
`.runtime/nvidia-json-worktree`. Nenhuma inferência real nesta implementação;
sem merge #32/#30, alteração de main ou do trabalho do Agente 3.

## Evidência real e reprodução

O quinto smoke, executado na base com autorização de uma chamada, recebeu
NVIDIA HTTP200 em 6,706s, `stop`, 1.018 tokens de entrada / 492 de saída.
Matilda respondeu502/invalid_generation, `lesson_slide_layout_invalid`,
provider/validation. SQLite preservou revisão e50min, sem publicar aula.
Não foi retida a resposta: não sabemos qual layout/slide falhou nem se o
conteúdo seria suficientemente profundo. Não atribuímos a falha à contagem
baixa de tokens, ao transporte, ao JSON ou a uma regra de layout específica.

Reprodução controlada histórica: PROCESS com apenas text era rejeitado pelo
model_validator de CompactSlide, mas **aceito pelo JSON Schema transmitido**.
O primeiro tracer novo, usando jsonschema Draft202012Validator independente,
ficou vermelho (`assert not ...is_valid(...)`, observado True). Depois do novo
contrato passou. O teste não reproduz o conteúdo descartado do smoke; reproduz
a classe arquitetural que permitia layout e conteúdo incompatíveis.

Hipóteses separadas: (1) enum e blocos independentes permitem a incompatibilidade
— confirmada; (2) o hospedado pode aplicar só parte do schema — ainda pendente;
(3) pouco conteúdo pode ser superficial mesmo se estruturalmente válido —
investigado separadamente, sem certificar semântica por tokens/tamanho.

## Decisão e interface

`compact-v4-layouts` mantém a autoridade aprovada do v3 e os pesos/alocação do
v2. A interface do módulo continua `contract(request)` e `expand(...)`.
`nvidia_slides` concentra as variantes e a conversão; `nvidia_pedagogy` concentra
a avaliação explícita de elaboração. A complexidade fica dentro do adapter
NVIDIA; Gemini e os chamadores não aprendem uma nova interface.

Alternativas avaliadas:

- União de seis slides inteiros: válida, mas repete título/subtítulo/notas em
  cada ramo e aumenta o schema.
- **Conteúdo tipado aninhado, escolhido:** campos comuns uma vez, e
  `content.layout` seleciona a variante com os campos próprios obrigatórios.
- Seis listas por layout: evita união, mas perde a ordem livre dos slides ou
  exige outro protocolo para reconstruí-la. Não foi adotada.

```json
{
  "title": "Reconhecimento e clivagem",
  "content": {
    "layout": "PROCESS",
    "steps": ["O RNA reconhece a sequência.", "A proteína cliva o DNA."]
  },
  "speaker_notes": "Peça que os alunos expliquem a sequência e justifiquem o papel de cada molécula; compare as respostas com o material original."
}
```

| content.layout | Campo obrigatório próprio | ContentBlock público |
|---|---|---|
| TITLE | nenhum além de layout; introduction opcional | text quando fornecido; caso contrário lista vazia |
| CONCEPT | text não vazio; bullets opcionais, até4 | text e, se presentes, bullets |
| PROCESS | steps não vazios,2–6 | steps |
| QUESTION | question não vazia | question |
| SUMMARY | synthesis não vazia | text |
| SCIENTIST_SPOTLIGHT | evidence_id literal autorizado | evidence_claim |

Todos os modelos proíbem campos adicionais e usam tipos estritos. Título,
subtítulo opcional e notas ficam no slide. `evidence_ids` opcionais (até4)
acrescentam claims aprovados sem alterar o layout. CONCEPT tem no máximo dois
blocos próprios; com quatro claims permanece no teto público de seis blocos.

O discriminador local é `content.layout`. Cada ramo exige seu literal e seus
campos: PROCESS não admite question/text nem omite steps; QUESTION não admite
steps. Não há layout independente do conteúdo, substituição por outro layout,
conversão de um texto genérico em etapas ou fallback para a representação v3.

A conversão copia literalmente campos pedagógicos do modelo para text, bullets,
steps ou question e empacota IDs aprovados em evidence_claim. Só os metadados e
snapshots canônicos existentes fornecem afirmação histórica, fonte e autoria.
Sem evidências aprovadas, SpotlightContent é removido por inteiro do schema,
o ramo correspondente deixa de existir e evidence_ids tem maxItems=0.
A conferência local rejeita claims não autorizados mesmo se o endpoint ignorar
o schema; não reescreve identificadores.

A alocação por pesos não mudou: um minuto por slide, restante proporcional por
maiores restos e desempate na ordem; divisão inteira dentro de cada seção.
3–8seções,4–12slides,1–4atividades e os índices de objetivos continuam obrigatórios.
O limite combinado de600caracteres visíveis é conferido localmente. O validador
público continua conferindo conteúdo/layout, tempo, vínculos, ciência e revisão.

## Compatibilidade investigada antes da escolha

Consultas em23/10/2026, sem fazer inferência exploratória:

- A [referência do modelo hospedado](https://docs.api.nvidia.com/nim/reference/nvidia-nemotron-3_5-super-vl-120b-a12b-infer)
  documenta response_format com JSON Schema. Ela não publica uma matriz de
  suporte para $defs, $ref, oneOf, anyOf ou discriminator. Os smokes anteriores
  com HTTP200 não provam que cada keyword tenha sido aplicada.
- A [documentação NVIDIA de structured generation para containers1.15](https://docs.nvidia.com/nim/large-language-models/1.15.0/structured-generation.html)
  descreve schemas e diferenças entre backends. Isso é contexto de engenharia,
  não comprovação de qual backend/versão serve integrate.api.nvidia.com.
  Não foram adicionados guided_json, parâmetros de containers ou fallback.
- [Pydantic: discriminated unions](https://docs.pydantic.dev/latest/concepts/unions/#discriminated-unions)
  fundamenta a seleção local do ramo. O discriminator OpenAPI não é necessário
  para os validadores JSON Schema reconhecerem os ramos exclusivos.

O schema enviado conserva $defs/$ref locais, mas troca o oneOf da união local
por anyOf e remove a anotação discriminator. Os ramos são exclusivos por
layout literal e additionalProperties=false; qualquer instância pertence a no
máximo um ramo. Nesse caso a troca preserva o conjunto de instâncias aceitas,
sem depender de uma extensão OpenAPI. Não é um transformador genérico para
uniões sobrepostas: o teste fixa a exclusividade destes seis ramos.

Validador independente e Pydantic exercitam os mesmos casos válidos/inválidos;
o fixture versionado fixa o schema transmitido e todas as referências resolvem
localmente. **Não se declara suporte live comprovado para anyOf/$ref ou para
este schema completo.** Compilação, aplicação e latência reais exigem novo smoke
autorizado. Não se remove uma restrição só para obter HTTP200.

Medição offline com a preparação textual controlada do script existente:
payload8.700bytes, schema4.126bytes, estimativa conservadora9.724/12.000tokens;
saída de exemplo2.809bytes. Não são tokens NVIDIA ou uma resposta do smoke real.
A reserva de1.024bytes e os limites12.000/8.000/128KiB permanecem. Materiais maiores
continuam podendo falhar explicitamente antes da rede, sem truncamento.

## Elaboração pedagógica, separada da validade de layout

492tokens não provam nem refutam adequação a50min. O conteúdo real não está
disponível. Não foi criado teto mínimo de tokens nem preenchimento automático.

Pisos privados de elaboração, explícitos e experimentais:

- Notas docentes:80–1500caracteres por slide.
- Atividade: enunciado de ao menos20caracteres, orientação de40 e cada critério
  de avaliação de20. Os campos são escritos pelo modelo.
- Ao menos80caracteres de texto/tópicos/etapas conceituais no conjunto de
  CONCEPT/PROCESS; uma aula de títulos não atende.
- Cada objetivo aprovado deve estar ligado a seção com CONCEPT/PROCESS e a
  uma atividade. Índices inexistentes/duplicados continuam rejeitados antes.

São pisos contra ausências óbvias, **não rubrica docente validada**. Tamanho,
repetição de palavras e vínculo por índice não comprovam explicação correta,
nota instrutiva ou alinhamento semântico. Os valores podem precisar de revisão
empírica; não se afirma que bastem para50min. As validações públicas não mudaram.

O evento sanitizado `nvidia_lesson_quality`, capturado pelo Recorder/smoke,
mostra contagens, cobertura estrutural e teacher_review_required=true. Ausência
estrutural de conceito/cobertura falha como lesson_pedagogy_insufficient, antes
de publicar aula. Pisos de campos falham como lesson_schema_invalid/Pydantic.
Nenhum texto, ID científico, objetivo livre ou mensagem de exceção entra no log.

Pontos sempre sujeitos à revisão docente: profundidade conceitual, uso instrutivo
das notas, aplicabilidade das atividades, objetivos efetivamente trabalhados,
relevância científica e ritmo. As referências continuam restritas ao snapshot
canônico; relevância para o argumento livre não é certificada por JSON.

Alocações de mais de12min por slide, menos de3min em seção com atividade,
notas repetidas ou evidências aprovadas não utilizadas geram pontos adicionais
de revisão. Não se corrige o ritmo automaticamente nem se reprova uma intenção
docente só por essa heurística. Atividades continuam incluídas nos minutos da seção.

Tracers vermelhos adicionais: uma aula só de TITLE retornava201; passou a502 sem
publicação. Notas "Explique." e atividades "Ok." eram aceitas; agora rejeitadas.
Testes também verificam objetivos sem ensino/avaliação e conceito mínimo ausente,
mais um relatório positivo sem conteúdo sensível. Nenhum teste declara uma aula
pedagogicamente certificada.

## Validação e limitações

Resultados estruturados em [nvidia-layouts-validation.json](nvidia-layouts-validation.json).
A matriz positiva mantém48combinações3–8seções/4–12slides/1ou4atividades, com/sem
evidências, exercitando os seis layouts. Cada uma passa NVIDIA MockTransport,
LessonDraft, LessonBundle50min, SQLite real, consulta, replay200 sem inferência
extra e Markdown. A representação pública salva permanece legível.

Primeiro backend completo:89falhas/863passaram. Harnesses ainda escreviam
content_blocks v3 antes da expansão; o conversor de doubles também encontrava
CONCEPT/SUMMARY com bullets nas fixtures públicas. Foram migrados para campos
v4 com o mesmo texto controlado; as asserções de falha/publicação/cientificidade
não foram relaxadas.103regressões afetadas passaram após a migração. O primeiro
focado teve195passaram/1falha: uma nota de teste JSON escapado tinha menos de80
caracteres; o material controlado foi elaborado mantendo os caracteres especiais
e a asserção de preservação literal. Tipos/contratos públicos e frontend não mudaram.

## Próximo smoke — não executar nesta tarefa

Somente após nova autorização explícita, a partir da raiz do workspace:

```sh
.venv/bin/python .runtime/nvidia-json-worktree/scripts/smoke_studio_nvidia_lesson.py \
  --env-file .env --allow-paid-nvidia
```

Confirmar head publicado e checkout limpo, cache datado/autoridade e credencial
carregada sem exibi-la. Uma chamada NVIDIA,100s totais, backend75s/reserva5s,
sem retry pago. Preparação simulada identificada; exigir contrato v4, seis layouts
quando escolhidos, LessonBundle50min, evidências, SQLite, leitura, replay e Markdown.
Conferir nvidia_lesson_quality e seus pontos docentes. Nem um futuro sucesso
isolado comprovaria prévias reais na mesma execução: full_flow_proven=false.
