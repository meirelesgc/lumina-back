# document-export Specification

## Purpose

Permite que analistas e usuários exportem relatórios de releases de documentos e tipificações em formato PDF estruturado, com identidade visual Lumina e renderização legível de conteúdos em Markdown.

## Requirements

### Requirement: Exportação de release em PDF com suporte a Markdown

O sistema DEVE processar a síntese da release e os pareceres de cada critério formatados em Markdown, convertendo títulos, ênfases em negrito ou itálico, listas e tabelas em elementos visuais do documento PDF.

#### Scenario: Relatório com síntese e pareceres estruturados em Markdown
- **WHEN** o usuário solicita a exportação em PDF de uma release com descrição e pareceres contendo listas, negrito e tabelas
- **THEN** o arquivo PDF gerado renderiza os blocos formatados sem exibir marcadores crus como asteriscos ou cerquilhas

### Requirement: Sanitização e escape de entidades XML

O sistema DEVE escapar caracteres especiais de XML (`<`, `>`, `&`) presentes no conteúdo textual da release antes de renderizar parágrafos do documento PDF.

#### Scenario: Texto contendo operadores de comparação ou caracteres especiais
- **WHEN** uma síntese ou parecer avaliativo contém trechos com `<` ou `&` que não representam tags suportadas
- **THEN** o documento PDF é compilado sem falhas de parsing de XML e os caracteres aparecem corretamente legíveis

### Requirement: Aplicação da identidade visual institucional no PDF

O sistema DEVE aplicar a paleta de cores institucional do Lumina (laranja, teal, ouro, fundo claro e texto tinta), cabeçalhos com logo institucional e tipografia padronizada em todos os relatórios emitidos.

#### Scenario: Geração de relatório com capa e rodapés institucionais
- **WHEN** o endpoint de exportação de release ou tipificação é acionado
- **THEN** o documento gerado inclui capa com informações do documento, cabeçalhos ou rodapés institucionais e estilos de texto coerentes com os tokens de design

### Requirement: Compatibilidade com relatórios legados em texto puro

O sistema DEVE garantir que descrições e pareceres gerados em texto puro simples, sem sintaxe Markdown, continuem sendo exportados e preservados no layout do documento sem regressões.

#### Scenario: Exportação de release antiga sem marcação Markdown
- **WHEN** uma release histórica com texto não formatado é exportada
- **THEN** o PDF gerado exibe o texto integral com quebras de linha e formatação padrão preservadas
