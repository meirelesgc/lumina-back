# Verificação ABNT via engenharia de prompt (somente IA), com foco em elementos
# TEXTUAIS, ESTRUTURAIS, CITAÇÕES e REFERÊNCIAS -- NÃO reavalia aspectos
# tipográficos (papel, margens, fonte, espaçamento, numeração de página), que já
# são cobertos deterministicamente pela abordagem híbrida (hybrid_comparison.py).
#
# Portado de template_abnt_feature/abnt_comparison.py (dashboard Streamlit),
# removendo apenas o que era exclusivo de CLI/dashboard (argparse, main(),
# persistência via storage.py -- agora feita por json_store.py). A lógica de
# negócio (prompt, schema, chamada à IA) permanece intacta.
#
# O schema aqui é AUTOCONTIDO: uma lista PLANA de critérios
# (criterio/norma/justificativa/match), sem "checks" aninhados -- no mesmo
# espírito dos "criterios" visuais da abordagem híbrida.
#
# Os critérios recomendados abaixo (ABNT_RECOMMENDED_CRITERIA) são um GUIA de
# cobertura para o modelo, não uma lista fixa/obrigatória nem uma tabela rígida
# de valores normativos: o modelo tem liberdade para agrupar, desdobrar ou
# acrescentar critérios, e decide por conta própria qual norma NBR citar em
# cada item.

from __future__ import annotations

from pathlib import Path

from openai import OpenAI
from pydantic import BaseModel

AI_MODEL = 'gpt-5'


# --------------------------------------------------------------------------
# Schema (autocontido neste arquivo -- ver nota no topo).
# --------------------------------------------------------------------------

class AbntCriterionItem(BaseModel):
    criterio: str
    norma: str
    justificativa: str
    match: bool


class AbntAiBody(BaseModel):
    criterios: list[AbntCriterionItem]


class AbntSummary(BaseModel):
    is_compliant: bool
    criterios_total: int
    criterios_passed: int
    description: str


class AbntMetadata(BaseModel):
    approach: str
    model: str
    article_file: str


class AbntReport(BaseModel):
    metadata: AbntMetadata
    summary: AbntSummary
    criterios: list[AbntCriterionItem]


def build_report(metadata: AbntMetadata, criterios: list[AbntCriterionItem], description: str) -> AbntReport:
    passed = sum(1 for c in criterios if c.match)
    summary = AbntSummary(
        is_compliant=bool(criterios) and passed == len(criterios),
        criterios_total=len(criterios),
        criterios_passed=passed,
        description=description,
    )
    return AbntReport(metadata=metadata, summary=summary, criterios=criterios)


# --------------------------------------------------------------------------
# Critérios recomendados -- guia de cobertura para o prompt, NÃO um enum fixo.
# Organizados por bloco temático, focados em texto/estrutura/citações/referências.
# --------------------------------------------------------------------------

ABNT_RECOMMENDED_CRITERIA = """
## Elementos pré-textuais
- Presença obrigatória de Capa, Folha de Rosto, Resumo (na língua nativa), Abstract (em inglês) e
  Sumário -- calibre a exigência ao tipo de documento identificado (um artigo científico normalmente
  não tem capa/folha de rosto próprias como um TCC ou monografia).
- Resumo em parágrafo único (sem parágrafos extras), com 150 a 500 palavras (calibre a faixa ao tipo de
  documento: ~100-250 palavras costuma ser aceitável para artigos de periódico) e finalizado com
  palavras-chave separadas por ponto.
- Sumário alinhado ao corpo do texto: os títulos do sumário devem corresponder exatamente aos títulos do
  corpo (mesma numeração, mesmos termos, mesma formatação -- ex.: se um título está em negrito no corpo,
  deve estar em negrito também no sumário).

## Estrutura textual
- Corpo principal estruturado obrigatoriamente com Introdução, Desenvolvimento (dividido em seções) e
  Conclusão/Considerações Finais.

## Referências
- Lista de referências completa: todas as fontes citadas no texto devem aparecer nela, e nenhuma fonte
  que não foi citada no texto pode aparecer na lista.
- Ordem alfabética pelo sobrenome do primeiro autor.

## Citações
- Citações diretas curtas (até 3 linhas): inseridas no parágrafo normal, obrigatoriamente entre aspas,
  com indicação de autor, ano e página.
- Citações diretas longas (mais de 3 linhas): destacadas em bloco próprio, com recuo de 4 cm da margem
  esquerda, sem aspas e em espaçamento simples.
- Citações indiretas: indicação obrigatória do sobrenome do autor e do ano, sem uso de aspas.
- Caixa alta no sistema autor-data: sobrenome do autor todo em maiúsculas quando estiver dentro dos
  parênteses (ex.: "(SILVA, 2026)"), mas em letras normais quando fizer parte da frase (ex.: "Segundo
  Silva (2026)...").

## Figuras e tabelas
- Toda figura, gráfico ou tabela deve ter título explicativo no topo e indicação da fonte na parte
  inferior (mesmo que seja "Fonte: o autor").
- Nenhuma figura ou tabela pode ficar "solta": é obrigatório citá-la no texto antes de exibi-la (ex.:
  "conforme apresentado na Figura 1...").
""".strip()


def build_prompt() -> str:
    return f"""# Papel
Você é um especialista em normalização de trabalhos acadêmicos segundo as normas ABNT (NBR 14724,
NBR 6023, NBR 10520, NBR 6024, NBR 6028 e demais aplicáveis), com foco na parte TEXTUAL e ESTRUTURAL
do documento -- NÃO em aspectos tipográficos como papel, margens, fonte, espaçamento entre linhas,
recuo de parágrafo, alinhamento ou numeração de página (esses já são verificados por outra etapa
determinística do sistema).

# Objetivo
Ler o PDF fornecido na íntegra e auditar a conformidade da sua estrutura textual, citações e
referências com as normas ABNT, produzindo uma LISTA de critérios avaliados, cada um com o nome do
critério, a norma ABNT à qual ele se relaciona, uma justificativa concreta e um veredito (match).

# Contexto
- Identifique o tipo de documento a partir do próprio PDF (artigo científico, TCC, monografia,
  dissertação, tese etc.) e calibre as exigências de acordo com esse tipo -- não penalize elementos
  que não se aplicam (ex.: um artigo científico normalmente não tem capa/folha de rosto próprias).
- Você tem conhecimento próprio das normas ABNT: os aspectos listados abaixo são uma RECOMENDAÇÃO de
  cobertura, não uma lista fixa e obrigatória nem uma tabela rígida de valores. Reporte quantos
  critérios forem necessários para cobrir de forma completa e honesta o que você observar no
  documento -- podendo agrupar, desdobrar ou acrescentar critérios além dos sugeridos, sempre que
  fizer sentido para o documento em questão.

# Aspectos recomendados a cobrir
{ABNT_RECOMMENDED_CRITERIA}

# Instruções
- Para cada critério reportado, preencha:
  - **criterio**: nome curto e objetivo (ex.: "Presença do Resumo e Abstract", "Citação direta longa",
    "Ordem alfabética das referências").
  - **norma**: a norma ABNT correspondente (ex.: "NBR 6023", "NBR 10520"), escolhida por você de
    acordo com o aspecto avaliado.
  - **justificativa**: explicação concreta, citando trechos/observações do documento, do porquê houve
    ou não conformidade.
  - **match**: true se o critério está de acordo com a norma; false caso contrário.
- Se um elemento não existir no documento (ex.: não há citações longas), reporte isso com match=true
  quando a ausência não violar a norma, ou match=false quando a norma exigir o elemento e ele estiver
  ausente.
- Não invente observações que você não consiga inferir com confiança do PDF; nesse caso, seja honesto
  na justificativa sobre a limitação da verificação, mas ainda assim emita o julgamento mais provável.
- Ignore inteiramente aspectos tipográficos (papel, margens, fonte, espaçamento entre linhas, recuo de
  parágrafo, alinhamento, numeração de página): eles NÃO fazem parte desta auditoria.

# Formato de saída (obrigatório)
Retorne o campo **criterios**: array com um item por critério avaliado, no formato:
[
  {{"criterio": "Presença do Resumo e Abstract", "norma": "NBR 14724",
    "justificativa": "O documento apresenta Resumo em português (180 palavras) e Abstract em "
                      "inglês, ambos seguidos de palavras-chave separadas por ponto.", "match": true}},
  {{"criterio": "Ordem alfabética das referências", "norma": "NBR 6023",
    "justificativa": "A lista de referências não segue ordem alfabética: 'Silva (2020)' aparece "
                      "após 'Souza (2019)'.", "match": false}}
]

Cubra TODOS os blocos temáticos recomendados acima (pré-textuais, estrutura textual, referências,
citações, figuras/tabelas), com um ou mais critérios por bloco conforme aplicável ao documento."""


def upload_pdf(client: OpenAI, path: str) -> str:
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(file_path)
    uploaded = client.files.create(file=open(file_path, 'rb'), purpose='user_data')
    return uploaded.id


def build_input(article_id: str) -> list[dict]:
    return [
        {
            'role': 'user',
            'content': [
                {'type': 'input_file', 'file_id': article_id},
                {'type': 'input_text',
                 'text': 'Audite este documento quanto aos aspectos textuais, estruturais, de '
                         'citações e referências indicados nas instruções.'},
            ],
        }
    ]


def request_criteria(article_path: str) -> list[AbntCriterionItem]:
    client = OpenAI()
    article_id = upload_pdf(client, article_path)

    response = client.responses.parse(
        model=AI_MODEL,
        instructions=build_prompt(),
        input=build_input(article_id),
        text_format=AbntAiBody,
    )
    body = response.output_parsed
    if body is None:
        raise RuntimeError('Modelo não retornou saída estruturada (possível refusal).')
    return body.criterios


# Orquestração.
def compare(article_path: str) -> AbntReport:
    criterios = request_criteria(article_path)
    metadata = AbntMetadata(approach='abnt', model=AI_MODEL, article_file=article_path)
    description = (
        f'Auditoria via engenharia de prompt (IA, modelo {AI_MODEL}), focada em elementos textuais, '
        f'estruturais, citações e referências ABNT. Os {len(criterios)} critérios foram definidos '
        f'livremente pelo modelo a partir de um guia de aspectos recomendados (não são fixos).'
    )
    return build_report(metadata, criterios, description)
