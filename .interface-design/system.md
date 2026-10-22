# Matilda — caderno de evidências

## Intenção e domínio

Professores preparam uma aula entre outras tarefas, conferem o que a sustenta e
levam o material à sala. A experiência deve parecer um caderno editorial de
pesquisa: calma, verificável e legível. Domínio: contribuição, autoria coletiva,
artigo, evidência documental, conceito, revisão docente, plano e projeção.

Mundo de cor: papel marfim, tinta verde de biblioteca, grafite de anotações,
cobre de marcação editorial, verde pálido de fichas e branco de folhas.
Assinatura: proposta pedagógica sempre ligada à afirmação documental, aos
participantes e à fonte; a faixa de evidência reaparece na prévia, revisão,
dossiê, slide e plano. Rejeitamos métricas decorativas, gradientes e painéis de
cartões equivalentes; a tarefa e seu documento definem o peso de cada região.

## Sistema

- Tokens em `frontend/src/design-system.css`, importados também pelos harnesses.
- Papel de fundo `#f6f5ef`, folha `#fffdf7`, campo `#f1f2eb`.
- Tinta `#233e33`, texto secundário `#52665a`, metadados `#626e60`.
- Ação `#264f43`, hover `#163f31`; evidência/foco cobre `#97532e`.
- Erro `#852f26` sobre `#fff0ec`. Estado sempre acompanhado de texto.
- Tipos locais: Arial para operação e Georgia para títulos editoriais. Sem rede
  de fontes. Corpo 16/1.6; escala aproximada 1.25: 12, 14, 16, 20, 24, 32, 40.
- Grade de 4px; controles com pelo menos 44px de altura, raio 6px; documentos
  com 24px de padding desktop, 16px mobile e raio 12px.
- Profundidade: bordas discretas, superfície de folha; sombra apenas no slide.

## Padrões e hierarquia

- Uma ação principal por etapa; configuração → conferir → revisar → gerar → aula.
  A lista de etapas informa posição, sem fingir navegação ou aprovação.
- Cabeçalho serifado identifica o documento. Corpo sans facilita configuração.
- Material e trecho original usam `details/summary` nativos para não soterrar a
  proposta. Conteúdo integral continua no DOM e acessível por teclado.
- Evidências ficam abertas; cobre marca sua ligação documental. Nenhuma fonte,
  pesquisadora, participante ou limitação é editada pelo tema.
- Botões secundários usam folha e tinta; ações de salvar/avançar usam verde.
  Foco cobre de 3px, offset 4px; disabled com texto e instrução de desbloqueio.
- Projeção mantém 16:9 e notas fora do diálogo; corpo e fontes ampliam com o
  espaço do slide. Conteúdo extenso rola em vez de ser cortado.
- Sem novas animações; respeitar movimento reduzido e impressão sem chrome.

Checkpoint para alterações: intenção docente; tarefa como foco; paleta do
caderno; bordas como profundidade; papel/folha/campo como superfícies; serif para
documento e sans para operação; espaçamento de 4px. Aplicar aos componentes
existentes antes de criar abstrações.
