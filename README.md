# 🔍 Behind The RAG

> A visual walkthrough of how enterprise RAG systems actually work — every step, every decision, enterprise detail at every layer.

---

## What is this?

**Behind The RAG** is an interactive educational app built for product managers, engineers, and anyone trying to understand how enterprise AI assistants actually work under the hood.

You have used Perplexity. You type a question, it searches the web, finds the most relevant pages, and gives you an answer with citations. That experience is **RAG — Retrieval Augmented Generation**. The AI does not answer from memory. It finds the right information first, then generates an answer grounded in what it found.

This app walks you through every layer of that pipeline — not as a diagram, but as a live, interactive system you can run yourself.

---

## What you'll learn

The app covers two pipelines end to end:

### 📦 Offline Pipeline — How the knowledge base gets built
| Step | What it covers |
|------|---------------|
| 1 | Document Ingestion + Parsing |
| 2 | Parsing + Cleaning |
| 3 | Chunking Strategy |
| 4 | Metadata Tagging |
| 5 | Embedding |
| 6 | Indexing (HNSW) |

### 🔍 Online Pipeline — What happens every time you ask a question
| Step | What it covers |
|------|---------------|
| 7 | Query Understanding + HyDE |
| 8 | Query Embedding |
| 9 | Vector Search + Hybrid Retrieval |
| 10 | Re-ranking |
| 11 | Context Ordering + Assembly |
| 12 | LLM Generation |
| 13 | Grounding Evaluation |
| 14 | RAGAS LLM-as-Judge |
| 15 | Observability + Drift Detection |

Each step includes:
- **What it does** — plain English explanation
- **Live demo** — runs the actual algorithm on real documents
- **Enterprise context** — what production systems actually do differently
- **PM Decision Matrix** — the decisions a PM owns at this layer, what to ask, real-world examples, and enterprise standards

---

## Who it's for

- **Product managers** learning to make informed decisions about RAG systems
- **Engineers** who want to see all the moving parts in one place
- **Anyone** curious about how enterprise AI actually works beyond the marketing

No prior ML knowledge required. The app explains every concept in plain English.

---

## Try it live

🚀 **[Launch the app](https://behind-the-rag.streamlit.app)**

Add your API key in the sidebar under **Settings** to enable the online pipeline steps. A free key from [Google AI Studio](https://aistudio.google.com) (Gemini) is the easiest option — no credit card required.

Optional: a free [Cohere](https://cohere.com) key enables live re-ranking in Step 10.

---

## Knowledge base

The app ships with 5 public research documents on RAG:

| Document | Why it's included |
|----------|------------------|
| Lewis et al. — RAG Paper (arXiv:2005.11401) | The original RAG research that started it all |
| LangChain Documentation | How the most popular RAG framework structures the pipeline |
| Lilian Weng — Retrieval Augmented Generation | The best conceptual overview of RAG components |
| RAGAS Documentation | How to evaluate RAG pipelines quantitatively |
| Pinecone — Vector Database Guide | How production vector stores work |

---

## Tech stack

| Layer | What's used |
|-------|------------|
| App framework | [Streamlit](https://streamlit.io) |
| Embeddings | [fastembed](https://github.com/qdrant/fastembed) — `all-MiniLM-L6-v2`, local, no API key needed |
| Vector search | [usearch](https://github.com/unum-cloud/usearch) — HNSW index |
| Re-ranking | [Cohere](https://cohere.com) `rerank-english-v3.0` (optional) |
| LLM generation | Gemini · Claude · OpenAI (your choice, your key) |
| Evaluation | [RAGAS](https://ragas.io) — faithfulness, answer relevancy, context precision, context recall, answer correctness |

---

## Project structure

```
behind-the-rag/
├── app.py                    # Main entry point + sidebar
├── ui.py                     # Shared UI components
├── state.py                  # Session state + navigation
├── requirements.txt
├── config/
│   └── content.py            # Static content constants
├── knowledge_base/
│   ├── kb.py                 # Chunk dataclass, search, HNSW index
│   ├── loader.py             # KB loader + embedding build
│   └── *.txt                 # 5 source documents
└── steps/
    ├── s00_landing.py        # Landing page
    ├── s01_ingestion.py      # Step 1: Ingestion + Parsing
    ├── s02_parsing.py        # Step 2: Parsing + Cleaning
    ├── s03_chunking.py       # Step 3: Chunking
    ├── s04_embedding.py      # Step 4: Embedding (offline)
    ├── s05_metadata.py       # Step 5: Metadata Tagging
    ├── s06_indexing.py       # Step 6: Indexing
    ├── s07_query_understanding.py
    ├── s08_query_embedding.py
    ├── s09_vector_search.py
    ├── s10_reranking.py
    ├── s11a_context_assembly.py
    ├── s11b_context_ordering.py
    ├── s12_generation.py
    ├── s13_grounding.py
    ├── s14_judge.py
    └── s15_observability.py
```

---

## Notes

- This is a **learning demo**, not a production system. The goal is to make every layer visible and understandable.
- The offline pipeline runs once per session. The online pipeline runs on every query.
- All embeddings run **locally** (no API key needed for the offline pipeline).
- API keys are never stored — they live only in your browser session.

