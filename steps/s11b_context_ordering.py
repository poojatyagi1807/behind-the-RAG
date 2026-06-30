"""Step 11b — Context Ordering (runs before assembly)."""
import streamlit as st
import plotly.graph_objects as go
from ui import (render_topbar, render_step_header, render_thinking_card,
                render_what_we_built, render_enterprise_note, render_risk_table, render_nav, render_pm_matrix)
from state import store_result, get_result

RISKS = [
    {"risk": "Wrong strategy for model", "example": "Relevance descending used with a model with strong recency bias — most relevant chunk ignored", "mitigation": "Benchmark ordering strategies on your specific LLM — don't assume one strategy works universally"},
    {"risk": "Static strategy for dynamic queries", "example": "Sandwich works for factual queries but simple queries only need one chunk — overhead wasted", "mitigation": "Query complexity classification — simple queries use top-1 only, complex use sandwich"},
    {"risk": "No strategy documented", "example": "Team changes ordering without recording why — future team member reverts — quality drops", "mitigation": "Version control ordering strategy alongside system prompt — treat as a product decision with a rationale"},
]

ATTENTION_BY_POSITION = [0.91, 0.72, 0.45, 0.38, 0.51, 0.88]


def _get_source_chunks():
    """Pull chunks from reranking if available, else vector search."""
    cohere_result = get_result("reranking_live")
    if cohere_result and cohere_result.get("reranked"):
        raw = cohere_result["reranked"]
        chunks = [{"chunk": r["chunk"], "score": r["cohere_score"], "rank": r["after_rank"]} for r in raw]
        return sorted(chunks, key=lambda x: x.get("score", 0), reverse=True), "Cohere rerank-english-v3.0", True

    vs_result = get_result("vector_search")
    if vs_result and vs_result.get("scored"):
        chunks = sorted(vs_result["scored"][:10], key=lambda x: x.get("score", 0), reverse=True)
        return chunks, "Hybrid vector search", False

    # Static fallback
    fallback = [
        {"chunk": type("C", (), {"doc_title": "Pinecone guide", "text": "RAG reduces hallucination by anchoring generation to retrieved evidence...", "tfidf_vector": [], "word_count": 87})(), "score": 0.94},
        {"chunk": type("C", (), {"doc_title": "RAG paper", "text": "Parametric vs non-parametric memory — factual grounding mechanism...", "tfidf_vector": [], "word_count": 112})(), "score": 0.91},
        {"chunk": type("C", (), {"doc_title": "LangChain docs", "text": "Retrieval grounds LLM responses in external knowledge...", "tfidf_vector": [], "word_count": 95})(), "score": 0.78},
    ]
    return fallback, "Pre-computed demo", False


def _apply_sandwich(chunks):
    """Best first, second-best last, rest in middle. Always sorts by score first."""
    s = sorted(chunks, key=lambda x: x.get("score", 0), reverse=True)
    if len(s) <= 2:
        return s
    return [s[0]] + s[2:] + [s[1]]


def render():
    render_topbar()
    render_step_header("🥪", "Context Ordering",
        "Decide which chunks to keep, remove duplicates, then arrange them for maximum LLM attention.")

    render_thinking_card(
        "LLMs pay more attention to content at the start and end of what they read — not the middle. "
        "So the order you put chunks in actually changes the quality of the answer. "
        "This step decides which chunks go where.",
        pipeline="online"
    )

    all_chunks, source_label, is_reranked = _get_source_chunks()

    # ── Source badge ──────────────────────────────────────────────────────────
    badge_color = "#1D9E75" if is_reranked else "#378ADD"
    st.markdown(
        f"<div style='display:inline-block;background:{badge_color}22;border:1px solid {badge_color}55;"
        f"border-radius:6px;padding:4px 12px;font-size:11px;color:{badge_color};margin-bottom:12px'>"
        f"{'✅ Cohere reranked' if is_reranked else '📊 Hybrid search'}"
        f" &nbsp;·&nbsp; Source: <strong>{source_label}</strong></div>",
        unsafe_allow_html=True,
    )

    # ── Step 1: Top-K ────────────────────────────────────────────────────────
    st.markdown("**Step 1 — Select top K from retrieved candidates:**")
    st.markdown(
        "<div style='font-size:12px;color:var(--color-text-secondary);margin-bottom:10px'>"
        "Not all retrieved chunks go into the prompt — that wastes tokens and adds noise. "
        "Pick the top K by relevance score. Everything below K is discarded here."
        "</div>", unsafe_allow_html=True,
    )

    total_retrieved = len(all_chunks)
    top_k = st.slider(
        "Top K — how many chunks to keep",
        min_value=1, max_value=min(total_retrieved, 8),
        value=min(3, total_retrieved), step=1, key="top_k_select",
    )
    top_chunks = all_chunks[:top_k]

    c1, c2, c3 = st.columns(3)
    for col, val, label, color in [
        (c1, total_retrieved, "candidates from search", "#378ADD"),
        (c2, top_k, "top K kept", "#1D9E75"),
        (c3, total_retrieved - top_k, "discarded", "#888780"),
    ]:
        with col:
            st.markdown(
                f"<div style='text-align:center;padding:10px;"
                f"background:var(--color-background-secondary);border-radius:8px'>"
                f"<div style='font-size:22px;font-weight:700;color:{color}'>{val}</div>"
                f"<div style='font-size:11px;color:var(--color-text-tertiary)'>{label}</div>"
                f"</div>", unsafe_allow_html=True,
            )

    st.markdown("---")

    # ── Step 2: Deduplication ────────────────────────────────────────────────
    st.markdown("**Step 2 — Deduplication:**")
    st.markdown(
        "<div style='font-size:12px;color:var(--color-text-secondary);margin-bottom:10px'>"
        "Sometimes two chunks say nearly the same thing from different sections. "
        "If both go into the prompt the LLM over-weights that idea. "
        "<strong>How it works:</strong> every pair of chunks is compared with cosine similarity (0 = different, 1 = identical). "
        "If two chunks score above the threshold, the lower-ranked one is dropped."
        "</div>", unsafe_allow_html=True,
    )

    threshold = st.slider(
        "Similarity threshold — chunks above this removed as near-duplicates",
        min_value=0.70, max_value=0.99, value=0.92, step=0.01, key="dedup_threshold",
    )

    kept, removed = [], []
    if top_chunks and hasattr(top_chunks[0]["chunk"], "tfidf_vector"):
        from knowledge_base.kb import cosine_similarity
        for item in top_chunks:
            is_dup = any(
                cosine_similarity(item["chunk"].tfidf_vector, k["chunk"].tfidf_vector) >= threshold
                for k in kept
                if item["chunk"].tfidf_vector and k["chunk"].tfidf_vector
            )
            (removed if is_dup else kept).append(item)
    else:
        kept = top_chunks

    if removed:
        st.warning(f"🗑 {len(removed)} chunk(s) removed as near-duplicates (threshold: {threshold})")
        for r in removed:
            st.caption(f"Removed: {r['chunk'].doc_title}")
    else:
        st.success(f"✅ No duplicates at threshold {threshold} — all {len(kept)} chunks kept")

    st.markdown("---")

    # ── Step 3: LLM attention chart ──────────────────────────────────────────
    st.markdown("**Step 3 — Where does the LLM actually pay attention?**")
    positions = [f"Pos {i+1}" for i in range(len(ATTENTION_BY_POSITION))]
    fig = go.Figure(go.Bar(
        x=positions, y=ATTENTION_BY_POSITION,
        marker_color=["#1D9E75" if a >= 0.7 else "#BA7517" if a >= 0.5 else "#E24B4A"
                      for a in ATTENTION_BY_POSITION],
        text=[f"{a:.0%}" for a in ATTENTION_BY_POSITION], textposition="outside",
    ))
    fig.update_layout(
        height=200, margin=dict(l=0, r=0, t=8, b=0),
        yaxis=dict(range=[0, 1.1], title="Relative attention"),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(size=11),
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Source: Liu et al. 2023 — 'Lost in the Middle: How Language Models Use Long Contexts'")

    st.markdown("---")

    # ── Step 4: Ordering strategy ─────────────────────────────────────────────
    st.markdown("**Step 4 — Choose an ordering strategy:**")

    if len(kept) >= 2:
        sorted_kept = sorted(kept, key=lambda x: x["score"], reverse=True)
        strategies = {
            "sandwich": {
                "label": "🥪 Sandwich (recommended)",
                "order": _apply_sandwich(sorted_kept),
                "why": "Best chunk at pos 1 (high attention) + 2nd-best at pos last (high attention). Both critical slots filled.",
            },
            "descending": {
                "label": "📉 Relevance descending",
                "order": sorted_kept,
                "why": "Most relevant first — straightforward, but middle chunks get low attention.",
            },
            "ascending": {
                "label": "📈 Relevance ascending",
                "order": list(reversed(sorted_kept)),
                "why": "Best chunk last — exploits recency bias. Works on models with strong end-weighting.",
            },
        }

        selected = st.radio(
            "Select ordering strategy:",
            options=list(strategies.keys()),
            format_func=lambda k: strategies[k]["label"],
            horizontal=True,
        )
        ordered = strategies[selected]["order"]

        st.markdown(
            f"<div style='font-size:12px;color:var(--color-text-secondary);"
            f"background:var(--color-background-secondary);border-radius:6px;"
            f"padding:8px 12px;margin:6px 0 10px'>{strategies[selected]['why']}</div>",
            unsafe_allow_html=True,
        )

        # Show ordered chunks with attention
        # Last position always gets the end-of-context attention (88%), regardless of total count
        for i, item in enumerate(ordered):
            is_last = i == len(ordered) - 1
            attn = ATTENTION_BY_POSITION[-1] if is_last else (ATTENTION_BY_POSITION[i] if i < len(ATTENTION_BY_POSITION) else ATTENTION_BY_POSITION[-2])
            color = "#1D9E75" if attn >= 0.7 else "#BA7517" if attn >= 0.5 else "#E24B4A"
            is_best = item == sorted_kept[0]
            is_second = len(sorted_kept) > 1 and item == sorted_kept[1]
            tag = " 🥇" if is_best else " 🥈" if is_second else ""
            st.markdown(
                f"<div style='display:flex;align-items:center;justify-content:space-between;"
                f"padding:8px 12px;background:var(--color-background-secondary);"
                f"border-radius:8px;margin-bottom:4px'>"
                f"<div><span style='font-size:11px;font-weight:500'>Pos {i+1}{tag}</span>"
                f"<span style='font-size:11px;color:var(--color-text-secondary);margin-left:8px'>"
                f"{item['chunk'].doc_title} · score {item['score']:.3f}</span></div>"
                f"<div style='font-size:11px;color:{color};font-weight:500'>{attn:.0%} attention</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

        store_result("context_ordering", {
            "strategy": selected,
            "ordered": ordered,
            "is_reranked": is_reranked,
            "source": source_label,
        })
    else:
        ordered = kept
        store_result("context_ordering", {"strategy": "single", "ordered": ordered, "is_reranked": is_reranked, "source": source_label})

    st.markdown("---")

    # ── PM Decision Matrix ────────────────────────────────────────────────────
    rows_data = [
        (
            "Do you know the lost in the middle problem exists?",
            "Are you assuming the LLM weighs every chunk in context equally regardless of position?",
            "Read the lost in the middle research before designing context assembly — position bias is well documented, not a hypothetical risk.",
            "We implemented sandwich ordering because it's the published best practice. We never measured whether it actually improves answer quality on our specific educational content — we applied the research finding without validating it here.",
            "Aware of lost in the middle — sandwich ordering is implemented by default, based on the documented finding that LLMs underweight middle-of-context content.",
            "Position bias documented as a known constraint in the RAG design doc — ordering strategy chosen deliberately, not left to default chunk order.",
        ),
        (
            "What goes first in context?",
            "Is your highest scoring chunk actually placed where the model pays the most attention?",
            "Place the single most relevant chunk first in context, every time — never let raw retrieval order determine this by accident.",
            "We put the highest similarity-scored chunk first. For educational content, the highest-scored chunk isn't always the most pedagogically useful — we never tested whether score rank equals explanation quality.",
            "Most relevant chunk placed first by design — sandwich ordering puts the top-scored chunk first and the second-best chunk last, with the remaining chunks in the middle.",
            "First position reserved for highest confidence chunk as a hard rule — verified in QA testing before any context assembly change ships.",
        ),
        (
            "Does ordering change by query type?",
            "Does a single-fact lookup query need the same context ordering as a multi-step reasoning query?",
            "Test whether ordering strategy should vary by query type — don't assume one strategy fits all before measuring.",
            "We apply sandwich ordering to every query regardless of complexity. A simple factual question and a multi-concept comparison get the same ordering strategy with no differentiation.",
            "Three ordering strategies exist — sandwich, descending, ascending — selectable via a manual toggle in this app, but selection isn't automatically driven by query type or intent. Sandwich is the default applied to every query regardless of type.",
            "Ordering strategy selection automated based on query classification — query type detected upstream, ordering strategy applied automatically, manual override available for debugging only.",
        ),
        (
            "How do you handle conflicting chunks?",
            "What happens when two retrieved chunks state contradictory facts — does your context assembly silently pass both forward?",
            "Add a contradiction check before final context assembly, even a simple heuristic, rather than shipping with no check at all.",
            "Our 5 documents sometimes frame the same concept differently — the RAG paper and Pinecone guide describe retrieval in different terms. We pass both to the LLM with no flag indicating they may conflict.",
            "No conflict detection — contradictory or outdated chunks are passed into context silently with no flag, warning, or precedence rule.",
            "Conflict detection layer checks for contradictory claims across retrieved chunks before assembly — flagged conflicts trigger recency-based precedence rules or are surfaced to the user explicitly.",
        ),
        (
            "Sandwich ordering — is it right for your use case?",
            "Is the published 'sandwich' pattern actually validated against your content and query types, or just adopted because it's the documented best practice?",
            "Validate sandwich ordering against your own query set before defaulting to it — the original research wasn't run on your domain or content structure.",
            "We adopted sandwich ordering as the default without running a comparison on our own content. We don't know whether sandwich, descending, or ascending ordering produces better answers for our specific educational queries.",
            "Sandwich ordering implemented as the default across all query types in this app — adopted as the documented best practice, not validated against a query benchmark specific to this content.",
            "Ordering strategy validated against an internal benchmark of representative queries before being set as default — re-validated whenever chunk size or content type changes meaningfully.",
        ),
    ]

    render_pm_matrix("Context Ordering", rows_data)

    render_what_we_built("We select top-K, deduplicate, then apply sandwich ordering by default — highest scored first, second-highest last.")
    render_enterprise_note(
        "Anthropic's internal evaluations show sandwich ordering outperforms relevance-descending by 8-12% on "
        "factual recall benchmarks. Google's RAG systems use relevance-weighted interleaving — alternating high "
        "and low scored chunks to maintain attention throughout. LangChain's LongContextReorder implements "
        "relevance ascending for models with strong recency bias. The right strategy depends on the specific "
        "LLM and should be empirically validated on your own query set."
    )
    render_risk_table(RISKS)
    render_nav(next_label="Next: Context Assembly →", pipeline="online", show_jump=True)
