# Proposta: Exportação de Relatórios em PDF com Design System e Suporte a Markdown

## Por que

A exportação em PDF de releases (Issue #14) insere campos em Markdown diretamente no `Paragraph` do ReportLab. Isso exibe marcadores crus (`**`, `-`, `#`, `|`) e agrupa quebras de linha em blocos ilegíveis. Ao mesmo tempo, os relatórios gerados carecem da identidade visual oficial da marca LUMINA (Fiocruz), cujas diretrizes de cores, tipografia, logos e elementos visuais constam no diretório `design-system`. Integrar a identidade visual em `lumina/assets/` e processar o Markdown garante relatórios legíveis, seguros contra injeção de tags XML no ReportLab e alinhados à comunicação institucional.

## O que muda

- Move a pasta `design-system` para `lumina/assets/design-system/`, disponibilizando tokens de design, fontes e logos dentro do pacote da aplicação.
- Cria um conversor de Markdown para elementos do ReportLab (`Flowable`), tratando títulos, listas numeradas e com marcadores, ênfases (negrito e itálico), tabelas e blocos de código com escape de entidades XML (`<`, `>`, `&`).
- Atualiza o gerador de relatórios em [lumina/services/report_service.py](file:///home/gls/Travail/Fiocruz/Lumina/lumina-back/lumina/services/report_service.py) aplicando a paleta oficial (laranja `#f8580a`, teal `#0e90a0`, ouro `#d9ae21`, texto tinta `#2b2b2b`, fundo claro `#efefef`), fontes recomendadas, capa estruturada, sumário e rodapés institucionais com logo Fiocruz/Lumina.
- Preserva a compatibilidade dos endpoints de exportação existentes (`/doc/{doc_id}/release/{document_release_id}/export/pdf`, `/export/release/pdf` e `/export/typifications/pdf`), assegurando que conteúdos legados em texto puro continuem sendo renderizados sem quebras.

## Capacidades

### Novas Capacidades

- `document-export`: Geração e exportação de relatórios formatados em PDF para releases de documentos e tipificações, com aplicação das diretrizes visuais do LUMINA e suporte completo a blocos e formatações em Markdown.

### Capacidades Modificadas

Nenhuma capacidade existente tem seus requisitos alterados.

## Impacto

- **Código**: [lumina/services/report_service.py](file:///home/gls/Travail/Fiocruz/Lumina/lumina-back/lumina/services/report_service.py), [lumina/routers/reports.py](file:///home/gls/Travail/Fiocruz/Lumina/lumina-back/lumina/routers/reports.py), [lumina/routers/docs/releases.py](file:///home/gls/Travail/Fiocruz/Lumina/lumina-back/lumina/routers/docs/releases.py) e [lumina/services/typification_service.py](file:///home/gls/Travail/Fiocruz/Lumina/lumina-back/lumina/services/typification_service.py).
- **Estrutura de arquivos**: Realocação de `design-system/` para `lumina/assets/design-system/`.
- **Dependências**: Nenhuma nova dependência de sistema. O ReportLab continua sendo o motor de renderização. Entra `svglib` (Python puro) para desenhar os logos SVG. As fontes WOFF2 são convertidas uma vez para TTF e versionadas.
