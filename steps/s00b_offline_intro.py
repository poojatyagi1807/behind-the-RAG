"""Step 0b — Offline pipeline intro: diagram + table before diving into steps."""
import streamlit as st
import os
from state import go_to, go_back

STEPS_TABLE = [
    {
        "step": "1. Document Ingestion + Parsing",
        "significance": "The front door and the first transformation. Documents arrive in any format — PDFs, wikis, Slack threads, spreadsheets, source code. Each format needs a specialist parser to preserve structure. Tables must stay as tables, images must be described, code must stay syntactically intact. What enters the pipeline here determines the ceiling of everything downstream.",
        "enterprise": "Dedicated data engineering teams own this. Apache Airflow or AWS Glue pipelines with 50+ connector types. AWS Textract and Azure Document Intelligence for structure-preserving parsing. Microsoft Presidio for PII. Specialist parsers per content type. ACLs preserved from source. This is months of work in production, not hours.",
        "we_do": "We load 5 public documents with a simple text loader and apply basic cleaning. In production this is a full pipeline: source connectors → type classifier → specialist parsers (OCR, AST, HTML) → quality & compliance → metadata enrichment. We keep it simple so the focus stays on the retrieval-specific decisions downstream.",
        "note": "⚠️ High complexity",
    },
    {
        "step": "2. Chunking",
        "significance": "The highest-leverage decision in the offline pipeline. Where you cut determines what the retriever finds. Too small — chunks lose context. Too large — chunks lose precision. Wrong strategy for your document type — silent retrieval failures at scale.",
        "enterprise": "LangChain RecursiveCharacterTextSplitter (most common default). Unstructured.io for structure-aware chunking. LlamaIndex HierarchicalNodeParser for nested documents. Chunk size decisions made empirically — benchmarked against real queries.",
        "we_do": "Fixed token chunking with 400 token size and 75 token overlap. Dropdown lets you explore all four strategies and see the difference on the same paragraph.",
        "note": "",
    },
    {
        "step": "3. Metadata Tagging",
        "significance": "Vectors tell you what chunks are similar. Metadata tells you which ones are actually relevant. Source, document type, section, permissions, timestamps — filtering on metadata before retrieval dramatically improves precision and enables access control.",
        "enterprise": "Glean maintains 50+ metadata fields per document. AWS Knowledge Base and Azure AI Search support metadata filtering natively. Auto-tagging pipelines use Amazon Comprehend or Azure Cognitive Services to extract metadata at scale without manual labeling.",
        "we_do": "15 metadata fields per chunk — structural (source, type, section, has_code, has_tables, has_citations, position, word count, timestamp), access control (allowed_roles, department, clearance_level), and freshness (created_at, updated_at, version). Tagging happens before embedding so metadata can optionally be prepended to chunk text to influence the vector.",
        "note": "",
    },
    {
        "step": "4. Embedding",
        "significance": "Convert meaning into math. Chunks become vectors in a high-dimensional space where semantic similarity equals geometric closeness. The embedding model you choose determines what 'similar' means — and therefore what retrieves. Critical rule: same model in, same model out, always.",
        "enterprise": "OpenAI text-embedding-3-small/large, Cohere embed-multilingual-v3, Amazon Bedrock Titan Embeddings. Embedding registries (MLflow, SageMaker) enforce model version consistency. Hybrid search combines dense + sparse vectors for best results.",
        "we_do": "all-MiniLM-L6-v2 (fastembed, local) — 384-dimensional dense vectors. No API key required. Same model used in the online pipeline to embed queries, ensuring consistent vector spaces.",
        "note": "",
    },
    {
        "step": "5. Vector Store Indexing",
        "significance": "Store vectors in a structure that enables millisecond search across millions of chunks. HNSW graphs navigate like finding a friend in a new city — coarse to precise, skipping most comparisons. Index type and parameters directly affect retrieval speed, accuracy, and memory cost.",
        "enterprise": "Pinecone (managed, auto-scaling), Weaviate (open source, self-hostable), pgvector (PostgreSQL extension), AWS OpenSearch. Hybrid indexing — HNSW for dense + BM25 for sparse — is the production standard. Re-indexing pipelines triggered by document changes, not schedules.",
        "we_do": "In-memory TF-IDF index — fast to build, sufficient for 312 chunks across 5 documents.",
        "note": "",
    },
]

def render():
    st.markdown("""
<div style="margin-bottom:20px">
  <div style="font-size:22px;font-weight:700;color:#ffffff;
  margin-bottom:6px">📦 Offline Pipeline — What you are about to build</div>
  <div style="font-size:13px;color:var(--color-text-secondary)">
    Five steps. Runs once. Every query that follows lives or dies by the
    decisions made here.
  </div>
</div>
""", unsafe_allow_html=True)

    # Show the enterprise architecture diagram
    asset_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "offline_pipeline.png")
    if os.path.exists(asset_path):
        st.image(asset_path, caption="Enterprise RAG offline pipeline — system architecture", use_container_width=True)
    else:
        st.info("Architecture diagram not found — ensure offline_pipeline.png is in the assets/ folder.")

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # Data engineering note
    st.markdown("""
<div style="background:#FAEEDA;border:0.5px solid #FAC775;border-radius:8px;
padding:12px 16px;margin-bottom:20px;font-size:12px;color:#4A2800;line-height:1.6">
  <strong>A note on Step 1 — Document Ingestion + Parsing:</strong><br>
  This is an entire discipline in itself — data engineering teams spend months on
  this in production. How you ingest, parse, and clean data fundamentally determines
  the ceiling of your RAG system. We implement it simply here not because it's less important,
  but because it deserves its own deep-dive. Our focus in this app is the
  retrieval-specific decisions: chunking strategy, metadata tagging, embedding, and indexing.
</div>
""", unsafe_allow_html=True)

    # Step overview table
    st.markdown("**Five steps — what each one does and why it matters:**")

    for item in STEPS_TABLE:
        has_note = bool(item["note"])
        border = "border-left:3px solid #BA7517" if has_note else "border-left:3px solid #0F6E56"

        with st.expander(f"{item['step']} {'⚠️' if has_note else ''}"):
            col1, col2, col3 = st.columns([1, 1, 1])

            with col1:
                st.markdown("**Why this step matters**")
                st.markdown(f"""
<div style="font-size:12px;color:var(--color-text-secondary);line-height:1.6">
{item['significance']}
</div>
""", unsafe_allow_html=True)

            with col2:
                st.markdown("**🏢 What enterprises do**")
                st.markdown(f"""
<div style="font-size:12px;color:var(--color-text-secondary);line-height:1.6">
{item['enterprise']}
</div>
""", unsafe_allow_html=True)

            with col3:
                st.markdown("**What we do in this app**")
                st.markdown(f"""
<div style="font-size:12px;color:var(--color-text-secondary);line-height:1.6">
{item['we_do']}
</div>
""", unsafe_allow_html=True)

            if has_note:
                st.caption(f"{item['note']} — intentionally simplified. Real enterprise implementations are significantly more complex.")

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    st.markdown("""
<div style="background:var(--color-background-secondary);border-radius:10px;
padding:14px 16px;font-size:13px;color:var(--color-text-secondary);
line-height:1.6;font-style:italic;border-left:3px solid #0F6E56">
  The offline pipeline runs once. Every query that follows lives or dies
  by the decisions made here. Let's build it.
</div>
""", unsafe_allow_html=True)

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("← Back", use_container_width=True):
            go_back()
    with col2:
        if st.button("Let's dive in — Step 1: Document Ingestion →",
                     type="primary", use_container_width=True):
            go_to("s01_ingestion")
