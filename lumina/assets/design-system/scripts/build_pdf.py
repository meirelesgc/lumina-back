#!/usr/bin/env python3
"""Gera um PDF A4 a partir de um HTML LUMINA usando Chromium (Playwright).

Uso:
    python3 scripts/build_pdf.py templates/relatorio-modelo.html exemplos/relatorio-exemplo.pdf

Instalação (uma vez):
    pip install playwright
    playwright install chromium
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright


def build(html_path: Path, pdf_path: Path) -> None:
    html_path = html_path.resolve()
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(html_path.as_uri(), wait_until="networkidle")
        page.evaluate("document.fonts.ready")  # garante Lexend e Barlow carregadas
        page.emulate_media(media="print")
        page.pdf(
            path=str(pdf_path),
            prefer_css_page_size=True,   # usa @page (A4 e margens do report.css)
            print_background=True,       # mantém fundos laranja, teal e ouro
        )
        browser.close()
    print(f"PDF gerado: {pdf_path}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    build(Path(sys.argv[1]), Path(sys.argv[2]))
