# NVIDIA + T13 atualizada — validação da sincronização

22/10/2026. Continuação da Issue #31 e do PR #32, que permanece Draft.

## Versões e integração

O GitHub foi consultado novamente antes do merge e antes da publicação:

- T13 / PR #30: `3917e2bb0c2171260ae09187ca69a92122b5884b`, Draft, base `main`.
- PR #34: merged na T13, merge commit `3917e2b`; nenhuma nova integração desse PR.
- NVIDIA antes da sincronização: `25b3032daccf724b06b97f81a8455c521605fb86`.
- Merge normal: `68ad33e5cdc9fb3d592ee097238aa2ef8b559f6f`, pais NVIDIA + T13.
- Código validado após a correção de foco: `d0f7851`.

Não houve rebase, force-push ou conflito textual. O merge automático de
`README.md` e `StudioSetup.tsx` conserva configuração/avisos NVIDIA e os
refinamentos UI/UX. Backend, scripts, `.env.example` e tipos públicos são
idênticos ao head NVIDIA anterior. A UI da T13 foi preservada; a única mudança
visual adicional é o título de etapa agora visível, descrito abaixo.

O trabalho ocorreu exclusivamente em `/private/tmp/matilda-nvidia`. O checkout
principal continuou detached em `394d109`, com seu arquivo não rastreado
`docs/decomposicao-mvp-v4.md` preservado. Outros processos Codex identificados
tinham como diretório o checkout principal; nenhum trabalho foi feito nele.

## P2 de foco comprovado e corrigido

As hipóteses verificadas foram título recortado, mudança de geometria ao perder
foco e perda de foco durante navegação. No navegador, a abertura da prévia
transferia corretamente o foco para `h2.studio-view-label`, mas o CSS o mantinha
em 1 × 1 px e `clip-path: inset(50%)`. O usuário de teclado perdia o indicador
visual de foco. `toBeVisible()` sozinho não detecta esse recorte.

O teste determinístico falhou antes da correção: esperava `clip-path: none`,
recebeu `inset(50%)`. A correção torna o título existente permanentemente
visível com os tokens do tema. O foco programático continua no mesmo elemento;
o título não muda de geometria ao perder foco. O teste exige foco no título,
ausência de recorte, altura legível e posição invariável da próxima ação após
blur, em 1440, 768 e 375 px. As três variantes passaram.

## Verificações da versão combinada

Todos os provedores externos foram controlados. Nenhuma inferência NVIDIA real
foi executada nesta sincronização.

| Verificação | Resultado |
|---|---|
| Backend completo | 670 aprovados; 10,29 s; 2 avisos de depreciação existentes |
| Contrato científico | 7 fixtures aprovadas |
| Contrato Studio HTTP/Pydantic/TypeScript | 40 payloads aprovados |
| Tipos LessonBundle | 4 fixtures aprovadas |
| TypeScript + Vite build | Aprovados; aviso de chunk JS de 520,42 kB |
| Playwright integrado + Forensics + UI/UX | 23 aprovados; 25,0 s |
| Playwright revisão | 19 aprovados; 7,3 s |
| Playwright slides/apresentação | 14 aprovados; 4,1 s |
| Playwright geração/recuperação/idempotência | 18 aprovados; 8,6 s |
| Playwright ponte Forensics/Studio | 5 aprovados; 2,8 s |
| Playwright exportação | 11 aprovados; 3,9 s |
| Revisões independentes | Standards 0; Spec 0; somente leitura |
| Smoke lesson sem autorização | `explicit_authorization_required`, exit 2, nenhuma chamada |

Total: **90 testes Playwright**, além das três execuções focadas da regressão de
foco. As suítes completas passaram na primeira execução da versão corrigida.
A primeira tentativa de iniciar o teste de reprodução foi bloqueada pelo sandbox
na porta local; o teste foi então executado com permissão para servidores locais.
Screenshots gerais regravados pela suíte não foram incluídos na alteração.

Os comandos são os do README, com os seis arquivos `playwright.*.config.ts`
para Studio, review, lesson, generation, bridge e export. A suíte Studio já
inclui `investigation.spec.ts`, a regressão Forensics. Veja também a
[revisão independente por eixo](reviews/nvidia-t13-sync-code-review.md).

## Gate real e comando no Mac

A correção de timeout NVIDIA foi preservada: janela do provedor de até 70 s
dentro dos 75 s de geração, com reserva de 5 s para persistência; contrato
LessonDraft privado compacto, `reasoning_effort=none`, JSON Schema e validações
científicas integrais. O diagnóstico e as limitações continuam em
[timeout de lesson](studio-nvidia-lesson-timeout.md).

Ainda falta comprovar uma aula completa com a NVIDIA real. O sucesso das prévias
no smoke anterior não comprova a latência da geração depois dessas mudanças.
Não houve novo resultado real de lesson, persistência ou exportação nesta tarefa.
O PR #32 não deve ser integrado até esse gate ser satisfeito.

Somente após nova autorização explícita, na versão publicada no head do PR #32:

```sh
.venv/bin/python scripts/smoke_studio_nvidia_lesson.py --env-file .env --allow-paid-nvidia
```

Para usar diretamente o worktree validado neste Mac, com o ambiente local do
checkout principal, sem trocar a branch que outras sessões usam:

```sh
/Users/isaacbahnzz/MVP-Matilda/Matilda-mvp/.venv/bin/python /private/tmp/matilda-nvidia/scripts/smoke_studio_nvidia_lesson.py --env-file /Users/isaacbahnzz/MVP-Matilda/Matilda-mvp/.env --allow-paid-nvidia
```

O smoke exige `NVIDIA_API_KEY` local, fixa o modelo autorizado, usa preparação
explicitamente simulada e ciência canônica real em cache, admite **uma única
inferência real**, mantém deadlines/idempotência e verifica validação, gravação,
leitura e Markdown. O teto do supervisor é 100 s. Não faz retry pago automático
nem fallback. O relatório sanitizado distingue preparação simulada de geração
real; esse teste isolado não comprova o fluxo completo real.

Riscos restantes: latência real da aula ainda desconhecida; distribuição uniforme
de duração entre slides da mesma seção requer avaliação pedagógica; avisos de
dependências/build existentes; validação humana com leitor de tela e projetor
físico não realizada. Nenhum merge do PR #32 ou #30 foi executado.
