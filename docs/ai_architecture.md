# Arquitetura de IA e Citation Tracking 🧠📄

Este documento descreve a arquitetura de Ingestão e Retenção de conhecimento do Lumina-back, especialmente focada no novo fluxo de Citation Tracking que mapeia coordenadas exatas para textos no frontend.

## 1. Visão Geral do Pipeline

O objetivo desta arquitetura é fornecer uma experiência de IA confiável e que embase as respostas diretamente com as evidências do documento fonte original, permitindo aos usuários clicarem na referência e serem levados magicamente para o trecho físico correspondente no arquivo (`.pdf`), com fallback funcional para outros documentos textuais (`.docx`, `.txt`).

O pipeline obedece à estrita regra arquitetural:
> **O LLM identifica os chunks baseados no conteúdo; o Backend resolve as coordenadas espaciais para uso no frontend.**

## 2. Ingestão e Chunking (Vector Service)

A ingestão de documentos é realizada no `lumina.services.vector_service.py` (`process_file`).

### 2.1. CoordinateChunker para PDF
Para PDFs originais (não-digitalizados com OCR), utilizamos a classe local `CoordinateChunker`. 
- Ao processar a página via PyMuPDF (`fitz`), agrupamos as palavras através de blocos e linhas físicas.
- Cada chunk é mantido dentro do tamanho limite (500 chars).
- O chunk recebe um identificador único de sessão `chunk_id` e metadados detalhados incluindo as caixas delimitadoras de cada linha (`rects`) e a página corrente (`page`).

### 2.2. Fallback Transparente para DOCX e TXT
Para documentos nativamente não baseados em viewport/rendering (DOCX e TXT), a quebra de texto é feita pelo `RecursiveCharacterTextSplitter`. 
- O contrato de dados não se rompe: esses chunks também recebem os atributos `chunk_id`, `page` e `rects`. 
- No entanto, `rects` é passado propositalmente como uma lista vazia `[]` e `page: 0`, garantindo previsibilidade para a engine de renderização no FrontEnd.

### 2.3. Modelagem de Metadados (PGVector)
O Vector Store (PGVector + SQLAlchemy + JSONB) deve armazenar os metadados exatamente na estrutura abaixo para que o Retriver tenha acesso determinístico pós-busca:
```json
{
  "chunk_id": "chunk_3_10",
  "page": 3,
  "rects": [[100, 200, 150, 210], [100, 215, 160, 225]],
  "section_title": "1. Introdução",
  "source": "lumina/storage/uploads/..."
}
```

## 3. Retrieval e Prompts (AI Service)

A recuperação (Retrieval) continua utilizando Similaridade de Cossenos baseada na string de query. Quando recuperados, os chunks passam por um processo de expansão contextual marginal (recuperar vizinhos próximos).

### Construção determinística do Contexto
O LLM não é onerado com dados de layout (como `rects` e `page`), já que números de ponto flutuante causam poluição e potencial alucinação. 
Ao invés disso, os chunks são entregues marcados deterministicamente.
```text
[FONTE] chunk_id: chunk_3_10
SECTION: 1. Introdução
Texto do conteúdo vai aqui...
```

## 4. LLM e Saída Estruturada

Usamos a capacidade funcional `with_structured_output` (`lumina/schemas/ai.py`) forçando o modelo a responder num JSON Pydantic estrito:
```python
class Citation(BaseModel):
    chunk_id: str
    text_snippet: Optional[str]

class AnswerWithCitations(BaseModel):
    answer: str
    citations: List[Citation]
```
O Prompt `CHAT` tem diretrizes fortificadas ordenando a vinculação e listagem obrigatória do ID, emulando rastreamento de referência acadêmica.

## 5. Resolução e Validação (Security & Mapping)

Essa é a barreira final de segurança do RAG.
A IA pode alucinar ou distorcer citações, logo não confiamos no seu cruzamento.

A função `resolve_citations` pega as respostas do LLM e intercede comparando os IDs enviados pela LLM com a lista em memória (chunks retidos após a busca similar).
- **Citação Falsa:** Se a LLM retornar um "chunk_falso_09", a validação silenciosamente ignora, protegendo a API.
- **Citação Válida:** O Backend funde a citação com os metadados (resgatando `rects` e `page` originais).
- **Fallback Válido (DOCX/TXT):** O Backend repassa a citação, com `rects = []`.

## 6. Saída HTTP
Finalmente, a camada de transporte (Router: `/doc/{doc_id}/message/ai`) desserializa os DTOs Pydantic devolvendo um JSON para o cliente que renderizará isso interativamente:
```json
{
    "answer": "O uso de IA é altamente recomendado para este projeto de software.",
    "citations": [
        {
            "chunk_id": "chunk_1_5",
            "text_snippet": "altamente recomendado",
            "page": 1,
            "rects": [[12.0, 55.4, 20.3, 60.1]]
        }
    ]
}
```
