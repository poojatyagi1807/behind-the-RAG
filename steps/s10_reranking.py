"""Step 10 — Re-ranking."""
import streamlit as st
from ui import (render_topbar, render_step_header, render_thinking_card,
                render_what_we_built, render_enterprise_note, render_risk_table, render_nav, render_pm_matrix,
                render_cohere_key_prompt)
from state import store_result, get_result, has_cohere_key

PRECALC_RERANK = [
    {"before_rank": 1, "after_rank": 2, "score_before": 0.91, "score_after": 0.91, "move": "↓", "chunk": "RAG paper — parametric vs non-parametric memory", "why": "Relevant but indirect — discusses architecture not grounding mechanism specifically"},
    {"before_rank": 2, "after_rank": 1, "score_before": 0.84, "score_after": 0.94, "move": "↑", "chunk": "Pinecone — RAG anchors generation to retrieved evidence", "why": "Cross-encoder reads 'anchoring generation to retrieved evidence' as direct answer to hallucination prevention"},
    {"before_rank": 3, "after_rank": 4, "score_before": 0.79, "score_after": 0.72, "move": "↓", "chunk": "RAGAS — faithfulness metric definition", "why": "Evaluation metric — relevant to assessing grounding but doesn't explain the mechanism"},
    {"before_rank": 4, "after_rank": 3, "score_before": 0.71, "score_after": 0.87, "move": "↑↑", "chunk": "RAG paper — retrieval provides grounding for generation", "why": "Contains 'retrieval provides grounding' — direct semantic match cross-encoder catches that bi-encoder missed"},
    {"before_rank": 5, "after_rank": 5, "score_before": 0.63, "score_after": 0.61, "move": "—", "chunk": "Lilian Weng — external memory reduces confabulation", "why": "Related concept but in context of agents not RAG specifically"},
]

RISKS = [
    {"risk": "Too few candidates", "example": "Vector search returns K=3, re-ranker only sees 3 — best chunk was at rank 4, never considered", "mitigation": "Always retrieve K×3 or K×4 candidates, re-rank all, take top-K"},
    {"risk": "Re-ranker latency", "example": "Cross-encoder adds 300ms — total query latency exceeds SLA", "mitigation": "Latency budget — if re-ranker exceeds 200ms p95, switch to faster model or reduce candidate set"},
    {"risk": "Domain mismatch", "example": "General-purpose re-ranker on medical knowledge base — clinical terminology scored incorrectly", "mitigation": "Domain-specific re-rankers — fine-tune on domain query-document pairs"},
    {"risk": "Cost invisible", "example": "Every query makes a Cohere API call — at 1M queries/day significant cost — nobody tracked it", "mitigation": "Re-ranking cost in per-query budget from day one, not as afterthought"},
]

def render():
    render_topbar()
    render_step_header("🎯", "Re-ranking",
        "Vector search found candidates. Re-ranking finds the right order.")

    render_thinking_card(
        "Vector search is fast but approximate — it never reads query and chunk together. "
        "Re-ranking is slow but precise — it reads them as a pair and scores contextual relevance. "
        "Two stages, two different jobs.",
        pipeline="online"
    )

    st.markdown("**Stage 1 vs Stage 2:**")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
<div style="background:#E6F1FB;border:0.5px solid #185FA5;border-radius:8px;padding:12px">
<div style="font-size:12px;font-weight:500;color:#0C447C;margin-bottom:8px">Stage 1 — Vector search</div>
<div style="font-size:11px;color:#185FA5;line-height:1.7">
Fast · Approximate<br>
Embeds query separately<br>
Embeds chunks separately<br>
Measures vector distance<br>
<br>
Handles: all chunks<br>
Latency: &lt;5ms
</div>
</div>
""", unsafe_allow_html=True)
    with col2:
        st.markdown("""
<div style="background:#E1F5EE;border:0.5px solid #0F6E56;border-radius:8px;padding:12px">
<div style="font-size:12px;font-weight:500;color:#085041;margin-bottom:8px">Stage 2 — Re-ranking</div>
<div style="font-size:11px;color:#0F6E56;line-height:1.7">
Slow · Precise<br>
Reads query + chunk together<br>
Scores contextual relevance<br>
Cross-encoder model<br>
<br>
Handles: top-K only<br>
Latency: 100-300ms
</div>
</div>
""", unsafe_allow_html=True)

    st.markdown("---")

    # ── Cohere key prompt (always visible when key not set) ───────────────────
    if not has_cohere_key():
        render_cohere_key_prompt()

    st.markdown("**Before and after re-ranking — static example:**")
    st.markdown(
        "<div style='font-size:11px;background:#fef3cd;border:1px solid #f0c060;"
        "border-radius:6px;padding:6px 12px;margin-bottom:10px;color:#7a4a00'>"
        "📋 <strong>Static illustration</strong> — hardcoded to show how re-ranking changes order. "
        "Add your Cohere key above to run live re-ranking on your actual search results."
        "</div>",
        unsafe_allow_html=True,
    )

    move_colors = {"↑": "#1D9E75", "↑↑": "#085041", "↓": "#E24B4A", "—": "#888780"}
    for item in PRECALC_RERANK:
        move_color = move_colors.get(item["move"], "#888780")
        st.markdown(f"""
<div style="padding:10px 12px;background:var(--color-background-secondary);
border-radius:8px;margin-bottom:6px">
  <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:4px">
    <div style="font-size:12px;font-weight:500;color:var(--color-text-primary)">
    {item['chunk']}</div>
    <div style="font-size:12px;font-weight:500;color:{move_color}">
    #{item['before_rank']} → #{item['after_rank']} {item['move']}</div>
  </div>
  <div style="font-size:10px;color:var(--color-text-tertiary);font-style:italic">
  Why: {item['why']}</div>
</div>
""", unsafe_allow_html=True)

    st.markdown("---")

    # ── Live Cohere re-ranking (manual — runs only when button clicked) ───────
    if has_cohere_key():
        query = st.session_state.get("query") or "How does RAG prevent hallucination?"
        vs_result = get_result("vector_search")
        scored_chunks = vs_result.get("scored", []) if vs_result else []

        live_result = get_result("reranking_live")
        # Invalidate if query changed
        if live_result and live_result.get("query") != query:
            live_result = None
            store_result("reranking_live", None)

        st.markdown("**🔑 Live Cohere re-ranking — run on your actual search results:**")
        col_btn, col_info = st.columns([2, 5])
        with col_btn:
            run_clicked = st.button("▶ Run Cohere Rerank", type="primary", use_container_width=True)
        with col_info:
            st.markdown(
                "<div style='font-size:11px;color:var(--color-text-tertiary);padding-top:10px'>"
                "Uses <code>rerank-english-v3.0</code> — reads query + chunk together as a pair, "
                "scores contextual relevance directly. Results flow to all downstream steps."
                "</div>",
                unsafe_allow_html=True,
            )

        if run_clicked and scored_chunks:
            try:
                import cohere
                co = cohere.ClientV2(api_key=st.session_state.cohere_key)
                docs = [item["chunk"].text for item in scored_chunks[:10]]
                with st.spinner("Calling Cohere rerank-english-v3.0…"):
                    response = co.rerank(
                        model="rerank-english-v3.0",
                        query=query,
                        documents=docs,
                        top_n=min(5, len(docs)),
                    )
                reranked = []
                for r in response.results:
                    orig = scored_chunks[r.index]
                    reranked.append({
                        "chunk": orig["chunk"],
                        "before_rank": orig["rank"],
                        "after_rank": len(reranked) + 1,
                        "vector_score": orig["score"],
                        "cohere_score": round(r.relevance_score, 4),
                        "move": orig["rank"] - (len(reranked) + 1),
                    })
                store_result("reranking_live", {"reranked": reranked, "query": query})
                st.rerun()
            except Exception as e:
                st.error(f"Cohere API error — re-ranking skipped.\n\n**Error:** {str(e)[:300]}")

        elif run_clicked and not scored_chunks:
            st.warning("Complete Vector Search (Step 9) first — no candidates to re-rank yet.")

        if live_result and live_result.get("reranked"):
            reranked = live_result["reranked"]
            st.markdown(
                "<div style='font-size:12px;color:var(--color-text-secondary);margin:8px 0 4px'>"
                "Before = hybrid search rank &nbsp;·&nbsp; After = Cohere re-rank &nbsp;·&nbsp; "
                "Cohere score = direct relevance to query (0–1)"
                "</div>",
                unsafe_allow_html=True,
            )
            # Header row
            st.markdown(
                "<div style='display:grid;grid-template-columns:2fr 80px 80px 90px 90px;gap:4px;"
                "padding:4px 12px;font-size:10px;font-weight:600;color:var(--color-text-tertiary)'>"
                "<span>Chunk</span><span style='text-align:center'>Before</span>"
                "<span style='text-align:center'>After</span>"
                "<span style='text-align:right'>Vector</span>"
                "<span style='text-align:right'>Cohere ↓</span>"
                "</div>",
                unsafe_allow_html=True,
            )
            for item in reranked:
                move = item["move"]
                if move > 0:
                    arrow, arrow_color = f"↑{move}", "#1D9E75"
                elif move < 0:
                    arrow, arrow_color = f"↓{abs(move)}", "#E24B4A"
                else:
                    arrow, arrow_color = "—", "#888780"
                st.markdown(
                    f"<div style='display:grid;grid-template-columns:2fr 80px 80px 90px 90px;gap:4px;"
                    f"padding:8px 12px;background:var(--color-background-secondary);"
                    f"border-radius:8px;margin-bottom:5px;align-items:center'>"
                    f"<div>"
                    f"<div style='font-size:11px;font-weight:500;color:var(--color-text-primary)'>"
                    f"{item['chunk'].doc_title}</div>"
                    f"<div style='font-size:10px;color:var(--color-text-secondary);margin-top:2px'>"
                    f"{item['chunk'].text[:80]}…</div>"
                    f"</div>"
                    f"<div style='font-size:12px;color:var(--color-text-tertiary);text-align:center'>#{item['before_rank']}</div>"
                    f"<div style='font-size:13px;font-weight:700;color:{arrow_color};text-align:center'>"
                    f"#{item['after_rank']} {arrow}</div>"
                    f"<div style='font-size:11px;color:var(--color-text-tertiary);text-align:right'>{item['vector_score']:.4f}</div>"
                    f"<div style='font-size:13px;font-weight:600;color:#1D9E75;text-align:right'>{item['cohere_score']:.4f}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
            # Biggest jump insight
            biggest_jump = max(reranked, key=lambda x: x["move"]) if reranked else None
            if biggest_jump and biggest_jump["move"] > 0:
                st.markdown(
                    f"<div style='border-left:3px solid #1D9E75;border-radius:0 8px 8px 0;"
                    f"padding:10px 14px;background:var(--color-background-secondary);"
                    f"font-size:12px;line-height:1.7;margin-top:8px'>"
                    f"<strong>What Cohere saw differently:</strong> "
                    f"<em>{biggest_jump['chunk'].doc_title}</em> jumped ↑{biggest_jump['move']} positions. "
                    f"The cross-encoder read the query and this chunk together as a pair — it found direct "
                    f"semantic relevance that the bi-encoder missed when encoding them separately. "
                    f"Cohere score: <strong>{biggest_jump['cohere_score']:.4f}</strong> vs vector score: "
                    f"<strong>{biggest_jump['vector_score']:.4f}</strong>."
                    f"</div>",
                    unsafe_allow_html=True,
                )
    else:
        pass  # key prompt + static example label already shown above


    st.markdown("---")
    st.markdown("**Bi-encoder vs cross-encoder — the core difference:**")
    col1, col2 = st.columns(2)
    with col1:
        st.code("""BI-ENCODER (vector search)

Query  → Encoder → Vector
                       ↕ distance
Chunk  → Encoder → Vector

Encoded separately.
Fast — pre-compute chunk vectors.
Scales to millions.""", language=None)
    with col2:
        st.code("""CROSS-ENCODER (re-ranking)

[Query + Chunk] → Encoder → Score

Read together in one pass.
Direct relevance scored.
Only feasible for top-K.""", language=None)

    st.markdown("---")

    # ── PM Decision Matrix ────────────────────────────────────────────────────
    rows_data = [
        (
            "Do you even need re-ranking?",
            "Is your vector search retrieval quality already good enough or are users consistently getting the right answer in the wrong order?",
            "Run a retrieval quality audit on top 20 queries before adding re-ranking — only add complexity if answer quality has a measurable gap.",
            "Cohere found teams adding re-ranking to already well-tuned pipelines saw less than 2% quality improvement but 300ms additional latency — re-ranking was solving a problem that did not exist.",
            "Re-ranking implemented as an optional live step — runs only when a Cohere key is added; a static before/after example is shown otherwise. No retrieval quality audit was run to decide whether it's needed.",
            "Retrieval quality baseline measured before re-ranking is considered — re-ranking added only when audit shows consistent rank order is hurting answer quality.",
        ),
        (
            "What signals define the best chunk?",
            "Is the most semantically similar chunk always the most useful one for your specific user or do recency, authority, and source type matter?",
            "Define re-ranking signals with domain experts before build — semantic similarity alone is rarely enough for enterprise content.",
            "ServiceNow found their support RAG was surfacing old resolved tickets above current documentation because similarity score favored them — adding content type and recency as re-ranking signals fixed it.",
            "Semantic relevance only — Cohere's cross-encoder scores query-chunk relevance directly. No recency, authority, or content-type signal is layered on top.",
            "Re-ranking signal matrix defined by PM — semantic similarity weighted alongside recency, source authority, content type, and user role — weights tested against real query sample before deployment.",
        ),
        (
            "Cross-encoder vs bi-encoder?",
            "How much additional latency can your pipeline absorb at the re-ranking step before users notice?",
            "Measure current pipeline latency before choosing re-ranker — cross-encoder adds 200-500ms, validate this against your latency budget.",
            "Glean deployed a cross-encoder re-ranker without measuring latency impact — total response time crossed 6 seconds, user satisfaction dropped 25% before engineering rolled back to bi-encoder.",
            "Cross-encoder used — Cohere's rerank-english-v3.0, called live via API when a key is provided. Latency is not measured or checked against any budget, because no latency budget is defined anywhere in this app.",
            "Cross-encoder evaluated against latency budget defined at query step — if cross-encoder exceeds budget, bi-encoder with fine-tuning used as default, latency monitored per deployment environment.",
        ),
        (
            "How many chunks survive re-ranking?",
            "Are you passing too many chunks to context after re-ranking and diluting the answer or too few and losing critical information?",
            "Define Top N post re-ranking based on empirical testing — test answer quality at N=2, N=3, and N=5 before deciding.",
            "A healthcare RAG passed Top 10 chunks after re-ranking to stay safe — context window was dominated by marginally relevant chunks, model produced vague averaged answers instead of precise ones.",
            "Top 5 of up to 10 candidates passed to context after Cohere re-ranking — a fixed value, not tested against query types.",
            "Top N defined per query type through systematic testing — precision queries use N=2-3, comprehensive summary queries use N=5-7, reviewed quarterly against query log analysis.",
        ),
        (
            "Does re-ranking introduce bias?",
            "If recency is a re-ranking signal, are you silently suppressing older but more authoritative documents your user actually needs?",
            "Audit re-ranking output for bias monthly — check if any content category, time period, or source type is being systematically suppressed.",
            "A legal tech RAG weighted recency heavily in re-ranking — landmark case documents from 10 years ago were consistently ranked below recent but less authoritative sources, lawyers flagged answers as dangerously incomplete.",
            "Low bias risk by design — only Cohere's relevance score is used, with no recency or authority weighting layered in. No formal audit performed since the signal set is single-dimensional.",
            "Monthly re-ranking bias audit owned by PM — suppression patterns tracked per content type, time period, and source authority, bias thresholds defined and enforced before deployment.",
        ),
    ]

    render_pm_matrix("Re-ranking", rows_data)

    render_what_we_built("Re-ranking is optional — click 'Run Cohere Rerank' to re-score your vector search results using a cross-encoder. When run, the reranked order flows through to Context Ordering and beyond. Without re-ranking, vector search order is used.")
    render_enterprise_note(
        "Cohere Rerank is the most widely deployed managed re-ranking API — used by Notion, HubSpot, and "
        "McKinsey's internal knowledge tools. Cross-encoder/ms-marco-MiniLM-L-6-v2 on Hugging Face is the "
        "most popular open-source alternative. Jina AI's jina-reranker-v2 supports both text and code. "
        "Typical enterprise config: vector search retrieves top-20, re-ranker scores all 20, top-5 pass to "
        "context assembly. FlashRank from PrithivirajDamodaran is popular in cost-sensitive deployments — "
        "extremely fast cross-encoder that runs locally with competitive accuracy."
    )
    render_risk_table(RISKS)
    render_nav(next_label="Next: Context Ordering →", pipeline="online", show_jump=True)
