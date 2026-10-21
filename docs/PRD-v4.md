# MATILDA
## Product Requirements Document — PRD v4.0
### Scientific Intelligence & Education Platform

**Projeto:** Matilda  
**Módulos:** Matilda Forensics + Matilda Studio  
**Infraestrutura compartilhada:** Matilda Scientific Intelligence Engine  
**Hackathon:** I Hackathon da SEDCITEC 2026 — Ciência Delas  
**Instituição:** Instituto Federal de São Paulo — Campus São Paulo  
**Data:** 21 de outubro de 2026  
**Prazo de apresentação:** 22 de outubro de 2026  
**Equipe:** 4 integrantes  
**Plataforma:** Aplicação web responsiva  
**Status:** Especificação final de produto e engenharia  
**Repositório:** https://github.com/FaellEmiliano/teste-matilda  
**Deploy informado:** https://teste-matilda-faell1.vercel.app/

---

# 1. RESUMO EXECUTIVO

## 1.1. Visão do produto

O **Matilda** é uma plataforma de inteligência científica e educacional desenvolvida para ampliar a descoberta, a compreensão e a integração de contribuições femininas à ciência e ao ensino.

Sua proposta consiste em conectar dois processos normalmente separados:

1. A investigação das contribuições de pesquisadoras para o desenvolvimento do conhecimento científico.
2. A transformação dessas descobertas em materiais didáticos contextualizados, verificáveis e utilizáveis por professores.

A plataforma possui dois modos principais, sustentados por uma infraestrutura científica comum.

### Matilda Forensics — Investigue a ciência

Ambiente dedicado à investigação de artigos científicos, conceitos, publicações e contribuições femininas.

Permite identificar pesquisadoras relacionadas a determinado conhecimento, compreender suas contribuições e acessar as evidências documentais que sustentam essas relações.

### Matilda Studio — Transforme ciência em educação

Ambiente dedicado à criação e ao enriquecimento de aulas com inteligência artificial.

Professores poderão fornecer conteúdos, materiais didáticos, artigos e objetivos educacionais.

O sistema investigará contribuições femininas relacionadas aos assuntos, proporá integrações pedagógicas contextualizadas e produzirá materiais de aula.

O resultado será um pacote pedagógico estruturado com:

- Plano de aula detalhado.
- Apresentação de slides.
- Notas para o professor.
- Atividades e questões.
- Referências científicas.
- Evidências das contribuições incluídas.

### Scientific Intelligence Engine

Infraestrutura compartilhada responsável por recuperar publicações, identificar conceitos, pesquisar contribuições, relacionar entidades científicas e fornecer evidências.

Essa arquitetura garante que o Studio utilize as mesmas informações científicas disponíveis no Forensics, evitando duplicações e divergências.

## 1.2. Proposta de valor

**Transformar conhecimento científico em descoberta e descoberta em educação, tornando as contribuições femininas parte integrante do aprendizado.**

## 1.3. Missão

Ampliar a presença contextualizada das contribuições femininas na pesquisa e na educação científica, utilizando tecnologia para conectar conhecimentos, pessoas, descobertas e evidências.

## 1.4. Visão de longo prazo

Tornar-se uma plataforma de inteligência científica e enriquecimento curricular utilizada por professores, estudantes, instituições educacionais e pesquisadores.

O produto deverá permitir que a participação feminina na ciência seja descoberta durante a investigação científica e incorporada naturalmente ao ensino.

## 1.5. Objetivo do hackathon

Demonstrar uma jornada completa entre os dois módulos:

**Artigo ou conteúdo didático → compreensão dos conceitos → investigação científica → contribuições documentadas → enriquecimento pedagógico → slides e plano de aula.**

A principal prova de valor será demonstrar que o Matilda não apenas encontra contribuições femininas, mas ajuda professores a ensiná-las de maneira cientificamente fundamentada.

---

# 2. PROBLEMA E JUSTIFICATIVA

## 2.1. Problema científico

Informações sobre contribuições científicas estão distribuídas entre artigos, referências bibliográficas, documentos históricos e diferentes bases acadêmicas.

Identificar uma contribuição específica, reconstruir suas relações e verificar sua origem pode exigir diversas pesquisas independentes.

Essa fragmentação dificulta a descoberta contextualizada de pesquisadoras associadas ao desenvolvimento de determinado conhecimento.

## 2.2. Problema educacional

Professores precisam preparar materiais coerentes com objetivos curriculares, com tempo e recursos frequentemente limitados.

A inclusão de contribuições femininas exige investigar quem participou de determinada descoberta, compreender a natureza dessa participação, localizar fontes e encontrar uma maneira pedagogicamente relevante de inserir a informação na aula.

Materiais educativos podem mencionar cientistas famosas sem explicar efetivamente suas contribuições.

O Matilda procura superar essa superficialidade.

## 2.3. Problema das ferramentas existentes

Buscadores acadêmicos recuperam artigos.

Plataformas de IA podem gerar planos de aula.

Ferramentas de grafos permitem explorar redes bibliográficas.

Entretanto, o diferencial pretendido pelo Matilda está em integrar investigação de contribuições femininas, evidências documentais e planejamento didático em um mesmo fluxo.

Não se presume exclusividade técnica de nenhuma funcionalidade isolada.

## 2.4. Hipótese principal

Se professores puderem fornecer seus materiais e receber propostas de enriquecimento científico com contribuições femininas relevantes e verificáveis, poderão produzir aulas mais contextualizadas com menos trabalho manual de investigação.

Essa hipótese deverá ser avaliada futuramente com professores reais.

---

# 3. OBJETIVOS E INDICADORES DE PRODUTO

## 3.1. Objetivos principais

- Preservar o Forensics como ambiente funcional de investigação científica.
- Desenvolver o Studio como ambiente integrado de criação pedagógica.
- Reutilizar os dados científicos do Forensics.
- Incorporar uma API generativa ao backend.
- Criar propostas contextualizadas de enriquecimento.
- Permitir revisão humana das contribuições sugeridas.
- Produzir planos de aula e slides a partir de uma representação comum.
- Garantir rastreabilidade das atribuições científicas.
- Entregar uma experiência visual consistente, acessível e demonstrável.

## 3.2. Métricas de aceite do MVP

| Indicador | Meta |
|---|---|
| Modos principais | Forensics e Studio acessíveis |
| Integração científica | Studio reutiliza o motor existente |
| Geração por IA | Funcional com resposta estruturada válida |
| Evidências | 100% das atribuições históricas verificadas têm fonte |
| Revisão | Professor aceita/rejeita sugestões |
| Apresentação | Slides navegáveis dentro do Matilda |
| Plano | Gerado com objetivos, sequência, atividades e fontes |
| Exportação | Plano imprimível/salvável em PDF |
| Erros críticos no pitch | Zero |
| Cenários demonstráveis | Pelo menos 2 |
| Documentação | Repositório reproduzível |

São metas de desenvolvimento, não resultados já verificados.

---

# 4. PÚBLICO-ALVO

## 4.1. Professores

Principal público do Matilda Studio.

**Problema:** precisam preparar materiais científicos, contextualizar descobertas e encontrar fontes confiáveis.

**Resultado desejado:** produzir uma aula pronta para utilização e adaptável à turma.

## 4.2. Estudantes

Principal público complementar do Forensics.

**Problema:** frequentemente conhecem conceitos científicos sem conhecer as contribuições de pessoas envolvidas em seu desenvolvimento.

**Resultado desejado:** investigar conhecimentos e compreender a participação de pesquisadoras.

## 4.3. Pesquisadores

Utilizam o Forensics para descobrir trabalhos, pesquisadores e relações bibliográficas.

## 4.4. Instituições

Potenciais clientes futuros:

- Escolas.
- Universidades.
- Redes de ensino.
- Editoras educacionais.
- Plataformas de aprendizagem.
- Organizações de divulgação científica.

---

# 5. ORGANIZAÇÃO DO PRODUTO

## 5.1. Matilda Forensics

**Responsabilidade:** descobrir, investigar e documentar.

Funcionalidades principais:

- Pesquisa por DOI.
- Recuperação de metadados científicos.
- Análise de conceitos.
- Identificação de contribuições femininas.
- Consulta a evidências.
- Grafo científico.
- Comparação bibliográfica.
- Exportação de investigações.
- Descoberta de novos candidatos documentais, sujeitos à revisão.

## 5.2. Matilda Studio

**Responsabilidade:** planejar, enriquecer e ensinar.

Funcionalidades principais:

- Criação de projetos pedagógicos.
- Entrada de conteúdos e artigos.
- Configuração educacional.
- Análise automática do material.
- Investigação científica integrada.
- Sugestões de enriquecimento.
- Aprovação das sugestões.
- Geração de plano de aula.
- Geração de slides.
- Notas de apresentação.
- Referências verificáveis.
- Exportação.

## 5.3. Integração bidirecional

### Forensics → Studio

Ação: **Transformar em aula**.

O sistema reutiliza artigo, conceitos, contribuições e evidências da investigação selecionada.

### Studio → Forensics

Ação: **Explorar descoberta**.

O professor poderá abrir a investigação científica que fundamenta uma contribuição incluída no material.

## 5.4. Regra de integração

Não deverão existir catálogos científicos independentes.

Ambos os módulos consultarão os mesmos serviços de recuperação e evidência, preservando IDs e classificações.

---

# 6. MATILDA FORENSICS — ESCOPO E ESTADO ATUAL

## 6.1. Funcionalidades identificadas no repositório

Na revisão do repositório realizada em 21/10/2026, foram identificados:

- Frontend React com TypeScript e React Flow.
- Backend FastAPI.
- Integração com OpenAlex.
- Recuperação por DOI.
- Catálogo editorial de pesquisadoras e contribuições.
- Análise conceitual.
- Grafo científico.
- Dossiês de evidência.
- Comparação de relações bibliográficas.
- Exportação Markdown e JSON.
- Cache e persistência SQLite.
- Descoberta automática de candidatos utilizando fontes acadêmicas complementares.
- Testes automatizados.

O repositório documenta um catálogo editorial inicial de três pesquisadoras e seis contribuições verificadas.

Candidatos adicionais recuperados automaticamente permanecem pendentes de revisão.

## 6.2. Decisão arquitetural

**Não reconstruir o Forensics.**

O desenvolvimento deverá preservar os contratos e comportamentos existentes, introduzindo apenas a adaptação necessária para que consultas conceituais originadas no Studio possam utilizar o motor científico.

## 6.3. Adaptação necessária

O mecanismo atual de investigação parte principalmente de um artigo identificado por DOI.

O Studio precisa também investigar assuntos provenientes de textos livres.

Será introduzida uma representação compartilhada de contexto científico:

`ScientificContext`

Campos principais:

- `origin_type`
- `paper_ids`
- `concept_ids`
- `concept_labels`
- `source_document_ids`
- `provenance`
- `limitations`

O contexto poderá ter origem em um DOI ou em um material pedagógico.

A recuperação de contribuições deverá aceitar essa representação, sem exigir a criação artificial de um artigo científico para processar textos livres.

## 6.4. Integridade

O Forensics não poderá afirmar influência histórica apenas por similaridade temática.

O Studio herdará essa restrição.

Contribuições pendentes de revisão não serão apresentadas como descobertas historicamente verificadas.

---

# 7. MATILDA STUDIO — EXPERIÊNCIA PRINCIPAL

## 7.1. Criação da aula

O professor acessará o Studio e preencherá:

- Título ou tema.
- Disciplina.
- Série ou nível.
- Duração.
- Objetivos de aprendizagem.
- Conceitos principais.
- Material didático.
- DOI de artigos, quando disponíveis.

O professor poderá iniciar uma aula com poucos campos.

Objetivos não preenchidos poderão ser sugeridos pela IA, sujeitos à aprovação.

## 7.2. Importação de conteúdos

### Entradas obrigatórias do MVP

**Texto livre:** apostilas ou trechos colados no formulário.

**Conceitos:** palavras-chave e assuntos.

**DOI:** artigos científicos recuperados pelo mecanismo existente.

### Entradas condicionadas

**PDF textual:** extração de conteúdo preservando sua origem.

### Entradas futuras

- DOCX.
- PPTX.
- Imagens e PDFs digitalizados.
- Links de materiais externos autorizados.
- Materiais de plataformas educacionais.

## 7.3. Análise pedagógica

O Matilda Teaching Agent deverá identificar:

- Assunto central.
- Conceitos.
- Conhecimentos prévios necessários.
- Complexidade da explicação.
- Objetivos pedagógicos.
- Estrutura do material existente.
- Seções relevantes para enriquecimento científico.

A análise não deverá substituir silenciosamente as escolhas do professor.

## 7.4. Investigação científica

O Studio criará um contexto científico e solicitará ao Forensics contribuições relacionadas.

Cada contribuição retornada deverá incluir:

- Pesquisadora.
- Trabalho ou contribuição.
- Conceitos relacionados.
- Explicação da correspondência.
- Evidências.
- Status de revisão.
- Limitações.

## 7.5. Enriquecimento do material

O agente analisará em que ponto do material a contribuição pode ser integrada.

Exemplo:

**Tema:** CRISPR-Cas9.

**Trecho original:** mecanismo de reconhecimento e corte do DNA.

**Contribuição recuperada:** trabalho documentado de Jennifer Doudna, Emmanuelle Charpentier e colaboradores.

**Sugestão:** incluir, após a explicação do mecanismo, a contextualização de como o conhecimento sobre o sistema CRISPR contribuiu para o desenvolvimento da técnica.

**Justificativa:** os estudantes já possuem a base conceitual para compreender a contribuição.

## 7.6. Aprovação

As sugestões serão apresentadas individualmente.

O professor poderá:

- Aceitar.
- Rejeitar.
- Editar.

O sistema deverá preservar o estado das decisões.

## 7.7. Geração

Após a revisão, o professor solicita:

**Gerar minha aula.**

O sistema produzirá um `LessonBundle`, contendo todos os elementos necessários para renderizar os slides e o plano pedagógico.

## 7.8. Revisão final

O professor poderá consultar as informações produzidas e visualizar as referências.

No MVP, alterações avançadas poderão exigir regeneração controlada. Edição direta por bloco é uma melhoria posterior.

---

# 8. MATILDA TEACHING AGENT

## 8.1. Objetivo

Produzir propostas pedagógicas a partir de conteúdo fornecido pelo professor e de contribuições científicas verificadas.

## 8.2. Modelo de IA

**Modelo principal:** Gemini 3.8 Flash.

**Identificador:** `gemini-3.8-flash`.

**Provedor:** Google Gemini API.

**SDK:** `google-genai` para Python.

**Local de execução:** backend FastAPI.

A chave deverá ser configurada pela variável `GEMINI_API_KEY`.

O frontend não poderá receber a chave ou chamar diretamente a API com credenciais do servidor.

## 8.3. Por que esse modelo?

O modelo oferece:

- Processamento de textos longos.
- Suporte a documentos PDF.
- Saídas estruturadas.
- Integração por API.
- Suporte a chamadas de ferramentas.
- Configurações de nível de raciocínio.

O modelo deverá ser configurável, permitindo migração futura.

## 8.4. Estratégia de orquestração

Será utilizado um **workflow agêntico controlado**, não um conjunto de agentes autônomos que executam livremente ações.

A aplicação será responsável pela sequência de execução.

O modelo ficará encarregado de tarefas cognitivas específicas.

Essa arquitetura facilita depuração, validação e controle de custos.

## 8.5. Pipeline

### Passo A — Material Analyzer

Recebe texto, conceitos, objetivos e nível.

Produz:

- Conceitos relevantes.
- Seções do material.
- Objetivos identificados.
- Resumo estruturado.
- Limitações da análise.

A saída deverá manter referências aos trechos de origem.

### Passo B — Scientific Retrieval

O backend consulta o Forensics.

Essa etapa não depende do modelo inventar pesquisadoras ou referências.

Produz:

- Contribuições elegíveis.
- Evidências verificadas.
- Relações temáticas.
- Limitações.

### Passo C — Enrichment Planner

A IA recebe o contexto pedagógico e o conjunto científico autorizado.

Produz sugestões de enriquecimento com IDs de contribuição e evidência.

### Passo D — Teacher Approval

O sistema apresenta as sugestões e registra as decisões.

Nenhuma geração final ocorre antes da revisão no fluxo padrão.

### Passo E — Lesson Generator

A IA recebe:

- Configuração pedagógica.
- Material original.
- Conceitos.
- Sugestões aceitas.
- Contribuições verificadas.
- Evidências permitidas.

Produz um `LessonBundle` estruturado.

### Passo F — Lesson Validator

Código determinístico valida o resultado.

### Passo G — Renderer

O React utiliza os dados validados para montar os slides e o plano.

## 8.6. Número de chamadas de IA

A implementação inicial deverá buscar o menor número razoável de chamadas.

Fluxo sugerido:

**Chamada 1:** análise pedagógica e elaboração de sugestões, após recuperação científica.

**Chamada 2:** geração do `LessonBundle` depois da aprovação.

Caso a análise de material seja muito extensa ou a geração falhe, o sistema poderá separar ou repetir etapas de maneira controlada.

Não deverão existir loops autônomos ilimitados.

---

# 9. KNOWLEDGE ENRICHMENT ENGINE

## 9.1. Definição

O Knowledge Enrichment Engine é o principal diferencial pedagógico do Matilda.

Ele transforma relações científicas em propostas contextualizadas de enriquecimento curricular.

## 9.2. Critério de pertinência

Uma sugestão deverá atender a três condições:

**Relevância científica:** a contribuição se relaciona ao conhecimento ensinado.

**Sustentação documental:** a atribuição científica possui evidência adequada.

**Relevância pedagógica:** a contribuição pode melhorar a compreensão dos objetivos de aprendizagem.

## 9.3. Estrutura mínima da sugestão

- ID.
- Conceito relacionado.
- Seção ou trecho de origem.
- Contribuição.
- Pesquisadora.
- Evidência.
- Proposta de inserção.
- Justificativa pedagógica.
- Status de aprovação.

## 9.4. Restrições

O sistema não deverá:

- Incluir cientistas apenas para preencher uma quota.
- Atribuir descobertas coletivas exclusivamente a uma pesquisadora.
- Inventar citações.
- Transformar relações temáticas em causalidade histórica.
- Alterar o conteúdo original sem identificação.
- Exibir conteúdo pendente como historicamente verificado.

## 9.5. Resultado esperado

O professor deverá compreender:

**O que inserir, onde inserir, por que inserir e como verificar.**

---

# 10. GERAÇÃO DA AULA

## 10.1. Unidade de geração

O sistema produzirá uma representação estruturada denominada:

`LessonBundle`

O `LessonBundle` será a fonte de verdade para todos os materiais gerados.

A IA não deverá produzir arquivos PowerPoint, PDFs ou páginas HTML arbitrárias.

Ela produzirá conteúdo estruturado que será interpretado pelos renderizadores controlados pelo Matilda.

## 10.2. Componentes do LessonBundle

**LessonMetadata**

Informações gerais da aula.

**LearningObjectives**

Objetivos de aprendizagem.

**LessonSections**

Sequência cronológica do plano pedagógico.

**Slides**

Estrutura de apresentação visual.

**SpeakerNotes**

Roteiro do professor associado aos slides.

**Activities**

Atividades e questões.

**EvidenceReferences**

Referências documentais utilizadas.

**Limitations**

Avisos e informações não verificadas.

## 10.3. Plano de aula

Deverá conter:

- Tema.
- Disciplina.
- Nível.
- Duração.
- Objetivos.
- Conhecimentos prévios.
- Materiais necessários.
- Sequência cronológica.
- Explicações.
- Atividades.
- Avaliação.
- Referências.
- Limitações.

## 10.4. Slides

O sistema deverá gerar uma apresentação 16:9 adequada para projetores e computadores.

Os slides serão renderizados pelo React.

A primeira versão deverá utilizar um conjunto limitado de layouts.

### Layouts permitidos

**TITLE:** abertura da aula.

**CONCEPT:** apresentação e explicação de conceito.

**PROCESS:** sequência de etapas de um mecanismo.

**SCIENTIST_SPOTLIGHT:** contribuição de pesquisadora, com fonte.

**QUESTION:** questão ou discussão.

**SUMMARY:** revisão e conclusão.

O modelo selecionará o layout e preencherá os campos apropriados.

A identidade visual será controlada por componentes React e CSS.

## 10.5. Notas do professor

Cada slide poderá possuir:

- Objetivo pedagógico.
- Orientação de explicação.
- Exemplos sugeridos.
- Perguntas para os alunos.
- Tempo previsto.
- Fontes pertinentes.

No modo de apresentação, as notas deverão ficar ocultas dos estudantes.

## 10.6. Atividades

O LessonBundle poderá incluir:

- Perguntas de compreensão.
- Questões conceituais.
- Estudos de caso.
- Discussões.
- Atividades de aplicação.

O nível de dificuldade deverá ser compatível com a turma.

## 10.7. Quantidade de slides

Para o MVP, utilizar preferencialmente entre 6 e 12 slides por aula de 50 minutos.

Essa é uma diretriz de design, não uma obrigação universal.

A quantidade deverá se ajustar à duração e aos objetivos.

## 10.8. Renderização

O frontend receberá o JSON e selecionará os componentes correspondentes.

Exemplo:

`layout = "SCIENTIST_SPOTLIGHT"`

Renderizador:

`ScientistSpotlightSlide`

O componente receberá título, conteúdo, fonte e notas.

Nenhum HTML ou JavaScript gerado pela IA será executado.

## 10.9. Ilustrações científicas

Para o MVP:

- Diagramas simples com SVG ou componentes próprios.
- Ícones de biblioteca licenciada.
- Elementos visuais reutilizáveis.
- Imagens documentais com direitos de uso confirmados, quando disponíveis.

A geração automática de imagens científicas complexas não será uma dependência do fluxo principal.

---

# 11. FORMATOS DE ENTREGA

## 11.1. Apresentação interativa

**Prioridade P0**

Slides renderizados em React.

Recursos:

- Tela cheia.
- Navegação anterior/próximo.
- Indicador de progresso.
- Atalhos de teclado.
- Referências nos slides relevantes.
- Notas de apresentação em visualização separada.

## 11.2. Plano de aula em PDF

**Prioridade P0**

O plano será apresentado como documento HTML responsivo com estilos específicos para impressão.

O professor poderá utilizar a função de imprimir/salvar em PDF do navegador.

No MVP, não será necessário gerar PDF binário no backend.

## 11.3. Exportação Markdown

**Prioridade P0**

Permitir exportar o plano de aula em formato textual com referências.

Servirá também como alternativa caso a impressão não funcione.

## 11.4. PowerPoint editável

**Prioridade P1**

Utilizar PptxGenJS para transformar o LessonBundle em uma apresentação `.pptx`.

A implementação deverá reutilizar os layouts e campos estruturados, mas criar os elementos editáveis do PowerPoint em vez de exportar capturas de tela.

## 11.5. PDF dos slides

**Prioridade P1**

Criar um layout de impressão 16:9 dos slides.

O documento será salvo como PDF pelo navegador.

## 11.6. Formatos futuros

- DOCX.
- Material de estudo para estudantes.
- Quiz interativo.
- Exercícios imprimíveis.
- Integração com ambientes virtuais de aprendizagem.

---

# 12. ARQUITETURA DE SOFTWARE

## 12.1. Princípios

- Reutilização do código existente.
- Contratos estáveis.
- Separação entre IA e renderização.
- Serviços científicos compartilhados.
- Validação estruturada.
- Segurança de credenciais.
- Baixa complexidade operacional.
- Evolução incremental.

## 12.2. Frontend

**Tecnologias:**

- React 19.
- TypeScript.
- Vite.
- React Flow.
- CSS e componentes existentes.
- Lucide Icons.

### Novos componentes propostos

- `ModeSelector`
- `StudioSetup`
- `MaterialInput`
- `EnrichmentPanel`
- `SuggestionCard`
- `LessonPreview`
- `SlideRenderer`
- `PresentationMode`
- `SpeakerNotes`
- `LessonPrintView`

## 12.3. Backend

**Tecnologias:**

- Python.
- FastAPI.
- Pydantic.
- HTTPX.
- SQLite.
- Google GenAI SDK.

### Novos serviços propostos

`studio/material_analyzer.py`

`studio/context_builder.py`

`studio/enrichment_planner.py`

`studio/lesson_generator.py`

`studio/lesson_validator.py`

`studio/lesson_export.py`

`llm/gemini_client.py`

`schemas/studio.py`

`api/studio.py`

A organização é uma estrutura-alvo; não exige reestruturação completa do repositório atual.

## 12.4. Scientific Intelligence Engine

O novo Studio utilizará serviços do Forensics responsáveis por:

- Análise conceitual.
- Recuperação de contribuições.
- Catálogo.
- Evidências.
- Identidades.
- Normalização bibliográfica.

Quando necessário, criar adaptadores explícitos.

## 12.5. Banco de dados

**MVP:** SQLite.

Entidades novas:

- `lesson_projects`
- `source_documents`
- `enrichment_previews`
- `enrichment_suggestions`
- `lesson_bundles`

O conteúdo original deverá ser armazenado separadamente das saídas geradas.

## 12.6. Implantação

O frontend poderá permanecer no Vercel.

O backend FastAPI deverá estar acessível por HTTPS em um serviço compatível com Python.

Opções técnicas incluem Render, Railway ou implantação equivalente.

**A implantação deverá ser escolhida conforme os recursos efetivamente disponíveis à equipe.**

O uso de SQLite requer atenção: armazenamento efêmero em ambientes serverless não garante persistência entre execuções.

Para a demonstração, poderá ser utilizado um backend com armazenamento persistente ou um ambiente controlado previamente testado.

O frontend deverá possuir uma configuração de API que permita acessar o backend publicado sem depender exclusivamente do proxy local do Vite.

---

# 13. MODELO DE DADOS

## 13.1. ScientificContext

```text
id
origin_type
paper_ids[]
concept_ids[]
concept_labels[]
source_document_ids[]
provenance[]
limitations[]
```

## 13.2. LessonProject

```text
id
title
subject
education_level
duration_minutes
learning_objectives[]
scientific_context_id
status
created_at
```

## 13.3. SourceDocument

```text
id
project_id
type
title
content
doi?
filename?
extraction_status
```

## 13.4. EnrichmentSuggestion

```text
id
project_id
source_document_id?
source_anchor?
concept_ids[]
researcher_ids[]
contribution_id
evidence_ids[]
scientific_explanation
pedagogical_rationale
suggested_content
status
```

## 13.5. LessonBundle

```text
id
project_id
title
subject
education_level
duration_minutes
objectives[]
sections[]
slides[]
activities[]
references[]
limitations[]
generation_metadata
```

## 13.6. Slide

```text
id
layout
title
subtitle?
content_blocks[]
speaker_notes
duration_minutes
contribution_ids[]
evidence_ids[]
```

## 13.7. Identificadores

Contribuições e evidências deverão manter os identificadores produzidos pelo Forensics.

O modelo generativo não poderá criar IDs de documentos ou registros científicos.

---

# 14. CONTRATOS DE API

## 14.1. Endpoints existentes

Preservar os endpoints científicos atuais:

- `GET /api/papers/{doi}`
- `POST /api/analyses`
- `GET /api/analyses/{id}`
- `GET /api/analyses/{id}/graph`
- `GET /api/evidence/{id}`
- `POST /api/analyses/{id}/discovery`

## 14.2. POST /api/studio/preview

**Objetivo:** analisar o material e gerar sugestões de enriquecimento.

Entrada:

```json
{
  "title": "Edição genética",
  "subject": "Biologia",
  "education_level": "Ensino Médio",
  "duration_minutes": 50,
  "objectives": [
    "Compreender o funcionamento do CRISPR-Cas9"
  ],
  "concepts": [
    "DNA",
    "RNA",
    "CRISPR-Cas9"
  ],
  "material_text": "Material original do professor",
  "doi": "10.1126/science.1231143"
}
```

Saída:

- `preview_id`
- `scientific_context`
- `concepts`
- `suggestions`
- `evidence_references`
- `limitations`

## 14.3. POST /api/studio/generate

**Objetivo:** produzir o LessonBundle.

Entrada:

```json
{
  "preview_id": "preview-example",
  "accepted_suggestion_ids": [
    "suggestion-example"
  ]
}
```

Saída:

- `lesson_bundle_id`
- `metadata`
- `sections`
- `slides`
- `activities`
- `references`
- `limitations`

## 14.4. GET /api/studio/lessons/{id}

Recupera um LessonBundle existente.

## 14.5. GET /api/studio/lessons/{id}/export

Formato inicial:

- `markdown`

O PDF será produzido a partir da interface imprimível.

## 14.6. Contratos estruturados

As respostas produzidas pelo modelo deverão ser validadas com esquemas Pydantic.

Campos desconhecidos, referências inexistentes e tipos inválidos deverão provocar rejeição ou correção controlada.

---

# 15. VALIDAÇÃO DO CONTEÚDO GERADO

## 15.1. Validação estrutural

Verificar:

- JSON válido.
- Campos obrigatórios.
- Layouts permitidos.
- Duracões válidas.
- Número máximo de slides.
- Comprimento do conteúdo.
- Identificadores consistentes.

## 15.2. Validação temporal

A soma das durações das seções deverá corresponder ao tempo solicitado para a aula, permitindo apenas tolerância explicitamente definida.

O tempo dos slides deverá ser compatível com as seções correspondentes.

## 15.3. Validação documental

Atribuições científicas históricas deverão utilizar evidências existentes e elegíveis.

O backend deverá conferir:

- Existência do ID.
- Associação à contribuição correta.
- Estado de verificação.
- Compatibilidade com o conjunto autorizado.

A correspondência semântica entre a afirmação gerada e a fonte não pode ser garantida apenas por validação de JSON.

Portanto, o sistema deverá restringir atribuições históricas a afirmações aprovadas no catálogo e preservar a revisão humana.

## 15.4. Validação pedagógica

Verificar:

- Adequação ao nível.
- Presença de objetivos.
- Coerência entre objetivos e atividades.
- Relação entre slides e plano.
- Distribuição temporal.
- Existência de atividades de avaliação.

A qualidade pedagógica final deverá ser avaliada por professores.

## 15.5. Tratamento de falhas

Em caso de erro:

- Preservar o material original.
- Preservar sugestões já aprovadas.
- Informar a falha.
- Permitir nova tentativa controlada.
- Não retornar conteúdo fictício como resultado válido.

---

# 16. EXPERIÊNCIA VISUAL

## 16.1. Identidade

O Matilda terá uma identidade visual única.

Os modos serão identificados pelas respectivas funções, sem parecerem dois produtos independentes.

## 16.2. Página inicial

Duas opções principais:

**Forensics — Investigar ciência**

**Studio — Criar aula**

## 16.3. Studio Setup

Formulário de preparação.

O professor informa conteúdos e objetivos.

## 16.4. Enrichment Workspace

Três áreas:

**Material original**

**Sugestões de enriquecimento**

**Evidências científicas**

## 16.5. Lesson Workspace

Duas visualizações:

**Apresentação:** slides de aula.

**Plano do professor:** roteiro e referências.

## 16.6. Presentation Mode

Recursos:

- Tela cheia.
- Slides em 16:9.
- Navegação por teclado.
- Progresso da apresentação.
- Referências identificáveis.
- Notas do apresentador separadas.

## 16.7. Acessibilidade

- Navegação por teclado.
- Foco visível.
- Contraste suficiente.
- Rótulos acessíveis.
- Alternativas textuais.
- Respeito a movimento reduzido.
- Informações científicas não dependentes apenas de cor.

---

# 17. REQUISITOS NÃO FUNCIONAIS

## 17.1. Desempenho

Metas iniciais, dependentes de testes:

| Operação | Meta de desenvolvimento |
|---|---|
| Recuperação de artigo | Até 5 segundos em condição normal |
| Prévia pedagógica | Até 30 segundos em cenário controlado |
| Geração do LessonBundle | Até 45 segundos em cenário controlado |
| Navegação entre slides | Sem atraso perceptível |
| Renderização inicial | Sem travamento da interface |

Esses números são objetivos internos, não garantias.

## 17.2. Resiliência

- Timeout.
- Retry limitado.
- Tratamento de rate limit.
- Mensagens claras.
- Cache de dados científicos.
- Logs de erro.
- Preservação de estado.

## 17.3. Segurança

- Chaves exclusivamente no backend.
- `.env` fora do Git.
- Validação de arquivos.
- Limites de upload.
- Proteção contra SSRF.
- Sanitização de conteúdo exibido.
- Nenhuma execução de HTML ou código vindo da IA.
- Restrição de acesso a registros de projetos.

## 17.4. Privacidade

O MVP deverá minimizar a coleta e a retenção de materiais enviados pelos professores.

Não exigir dados pessoais de alunos.

Documentos enviados deverão possuir tratamento de retenção definido.

O envio de materiais ao provedor de IA deverá ser informado ao usuário.

## 17.5. Direitos autorais

O sistema não deverá redistribuir PDFs protegidos sem autorização.

O uso de documentos externos deverá respeitar suas licenças.

Materiais de terceiros não poderão ser incorporados indiscriminadamente às exportações.

## 17.6. Custos

Implementar:

- Limite de tamanho de entrada.
- Limite de tokens.
- Limite de requisições.
- Timeout por etapa.
- Registro do modelo utilizado.
- Controle de uso por sessão.

---

# 18. ESTRATÉGIA DE IMPLEMENTAÇÃO

## 18.1. Restrições

O regulamento prevê apresentação em 22/10/2026.

O prazo restante torna obrigatório priorizar uma jornada integrada sobre funcionalidades complementares.

## 18.2. Estratégia

**Vertical Slice First:** concluir um fluxo completo antes de ampliar recursos.

Primeira entrega funcional:

Texto/DOI → contribuições → sugestões → aprovação → LessonBundle → slides.

## 18.3. Divisão da equipe

### Integrante A — Backend

- Endpoints Studio.
- Adaptador ScientificContext.
- Contratos Pydantic.
- Persistência.
- Tratamento de erros.

### Integrante B — IA

- Integração Gemini.
- Prompts estruturados.
- Enrichment Planner.
- Lesson Generator.
- Validação de evidências.

### Integrante C — Frontend

- Navegação entre modos.
- Formulários.
- Painel de sugestões.
- Slide Renderer.
- Plano imprimível.

### Integrante D — Integração e qualidade

- Testes.
- Deploy.
- Correções.
- Documentação.
- Cenários de demonstração.
- Pitch.

## 18.4. Ordem de execução

**Marco 1:** contratos definidos e geração estruturada funcionando no backend.

**Marco 2:** Forensics conectado ao Studio.

**Marco 3:** sugestões de enriquecimento apresentadas e revisáveis.

**Marco 4:** LessonBundle produzido e renderizado em slides.

**Marco 5:** plano imprimível e exportação Markdown.

**Marco 6:** integração, testes e estabilização.

## 18.5. Regra de corte

Se a jornada completa não estiver estável, interromper:

- Upload de PDF.
- Exportação PowerPoint.
- Geração de novos tipos de atividade.
- Animações avançadas.
- Edição livre de slides.
- Expansões bibliográficas adicionais.

O Forensics existente deve continuar operacional.

---

# 19. TESTES

## 19.1. Testes funcionais

**CT-01:** criar aula usando texto livre.

**CT-02:** criar aula utilizando DOI válido.

**CT-03:** identificar conceitos científicos.

**CT-04:** recuperar contribuições existentes no Forensics.

**CT-05:** gerar sugestões contextualizadas.

**CT-06:** rejeitar uma sugestão.

**CT-07:** aprovar uma sugestão.

**CT-08:** produzir plano com apenas as sugestões aprovadas.

**CT-09:** renderizar slides de layouts diferentes.

**CT-10:** consultar evidências utilizadas.

**CT-11:** exportar plano em Markdown.

**CT-12:** imprimir/salvar PDF.

**CT-13:** tratar falha do Gemini.

**CT-14:** impedir inclusão de referência inexistente.

**CT-15:** processar conteúdo fora da cobertura documental.

**CT-16:** manter o Forensics funcionando após a integração.

## 19.2. Testes de segurança

- Input excessivamente longo.
- JSON malformado.
- IDs inválidos.
- Prompt injection no material didático.
- Tentativa de inserir HTML executável.
- Erros de autenticação das APIs.
- Exposição indevida de credenciais.
- Arquivos inválidos ou fora do limite.

## 19.3. Testes de apresentação

- Navegador utilizado no pitch.
- Conexão com backend.
- Exibição no projetor.
- Leitura dos slides.
- Acesso às fontes.
- Navegação por teclado.
- Exportação.
- Erros e estados vazios.

## 19.4. Cenários principais

### Cenário A — CRISPR-Cas9

O professor prepara uma aula sobre edição genética.

O Matilda recupera contribuições documentadas de pesquisadoras relacionadas ao desenvolvimento da técnica.

Gera uma aula com explicações, contextualização, atividades e referências.

### Cenário B — Vacinas de RNA

O professor fornece conteúdo sobre vacinas de RNA.

O Matilda recupera contribuições documentadas pertinentes e propõe integração didática.

### Cenário C — Fora da cobertura

O professor insere um assunto sem correspondência verificada no catálogo.

O Studio deverá informar a limitação e não fabricar contribuições.

---

# 20. ESTRATÉGIA DE PITCH

**Tempo máximo:** 10 minutos.

## 20.1. Abertura — 1 minuto

Apresentar o problema: contribuições femininas podem estar pouco contextualizadas na maneira como aprendemos ciência.

## 20.2. Proposta — 1 minuto

Apresentar os dois modos integrados.

## 20.3. Forensics — 2 minutos

Demonstrar:

- Artigo real.
- Contribuições.
- Grafo.
- Evidências.

## 20.4. Studio — 4 minutos

Demonstrar:

1. Criação da aula.
2. Entrada de material.
3. Investigação automática.
4. Sugestão de enriquecimento.
5. Aprovação.
6. Geração de slides.
7. Visualização do plano e referências.

## 20.5. Engenharia e impacto — 1 minuto

Explicar o motor compartilhado, as evidências e a aplicabilidade na educação.

## 20.6. Encerramento — 1 minuto

Apresentar possibilidades de implantação e evolução.

Mensagem final:

**O Matilda conecta as contribuições de mulheres à ciência que pesquisamos e às aulas que ensinamos.**

---

# 21. MODELO DE NEGÓCIO

## 21.1. Tese comercial

A plataforma poderá atender professores que desejam enriquecer conteúdos científicos e instituições interessadas em apoiar a atualização de materiais curriculares.

## 21.2. Modelo inicial hipotético

**Gratuito**

Investigações científicas e gerações limitadas.

**Plano docente**

Aulas, apresentações, materiais exportáveis e recursos adicionais.

**Plano institucional**

Licenciamento para escolas, universidades e redes de ensino.

## 21.3. Diferencial comercial

- Motor científico especializado.
- Evidências rastreáveis.
- Planejamento pedagógico.
- Slides prontos para apresentação.
- Materiais reutilizáveis.
- Integração entre investigação e ensino.

## 21.4. Validação necessária

Testar com professores:

- Economia de tempo.
- Qualidade dos materiais.
- Relevância das sugestões.
- Facilidade de conferência das fontes.
- Frequência de utilização.
- Disposição a pagar.

Nenhuma receita, cliente ou demanda validada deverá ser inventada no pitch.

---

# 22. DEFINITION OF DONE

## 22.1. Forensics

- [ ] Recuperação por DOI preservada.
- [ ] Grafo científico funcional.
- [ ] Contribuições e evidências acessíveis.
- [ ] Descoberta automática preservada.
- [ ] Exportações existentes operacionais.
- [ ] Testes de regressão aprovados.

## 22.2. Studio

- [ ] Nova aula pode ser configurada.
- [ ] Texto e conceitos podem ser enviados.
- [ ] DOI pode ser vinculado.
- [ ] Material é analisado.
- [ ] Contribuições verificadas são recuperadas.
- [ ] Sugestões são geradas.
- [ ] Professor aprova/rejeita sugestões.
- [ ] LessonBundle válido é produzido.
- [ ] Slides são renderizados no navegador.
- [ ] Notas para professor estão disponíveis.
- [ ] Plano detalhado é exibido.
- [ ] Material pode ser exportado ou impresso.
- [ ] Fontes científicas podem ser conferidas.

## 22.3. Integração e qualidade

- [ ] O Studio utiliza serviços científicos compartilhados.
- [ ] Nenhuma atribuição histórica é inventada.
- [ ] Candidatos pendentes não são tratados como verificados.
- [ ] Identificadores de evidência são validados.
- [ ] Credenciais permanecem no backend.
- [ ] Erros não comprometem o Forensics.
- [ ] A aplicação funciona no ambiente demonstrado.
- [ ] O README está atualizado.
- [ ] A demonstração está ensaiada.

---

# 23. ROADMAP FUTURO

## Versão 4.1 — Produção avançada de aulas

- PPTX editável.
- Exportação DOCX.
- Melhor editor de slides.
- Geração de atividades adicionais.
- Upload de materiais variados.

## Versão 4.2 — Plataforma docente

- Projetos persistentes.
- Histórico de aulas.
- Organização por disciplina.
- Compartilhamento entre professores.
- Bibliotecas de materiais.

## Versão 4.3 — Experiência estudantil

- Aulas navegáveis.
- Grafos interativos.
- Atividades de descoberta.
- Questionários.
- Trilhas personalizadas.

## Versão 5.0 — Inteligência curricular institucional

- Análise de materiais curriculares.
- Mapeamento de conceitos e contribuições.
- Recomendações de enriquecimento.
- Gestão institucional.
- Integrações com ambientes educacionais.
- Ampliação da cobertura científica.

---

# 24. PRINCÍPIOS FUNDAMENTAIS

## Ciência antes de narrativa

O sistema não deverá adaptar fatos para construir histórias mais impressionantes.

## Evidência antes de atribuição

As contribuições históricas precisam possuir documentação adequada.

## Educação antes de automação

O produto deverá ajudar professores a ensinar, não substituir seu julgamento pedagógico.

## Integração antes de duplicação

Os dois modos compartilham a mesma infraestrutura científica.

## Experiência antes de complexidade

A tecnologia deverá servir a uma jornada simples, utilizável e compreensível.

## Funcionamento antes de amplitude

Uma aula bem construída e cientificamente fundamentada possui mais valor para o MVP do que dezenas de recursos instáveis.

---

# 25. CONCLUSÃO

O Matilda é uma plataforma que conecta investigação científica e produção educacional por meio de inteligência artificial e evidências documentais.

O **Forensics** permite descobrir e compreender contribuições femininas relacionadas ao conhecimento científico.

O **Studio** utiliza essas descobertas para apoiar professores na criação de aulas, apresentações e atividades contextualizadas.

O **Scientific Intelligence Engine** fornece a infraestrutura comum de recuperação, organização e rastreabilidade das informações científicas.

Seu diferencial está na integração entre descoberta, evidência e ensino.

A plataforma busca permitir que as contribuições femininas sejam reconhecidas não apenas quando alguém pesquisa a história da ciência, mas também durante o aprendizado cotidiano de conceitos científicos.

**MATILDA**

**Investigue a ciência. Descubra as contribuições. Transforme o aprendizado.**

---

## ANEXO A — DOCUMENTAÇÃO TÉCNICA

- GitHub: https://github.com/FaellEmiliano/teste-matilda
- Gemini API: https://ai.google.dev/gemini-api/docs
- Modelos Gemini: https://ai.google.dev/gemini-api/docs/models
- Saídas estruturadas: https://ai.google.dev/gemini-api/docs/structured-output
- Processamento de PDF: https://ai.google.dev/gemini-api/docs/document-processing
- OpenAlex: https://help.openalex.org/api/
- React Flow: https://reactflow.dev/
- FastAPI: https://fastapi.tiangolo.com/
- PptxGenJS: https://gitbrent.github.io/PptxGenJS/

## ANEXO B — RESTRIÇÃO DO REGULAMENTO

Esta especificação considera o regulamento preliminar do I Hackathon da SEDCITEC 2026, com desenvolvimento oficial entre 19 e 22 de outubro, equipe de até quatro integrantes, uso permitido de IA generativa e avaliação por critérios igualmente ponderados.

A versão final do regulamento e eventuais orientações posteriores da comissão organizadora prevalecem sobre as premissas deste documento.