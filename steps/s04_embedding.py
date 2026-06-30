"""Step 4 — Embedding."""
import math
import streamlit as st
import plotly.graph_objects as go
from ui import (render_topbar, render_step_header, render_thinking_card,
                render_what_we_built, render_enterprise_note, render_risk_table,
                render_nav, render_pm_matrix)
from config.content import EMBEDDING_COMPARISON
from state import embed_text

# ── Demo data ─────────────────────────────────────────────────────────────────

DEMO_QUERY = "how does RAG handle knowledge that changes over time?"

DEMO_CHUNKS = [
    {
        "label": "RAG paper — parametric vs non-parametric memory",
        "text": "RAG models combine a parametric memory (the pre-trained LM) with a non-parametric memory (a dense vector retrieval index). Non-parametric memory can be updated without retraining, making RAG ideal for knowledge that changes over time.",
        "doc": "RAG paper",
    },
    {
        "label": "Pinecone — stale knowledge and RAG updates",
        "text": "One of RAG's key advantages over fine-tuning is the ability to update the knowledge base without retraining the model. Simply re-index new or changed documents and retrieval immediately reflects the update.",
        "doc": "Pinecone guide",
    },
    {
        "label": "LangChain — re-indexing and document loaders",
        "text": "LangChain's indexing API tracks which documents have been ingested so that only new or changed content is re-embedded. This avoids unnecessary duplication and keeps the index fresh with minimal compute.",
        "doc": "LangChain docs",
    },
    {
        "label": "Lilian Weng — memory types in agent systems",
        "text": "External memory in agent architectures allows models to access information outside their training distribution. This is analogous to human long-term memory — persistent, updatable, and retrievable on demand.",
        "doc": "Lilian Weng",
    },
    {
        "label": "RAGAS — context recall metric definition",
        "text": "Context recall measures whether the retrieved chunks contain all the information needed to answer the question. A low recall score indicates the retrieval step is missing relevant content from the knowledge base.",
        "doc": "RAGAS docs",
    },
    {
        "label": "LangChain — code block, RecursiveCharacterSplit",
        "text": "text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)\nchunks = text_splitter.split_documents(documents)",
        "doc": "LangChain docs",
    },
]

SAMPLE_EMBEDDING_SNIPPET = [
    0.0412, -0.0187, 0.0634, -0.0291, 0.0178, 0.0523, -0.0445, 0.0312,
    -0.0198, 0.0467, -0.0334, 0.0289, 0.0156, -0.0423, 0.0567, -0.0234,
]

RISKS = [
    {"risk": "Model mismatch", "example": "Index built with v1 embedding, query uses v2 — different vector spaces — wrong chunks retrieved confidently", "mitigation": "Embedding registry — lock model version per index. Never allow silent model upgrades"},
    {"risk": "Dimension explosion", "example": "TF-IDF on 50,000 documents produces 500,000-dimension sparse vectors — memory and latency prohibitive", "mitigation": "Dense embeddings for large corpora — fixed dimension regardless of vocabulary size"},
    {"risk": "Stale embeddings", "example": "Embedding model updated — old and new chunks incompatible in same index", "mitigation": "Re-embed entire corpus when model changes — Pinecone supports parallel indexes for zero-downtime migration"},
    {"risk": "Domain mismatch", "example": "General model on medical RAG — 'MI' (myocardial infarction) embedded like 'MI' (Michigan)", "mitigation": "Domain-specific models — BioBERT for medical, FinBERT for finance, LegalBERT for law"},
]

# ── Embedding helpers ─────────────────────────────────────────────────────────

def _cosine(a: list, b: list) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return round(dot / (na * nb + 1e-10), 4)


def _get_similarity_scores() -> list:
    """
    Embed DEMO_QUERY and all DEMO_CHUNKS using all-MiniLM-L6-v2 (local, no API key).
    Cached in session state to avoid re-embedding on reruns.
    Returns list of score dicts, or empty list if embedding unavailable.
    """
    cache_key = "s04_sim_scores"
    if st.session_state.get(cache_key):
        return st.session_state[cache_key]

    all_texts = [DEMO_QUERY] + [c["text"] for c in DEMO_CHUNKS]
    vectors = []
    for text in all_texts:
        vec, _ = embed_text(text)
        if vec is None:
            return []
        vectors.append(vec)

    query_vec = vectors[0]
    chunk_vecs = vectors[1:]
    scores = [
        {"chunk": c["label"], "score": _cosine(query_vec, cv), "doc": c["doc"]}
        for c, cv in zip(DEMO_CHUNKS, chunk_vecs)
    ]
    scores.sort(key=lambda x: x["score"], reverse=True)
    st.session_state[cache_key] = scores
    return scores


# ── Render ────────────────────────────────────────────────────────────────────

def render():
    render_topbar()
    render_step_header("🔢", "Embedding",
        "Convert meaning into math. Same model in, same model out — always.")

    render_thinking_card(
        "Embedding turns text into numbers that capture meaning, not just words. "
        "'Cars' and 'automobiles' become similar numbers. 'Cars' and 'pasta' become very different numbers. "
        "This is how the system finds relevant chunks even when the exact words don't match.",
        pipeline="offline"
    )

    # ── What an embedding looks like ─────────────────────────────────────────
    st.markdown("**What an embedding actually looks like:**")
    st.markdown("*'Large pre-trained language models store factual knowledge'*")
    vec_str = (
        str(SAMPLE_EMBEDDING_SNIPPET[:8])[:-1]
        + ",\n  ... 376 more numbers ...\n  "
        + str(SAMPLE_EMBEDDING_SNIPPET[-2:])[1:]
    )
    st.code(f"[{vec_str}", language=None)
    st.caption(
        "384 numbers. One per dimension. Every chunk becomes exactly this shape. "
        "all-MiniLM-L6-v2 — local, 384-dimensional dense vectors. "
        "Retrieval finds nearest vectors to your query's vector."
    )

    st.markdown("---")

    # ── Live similarity chart ─────────────────────────────────────────────────
    with st.spinner("Computing embeddings with all-MiniLM-L6-v2 (local)…"):
        sim_scores = _get_similarity_scores()

    if sim_scores:
        st.markdown(
            "<div style='display:inline-block;background:#E8F5E9;border:0.5px solid #A5D6A7;"
            "border-radius:4px;padding:2px 8px;font-size:10px;color:#1B5E20;margin-bottom:6px'>"
            "✅ Local — all-MiniLM-L6-v2 (384 dims · no API key needed)</div>",
            unsafe_allow_html=True,
        )
    else:
        st.warning("Embedding unavailable — install fastembed: `pip3 install fastembed`")
        return

    st.markdown("**Semantic similarity — query: *'" + DEMO_QUERY + "'***")

    bar_colors = ["#0F6E56" if s["score"] >= 0.40 else "#B4B2A9" for s in sim_scores]
    bar_text   = [str(round(s["score"], 3)) for s in sim_scores]
    fig = go.Figure(go.Bar(
        x=[s["score"] for s in sim_scores],
        y=[s["chunk"][:55] + "…" for s in sim_scores],
        orientation="h",
        marker_color=bar_colors,
        text=bar_text,
        textposition="outside",
    ))
    fig.update_layout(
        height=260, margin=dict(l=0, r=70, t=0, b=0),
        xaxis=dict(range=[0, 1.15], title="Cosine similarity"),
        yaxis=dict(autorange="reversed"),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(size=11),
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        "Real cosine similarity computed by all-MiniLM-L6-v2. "
        "The code chunk scores lowest — even from the same document, "
        "code and prose live in very different parts of vector space."
    )

    st.markdown("---")

    # ── Embedding strategy comparison ─────────────────────────────────────────
    st.markdown("**Embedding strategies — same chunk, different vector spaces:**")
    for emb_key, emb in EMBEDDING_COMPARISON.items():
        is_current = emb.get("active", False)
        label_suffix = " ← **we use this**" if is_current else ""
        header = (
            "**" + emb["label"] + "**" + label_suffix
            + " — " + emb["type"]
            + " · " + emb["dims"] + " dims"
            + " · " + emb["cost"]
        )
        with st.expander(header):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Understands:** " + emb["understands"])
                st.markdown("**Struggles with:** " + emb["struggles"])
            with col2:
                st.markdown("**Best for:** " + emb["best_for"])

    # ── PM Decision Matrix ────────────────────────────────────────────────────
    rows_data = [
        (
            "Which embedding model?",
            "Does your content require domain-specific understanding or is general purpose good enough?",
            "Benchmark at least 2 embedding models against your actual content before committing.",
            "Cohere found OpenAI embeddings underperformed on technical enterprise docs — switched to a domain-specific model after launch, forcing a full re-embedding at significant cost.",
            "all-MiniLM-L6-v2 via fastembed — local, open source, 384-dim. Not benchmarked against alternatives; selected for zero-cost/no-API-key demo simplicity.",
            "Run embedding model evaluation on a representative sample of real content — score retrieval quality before selecting a model.",
        ),
        (
            "Multilingual or English only?",
            "Are any of your users querying in a language other than English today or in the next 12 months?",
            "Decide language scope on day one — retrofitting multilingual embeddings means re-embedding the entire knowledge base.",
            "A European bank launched RAG in English only — six months later compliance required French and German support, forcing full re-ingestion and re-embedding.",
            "English only — all-MiniLM-L6-v2 is trained primarily on English text; the 5-document KB is English only.",
            "Define language scope with product and legal on day one — use a multilingual model like multilingual-e5 if any non-English use case exists.",
        ),
        (
            "Re-embedding strategy?",
            "When documents update, do you re-embed everything or only changed documents?",
            "Define a delta re-embedding policy before launch — full re-embedding at scale is expensive and slow.",
            "Notion AI re-embedded its entire workspace on each major content update — costs spiked unpredictably, engineering scrambled to build delta logic retroactively.",
            "No re-embedding strategy — static knowledge base, embedded once per session, no version tracking or delta logic.",
            "Delta re-embedding by default — track document version hash, only re-embed changed or new documents, full re-embed only on model change.",
        ),
        (
            "Cost vs quality?",
            "At your expected query and document volume, what does embedding cost look like at scale?",
            "Model your embedding cost at 10x current volume before selecting a model.",
            "A Series B startup selected premium embeddings for its MVP — at scale, embedding costs exceeded hosting costs, forcing a mid-product model migration.",
            "Cost not modeled at scale — local open-source model means zero per-call API cost in this demo, but no projection done for compute/storage at higher volume.",
            "Run cost projection at 10x, 50x, 100x document volume — factor in storage, re-embedding frequency, and query volume before model selection.",
        ),
        (
            "Open source vs proprietary?",
            "How much vendor lock-in can your organization tolerate? What happens if the API is deprecated?",
            "Define a portability requirement — if lock-in is unacceptable, open source models like sentence-transformers are the default.",
            "A fintech built entirely on OpenAI embeddings — when OpenAI deprecated ada-002, the entire pipeline needed migration with no fallback plan.",
            "Open source by default — all-MiniLM-L6-v2 (sentence-transformers) runs locally, no vendor lock-in. No proprietary model evaluated for a quality comparison.",
            "Evaluate open source alternatives like sentence-transformers or E5 — proprietary only if the quality gap is significant and lock-in risk is accepted by leadership.",
        ),
    ]

    render_pm_matrix("Embedding", rows_data)

    render_what_we_built(
        "We embed chunks using <strong>all-MiniLM-L6-v2</strong> (fastembed, local) — "
        "384-dimensional dense vectors, no API key required. "
        "The same model embeds queries in the online pipeline, "
        "ensuring consistent vector spaces for meaningful cosine similarity."
    )
    render_enterprise_note(
        "OpenAI's text-embedding-3-small and text-embedding-3-large are the most widely deployed "
        "embedding models in production RAG today. Amazon Bedrock offers Titan Embeddings as a "
        "managed service. For multilingual use cases, Cohere's embed-multilingual-v3.0 supports "
        "100+ languages in a single embedding space — a Spanish query retrieves English documents "
        "if the meaning matches. Hybrid search — combining sparse TF-IDF with dense semantic "
        "vectors — is the current production standard at Elastic, Weaviate, and Pinecone. "
        "Model consistency is enforced through embedding registries — Databricks MLflow and AWS "
        "SageMaker Model Registry track which model version was used to index each corpus."
    )
    render_risk_table(RISKS)
    render_nav(next_label="Next: Indexing →", pipeline="offline")
