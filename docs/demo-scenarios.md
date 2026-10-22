# Demonstração

## Cenário 1 — CRISPR

DOI: `10.1126/science.1231143` — Cong e colaboradores, 2013.

1. Selecionar Edição genômica na página inicial.
2. Conferir título, autores, origem, data do cache e conceitos.
3. Clicar em Investigar contribuições femininas.
4. Abrir Cas9 programável guiada por dois RNAs.
5. Identificar Doudna e Charpentier com todos os coautores preservados.
6. Conferir a citação identificada do artigo de 2012 e abrir o DOI da evidência.
7. Comparar Bibliografia e Contribuições; usar Lista para ler as relações.
8. Exportar o dossiê.

## Cenário 2 — RNA

DOI: `10.1056/NEJMoa2034577` — Polack e colaboradores, 2020.

1. Selecionar Vacinas de RNA.
2. Investigar e selecionar uma das duas contribuições de Karikó.
3. Conferir fontes de 2005 e 2008, autorias coletivas e comparação bibliográfica.
4. Explicar que uma relação temática não estabelece influência histórica direta.
5. Demonstrar a navegação por abas no celular.

## Estado vazio e limites

DOI: `10.1038/171737a0`. O registro real de DNA é recuperado, mas não há
correspondência com os conceitos específicos do catálogo atual. A aplicação
informa ausência de cobertura, sem concluir inexistência de contribuições.

DOI sem resumo: `10.1038/nature09886`. A aplicação usa título e metadados e
informa a limitação. DOI inválido: `não-é-doi`, com erro compreensível.

Os dez snapshots permitem repetir a demonstração com cache identificado.
Para testar recuperação ao vivo use outro DOI válido ou `MATILDA_CACHE_TTL=0`.
Se a API falhar, cache anterior será sinalizado; sem cache haverá erro controlado.
Não confundir uma demonstração com cache com validação atual da API.

## Conferência humana antes da apresentação

Ler as seis fontes primárias, verificar os links no equipamento da apresentação,
confirmar o contraste e a legibilidade no projetor, ensaiar o tempo e testar a
navegação por teclado. Os testes automatizados não substituem esses passos.


## Studio integrado — roteiro T13

Começar pela versão candidata do PR T13, no mesmo navegador/sessão. Antes do
ensaio live, obter autorização específica para uso Gemini e confirmar quota,
modelo, API, cookie, SQLite persistente e proxy. Em ambiente local, anunciar essa
condição; não anunciar HTTPS/deploy não verificado. Nunca executar o servidor
`studio_e2e_app` de testes como demonstração de produção.

1. CRISPR: investigar `10.1126/science.1231143` no Forensics, conferir os dados
   reais/cache e clicar **Transformar em aula**. Confirmar investigação, nível e
   duração 50 minutos. Criar prévia com Gemini real autorizado.
2. Abrir revisão, explorar descoberta, conferir DOI, afirmação, participantes e
   limites. Editar somente a proposta pedagógica, voltar ao editor, aceitar uma
   sugestão, rejeitar as demais e aprovar objetivos. Salvar.
3. Gerar com Gemini real. Conferir metadados/modelo, soma de 50 minutos, avaliação,
   plano e fontes. Abrir aula, percorrer slides por teclado, abrir/fechar dossiê
   conservando slide, apresentar sem notas projetadas, sair com Escape.
4. Baixar Markdown e conferir as mesmas fontes; imprimir plano/salvar PDF no
   navegador do pitch, conferir quebras, notas e referências. Recarregar URL da
   aula e anunciar **aula recuperada**, com data/modelo reais.
5. RNA: iniciar Studio por DOI `10.1056/NEJMoa2034577`, 50 minutos; repetir
   revisão/geração/entrega/exportação. Conferir Karikó, Weissman e demais
   participantes documentados, sem inferir influência de relação temática.
6. Sem cobertura: usar texto sobre dinâmica de fluidos sem conceitos do catálogo.
   Conferir aviso explícito, revisão/objetivos e geração sem atribuições. Essa
   chamada também requer autorização de custo, além dos dois cenários acima.
7. Falha de IA: em ambiente de ensaio sem chave ou com provedor indisponível,
   confirmar erro explícito e entrada preservada. Voltar ao Forensics e conferir
   investigação. Não usar uma resposta controlada como evidência de Gemini live.
8. Desconexão após geração admitida: reconectar, consultar estado, abrir aula já
   persistida; retry exige ação explícita. Confirmar a mesma chave/operação.

Registrar duração de cada etapa, total, modelo, cache e resultado efetivo, inclusive
falhas. Os testes repetíveis cobrem esses erros com provedor controlado e não
precisam de gasto. **Pendentes nesta execução:** Gemini live autorizado, gargalo
real, projetor físico, diálogo PDF no equipamento e aprovação científica/pedagógica
das frentes. Ver [matriz e resultados T13](integrated-demo-t13.md).
