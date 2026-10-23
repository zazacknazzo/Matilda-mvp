# Revisão NVIDIA lesson: validação temporal (#31 / PR #32)

Base fixa: `8051fbd4c55848e637acfe18c3780a035eada4f1`.
Head de implementação: `b8e91e7`.
Diff: `git diff 8051fbd4c55848e637acfe18c3780a035eada4f1...b8e91e7`.

Commits:

- `0ac4f20` — distinguish NVIDIA lesson validation failures.
- `b8e91e7` — allocate NVIDIA lesson time from pedagogical weights.

Revisores independentes Standards/Spec, somente leitura, em branches/checkouts
`review/nvidia-validation-standards` e `review/nvidia-validation-spec`.
Nenhum revisor editou contratos ou implementação. Sem inferências reais.
Especificação: pedido do usuário e proposta registrada na Issue #31,
[comentário de escopo](https://github.com/zazacknazzo/Matilda-mvp/issues/31#issuecomment-6354872549).

## Standards

**0 achados** na comparação `8051fbd4...b8e91e7`.

Não identifiquei violações documentadas nem smells relevantes nos hunks alterados.
Consultei AGENTS.md, README, arquitetura, instruções de issue/domain, PRD v4 e
`docs/studio-contracts.md`.

A alocação permanece encapsulada no adaptador NVIDIA; contratos públicos, Gemini
e autoridade científica são preservados. Os diagnósticos usam códigos constantes
e métricas numéricas, sem incorporar conteúdo ou mensagens das exceções. O
contrato antigo é rejeitado explicitamente.

Validação independente: **57 testes passaram**, cobrindo contrato compacto,
diagnósticos e smoke isolado com MockTransport. Checkout permaneceu limpo;
nenhuma inferência real ou operação GitHub.

Limitações: aviso de depreciação existente Starlette/HTTPX. Esta revisão não
certifica inferência real nem qualidade pedagógica; esses gates continuam
registrados na documentação.

## Spec

**0 achados** no diff `8051fbd4...b8e91e7`.

A implementação atende ao escopo solicitado:

- Separa estrutura Pydantic, configuração, orçamento temporal e expansão com
  códigos sanitizados.
- O contrato privado compact-v2-weighted produz tempos inteiros determinísticos,
  preservando o total aprovado, mínimo por slide, ordem e conteúdo do modelo.
- Rejeita payloads legados sem reparação silenciosa.
- Preserva contratos públicos, ciência, revisão, Gemini, UI e deadlines.
- Mantém o smoke isolado limitado a uma chamada NVIDIA.
- Documenta corretamente a soma incorreta como causa reproduzida e hipótese
  principal do incidente, sem alegar conhecimento da resposta real.

Validação independente offline: **57 passed** nas suítes de contrato compacto,
diagnósticos e smoke isolado. Nenhuma inferência real executada.

Os resultados finais dos gates amplos e a atualização do PR seguem sob
responsabilidade do agente principal.

Standards: 0 achados, nenhum problema pendente nesse eixo. Spec: 0 achados,
nenhum problema pendente nesse eixo.
