# Validation Documents

Este diretório é reservado para armazenar documentos utilizados na validação e avaliação das respostas do LLM (Ground Truth). 

Recomenda-se manter um formato estruturado (como JSON, CSV ou JSONL) para mapear o documento original à sua resposta esperada.

**Exemplo de estrutura (JSON):**
```json
[
  {
    "document_path": "doc_01.txt",
    "question": "Qual é a informação X do documento?",
    "expected_answer": "A informação X é Y.",
    "metadata": {
      "difficulty": "easy"
    }
  }
]
```
