# LUMINA — Design System

Este arquivo é a referência única de aparência para tudo que levar a marca **LUMINA** (Fiocruz): relatórios em PDF, apresentações, páginas web e telas. Quem for criar algo novo (pessoa ou agente de IA) deve ler este arquivo e usar os arquivos desta pasta, sem inventar cores, fontes ou logos.

**Origem dos valores.** Tudo o que está marcado como *(guia)* foi extraído do PDF "LUMINA guia de marca". Tudo o que está marcado como *(derivado)* foi acrescentado aqui porque o guia não define (por exemplo, cor de texto corrido). Se a Fiocruz fornecer regras oficiais para esses pontos, elas valem mais que este arquivo.

---

## 1. Ideia da marca (guia)

- **Nome:** do latim *lumen*, luz, clareza, iluminação. LUMINA é o plural: múltiplas luzes, múltiplos caminhos, múltiplas produções.
- **Frase:** "Transforme **processos** em resultados" (a palavra *processos* em negrito, o resto em Lexend Light).
- **Site:** lumina.fiocruz.br
- **Tom visual:** quente e luminoso. Laranja forte como cor dominante, formas geométricas arredondadas, muito espaço livre, cantos grandes.

## 2. Cores

### Cores da marca (guia)

| Nome | Hex | Uso principal |
|---|---|---|
| Laranja | `#f8580a` | Cor dominante: capas, títulos grandes, destaques, fundo de blocos |
| Ouro | `#d9ae21` | Secundária: blocos e formas |
| Teal | `#0e90a0` | Secundária: tags, blocos, cabeçalho de tabela |
| Claro | `#efefef` | Fundo padrão de páginas e texto sobre cores da marca. **Não use branco puro como fundo de página.** |

### Tons de apoio (guia, só para formas e linhas)

| Nome | Hex | Onde aparece |
|---|---|---|
| Laranja claro | `#f77948` | Linhas e grade da capa, losangos |
| Ouro escuro | `#b58d1d` | Formas sobre ouro |
| Teal escuro | `#0b6970` | Formas sobre teal |

### Cinzas do logo monocromático (guia)

`#b2b2b2` · `#9d9d9c` · `#878787` · `#706f6f`

### Derivados para texto e interface (derivado)

| Nome | Hex | Uso |
|---|---|---|
| Tinta | `#2b2b2b` | Texto corrido, tabelas |
| Laranja texto | `#b04406` | Texto laranja pequeno (rótulos, destaque dentro de parágrafo) |
| Teal texto | `#0b6970` | Links, subtítulos (h3), números de seção |
| Papel | `#ffffff` | Fundo de cartões sobre `#efefef` |
| Linha | `#d6d6d6` | Fios e bordas de tabela |

### Contraste (importante)

O laranja da marca **não tem contraste suficiente** para texto pequeno. Valores calculados (WCAG, mínimo 4,5:1 para texto normal e 3:1 para texto grande):

| Combinação | Contraste | Regra |
|---|---|---|
| Tinta `#2b2b2b` sobre claro `#efefef` | 12,3:1 | Texto corrido |
| Teal escuro `#0b6970` sobre claro | 5,6:1 | Texto pequeno e links |
| Laranja texto `#b04406` sobre claro | 5,0:1 | Texto laranja pequeno |
| Tinta sobre ouro `#d9ae21` | 6,8:1 | Único texto permitido sobre ouro |
| Tinta sobre laranja | 4,3:1 | Aceitável para texto médio |
| Claro sobre teal `#0e90a0` | 3,3:1 | Só texto grande ou em negrito (≥ 14 pt) |
| Branco sobre laranja `#f8580a` | 3,3:1 | Só texto grande (títulos, números, capa) |
| Laranja `#f8580a` sobre claro | 2,9:1 | **Só títulos grandes e elementos gráficos**, nunca parágrafos |
| Claro sobre ouro | 1,8:1 | **Proibido** |

## 3. Tipografia (guia)

| Papel | Família | Pesos | Observação |
|---|---|---|---|
| Títulos | **Barlow** | Medium (500), SemiBold (600) | Cor laranja (h1, h2) ou teal escuro (h3) |
| Corpo, parágrafos, web | **Lexend** | Light (300), Regular (400), SemiBold (600), Bold (700), ExtraBold (800) | Corpo em Light; negrito para ênfase |

As fontes estão em `assets/fonts/` (WOFF2, subconjunto latino, licença OFL). Para uso fora do navegador (Word, PowerPoint, Illustrator), baixe as famílias completas em fonts.google.com.

### Escala para relatório em PDF (derivado)

| Elemento | Fonte | Tamanho | Entrelinha |
|---|---|---|---|
| Capa — título | Barlow 600 | 54 pt | 1,0 |
| Título 1 (seção) | Barlow 600 | 34 pt | 1,05 |
| Título 2 | Barlow 600 | 20 pt | 1,05 |
| Título 3 | Barlow 600 | 14 pt | 1,05 |
| Texto de abertura (lead) | Lexend 300 | 13 pt | 1,45 |
| Texto corrido | Lexend 300 | 10 pt | 1,55 |
| Tabela | Lexend 300/700 | 9 pt | — |
| Legendas e notas | Lexend 300 | 8 pt | — |
| Rótulo de seção ("01") | Lexend 800 | 9 pt, caixa alta | — |

Para web, use a mesma proporção em `rem` (1 rem = 16 px = corpo; títulos 1,25× a 3,5×).

## 4. Logo (guia)

O guia traz quatro versões, cada uma extraída em vetor (SVG) em `assets/logos/`:

| Versão | Arquivo | Quando usar |
|---|---|---|
| Horizontal | `lumina-horizontal-*.svg` | Padrão: cabeçalhos, rodapés, web |
| Horizontal + Fiocruz | `lumina-fiocruz-*.svg` | Capas e contracapas (assinatura institucional) |
| Vertical | `lumina-vertical-*.svg` | Espaços estreitos e altos |
| Abreviada | `lumina-abreviada-*.svg` | Espaços muito pequenos |
| Símbolo | `simbolo-*.svg`, `icone-app-*.svg` | Favicon, avatar, ícone de aplicativo |
| Assinatura Fiocruz | `fiocruz-assinatura-*.svg`, `fiocruz-castelo-*.svg` | Quando só a Fiocruz deve aparecer |

Sufixos de cor: `-laranja` (`#f8580a`), `-claro` (`#efefef`), `-teal` (`#0e90a0`), `-cinza` (`#706f6f`).

Regras:
- Sobre laranja, teal ou ouro escuro: versão **clara**. Sobre fundo claro ou branco: versão **laranja** (ou cinza em material monocromático).
- Não esticar, girar, recolorir fora das cores acima nem adicionar sombra.
- O guia não define área de proteção nem tamanho mínimo *(derivado, sugestão)*: deixe ao redor do logo um espaço igual à altura da letra "L" e não use o logo horizontal com menos de 25 mm de largura (impressão) ou 100 px (tela).

## 5. Elementos gráficos (guia)

Em `assets/elements/`:

- `composicao-elementos.svg` — a composição da página "Elementos" do guia (círculos, pétalas, estrela, cruz). Serve para aberturas e páginas de destaque.
- `forma-*.svg` — as formas individuais, cada uma como camada de página inteira.
- `grade-cruz-capa.svg` — a grade de linhas em laranja claro com cantos arredondados usada na capa. Em capas retrato, use `object-fit: cover; object-position: right top`.

Princípios: formas simples, cantos arredondados, cores chapadas (sem degradê, sem sombra), sobreposição de cores da marca e de seus tons de apoio.

## 6. Forma e espaço (guia + derivado)

- **Cantos:** muito arredondados. Cartões e blocos usam raio de 8 mm (≈ 28 px); componentes menores, 4 mm; tags, 2 mm; botões em pílula.
- **Linhas:** contornos de 0,25 mm em laranja (cartão de contorno, trilho lateral).
- **Respiro:** margens generosas; entre blocos, 4 mm (≈ 16 px).
- **Fundos:** `#efefef` em páginas internas; laranja em capa e contracapa; branco só dentro de cartões.

### Assinatura do guia: o trilho lateral

Todas as páginas do guia têm, à esquerda, um retângulo vertical de cantos arredondados e contorno fino, com o castelo da Fiocruz no topo, o nome do documento escrito na vertical (**LUMINA** em negrito + resto em Light) e o número da página no formato `001` na base. O template de relatório reproduz isso em todas as páginas internas.

## 7. Layout do relatório em PDF

Formato **A4 retrato**. Arquivos: `templates/relatorio-modelo.html`, `css/report.css`.

| Área | Medida |
|---|---|
| Margem superior / inferior | 20 mm |
| Margem esquerda (com trilho) | 34 mm |
| Margem direita | 16 mm |
| Trilho lateral | 11 mm de largura, a 10 mm da borda esquerda |
| Capa e contracapa | Sem margem (sangria total), fundo laranja |

Estrutura de um relatório, em ordem:

1. **Capa** — fundo laranja, grade de cruz, logo LUMINA + Fiocruz (claro) no alto, título em Barlow 54 pt claro, subtítulo em Lexend Light, rodapé com setor, data, versão e site.
2. **Sumário** — lista numerada com fio entre itens.
3. **Seções** — cada uma começa em página nova: rótulo numérico (teal), título 1 em laranja, depois o conteúdo.
4. **Contracapa** — fundo laranja, logo centralizado, frase "Transforme **processos** em resultados" e o site.

Blocos disponíveis (classes em `css/base.css` e `css/report.css`):

| Bloco | Classe | Observação |
|---|---|---|
| Texto de abertura | `.lead` | Lexend 13 pt, negrito em laranja texto |
| Indicadores | `.kpis` + `.kpi--laranja / --teal / --ouro / --claro` | Três por linha; valor em Barlow 30 pt |
| Cartão | `.cartao`, `.cartao--contorno`, `--laranja`, `--teal`, `--ouro` | Cantos 8 mm |
| Chamada | `.chamada`, `--teal`, `--laranja` | Barra lateral colorida |
| Tabela | `table` | Cabeçalho teal com texto claro em caixa alta, linhas com fio fino, números alinhados à direita |
| Barras | `.barras` / `.barra` | Gráfico simples sem biblioteca; cores alternam laranja, teal, ouro |
| Duas colunas | `.duas-colunas` | Grade 1fr 1fr, espaço de 8 mm |
| Figura e legenda | `figure` + `figcaption` | Legenda 8 pt cinza |
| Tag | `.tag`, `--laranja`, `--ouro` | Texto claro sobre teal; ouro usa texto tinta |

### Gráficos e dados

Ordem das cores em séries: laranja → teal → ouro → laranja escuro `#b04406` → teal escuro `#0b6970`. Não depender só da cor: use rótulos diretos ou padrões quando houver mais de três séries. Fundo do gráfico: transparente ou papel branco.

## 8. Como usar em um projeto novo

1. Copie esta pasta (ou mantenha-a como submódulo/pacote compartilhado).
2. No HTML, carregue na ordem: `tokens/tokens.css`, `css/base.css` e, para PDF, `css/report.css`.
3. Use as variáveis (`var(--lumina-laranja)`, `var(--fonte-titulo)`) em vez de valores soltos.
4. Para PDF: `python3 scripts/build_pdf.py templates/relatorio-modelo.html saida.pdf` (requer Playwright com Chromium).
5. Para interfaces web com Tailwind: `presets: [require('./tokens/tailwind.preset.js')]`.
6. Para Word/PowerPoint/Illustrator: use os hex acima, instale Lexend e Barlow e insira os logos em SVG (ou converta para PNG/EMF).

### Instruções para agentes de IA

- Leia este arquivo antes de gerar qualquer layout. Use só as cores, fontes e logos daqui.
- Texto corrido: `#2b2b2b` sobre `#efefef` ou branco. Nunca parágrafo em laranja, ouro ou teal claros.
- Títulos: Barlow SemiBold. Corpo: Lexend Light. Tudo o mais é variação de peso, não de família.
- Não redesenhe o logo; referencie os SVGs de `assets/logos/`.
- Cantos sempre arredondados; sem sombras, sem degradês.
- Se precisar de um valor que não existe aqui, adicione-o em `tokens/tokens.json` **e** `tokens/tokens.css`, marcado como *(derivado)*, e registre neste arquivo.

## 9. Limites conhecidos

- O guia original tem 7 páginas e não define: cor de texto corrido, escala tipográfica, área de proteção do logo, tamanho mínimo, cores de estados (erro, sucesso) nem modo escuro. Os valores dessas áreas aqui são *(derivados)* e sugeridos.
- As fontes vêm em subconjunto latino (cobre português, inglês, espanhol, francês). Para outros alfabetos, use as famílias completas.
- Chromium não calcula números de página no sumário automaticamente: escreva-os à mão se precisar.
- Os logos foram extraídos como vetores do PDF; confira com a equipe da Fiocruz se existe um pacote oficial de arquivos e prefira-o se houver diferença.
