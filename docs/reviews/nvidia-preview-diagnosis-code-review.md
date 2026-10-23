# Revisão independente — diagnóstico da prévia NVIDIA (#31 / PR #32)

Base fixa: `d42432b6f3f50581b94707bcc6591d66c82a548a`, cabeça anterior do PR #32.
Diff revisado: `git diff d42432b...29b15a4`, mais a extração posterior da constante
TYPED_SCIENTIFIC_CODES, inspecionada pelo revisor Standards antes do fechamento.
Commit principal: `29b15a4`.

Agentes independentes, somente leitura, em branches/checkouts separados:
review/nvidia-standards e review/nvidia-spec. Standards consultou AGENTS, README,
arquitetura, contratos, método científico e baseline Fowler. Spec confrontou o
pedido de diagnóstico do usuário e a tarefa #31, sem assumir o JSON original.

## Standards

**0 achados pendentes.** A extração de TYPED_SCIENTIFIC_CODES resolve a sugestão
P3, preservando os mesmos códigos e comportamento nos dois ramos.

Nenhuma violação documentada identificada. A sugestão inicial era um possível
Duplicated Code, pois a lista de códigos reconhecidos estava repetida no caso de
ValidationError e PydanticCustomError. Foi tratada como heurística de manutenção,
sem bloqueio, e corrigida pela constante comum. Revisão estática; sem chamadas
externas nem reexecução de testes pelo revisor Standards.

## Spec

**0 achados abertos** no diff d42432b...29b15a4.

O schema condicional exige sugestões somente quando há cobertura. Enums e
exemplos de âncoras preservam as verificações independentes de contribuição,
evidência, conceito e literalidade. Os diagnósticos registram códigos, contagens
e resultados de validação sem incluir material docente, IDs ou resposta bruta.
O smoke mantém uma inferência por operação.

O revisor Spec reexecutou a suíte específica: **16 testes aprovados**, sem chamadas
reais. A investigação permanece parcialmente limitada pela evidência disponível:
o JSON original não foi recuperado, portanto sua causa exata e quantidade de
sugestões continuam desconhecidas. A documentação distingue essa limitação do
defeito comprovado e corrigido no contrato de cobertura; não apresenta reprodução
sintética como sucesso ou diagnóstico definitivo do smoke real.

## Verificação consolidada

- Backend após a correção Standards: **635 passed**, 8,57 s.
- Contratos científicos/Studio/LessonBundle: **7 / 40 / 4**.
- TypeScript/build aprovado; aviso Vite de chunk acima de 500 kB.
- Playwright: **87 casos aprovados**, com uma falha transitória inicial no harness
  de geração documentada, seguida de reprodução isolada verde e rerun 18/18.
- Zero novas inferências NVIDIA/Gemini nesta investigação.
- Relatório: [diagnóstico e limite da evidência](../nvidia-preview-diagnosis.md).

Standards: **1 sugestão P3 resolvida, 0 violações e 0 pendências**; Spec:
**0 achados técnicos abertos**, com diagnóstico exato live limitado pela ausência
do JSON original. Maior gravidade inicial: P3 em Standards; nenhuma em Spec.
