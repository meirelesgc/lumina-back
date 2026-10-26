# Design Técnico: Exportação de Relatórios em PDF com Identidade Visual e Parser Markdown

## Contexto

A Issue #14 relata que a síntese de documentos e os pareceres de critérios em releases exibem formatação Markdown crua e linhas colapsadas quando exportados em PDF via ReportLab. O repositório contém uma pasta `design-system` com ativos visuais, paletas de cores, fontes e diretrizes da marca LUMINA (Fiocruz). A aplicação utiliza FastAPI e ReportLab. Veja [proposal.md](proposal.md) para a motivação.

## Objetivos e Não-Objetivos

**Objetivos:**
- Mover a pasta `design-system` para `lumina/assets/design-system/` para disponibilizar ativos e tokens dentro do pacote da aplicação.
- Implementar um conversor de Markdown para elementos do ReportLab (`Flowable`), suportando títulos, ênfases (negrito e itálico), listas e tabelas GFM com escape de XML.
- Atualizar a estética do relatório em [lumina/services/report_service.py](file:///home/gls/Travail/Fiocruz/Lumina/lumina-back/lumina/services/report_service.py), adotando as cores da marca (laranja `#f8580a`, teal `#0e90a0`, ouro `#d9ae21`, texto tinta `#2b2b2b`), espaçamentos adequados e cabeçalho institucional.
- Garantir retrocompatibilidade para conteúdos em texto puro sem formatação.

**Não-Objetivos:**
- Não migrar o motor de PDF para Chromium/Playwright ou WeasyPrint nesta etapa, mantendo o ReportLab para evitar novas dependências de sistema no contêiner.
- Não alterar contratos de dados dos endpoints nem adicionar novas rotas de exportação nesta mudança.

## Decisões Técnicas

### 1. Localização dos ativos em `lumina/assets/design-system/`
- **Decisão**: Mover a pasta `design-system` da raiz do repositório para `lumina/assets/design-system/`.
- **Justificativa**: Permite referenciar caminhos absolutos e relativos de logos, tokens e fontes a partir de `Path(__file__).parent.parent / 'assets' / 'design-system'` em tempo de execução e durante o empacotamento do Poetry.
- **Alternativas consideradas**: Manter na raiz (dificulta distribuição em pacotes e empacotamento Docker) ou espalhar em pastas soltas `lumina/templates` e `lumina/css`.

### 2. Conversor Modular de Markdown para ReportLab
- **Decisão**: Criar o utilitário `lumina/utils/markdown_reportlab.py` contendo a função `markdown_to_flowables(text: str, styles: StyleSheet1) -> list[Flowable]`.
- **Justificativa**: Desacopla a regra de conversão de texto rico do layout específico de relatórios, facilitando testes unitários focados em cada elemento (títulos, listas, tabelas e parágrafos).
- **Funcionamento**:
  1. Quebra o texto em blocos de linha.
  2. Detecta tabelas GFM (delimitadas por `|`), extrai cabeçalho e linhas, calculando larguras de coluna e gerando `Table` com `TableStyle` da paleta Lumina.
  3. Detecta itens de lista (`- `, `* `, `1. `), gerando parágrafos com recuo e marcador.
  4. Detecta títulos (`# `, `## `, `### `), aplicando os estilos de cabeçalho correspondentes.
  5. Escapa entidades XML (`&` para `&amp;`, `<` para `&lt;`, `>` para `&gt;`) antes de injetar as tags seguras do ReportLab (`<b>`, `<i>`, `<font>`).
- **Alternativas consideradas**: Usar bibliotecas externas pesadas como `xhtml2pdf` ou `mistune` compilando HTML intermediário. O conversor direto em Python puro oferece controle exato sobre os `Flowables` sem adicionar dependências de terceiros.

### 3. Paleta de Cores e Estilos no `report_service.py`
- **Decisão**: Definir cores constantes baseadas nos tokens do Lumina:
  - `COR_LARANJA = colors.HexColor('#f8580a')`
  - `COR_TEAL = colors.HexColor('#0e90a0')`
  - `COR_OURO = colors.HexColor('#d9ae21')`
  - `COR_TINTA = colors.HexColor('#2b2b2b')`
  - `COR_FUNDO = colors.HexColor('#efefef')`
  - `COR_LINHA = colors.HexColor('#d6d6d6')`
- **Justificativa**: Uniformiza os relatórios de release e tipificação com as regras definidas no `DESIGN.md`.

### 4. Fontes Barlow e Lexend convertidas para TTF
- **Decisão**: Converter uma única vez os arquivos WOFF2 de `assets/fonts/` para TTF com `fontTools` e versionar os TTF ao lado dos originais. O `report_service.py` registra Barlow 600 nos títulos e Lexend 300 e 700 no corpo via `TTFont`.
- **Justificativa**: O ReportLab só lê TTF e OTF. A conversão roda fora da aplicação, então `fontTools` não entra nas dependências do projeto. Decidido com o usuário em 2026-10-24.
- **Alternativas consideradas**: Manter Helvetica (foge da tipografia do guia).
- **Itálico**: Lexend não tem variante itálica. O `<i>` vindo do Markdown usa Lexend Regular (400), que se destaca do corpo em Light (300).

### 5. Logos SVG desenhados com `svglib`
- **Decisão**: Adicionar `svglib` às dependências e desenhar os logos SVG como vetor na capa e no rodapé.
- **Justificativa**: `svglib` é Python puro sobre `lxml` e não exige pacote de sistema no contêiner. Mantém os SVGs do design system como fonte única. Decidido com o usuário em 2026-10-24.
- **Alternativas consideradas**: PNGs gerados a partir dos SVGs (raster e ativos duplicados) ou logo em texto (não usa a marca oficial).

## Riscos e Mitigações

- **[Risco]** Erro de sintaxe XML no ReportLab se o Markdown contiver tags arbitrárias ou operadores `<` e `&`.
  - **Mitigação**: Função de sanitização que escapa previamente qualquer caractere `<` e `&` do texto de entrada antes de aplicar as marcações de negrito e itálico.
- **[Risco]** Tabelas com muitas colunas estourarem a largura útil da folha A4.
  - **Mitigação**: O gerador de tabelas divide a largura útil total da página (17 cm) igualmente entre as colunas detectadas, encapsulando o texto das células em `Paragraph` para suportar quebras automáticas de linha.
- **[Risco]** Releases antigas sem formatação Markdown sofrerem quebras no layout.
  - **Mitigação**: O parser trata parágrafos sem marcadores como texto padrão, preservando quebras de linha existentes.
