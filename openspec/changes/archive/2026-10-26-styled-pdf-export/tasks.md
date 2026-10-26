# Tasks

## 1. Organização dos ativos do design system

- [x] 1.1 Mover a pasta `design-system` para `lumina/assets/design-system/` e verificar a presença de tokens, fontes e logos em `lumina/assets/design-system/`
- [x] 1.2 Atualizar o arquivo `.gitignore` para permitir o rastreamento dos ativos em `lumina/assets/design-system/` no repositório
- [x] 1.3 Converter as fontes WOFF2 de Barlow e Lexend para TTF (ao lado dos originais) e adicionar `svglib` às dependências com `poetry add svglib`

## 2. Parser de Markdown para elementos do ReportLab

- [x] 2.1 Criar testes unitários em `tests/unit/services/test_markdown_reportlab.py` cobrindo títulos, listas, negrito, itálico, tabelas GFM, texto puro e escape de entidades XML. Confirmar que os testes falham antes da implementação
- [x] 2.2 Implementar `lumina/utils/markdown_reportlab.py` convertendo blocos e ênfases de Markdown em Flowables (`Paragraph`, `Table`, `Spacer`) com escape seguro de XML. Confirmar que todos os testes de `tests/unit/services/test_markdown_reportlab.py` passam

## 3. Estilização dos relatórios e integração com o ReportLab

- [x] 3.1 Criar testes em `tests/integration/test_report_export.py` validando os endpoints de exportação de release (`GET /export/release/pdf` e `/doc/{doc_id}/release/{document_release_id}/export/pdf`) e tipificação (`GET /export/typifications/pdf`). Confirmar que os testes falham antes das alterações
- [x] 3.2 Atualizar `lumina/services/report_service.py` definindo a paleta de cores Lumina (laranja `#f8580a`, teal `#0e90a0`, ouro `#d9ae21`, texto tinta `#2b2b2b`, fundo claro `#efefef`), cabeçalhos, rodapés e capa institucional com logotipo Fiocruz
- [x] 3.3 Integrar a conversão de Markdown na síntese da release (`description`) e nos pareceres por critério (`feedback`), tratando também conteúdos legados em texto puro. Confirmar aprovação dos testes de integração

## 4. Verificação final e encerramento da issue

- [x] 4.1 Executar a suíte completa de testes de exportação e rotas relacionadas via `poetry run pytest`, confirmando que não há regressões
  - Resultado em 2026-10-24: `poetry run pytest` com 396 aprovados e 12 pulados (marcados como `ai`). Os 14 testes de `tests/unit/services/test_markdown_reportlab.py` e os 6 de `tests/integration/test_report_export.py` passam.
- [x] 4.2 Encerrar a issue #14 no GitHub (`gh issue close 14`) referenciando a resolução do bug de renderização de Markdown e a nova estilização institucional
