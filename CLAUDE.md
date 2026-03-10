# RAG Citation LangChain

A RAG-based API that automatically inserts APA 7th edition in-text citations into paragraphs using LangChain agents, Pinecone vector storage, and GROBID PDF parsing.

## Architecture

**Workflow:**
1. Upload a PDF → GROBID parses it into structured sections → chunks stored in Pinecone
2. Submit a paragraph → retriever agent breaks it into claims → fetches supporting docs from Pinecone → citator agent inserts APA citations

**Key components:**
- `main.py` — FastAPI app with `/upload-document` and `/get-citations` endpoints
- `services/agents.py` — Two LangChain agents: `document_retriever_agent` (finds supporting docs per claim) and `citator_agent` (inserts APA citations)
- `services/document_loading.py` — GROBID-based PDF parsing + tiktoken chunking (1500 tokens, 300 overlap)
- `infra/vector_store.py` — Pinecone vector store using VoyageAI `voyage-4-lite` embeddings (1024 dimensions, cosine similarity)
- `infra/auth.py` — Firebase Auth middleware
- `infra/firestore.py` — Firestore client and helpers
- `models.py` — Pydantic models for API requests/responses
- `docker-compose.yml` — GROBID service (`lfoppiano/grobid:0.8.2-crf` on port 8070)

## Setup

### Prerequisites
- Docker (for GROBID)
- Python 3.11+

### Environment Variables
Create a `.env` file:
```
ANTHROPIC_API_KEY=...
PINECONE_API_KEY=...
VOYAGE_API_KEY=...
```

### Start GROBID
```bash
docker compose up -d
```

### Install Dependencies
```bash
pip install -r requirements.txt  # or use uv/poetry if configured
```

### Run the API
```bash
uvicorn main:app --reload
```

## API Endpoints

- `POST /upload-document` — Upload a PDF file; returns `chunks_indexed` count
- `POST /get-citations` — Body: `{"paragraph": "..."}` — Returns paragraph with APA citations inserted

## External Services

| Service | Purpose | Config |
|---------|---------|--------|
| GROBID | PDF → TEI XML parsing | `http://localhost:8070` via Docker |
| Pinecone | Vector store | Index: `langchain-test-index`, AWS us-east-1 |
| VoyageAI | Embeddings | Model: `voyage-4-lite` |
| Anthropic | LLM agents | Model: `claude-sonnet-4-20250514` |

## Notes

- Similarity search uses score threshold of 0.5; retriever fetches top-1 doc per claim
- GROBID extracts authors and publication year from TEI header for APA citation metadata
- The citator agent only inserts citations supported by retrieved documents — it does not hallucinate citations
