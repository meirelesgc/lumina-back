# LUMINA — pasta de design

Tudo o que você precisa para manter a mesma aparência em relatórios em PDF, páginas web e outros materiais.

## Comece por aqui

| Arquivo | Para quê |
|---|---|
| `DESIGN.md` | Regras de cor, fonte, logo, layout e uso. Leia primeiro (serve também como instrução para agentes de IA). |
| `guia-de-estilos.html` | Versão visual: abra no navegador para ver cores, fontes, logos e componentes. |
| `templates/relatorio-modelo.html` | Modelo de relatório A4 (capa, sumário, seções, contracapa). Copie e edite. |
| `exemplos/relatorio-exemplo.pdf` | Como o modelo fica pronto. |

## Estrutura

```
lumina-design-system/
├── DESIGN.md
├── README.md
├── guia-de-estilos.html
├── tokens/
│   ├── tokens.json            valores (cores, fontes, espaços, página)
│   ├── tokens.css             os mesmos valores como variáveis CSS + @font-face
│   └── tailwind.preset.js     preset opcional para Tailwind
├── css/
│   ├── base.css               tipografia e componentes (web e PDF)
│   └── report.css             layout de PDF A4 (página, trilho, capa, KPIs, barras)
├── assets/
│   ├── logos/                 SVG: horizontal, vertical, abreviada, símbolo, Fiocruz, ícones
│   ├── elements/              SVG: formas e grade de capa
│   └── fonts/                 Lexend e Barlow (WOFF2) + licenças OFL
├── templates/
│   └── relatorio-modelo.html
├── scripts/
│   └── build_pdf.py           HTML → PDF com Chromium
└── exemplos/
    └── relatorio-exemplo.pdf
```

## Gerar um PDF

Instale uma vez:

```
pip install playwright
playwright install chromium
```

Depois:

```
python3 scripts/build_pdf.py templates/relatorio-modelo.html exemplos/relatorio-exemplo.pdf
```

Para um relatório novo, copie `templates/relatorio-modelo.html`, troque o texto e rode o mesmo comando com o novo nome. Para mudar o texto vertical do trilho lateral, edite `--titulo-doc` no `<style>` do HTML.

## Regras de ouro

1. Texto corrido em `#2b2b2b`, nunca em laranja, ouro ou teal.
2. Fundo de página `#efefef`, não branco puro.
3. Títulos em Barlow SemiBold, corpo em Lexend Light.
4. Logo só pelos SVGs da pasta `assets/logos/`.

## Observação

As cores, fontes e logos vêm do guia de marca. Texto corrido (`#2b2b2b`), escala tipográfica e layout do relatório foram definidos aqui e estão marcados como *derivados* no `DESIGN.md`.
