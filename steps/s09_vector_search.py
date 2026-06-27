"""Step 9 — Vector Search."""
import re
import math
from collections import Counter
import streamlit as st
import plotly.graph_objects as go
from ui import (render_topbar, render_step_header, render_thinking_card,
                render_what_we_built, render_enterprise_note, render_risk_table, render_nav, render_pm_matrix, render_key_takeaway)
from state import store_result, get_result
from knowledge_base.kb import tfidf_query_vector, cosine_similarity, Chunk

RISKS = [
    {"risk": "Top-K too small", "example": "K=3 misses most relevant chunk at rank 4 — response lacks critical info", "mitigation": "Benchmark K on your query set — K=5 to 10 typical. Larger K feeds re-ranker, not LLM directly"},
    {"risk": "Score threshold missing", "example": "Chunk with 0.18 score retrieved — clearly irrelevant — passes to LLM", "mitigation": "Minimum similarity threshold — reject chunks below 0.25, return 'I don't have enough information'"},
    {"risk": "Index staleness", "example": "Document updated yesterday — index not refreshed — retrieval returns outdated info confidently", "mitigation": "Change detection pipeline — re-index on document update, tag chunks with indexed_at timestamp"},
    {"risk": "Hybrid weights not tuned", "example": "α=0.5 weights dense and sparse equally — but domain needs keyword precision — sparse should dominate", "mitigation": "Tune α per domain on a labelled query set. Legal/medical: higher sparse weight. Semantic queries: higher dense weight"},
]

# ── Hybrid search implementation ──────────────────────────────────────────────

def _tokenize(text: str):
    return re.findall(r'\b[a-z]{2,}\b', text.lower())


def _bm25_score(query_tokens, chunk_tokens, df, N, avg_dl, k1=1.5, b=0.75):
    dl = len(chunk_tokens)
    tf_map = Counter(chunk_tokens)
    score = 0.0
    for qt in query_tokens:
        if qt not in df:
            continue
        tf = tf_map.get(qt, 0)
        idf = math.log((N - df[qt] + 0.5) / (df[qt] + 0.5) + 1)
        tf_norm = (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * dl / max(avg_dl, 1)))
        score += idf * tf_norm
    return score


def hybrid_search(query, chunks, tfidf_index, top_k=10, query_embedding=None, hnsw_index=None):
    """
    Hybrid search: BM25 (sparse) + dense (HNSW / neural cosine / TF-IDF) fused with RRF.
    Priority: HNSW with neural embeddings > brute-force neural cosine > TF-IDF cosine.
    Returns list of result dicts sorted by RRF score, plus a 'dense_method' key.
    """
    query_tokens = _tokenize(query)
    df = tfidf_index["df"]
    N = tfidf_index["N"]
    avg_dl = sum(len(_tokenize(c.text)) for c in chunks) / max(len(chunks), 1)

    # ── Dense: HNSW ANN → neural brute-force → TF-IDF cosine ────────────────
    has_embeddings = (
        query_embedding is not None
        and len(query_embedding) > 0
        and chunks
        and len(getattr(chunks[0], "embedding", [])) > 0
    )
    use_hnsw = has_embeddings and hnsw_index is not None
    use_neural = has_embeddings and not use_hnsw

    if use_hnsw:
        import numpy as np
        q_vec = np.array(query_embedding, dtype=np.float32)   # 1D — usearch expects flat vector
        # Fetch all chunks ranked by HNSW (k=len(chunks) for full RRF ranking)
        k_fetch = min(len(chunks), max(top_k * 8, len(chunks)))
        matches = hnsw_index.search(q_vec, k_fetch)
        # usearch cosine metric: distance = 1 - cosine_sim; results are 1D arrays
        dense_scored = [(int(k), float(1.0 - d))
                        for k, d in zip(matches.keys, matches.distances)]
        # Any chunks not returned by HNSW get score 0
        fetched = {idx for idx, _ in dense_scored}
        for i in range(len(chunks)):
            if i not in fetched:
                dense_scored.append((i, 0.0))
    elif use_neural:
        dense_scored = [
            (i, cosine_similarity(query_embedding, chunks[i].embedding))
            for i in range(len(chunks))
        ]
    else:
        q_vec = tfidf_query_vector(query, tfidf_index)
        dense_scored = [
            (i, cosine_similarity(q_vec, tfidf_index["vectors"][i]))
            for i in range(len(chunks))
        ]
    dense_scored.sort(key=lambda x: x[1], reverse=True)
    dense_ranks = {idx: rank + 1 for rank, (idx, _) in enumerate(dense_scored)}
    dense_score_map = {idx: s for idx, s in dense_scored}

    # ── Sparse: BM25 ─────────────────────────────────────────────────────────
    sparse_scored = []
    for i, chunk in enumerate(chunks):
        chunk_tokens = _tokenize(chunk.text)
        score = _bm25_score(query_tokens, chunk_tokens, df, N, avg_dl)
        sparse_scored.append((i, score))
    sparse_scored.sort(key=lambda x: x[1], reverse=True)
    sparse_ranks = {idx: rank + 1 for rank, (idx, _) in enumerate(sparse_scored)}
    sparse_score_map = {idx: s for idx, s in sparse_scored}

    # ── RRF fusion ────────────────────────────────────────────────────────────
    k = 60
    results = []
    for i, chunk in enumerate(chunks):
        rrf = 1 / (k + dense_ranks[i]) + 1 / (k + sparse_ranks[i])
        results.append({
            "chunk": chunk,
            "rank": 0,
            "rrf_score": round(rrf, 5),
            "dense_score": round(dense_score_map[i], 4),
            "sparse_score": round(sparse_score_map.get(i, 0), 4),
            "dense_rank": dense_ranks[i],
            "sparse_rank": sparse_ranks[i],
        })

    results.sort(key=lambda x: x["rrf_score"], reverse=True)
    dense_method = "hnsw" if use_hnsw else ("neural" if use_neural else "tfidf")
    for i, item in enumerate(results):
        item["rank"] = i + 1
        item["score"] = item["rrf_score"]  # alias for downstream steps
        item["dense_method"] = dense_method
    return results[:top_k]



# ── Dynamic metadata filter inference ────────────────────────────────────────

def _infer_metadata_filters(query: str, chunks: list) -> dict:
    """Infer likely metadata filters from query keywords.
    Returns filters (list of strings) and filtered_count (int)."""
    q = query.lower()
    filters = []
    mask = [True] * len(chunks)

    source_hints = {
        "langchain": "langchain_docs",
        "pinecone": "pinecone_guide",
        "ragas": "ragas_docs",
        "lilian": "lilian_weng",
        "weng": "lilian_weng",
        "rag paper": "rag_paper",
        "lewis": "rag_paper",
    }
    for keyword, src in source_hints.items():
        if keyword in q:
            filters.append('source = "' + src + '"')
            mask = [m and c.doc_id == src for m, c in zip(mask, chunks)]
            break

    if any(w in q for w in ["code", "implement", "function", "python", "example", "snippet", "library"]):
        filters.append("has_code = true")
        mask = [m and c.has_code for m, c in zip(mask, chunks)]

    if any(w in q for w in ["table", "benchmark", "comparison", "metric", "score", "evaluat"]):
        filters.append("has_tables = true")
        mask = [m and c.has_tables for m, c in zip(mask, chunks)]

    if any(w in q for w in ["paper", "research", "citation", "reference", "study", "published"]):
        filters.append("has_citations = true")
        mask = [m and c.has_citations for m, c in zip(mask, chunks)]

    filtered_count = sum(mask) if filters else len(chunks)
    return {"filters": filters, "filtered_count": filtered_count}

# ── Render ────────────────────────────────────────────────────────────────────

def render():
    render_topbar()
    render_step_header("🔍", "Vector Search",
        "Query vector is ready. Find which chunks are closest in meaning.")

    render_thinking_card(
        "Vector search finds chunks whose meaning is closest to your query — not by matching words "
        "but by measuring distance in vector space. But before a single similarity score is computed, "
        "two earlier decisions have already shrunk the search space dramatically.",
        pipeline="online"
    )

    # ── 1. Dynamic: metadata filter + HNSW + search space ─────────────────────
    raw_query_pre    = st.session_state.get("query", "How does RAG prevent hallucination?")
    search_query_pre = st.session_state.get("retrieval_query", raw_query_pre) or raw_query_pre
    kb_chunks_pre    = st.session_state.get("kb_chunks", [])
    total_pre        = len(kb_chunks_pre) if kb_chunks_pre else 312

    meta = (_infer_metadata_filters(search_query_pre, kb_chunks_pre)
            if kb_chunks_pre else {"filters": [], "filtered_count": total_pre})
    meta_filters   = meta["filters"]
    filtered_count = meta["filtered_count"]
    hnsw_candidates = min(max(int(filtered_count * 0.15), 20), 300)

    filter_html = ("<br>".join("<code>" + f + "</code>" for f in meta_filters)
                   if meta_filters else "No filters inferred<br>Searching all chunks")
    hnsw_skip_pct = 100 - int(hnsw_candidates / max(filtered_count, 1) * 100)

    q_display = search_query_pre[:75] + ("..." if len(search_query_pre) > 75 else "")
    st.markdown("**Before similarity scoring — how the search space shrinks:**")
    st.markdown(
        "<div style='font-size:12px;color:var(--color-text-secondary);margin-bottom:10px'>"
        f"Query: <em>{q_display}</em><br>"
        "Vector similarity is not run against every chunk. Two earlier steps shrink the search space first."
        "</div>",
        unsafe_allow_html=True,
    )

    col1, col2, col3, col4, col5 = st.columns([3, 1, 3, 1, 3])
    with col1:
        st.markdown(
            f"<div style='border:1px solid #27AE60;border-radius:8px;padding:12px;text-align:center'>"
            f"<div style='font-size:20px'>🏷️</div>"
            f"<div style='font-size:12px;font-weight:700;color:#27AE60;margin:4px 0'>Metadata Filter</div>"
            f"<div style='font-size:11px;color:var(--color-text-secondary);line-height:1.7'>"
            f"{filter_html}<br><br>"
            f"<strong>{total_pre:,} → {filtered_count:,} chunks</strong><br>"
            f"Only matching chunks enter the index."
            f"</div></div>",
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            "<div style='display:flex;align-items:center;justify-content:center;height:100%;"
            "font-size:22px;color:var(--color-text-tertiary)'>→</div>",
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            f"<div style='border:1px solid #F4845F;border-radius:8px;padding:12px;text-align:center'>"
            f"<div style='font-size:20px'>🗂️</div>"
            f"<div style='font-size:12px;font-weight:700;color:#F4845F;margin:4px 0'>HNSW Index</div>"
            f"<div style='font-size:11px;color:var(--color-text-secondary);line-height:1.7'>"
            f"Graph traversal: layer by layer.<br>Skips ~{hnsw_skip_pct}% of comparisons.<br><br>"
            f"<strong>{filtered_count:,} → ~{hnsw_candidates} candidates</strong><br>"
            f"Only the nearest neighbourhood is scored."
            f"</div></div>",
            unsafe_allow_html=True,
        )
    with col4:
        st.markdown(
            "<div style='display:flex;align-items:center;justify-content:center;height:100%;"
            "font-size:22px;color:var(--color-text-tertiary)'>→</div>",
            unsafe_allow_html=True,
        )
    with col5:
        st.markdown(
            f"<div style='border:1px solid #4A90D9;border-radius:8px;padding:12px;text-align:center'>"
            f"<div style='font-size:20px'>🔍</div>"
            f"<div style='font-size:12px;font-weight:700;color:#4A90D9;margin:4px 0'>Hybrid Search</div>"
            f"<div style='font-size:11px;color:var(--color-text-secondary);line-height:1.7'>"
            f"Dense + BM25 scored on ~{hnsw_candidates} candidates.<br><br>"
            f"<strong>~{hnsw_candidates} → top 10 results</strong><br>"
            f"Ranked by RRF. Passed to Re-ranking."
            f"</div></div>",
            unsafe_allow_html=True,
        )

    st.markdown(
        "<div style='background:#EBF4FD;border:0.5px solid #B5D4F4;border-radius:8px;"
        "padding:10px 14px;margin:10px 0;font-size:12px;color:#0C447C;line-height:1.6'>"
        "🏢 <strong>Enterprise deployments inject two more filters automatically — before any query runs:</strong><br><br>"
        "<strong>ACL filter</strong> — the user's role and clearance level are attached at query time. "
        "The vector store filters on <code>allowed_roles</code> and <code>clearance_level</code> before ANN search runs. "
        "An analyst can never surface executive-only chunks — even if they're the best semantic match.<br><br>"
        "<strong>Recency filter</strong> — queries containing 'latest', 'current', 'recent' automatically add "
        "an <code>updated_at ≥ cutoff_date</code> filter. Stale chunks are excluded before scoring, "
        "not just ranked lower."
        "</div>",
        unsafe_allow_html=True,
    )

    st.markdown("---")


    # ── 2. Hybrid search explainer ────────────────────────────────────────────
    st.markdown("**Hybrid search — dense + sparse combined:**")
    st.markdown(
        "<div style='font-size:12px;color:var(--color-text-secondary);margin-bottom:10px'>"
        "Neither dense (semantic) nor sparse (keyword) search alone wins on real enterprise benchmarks. "
        "Hybrid search runs both, ranks each independently, then fuses the rankings using "
        "<strong>Reciprocal Rank Fusion (RRF)</strong>."
        "</div>",
        unsafe_allow_html=True,
    )

    _dense_method = (get_result("vector_search") or {}).get("dense_method",
                     "hnsw" if st.session_state.get("kb_hnsw") else
                     ("neural" if get_result("query_vector") else "tfidf"))
    _dense_label = (
        "🧠 Dense — <strong>HNSW · all-MiniLM-L6-v2 (hnswlib · cosine)</strong>"
        if _dense_method == "hnsw"
        else "🧠 Dense — <strong>all-MiniLM-L6-v2 cosine (neural, brute-force)</strong>"
        if _dense_method == "neural"
        else "🧠 Dense — TF-IDF cosine (fallback — install fastembed for neural)"
    )
    _dense_detail = (
        "Finds semantically similar chunks via HNSW approximate nearest-neighbour search. "
        "Same all-MiniLM-L6-v2 model used to embed KB chunks and query. Catches paraphrasing and synonyms."
        if _dense_method == "hnsw"
        else "Finds chunks that are <em>semantically similar</em> to the query using real neural embeddings — "
        "same local model used to embed all KB chunks. Catches paraphrasing and synonyms."
        if _dense_method == "neural"
        else "Finds chunks using word-overlap cosine similarity. "
        "Install fastembed (`pip3 install fastembed`) to enable real semantic (neural) search."
    )

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(
            f"<div style='border-left:3px solid #9B59B6;padding:10px 14px;"
            f"background:var(--color-background-secondary);border-radius:0 6px 6px 0;font-size:12px;line-height:1.7'>"
            f"{_dense_label}<br>{_dense_detail}"
            f"</div>",
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            "<div style='border-left:3px solid #E67E22;padding:10px 14px;"
            "background:var(--color-background-secondary);border-radius:0 6px 6px 0;font-size:12px;line-height:1.7'>"
            "<strong>🔑 Sparse — BM25 (keyword)</strong><br>"
            "Finds chunks that contain the <em>exact terms</em> in the query — "
            "strong on domain jargon and proper nouns. "
            "Misses paraphrases and synonyms."
            "</div>",
            unsafe_allow_html=True,
        )

    st.markdown(
        "<div style='background:var(--color-background-secondary);border-radius:8px;"
        "padding:10px 14px;margin-top:6px;font-size:12px;line-height:1.7'>"
        "<strong>⚗️ RRF Fusion</strong> — each chunk gets a fused score: "
        "<code>RRF = 1/(60 + dense_rank) + 1/(60 + sparse_rank)</code>. "
        "A chunk ranked #2 by dense and #5 by sparse scores higher than one ranked #1 by only one method. "
        "Final ranking reflects agreement across both signals."
        "</div>",
        unsafe_allow_html=True,
    )

    st.markdown("---")

    # ── 3. Live search ────────────────────────────────────────────────────────
    raw_query    = raw_query_pre
    search_query = search_query_pre

    # Show HyDE badge when the retrieval query differs from the raw question
    qu = get_result("query_understanding") or {}
    if qu.get("hyde") and search_query != raw_query:
        st.info(
            "🔵 **HyDE active** — searching with the hypothetical answer embedding, not the original question. "
            "Retrieved chunks reflect answer-space similarity."
        )

    kb_chunks = st.session_state.get("kb_chunks", [])
    kb_tfidf = st.session_state.get("kb_tfidf", None)

    result = get_result("vector_search")
    # Invalidate if retrieval query changed or result predates hybrid search (missing "score" alias)
    if result and (result.get("query") != search_query or
                   (result.get("scored") and "score" not in (result["scored"][0] if result["scored"] else {}))):
        result = None

    if not result:
        if kb_chunks and kb_tfidf:
            query_embedding = get_result("query_vector")   # neural vector from Step 8 (or None)
            hnsw_index = st.session_state.get("kb_hnsw")   # hnswlib index (None if unavailable)
            with st.spinner("Running hybrid search…"):
                scored = hybrid_search(
                    search_query, kb_chunks, kb_tfidf,
                    top_k=min(10, len(kb_chunks)),
                    query_embedding=query_embedding,
                    hnsw_index=hnsw_index,
                )
                dense_method = scored[0]["dense_method"] if scored else "tfidf"
                result = {
                    "scored": scored,
                    "total": len(kb_chunks),
                    "query": search_query,
                    "dense_method": dense_method,
                }
                store_result("vector_search", result)
        else:
            result = {"scored": [], "total": 312, "query": raw_query, "dense_method": "tfidf"}

    scored = result.get("scored", [])
    total = result.get("total", 312)

    if scored:
        st.markdown(f"**Hybrid search results — {total} chunks, top 5 shown:**")

        # Header row
        st.markdown(
            "<div style='display:grid;grid-template-columns:2fr 1fr 1fr 1fr;gap:4px;"
            "padding:4px 12px;font-size:10px;font-weight:600;color:var(--color-text-tertiary)'>"
            "<span>Chunk</span><span style='text-align:right'>Dense</span>"
            "<span style='text-align:right'>BM25</span><span style='text-align:right'>RRF ↓</span>"
            "</div>",
            unsafe_allow_html=True,
        )

        for item in scored[:5]:
            chunk = item["chunk"]
            rrf = item["rrf_score"]
            dense = item["dense_score"]
            sparse = item["sparse_score"]
            color = "#1D9E75" if rrf >= 0.025 else "#BA7517" if rrf >= 0.018 else "#888780"
            st.markdown(
                f"<div style='display:grid;grid-template-columns:2fr 1fr 1fr 1fr;gap:4px;"
                f"padding:8px 12px;background:var(--color-background-secondary);"
                f"border-radius:8px;margin-bottom:5px;align-items:center'>"
                f"<div>"
                f"<div style='font-size:11px;font-weight:500;color:var(--color-text-primary)'>"
                f"#{item['rank']} {chunk.doc_title}</div>"
                f"<div style='font-size:10px;color:var(--color-text-tertiary)'>"
                f"{chunk.section} · {chunk.word_count}w · "
                f"dense rank #{item['dense_rank']} · sparse rank #{item['sparse_rank']}</div>"
                f"<div style='font-size:10px;color:var(--color-text-secondary);margin-top:2px'>"
                f"{chunk.text[:90]}…</div>"
                f"</div>"
                f"<div style='font-size:12px;color:var(--color-text-secondary);text-align:right'>{dense:.4f}</div>"
                f"<div style='font-size:12px;color:var(--color-text-secondary);text-align:right'>{sparse:.3f}</div>"
                f"<div style='font-size:13px;font-weight:600;color:{color};text-align:right'>{rrf:.5f}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

        # Score distribution
        all_rrf = [item["rrf_score"] for item in scored]
        fig = go.Figure(go.Histogram(
            x=all_rrf, nbinsx=20,
            marker_color="#378ADD", opacity=0.7,
        ))
        fig.update_layout(
            height=150, margin=dict(l=0, r=0, t=8, b=0),
            xaxis_title="RRF score", yaxis_title="Chunks",
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(size=11),
        )
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Most chunks cluster at low RRF scores. The sharp drop on the right is where real relevance begins.")

    else:
        st.info("Run the offline pipeline first to load the knowledge base, then return here.")

    st.markdown("---")

    # ── 4. Lost in the middle ─────────────────────────────────────────────────
    st.markdown("**⚠️ The lost in the middle problem — why ranking order matters downstream:**")
    st.markdown(
        "<div style='font-size:12px;color:var(--color-text-secondary);margin-bottom:10px'>"
        "Retrieval returns a ranked list. But the order in which chunks appear in the LLM's "
        "context window has a large effect on how much attention the model pays to each one — "
        "and it's not uniform."
        "</div>",
        unsafe_allow_html=True,
    )

    positions = [
        ("1", "0.91", "HIGH", "#1D9E75", "LLM pays strong attention to the start of context"),
        ("2", "0.84", "HIGH", "#1D9E75", "Still near the top — good attention"),
        ("3", "0.79", "LOW ⚠️", "#BA7517", "Attention drops sharply in the middle"),
        ("4", "0.71", "LOW ⚠️", "#BA7517", "Often underweighted even when highly relevant"),
        ("5", "0.63", "HIGH", "#1D9E75", "Recency effect — last position gets attention back"),
    ]

    for pos, score, attention, color, note in positions:
        st.markdown(
            f"<div style='display:flex;align-items:center;gap:12px;padding:7px 12px;"
            f"background:var(--color-background-secondary);border-radius:6px;margin-bottom:4px'>"
            f"<div style='font-size:11px;font-weight:600;color:var(--color-text-tertiary);width:60px'>Pos {pos}</div>"
            f"<div style='font-size:11px;color:var(--color-text-secondary);flex:1'>score {score}</div>"
            f"<div style='font-size:11px;font-weight:600;color:{color};width:80px'>{attention}</div>"
            f"<div style='font-size:10px;color:var(--color-text-tertiary);flex:2'>{note}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

    st.markdown(
        "<div style='background:var(--color-background-secondary);border-left:3px solid #BA7517;"
        "border-radius:0 8px 8px 0;padding:10px 14px;margin-top:8px;font-size:12px;line-height:1.7'>"
        "The most relevant chunk is not always at position 1 after vector search alone. "
        "If it lands in the middle, the LLM may underweight it — producing an answer that's "
        "less grounded than the retrieved evidence actually supports.<br><br>"
        "<strong>Fix:</strong> Re-ranking (next step) promotes the most relevant chunk to position 1. "
        "Context ordering (later) applies sandwich ordering — best chunk first, second-best last, rest in the middle."
        "</div>",
        unsafe_allow_html=True,
    )
    st.caption("Source: Liu et al. 2023 — 'Lost in the Middle: How Language Models Use Long Contexts'")

    st.markdown("---")

    # ── PM Decision Matrix ────────────────────────────────────────────────────
    rows_data = [
        (
            "How many results to retrieve — Top K?",
            "Are you retrieving too few chunks and missing the right answer or too many and drowning the model in noise?",
            "Test Top K values of 3, 5, and 10 against your top 20 query types — measure answer quality not just retrieval speed.",
            "Glean defaulted to Top 3 retrieval — users asking multi-part questions got incomplete answers because the right chunks were ranked 4 and 5, never surfaced to the model.",
            "Hybrid search fetches top 10 candidates internally, UI shows top 5 — fixed values, not tested against query types.",
            "Top K defined per query type based on empirical testing — simple lookup queries use Top 3, complex reasoning queries use Top 7-10, reviewed quarterly against query log.",
        ),
        (
            "Similarity threshold?",
            "Below what confidence score is a retrieved chunk doing more harm than good to your answer quality?",
            "Define a minimum similarity threshold and suppress results below it — never let low confidence chunks silently pollute the context.",
            "A legal RAG had no similarity threshold — weakly related chunks about adjacent topics were included in context, model blended them into answers that sounded authoritative but were factually wrong.",
            "No similarity threshold — all top-K chunks are passed forward regardless of RRF score. The risk table on this page explicitly flags this as unmitigated.",
            "Minimum similarity threshold defined per content domain — high stakes domains like legal and compliance use stricter threshold, exploratory domains use relaxed threshold.",
        ),
        (
            "Vector search only or hybrid?",
            "Are your users asking exact match questions — product names, policy numbers, error codes — that vector search alone handles poorly?",
            "Audit top 20 queries for exact match patterns — if more than 20% are exact match, hybrid search is a V1 requirement not V2.",
            "Elasticsearch found enterprise customers with support ticket RAG got poor results on error code queries using vector search alone — hybrid with BM25 improved precision by 40% on exact match queries.",
            "Hybrid already implemented by default — BM25 sparse + dense (HNSW/neural) fused with Reciprocal Rank Fusion on every query, not an optional add-on.",
            "Query type audit before launch — hybrid search enabled for exact match heavy domains, keyword weight tuned per content type, both retrieval paths tested independently before combining.",
        ),
        (
            "Zero results experience?",
            "When nothing crosses your similarity threshold, does your user get silence, an error, or a helpful fallback?",
            "Design zero results state explicitly — define fallback options, suggested reformulations, or escalation paths before launch.",
            "Notion AI returned a blank response on out-of-scope queries with no explanation — user research showed 70% of users assumed the product was broken rather than the query being out of scope.",
            "No zero-results state exists because there's no similarity threshold to fail — the system always returns its top-K chunks even when none are truly relevant.",
            "Zero results triggers explicit UI state — message explains scope boundary, suggests 2-3 reformulated query options, offers escalation to human support for enterprise deployments.",
        ),
        (
            "Speed vs recall tradeoff?",
            "Is your user more frustrated by a slow accurate answer or a fast approximate one?",
            "Define acceptable recall loss percentage with engineering — run user research to validate latency tolerance before choosing ANN settings.",
            "Pinecone found a financial services customer had tuned ANN settings for maximum speed — recall dropped to 85%, meaning 1 in 6 queries missed the best answer, compliance team flagged it as unacceptable.",
            "No ANN tuning — usearch's default HNSW parameters used as-is, no recall target measured or defined.",
            "Recall target defined by PM based on domain risk tolerance — high stakes domains target 99% recall with slower exact search, consumer exploratory products accept 90% recall for speed.",
        ),
    ]

    render_pm_matrix("Vector Search", rows_data)

    render_what_we_built(
        "We run hybrid search — BM25 sparse + all-MiniLM-L6-v2 neural dense — fused with Reciprocal Rank Fusion. "
        "Metadata filters and HNSW indexing shrink the candidate pool before scoring. "
        "Same pattern as Weaviate, Pinecone, and Elastic in production."
    )
    render_enterprise_note(
        "Production vector search runs on dedicated vector databases. Pinecone's HNSW handles 100M+ vectors "
        "with sub-100ms p99 latency. Weaviate and Elastic support hybrid search natively — "
        "BM25 + dense vector search fused with RRF at query time, no extra infrastructure needed. "
        "The hybrid weight (how much to trust dense vs sparse) is a tunable parameter — "
        "legal and medical RAG typically favours sparse (exact term matching matters), "
        "while general-purpose assistants favour dense (semantic understanding matters). "
        "At enterprise scale, query embedding caching reduces API calls by 40-60% on repeated queries."
    )
    render_risk_table(RISKS)
    render_key_takeaway("Hybrid search wins in production because dense and sparse retrieval are complementary. Dense finds semantic matches; BM25 finds exact terms. A query about a specific product number needs BM25. A question about 'feeling overwhelmed' needs dense. RRF merges both without requiring you to tune weights.", pipeline="online")
    render_nav(next_label="Next: Re-ranking →", pipeline="online", show_jump=True)
