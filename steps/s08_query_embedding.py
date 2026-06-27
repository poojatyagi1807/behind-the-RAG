"""Step 8 — Query Embedding."""
import math
import streamlit as st
from ui import (render_topbar, render_step_header, render_thinking_card,
                render_what_we_built, render_enterprise_note, render_risk_table, render_nav, render_pm_matrix,
                render_fallback_badge)
from state import store_result, get_result, embed_text
from knowledge_base.kb import tfidf_query_vector

RISKS = [
    {"risk": "Model mismatch", "example": "Index built with v1, query uses v2 — meaningless similarity scores — wrong chunks retrieved confidently", "mitigation": "Embedding registry — lock model version per index. Tag every chunk with model name and version"},
    {"risk": "Embedding latency spike", "example": "Embedding API cold starts at 3am — first query takes 3 seconds", "mitigation": "Embedding model warm-up — scheduled keepalive pings. Local fallback model for latency-sensitive paths"},
    {"risk": "Query too long", "example": "User pastes 2,000 word document — exceeds embedding context window — silently truncated", "mitigation": "Query length validation before embedding — truncate or summarise, warn user, log truncation events"},
    {"risk": "No caching", "example": "Same question asked 10,000 times per day — 10,000 API calls", "mitigation": "Semantic query cache — embed once, store result, retrieve for near-identical queries"},
]

def render():
    render_topbar()
    render_step_header("🔢", "Query Embedding",
        "One rule: the query must be embedded with the exact same model used during indexing.")

    render_thinking_card(
        "Your query gets converted into a vector using all-MiniLM-L6-v2 — the same local model "
        "used to embed all chunks in the index. Same model = same vector space = meaningful similarity scores. "
        "The query vector computed here is passed directly to Vector Search for real neural semantic search. "
        "Different model = retrieval breaks silently.",
        pipeline="online"
    )

    raw_query    = st.session_state.get("query", "How does RAG prevent hallucination?")
    search_query = st.session_state.get("retrieval_query", raw_query)

    # Show HyDE badge when the retrieval query differs from the raw question
    qu = get_result("query_understanding") or {}
    if qu.get("hyde") and search_query != raw_query:
        st.info(
            "🔵 **HyDE active** — embedding the hypothetical answer, not the original question. "
            "This is what gets sent to the vector index."
        )

    st.markdown("**What happens:**")
    st.code("""Query  → all-MiniLM-L6-v2 → [-0.089, 0.124, -0.056 ... 384 numbers]
                                ↕ same model, same space
Chunks → all-MiniLM-L6-v2 → [-0.091, 0.118, -0.061 ... 384 numbers]

Same model = similarity scores are meaningful.
Different model = similarity scores are meaningless.
                 Retrieval breaks silently.""", language=None)

    # ── Embed locally with all-MiniLM-L6-v2 (no API key needed) ──────────────
    with st.spinner("Embedding query with all-MiniLM-L6-v2 (local)…"):
        q_vec, used_provider = embed_text(search_query)

    if q_vec is not None:
        store_result("query_vector", q_vec)
        st.markdown(
            "<div style='display:inline-block;background:#E8F5E9;border:0.5px solid #A5D6A7;"
            "border-radius:4px;padding:2px 8px;font-size:10px;color:#1B5E20;margin-bottom:6px'>"
            "✅ Local — all-MiniLM-L6-v2 (384 dims · no API key needed)</div>",
            unsafe_allow_html=True,
        )
    else:
        # TF-IDF fallback — clear neural vector so Step 9 uses TF-IDF path
        store_result("query_vector", None)
        kb_chunks = st.session_state.get("kb_chunks", [])
        kb_tfidf  = st.session_state.get("kb_tfidf", None)
        if kb_chunks and kb_tfidf:
            q_vec = tfidf_query_vector(search_query, kb_tfidf)

        render_fallback_badge()

        # ── Educational banner ────────────────────────────────────────────────────────────────────────
        st.warning(
            "⚠️ **fastembed unavailable — falling back to TF-IDF.**\n\n"
            "**What this means right now:**\n"
            "- Chunk embeddings: TF-IDF (bag-of-words keyword overlap)\n"
            "- Query embedding: TF-IDF (same method, same vector space)\n\n"
            "Both use the same vector space, so cosine similarity is valid and search works. "
            "The limitation: TF-IDF is keyword-based — it misses semantic meaning. "
            "A query about *'automobiles'* won't match a chunk about *'cars'* even though they mean the same thing.\n\n"
            "**📚 Teaching moment — what a real vector space mismatch looks like:**  \n"
            "The dangerous silent failure is when chunks are embedded with a neural model (e.g. all-MiniLM-L6-v2, 384-dim) "
            "but the query is embedded with TF-IDF (sparse, vocab-size dimensions) — or with a *different* neural model. "
            "Those vectors live in incompatible spaces. Cosine similarity returns garbage scores, "
            "wrong chunks are retrieved confidently, and the system gives no warning. "
            "This happens in production when teams upgrade the query path but forget to re-index the chunks.\n\n"
            "To fix: run `pip3 install fastembed` and restart."
        )

    if q_vec is not None:
        st.markdown("**Your query vector (first 20 dimensions):**")
        st.code(
            str([round(v, 4) for v in q_vec[:20]])
            + f"\n... {len(q_vec)} total dimensions",
            language=None,
        )
    else:
        st.info("Knowledge base not loaded yet — run the offline pipeline first or start from Step 7.")

    st.markdown("---")
    st.markdown("**The model consistency problem:**")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
<div style="background:#EAF3DE;border:0.5px solid #C0DD97;border-radius:8px;padding:12px">
<div style="font-size:12px;font-weight:500;color:#3B6D11;margin-bottom:8px">✅ Same model</div>
<div style="font-size:11px;color:#27500A;line-height:1.6">
Index built with all-MiniLM-L6-v2<br>
Query embedded with all-MiniLM-L6-v2<br><br>
→ Same vector space<br>
→ Similarity scores meaningful<br>
→ Retrieval works correctly
</div>
</div>
""", unsafe_allow_html=True)
    with col2:
        st.markdown("""
<div style="background:#FCEBEB;border:0.5px solid #F7C1C1;border-radius:8px;padding:12px">
<div style="font-size:12px;font-weight:500;color:#501313;margin-bottom:8px">❌ Different model</div>
<div style="font-size:11px;color:#791F1F;line-height:1.6">
Index built with OpenAI embeddings<br>
Query embedded with Cohere<br><br>
→ Different vector spaces<br>
→ Similarity scores meaningless<br>
→ Wrong chunks retrieved confidently
</div>
</div>
""", unsafe_allow_html=True)

    st.markdown("---")

    # ── PM Decision Matrix ────────────────────────────────────────────────────
    rows_data = [
        (
            "Same model as document embedding?",
            "Do you know if your query and document embeddings are living in the same vector space?",
            "Lock query and document embedding model as a single versioned config — any model change must update both simultaneously.",
            "A fintech team upgraded document embedding model during a routine update without updating query embedding — retrieval quality dropped 60%, took 2 weeks to diagnose because failure was silent.",
            "Same model used by design — all-MiniLM-L6-v2 embeds both chunks and queries via the same `embed_text()` helper, but there is no formal version-lock config or registry enforcing this.",
            "Query and document embedding model locked in shared config file, versioned together, any change triggers full regression test before deployment.",
        ),
        (
            "Latency vs quality?",
            "How much of your total response latency budget is query embedding consuming?",
            "Define a latency budget across all pipeline steps — query embedding should consume no more than 10% of total allowed latency.",
            "Perplexity found query embedding was consuming 40% of their total response latency — switched to a lighter embedding model for queries while keeping a high quality model for documents.",
            "No latency budget defined — local all-MiniLM-L6-v2 runs in ~2-5ms per query (no GPU), but this isn't tracked or budgeted anywhere in the app.",
            "Total latency budget defined by PM based on user research — allocated per pipeline step, query embedding monitored separately from document embedding.",
        ),
        (
            "Query preprocessing before embedding?",
            "Does cleaning the query before embedding improve retrieval or does it strip away intent signals?",
            "Test retrieval quality with and without preprocessing on your top 20 query types — let data decide.",
            "Elastic found that aggressive stopword removal before query embedding hurt retrieval on conversational queries — users asking 'how do I' got worse results than users asking 'configure'.",
            "No lexical preprocessing (no stopword removal, no spell correction) — but the query is already transformed by HyDE in Step 7 before it reaches this step, so what gets embedded is a generated hypothetical answer, not the raw question.",
            "Preprocessing rules defined per query type — spelling correction for all, stopword removal only for keyword-heavy queries, tested against retrieval quality baseline before enabling.",
        ),
        (
            "Caching frequent query embeddings?",
            "Are your users asking the same questions repeatedly and are you recomputing embeddings every time?",
            "Analyze query logs for repeat patterns — if top 20 queries account for 30% of volume, caching is a V1 requirement.",
            "Intercom found 35% of all support queries were variations of the same 15 questions — implementing query embedding cache reduced average response latency by 1.2 seconds.",
            "No semantic query cache — every submitted query is embedded fresh. Results are cached per-session only to avoid recomputing on reruns, not across different queries.",
            "Query log analyzed at launch — top recurring queries cached with TTL defined by PM based on content freshness requirements.",
        ),
        (
            "Multilingual query handling?",
            "What happens when a user queries in a language different from your document language?",
            "Define supported language combinations explicitly — test cross-lingual retrieval before launch, never assume it works.",
            "A European enterprise deployed RAG with English documents — French-speaking users got empty results with no explanation because cross-lingual retrieval was never tested.",
            "English only — all-MiniLM-L6-v2 and the 5-document knowledge base are both English; no multilingual handling or fallback message exists.",
            "Supported language matrix defined by PM before launch — cross-lingual retrieval tested per combination, unsupported languages shown explicit message rather than empty or wrong results.",
        ),
    ]

    render_pm_matrix("Query Embedding", rows_data)

    render_what_we_built("We embed the query using all-MiniLM-L6-v2 (sentence-transformers, local) — the same model used to embed all KB chunks at load time. No API key needed. This query vector is passed to Step 9 for real neural cosine similarity search. Falls back to TF-IDF if the package is unavailable.")
    render_enterprise_note(
        "Model consistency enforced through embedding registries — Databricks MLflow and AWS SageMaker Model Registry "
        "track which model version indexed each corpus. When enterprises upgrade their embedding model — moving from "
        "text-embedding-ada-002 to text-embedding-3-large — the entire corpus must be re-embedded before the new model "
        "can be used for queries. This is an embedding migration — a planned, versioned operation. "
        "Pinecone and Weaviate support parallel indexes — old model serves live traffic while new model index is built, "
        "then traffic is cut over. Query embedding latency benchmarks: OpenAI text-embedding-3-small — 20-50ms. "
        "Cohere embed-english-v3 — 15-40ms. Local all-MiniLM-L6-v2 — 2-5ms but requires GPU. "
        "At millions of queries per day, 30ms embedding latency adds up — enterprises cache query embeddings."
    )
    render_risk_table(RISKS)
    render_key_takeaway("The query and all knowledge base chunks must be embedded with the same model. Different models produce incompatible vector spaces — distances between them are meaningless. This is why embedding model upgrades require re-embedding the entire knowledge base.", pipeline="online")
    render_nav(next_label="Next: Vector Search →", pipeline="online", show_jump=True)
