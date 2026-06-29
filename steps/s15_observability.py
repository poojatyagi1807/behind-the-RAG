"""Step 15 — Observability and drift detection."""
import streamlit as st
from datetime import datetime
from ui import render_topbar, render_step_header, render_thinking_card, render_enterprise_note, render_risk_table, render_pm_matrix, render_nav
from state import get_result, reset_session, go_to

RISKS = [
    {"risk": "No drift detection", "example": "Embedding model updated silently — scores degrade 8% over 3 weeks — nobody notices", "mitigation": "Statistical drift detector on score distributions — alert on week-over-week shift exceeding 0.05"},
    {"risk": "Vanity metrics only", "example": "Team tracks query volume and latency but not faithfulness — quality problems invisible", "mitigation": "RAGAS metrics as primary KPIs — faithfulness and context precision in weekly engineering reviews"},
    {"risk": "PII in logs", "example": "Raw user queries stored in plain text — GDPR violation", "mitigation": "PII scrubbing before logging — anonymise queries, never store raw user input"},
    {"risk": "No feedback loop", "example": "Metrics logged but never acted on — same problems repeat quarterly", "mitigation": "Designated AI ops owner — someone whose job is to read dashboards and translate into product decisions"},
]

def render():
    render_topbar()
    render_step_header("📊", "Observability",
        "Every decision logged. Patterns across thousands of queries tell the story no single run could.")

    render_thinking_card(
        "A single pipeline run tells you what happened once. Observability tells you what is happening "
        "always — trends, degradation, drift, anomalies. Without it you are flying blind. "
        "With it you catch problems before users feel them.",
        pipeline="online"
    )

    query = st.session_state.get("query", "—")
    vs_result = get_result("vector_search")
    assembly = get_result("context_assembly")
    gen_result = get_result("generation")
    grounding = get_result("grounding")
    judge = get_result("judge")

    best_score = vs_result.get("scored", [{"score": 0}])[0].get("score", 0) if vs_result and vs_result.get("scored") else 0
    total_chunks = vs_result.get("total", 312) if vs_result else 312
    total_tokens = assembly.get("total_tokens", 0) if assembly else 0
    gen_latency = gen_result.get("latency_ms", 0) if gen_result else 0
    grounding_score = sum(1 for r in (grounding or []) if r.get("status") == "grounded") / max(len(grounding or [1]), 1)
    judge_score = judge.get("overall_score", 0) if judge else 0

    st.markdown("**This conversation's trace:**")
    st.code(f"""TRACE — SESSION-BTR-{datetime.now().strftime('%H%M%S')}
Timestamp:  {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC

── QUERY ──────────────────────────────────────────────
Raw query:          {query[:60]}
Strategy:           HyDE

── RETRIEVAL ──────────────────────────────────────────
Chunks searched:    {total_chunks}
Best score:         {best_score:.3f}
Low confidence:     {"Yes ⚠️" if best_score < 0.25 else "No"}

── CONTEXT ────────────────────────────────────────────
Token count:        {total_tokens:,} / 8,192
Ordering:           Sandwich

── GENERATION ─────────────────────────────────────────
Model:              gemini-2.0-flash
Latency:            {gen_latency}ms

── EVALUATION ─────────────────────────────────────────
Grounding:          {grounding_score:.0%}
Judge score:        {judge_score:.2f}
Weakest layer:      {judge.get("weakest_layer", "—") if judge else "—"}

── OUTCOME ────────────────────────────────────────────
Est. cost:          ~${max(gen_latency * 0.0000015, 0.001):.4f}""", language=None)

    st.markdown("---")
    st.markdown("**Three time horizons:**")

    tab1, tab2, tab3 = st.tabs(["📡 Daily — real-time health", "📈 Weekly — quality trends", "📊 Monthly — strategic patterns"])

    with tab1:
        st.markdown("*Is anything broken right now?*")
        st.markdown("""
| Metric | Today | Baseline | Status |
|---|---|---|---|
| Query volume | 12,847 | ~13,000 | ✅ Normal |
| Avg retrieval latency | 94ms | 90ms | ✅ Normal |
| P95 generation latency | 3,200ms | 2,800ms | 🟡 Watch |
| Low confidence queries | 8.3% | 7.5% | 🟡 Watch |
| Faithfulness avg | 0.89 | 0.88 | ✅ Normal |
| Error rate | 0.02% | 0.02% | ✅ Normal |
""")

    with tab2:
        st.markdown("*Is anything slowly degrading?*")
        st.markdown("""
| Week | Faithfulness | Context precision | Recall |
|---|---|---|---|
| Week 1 | 0.91 | 0.84 | 0.86 |
| Week 2 | 0.90 | 0.82 | 0.85 |
| Week 3 | 0.89 | 0.79 | 0.84 |
| Week 4 | 0.88 | **0.76 ← flagged** | 0.83 |
""")
        st.warning("Context precision on consistent downward trend — 2.5% per week. Structural problem, not noise.")

    with tab3:
        st.markdown("*What should we change next quarter?*")
        st.markdown("""
**Top query intents — last 30 days:**
- RAG fundamentals: 34%
- Evaluation metrics: 22%
- Implementation details: 19%
- Enterprise architecture: 15%
- ??? unknown intent: 3% ← new pattern emerging

**Consistently lowest scoring document:** Lilian Weng blog (0.71 avg) — consider re-chunking

**Queries with no good answer:**
- "what is agentic RAG" ← not in knowledge base
- "how does GraphRAG work" ← not in knowledge base
""")

    st.markdown("---")
    st.markdown("**⚠️ Drift — the central threat:**")

    with st.expander("Embedding drift — provider updates model silently"):
        st.markdown("""
**What happens:** Embedding provider silently updates model. Query vectors now in slightly different space than indexed chunks. Scores drop gradually across the board.

**What it looks like:** "Answers are getting worse" — users. "Retrieval scores all down 5-8%" — observability.

**What observability catches:** Best similarity score distribution shifts downward. No individual query fails — everything just scores lower.

**Fix:** Re-embed entire knowledge base with new model version.
""")

    with st.expander("Data drift — world changes, knowledge base stays static"):
        st.markdown("""
**What happens:** New RAG techniques published. Old recommendations become outdated. Retrieved context is increasingly stale.

**What it looks like:** "Answers seem outdated" — users. "Faithfulness high but correctness dropping" — metrics.

**What observability catches:** Answer correctness diverging from faithfulness. High faithfulness (grounded in chunks) but low correctness (chunks themselves are outdated).

**Fix:** Audit knowledge base quarterly. Add change detection to source documents. Re-index on update.
""")

    with st.expander("Query drift — users ask new types of questions"):
        st.markdown("""
**What happens:** Users start asking questions the system wasn't designed for. New intent patterns emerge. They fall into general_inquiry and get poor responses.

**What it looks like:** "It doesn't understand what I'm asking" — users. "Unknown intent cluster growing" — observability.

**What observability catches:** Growing percentage of queries in general_inquiry. New patterns clustering together — structural, not random.

**Fix:** Expand intent taxonomy. Add knowledge base documents covering new patterns. Retrain classifier.
""")

    st.info("All three drift types look identical from outside — gradually worse answers. Only observability tells you which type is happening and where to fix it.")

    st.markdown("---")
    st.markdown("**RLHF — turning human signals into pipeline improvements**")

    st.markdown("""
<div style="background:var(--color-background-secondary);border-left:3px solid #9B59B6;
border-radius:0 8px 8px 0;padding:12px 16px;font-size:12px;color:var(--color-text-secondary);
line-height:1.7;margin-bottom:16px">
<strong style="color:#c78fff">RLHF in RAG is not the same as RLHF used to train ChatGPT.</strong><br><br>
In LLM training, RLHF adjusts the model's weights based on human preference scores — expensive, slow, requires thousands of examples.<br><br>
In RAG, RLHF means using signals from real users — thumbs up/down, query retries, citation clicks, session abandonment —
to automatically improve <em>which chunks get retrieved</em> and <em>how they're ranked</em>.
It's not retraining the LLM. It's retraining the <strong>retrieval layer</strong> based on what humans found useful.
Every thumbs down tells you: these chunks were retrieved, this answer was generated, something went wrong — adjust accordingly.
</div>
""", unsafe_allow_html=True)

    col1, col2, col3, col4, col5 = st.columns(5)
    signals = [
        ("👍", "Thumbs up", "Answer was useful", "Boost contributing chunks — raise retrieval weight for this query pattern", "#1D9E75"),
        ("👎", "Thumbs down", "Answer was wrong or unhelpful", "Penalise contributing chunks — lower score in future similar queries", "#E24B4A"),
        ("🔄", "Query retry", "User asked again immediately", "Answer was insufficient — flag query+chunks for investigation", "#BA7517"),
        ("🔗", "Citation click", "User verified the source", "Strong trust signal — chunk was credible, boost in re-ranker", "#4285F4"),
        ("🚪", "Session abandon", "User left without engaging", "Answer was irrelevant or confusing — review retrieval for intent", "#9B59B6"),
    ]
    for col, (icon, name, meaning, action, color) in zip([col1, col2, col3, col4, col5], signals):
        with col:
            st.markdown(
                f"<div style='background:var(--color-background-secondary);border-top:3px solid {color};"
                f"border-radius:0 0 8px 8px;padding:10px;height:100%'>"
                f"<div style='font-size:20px;text-align:center;margin-bottom:6px'>{icon}</div>"
                f"<div style='font-size:11px;font-weight:700;color:{color};margin-bottom:4px;text-align:center'>{name}</div>"
                f"<div style='font-size:10px;color:var(--color-text-secondary);margin-bottom:6px;font-style:italic'>{meaning}</div>"
                f"<div style='font-size:10px;color:var(--color-text-primary);line-height:1.5'>{action}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

    st.markdown("")
    st.markdown("""
<div style="background:var(--color-background-secondary);border-radius:8px;padding:14px 16px;
font-size:12px;line-height:1.8;margin:12px 0">
<strong style="color:var(--color-text-primary)">The RLHF loop in 4 steps:</strong><br>
<span style="color:#9B59B6">①</span> User gets answer →
<span style="color:#9B59B6">②</span> Gives signal (👍 / 👎 / retries) →
<span style="color:#9B59B6">③</span> Signal logged with chunk IDs that contributed to the answer →
<span style="color:#9B59B6">④</span> Re-ranker weights updated — next query with similar intent retrieves better chunks
</div>
""", unsafe_allow_html=True)

    st.markdown("""
<div style="background:#2a1a00;border:0.5px solid #BA7517;border-radius:8px;
padding:12px 14px;font-size:12px;color:#f0d090;line-height:1.7;margin-bottom:8px">
⚠️ <strong>This app vs enterprise:</strong> No feedback capture is implemented here — thumbs up/down are not wired up, and no chunk weights are adjusted.
In production, Cohere's re-ranker can be fine-tuned on <em>(query, good_chunk, bad_chunk)</em> triplets built from human feedback.
Pinecone and Weaviate both support preference-based score boosting.
The loop closes when a thumbs down in week 1 measurably improves retrieval in week 3.
</div>
""", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("**The closed feedback loop — how all 15 steps connect:**")
    st.components.v1.html("""
<style>
  .rag-diagram { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; padding: 8px 0; }
  .lane-label  { font-size: 11px; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; margin-bottom: 8px; }
  .lane        { border-radius: 12px; padding: 14px 16px; margin-bottom: 6px; }
  .steps-row   { display: flex; align-items: center; gap: 0; flex-wrap: nowrap; }
  .step-box    { border-radius: 8px; padding: 7px 10px; font-size: 11px; font-weight: 600;
                 text-align: center; white-space: nowrap; flex-shrink: 0; line-height: 1.3; }
  .step-num    { font-size: 9px; font-weight: 400; opacity: 0.75; display: block; margin-bottom: 2px; }
  .arrow       { font-size: 16px; padding: 0 3px; opacity: 0.5; flex-shrink: 0; }
  .connector   { display: flex; align-items: flex-start; justify-content: center;
                 gap: 0; padding: 0 16px; }
  .v-arrow     { display: flex; flex-direction: column; align-items: center;
                 font-size: 11px; color: #888; gap: 1px; }
  .v-line      { width: 2px; height: 18px; background: #aaa; }
  .v-tip       { font-size: 14px; line-height: 1; color: #aaa; }
  .feedback-row { display: flex; justify-content: space-between; padding: 8px 16px 0; gap: 10px; }
  .fb-box      { flex: 1; border-radius: 8px; padding: 8px 10px; font-size: 10px;
                 text-align: center; line-height: 1.5; }
  .fb-arrow    { font-size: 18px; color: #9B59B6; text-align: center; line-height: 1; }
  .fb-label    { font-size: 9px; font-weight: 700; letter-spacing: 0.05em; margin-bottom: 4px; }
  .loop-arc    { border: 2px dashed #9B59B6; border-radius: 0 0 16px 16px;
                 border-top: none; margin: 0 8px; height: 20px; }
  .loop-line   { border-left: 2px dashed #9B59B6; height: 100%; }
</style>

<div class="rag-diagram">

  <!-- OFFLINE PIPELINE -->
  <div class="lane" style="background:#1a3a6e; border: 1px solid #4285F4;">
    <div class="lane-label" style="color:#a8c8ff;">📦 Offline pipeline &nbsp;·&nbsp; runs once (or when docs change)</div>
    <div class="steps-row">
      <div class="step-box" style="background:#2a4f8e;border:1px solid #6aaaf8;color:#e8f2ff;">
        <span class="step-num" style="color:#a8c8ff;">Step 1</span>Ingest + Parse
      </div>
      <span class="arrow" style="color:#6aaaf8;">→</span>
      <div class="step-box" style="background:#2a4f8e;border:1px solid #6aaaf8;color:#e8f2ff;">
        <span class="step-num" style="color:#a8c8ff;">Step 2</span>Chunking
      </div>
      <span class="arrow" style="color:#6aaaf8;">→</span>
      <div class="step-box" style="background:#2a4f8e;border:1px solid #6aaaf8;color:#e8f2ff;">
        <span class="step-num" style="color:#a8c8ff;">Step 3</span>Metadata
      </div>
      <span class="arrow" style="color:#6aaaf8;">→</span>
      <div class="step-box" style="background:#2a4f8e;border:1px solid #6aaaf8;color:#e8f2ff;">
        <span class="step-num" style="color:#a8c8ff;">Step 4</span>Embedding
      </div>
      <span class="arrow" style="color:#6aaaf8;">→</span>
      <div class="step-box" style="background:#4285F4;border:1.5px solid #a8c8ff;color:#ffffff;font-weight:700;">
        <span class="step-num" style="color:#cce0ff;">Step 5</span>🗄️ Index
      </div>
    </div>
  </div>

  <!-- DOWN ARROW: KB ready -->
  <div style="text-align:center;margin:4px 0;">
    <div style="display:inline-block;text-align:center;">
      <div style="width:2px;height:12px;background:#888;margin:0 auto;"></div>
      <div style="font-size:14px;color:#888;">▼</div>
      <div style="font-size:10px;color:#aaa;margin-top:-2px;">Knowledge base ready</div>
    </div>
  </div>

  <!-- ONLINE PIPELINE -->
  <div class="lane" style="background:#0d3d2a; border: 1px solid #1D9E75; margin-top:2px;">
    <div class="lane-label" style="color:#6fcfaa;">🔍 Online pipeline &nbsp;·&nbsp; runs on every user query</div>
    <div class="steps-row" style="flex-wrap:wrap; gap: 2px 0;">
      <div class="step-box" style="background:#1a5c40;border:1px solid #3db882;color:#d0f5e8;">
        <span class="step-num" style="color:#6fcfaa;">Step 7</span>Query<br>Understanding
      </div>
      <span class="arrow" style="color:#3db882;">→</span>
      <div class="step-box" style="background:#1a5c40;border:1px solid #3db882;color:#d0f5e8;">
        <span class="step-num" style="color:#6fcfaa;">Step 8</span>Query<br>Embedding
      </div>
      <span class="arrow" style="color:#3db882;">→</span>
      <div class="step-box" style="background:#1a5c40;border:1px solid #3db882;color:#d0f5e8;">
        <span class="step-num" style="color:#6fcfaa;">Step 9</span>Vector<br>Search
      </div>
      <span class="arrow" style="color:#3db882;">→</span>
      <div class="step-box" style="background:#1a5c40;border:1px solid #3db882;color:#d0f5e8;">
        <span class="step-num" style="color:#6fcfaa;">Step 10</span>Re-ranking
      </div>
      <span class="arrow" style="color:#3db882;">→</span>
      <div class="step-box" style="background:#1a5c40;border:1px solid #3db882;color:#d0f5e8;">
        <span class="step-num" style="color:#6fcfaa;">Step 11</span>Context<br>Ordering
      </div>
      <span class="arrow" style="color:#3db882;">→</span>
      <div class="step-box" style="background:#1a5c40;border:1px solid #3db882;color:#d0f5e8;">
        <span class="step-num" style="color:#6fcfaa;">Step 11b</span>Context<br>Assembly
      </div>
      <span class="arrow" style="color:#3db882;">→</span>
      <div class="step-box" style="background:#1D9E75;border:1.5px solid #6fcfaa;color:#ffffff;font-weight:700;">
        <span class="step-num" style="color:#cdfaeb;">Step 12</span>⚡ Generation
      </div>
    </div>
  </div>

  <!-- DOWN ARROW: response -->
  <div style="text-align:center;margin:4px 0;">
    <div style="display:inline-block;text-align:center;">
      <div style="width:2px;height:12px;background:#888;margin:0 auto;"></div>
      <div style="font-size:14px;color:#888;">▼</div>
      <div style="font-size:10px;color:#aaa;margin-top:-2px;">LLM response</div>
    </div>
  </div>

  <!-- EVALUATION -->
  <div class="lane" style="background:#3d2000; border: 1px solid #BA7517; margin-top:2px;">
    <div class="lane-label" style="color:#f0b84a;">📐 Evaluation &nbsp;·&nbsp; how good was the response?</div>
    <div class="steps-row">
      <div class="step-box" style="background:#5a3200;border:1px solid #d4880a;color:#ffe0a0;min-width:160px;">
        <span class="step-num" style="color:#f0b84a;">Step 13 · every response</span>Rule-based Grounding Score
      </div>
      <span class="arrow" style="color:#d4880a;">→</span>
      <div class="step-box" style="background:#5a3200;border:1px solid #d4880a;color:#ffe0a0;min-width:160px;">
        <span class="step-num" style="color:#f0b84a;">Step 14 · 5–10% sampled</span>RAGAS (LLM-as-Judge)
      </div>
      <span class="arrow" style="color:#d4880a;">→</span>
      <div class="step-box" style="background:#BA7517;border:1.5px solid #f0b84a;color:#ffffff;font-weight:700;min-width:140px;">
        <span class="step-num" style="color:#ffe4b0;">Step 15</span>📊 Observability<br>dashboard + alerts
      </div>
    </div>
  </div>

  <!-- FEEDBACK LOOP -->
  <div style="margin-top:10px;border:1.5px dashed #9B59B6;border-radius:12px;padding:12px 16px;background:#1a0d2e;">
    <div style="font-size:11px;font-weight:700;color:#c78fff;margin-bottom:10px;text-align:center;">
      🔁 Closed feedback loop — observability triggers fixes back upstream
    </div>
    <div style="display:flex;gap:10px;justify-content:space-between;">

      <div style="flex:1;background:#1a3a6e;border:1px solid #4285F4;border-radius:8px;padding:10px;text-align:center;">
        <div style="font-size:10px;font-weight:700;color:#a8c8ff;margin-bottom:4px;">Embedding drift detected</div>
        <div style="font-size:10px;color:#c0d4f0;margin-bottom:6px;">Provider updates model silently — retrieval scores drop across the board</div>
        <div style="font-size:18px;color:#6aaaf8;">↑</div>
        <div style="font-size:10px;font-weight:600;color:#a8c8ff;">Re-embed entire KB</div>
        <div style="font-size:9px;color:#7aa8d8;">→ back to Step 4</div>
      </div>

      <div style="flex:1;background:#0d3d2a;border:1px solid #1D9E75;border-radius:8px;padding:10px;text-align:center;">
        <div style="font-size:10px;font-weight:700;color:#6fcfaa;margin-bottom:4px;">Data drift detected</div>
        <div style="font-size:10px;color:#b0e8d0;margin-bottom:6px;">World changes, KB stays static — faithfulness high but correctness drops</div>
        <div style="font-size:18px;color:#3db882;">↑</div>
        <div style="font-size:10px;font-weight:600;color:#6fcfaa;">Refresh source docs</div>
        <div style="font-size:9px;color:#4ab890;">→ back to Step 1</div>
      </div>

      <div style="flex:1;background:#3d2000;border:1px solid #BA7517;border-radius:8px;padding:10px;text-align:center;">
        <div style="font-size:10px;font-weight:700;color:#f0b84a;margin-bottom:4px;">Query drift detected</div>
        <div style="font-size:10px;color:#f0d090;margin-bottom:6px;">Users ask new question types — unknown intent cluster grows week on week</div>
        <div style="font-size:18px;color:#d4880a;">↑</div>
        <div style="font-size:10px;font-weight:600;color:#f0b84a;">Expand intent taxonomy</div>
        <div style="font-size:9px;color:#d4a040;">→ back to Step 7</div>
      </div>

    </div>
  </div>

</div>
""", height=620)

    render_enterprise_note(
        "LangSmith by LangChain is the most widely deployed RAG observability platform. Datadog's LLM Observability "
        "and Weights & Biases Weave offer similar capabilities. RAGAS in continuous evaluation mode evaluates 5-10% "
        "of production queries hourly — scores aggregated into dashboards, alerts firing when metrics cross thresholds. "
        "Embedding drift detection is an emerging practice — few teams do it today, all teams will need to in two years. "
        "The most sophisticated RAG teams treat observability as a product capability — they have dedicated AI ops roles "
        "who own dashboards, run weekly quality reviews, and translate metric trends into product decisions."
    )
    render_risk_table(RISKS)

    # ── PM Decision Matrix ────────────────────────────────────────────────────
    rows_data = [
        (
            "What does healthy look like?",
            "Have you defined baseline metrics for latency, retrieval success rate, answer quality, and user satisfaction before a single alert is configured — or will you only know something is wrong when users complain?",
            "Define a health baseline document before launch — measure each metric for 2 weeks post launch to establish baseline, then set alert thresholds at 15% degradation from baseline.",
            "A fintech RAG launched with no health baseline — when retrieval latency doubled 6 weeks post launch engineering argued it was always slow, PM had no baseline to prove otherwise, SLA breach went unresolved for 3 months.",
            "Health baselines shown as static demo values in the daily dashboard tab — query volume ~13k, retrieval latency ~90ms, faithfulness avg 0.88. These are illustrative, not measured from real traffic. No formal baseline document or alert thresholds defined.",
            "Health baseline document owned by PM — latency p50 and p95, retrieval success rate, grounding score, user satisfaction score, and session completion rate measured for 2 weeks post launch, alert thresholds set at 15% degradation, reviewed monthly.",
        ),
        (
            "What gets logged and who owns the logs?",
            "Do you know which pipeline steps are being logged, where those logs live, who has access to them, and how long they are retained — or did engineering make all those decisions without PM input?",
            "Define a minimum viable logging spec before build — log original query, expanded query, retrieved chunks with scores, context assembly output, final answer, grounding score, and user feedback signal at minimum.",
            "Intercom discovered during a compliance audit that their RAG was logging full user queries including personally identifiable information with no retention policy — GDPR violation required emergency log purge and pipeline rebuild, 6 engineer weeks lost.",
            "A session trace is displayed showing query, retrieval score, token count, grounding, and judge score — educational display only. No actual log storage, no log ownership policy, and no PII handling or retention rules defined.",
            "Logging spec owned jointly by PM and legal — defines which pipeline steps are logged, what data is captured per step, PII handling policy, retention period per data type, access controls, and log review cadence before pipeline goes to production.",
        ),
        (
            "Who gets alerted and when?",
            "When your faithfulness score drops below threshold at 2am on a Sunday, does the right person find out immediately or does it sit in a dashboard until someone checks it Monday morning?",
            "Define an alert routing matrix before launch — map each alert type to a named owner, severity level, response SLA, and escalation path.",
            "A healthcare RAG had all alerts routed to the engineering on-call — a sustained grounding score drop over a weekend was triaged as low priority infrastructure noise, clinical PM discovered it Monday morning after 3 patient facing sessions had already used the degraded pipeline.",
            "No alert routing — the static daily dashboard shows status indicators (Normal/Watch) but there is no live alerting system, no named owners per alert type, and no escalation path.",
            "Alert routing matrix owned by PM — latency alerts route to engineering on-call, grounding and faithfulness alerts route to PM and domain expert, user satisfaction drop alerts route to PM and product leadership, severity levels and response SLAs defined per alert type.",
        ),
        (
            "How do you separate pipeline failures from content failures?",
            "When answer quality drops, do you know within 30 minutes whether it is a retrieval problem, a chunking problem, a generation problem, or a content staleness problem — or does debugging take days?",
            "Build a failure taxonomy before launch — define the distinguishing signals for each failure type so triage is fast and escalation goes to the right team immediately.",
            "Glean spent 2 weeks debugging a quality degradation that turned out to be a content staleness problem misidentified as a retrieval failure — engineering optimized vector search indexes while the real issue was a Confluence sync that had silently stopped running 3 weeks earlier.",
            "Three drift failure types documented with distinguishing signals — embedding drift, data drift, and query drift — each with what it looks like, what observability catches, and how to fix it. No formal triage runbook or named team assignment per failure type.",
            "Failure taxonomy document owned by PM — pipeline failures mapped to distinguishing signals, triage runbook defined per failure type, each failure type assigned to a named team owner, runbook tested in a simulated failure exercise before launch.",
        ),
        (
            "How do you close the loop from user feedback to pipeline fix?",
            "When a user clicks thumbs down, do you know within 24 hours which pipeline step caused the bad answer and whether a fix is on the roadmap — or does that signal disappear into a feedback database nobody queries?",
            "Define a user feedback to pipeline fix workflow before launch — thumbs down triggers named investigation, investigation maps to pipeline step, pipeline step owner creates fix ticket within 48 hours.",
            "Notion AI collected thousands of thumbs down signals in their first month — feedback sat in a database with no review process, PM assumed engineering was analyzing it, engineering assumed PM was triaging it, 6 weeks passed before anyone built the query to look at it.",
            "No user feedback mechanism — thumbs up/down are not implemented in this app. The feedback loop shown in this step is educational and illustrative, not a live data capture or triage system.",
            "User feedback workflow owned by PM — thumbs down triggers automated ticket creation, PM reviews aggregate daily, patterns mapped to pipeline steps weekly, fix tickets assigned to named owners within 48 hours of pattern identification, feedback loop closure rate tracked as a PM metric.",
        ),
        (
            "How do you turn user feedback into retrieval improvements?",
            "When a user clicks thumbs down, do you know which chunks contributed to the bad answer and does that signal automatically adjust how those chunks score in future queries — or does the feedback disappear into a database nobody acts on?",
            "Define a feedback-to-retrieval improvement pipeline before launch — map each signal type to a specific pipeline action, set minimum signal volume before weights are adjusted to avoid overfitting to single signals, and document who reviews weight changes before they go live.",
            "Intercom implemented thumbs down feedback but routed all signals to a product analytics dashboard with no pipeline integration. After 6 months they had 40,000 negative signals and retrieval weights were identical to day one. A junior engineer spent 3 weeks backfilling the integration that should have been built first.",
            "No feedback capture in this app — thumbs up/down are not implemented. RLHF is taught as an educational concept; the actual signal capture and weight adjustment loop is not running.",
            "RLHF pipeline owned jointly by PM and ML engineer — thumbs down triggers chunk penalty logged with query ID and chunk IDs, minimum 50 signals before weight update, PM reviews proposed weight changes weekly, A/B test new weights on 10% of traffic before full rollout, improvement measured against golden dataset baseline.",
        ),
        (
            "How do you monitor for silent degradation?",
            "Is your pipeline getting quietly worse week over week in ways that never trigger an alert because each individual drop is too small to cross a threshold but the cumulative drift is destroying user trust?",
            "Define a weekly trend review process separate from alert monitoring — plot each health metric as a 4 week trend line, flag any metric showing consistent directional movement even if it has not crossed alert threshold.",
            "A legal tech RAG had stable alert dashboards for 4 months — a PM quarterly review revealed context precision had dropped from 0.91 to 0.74 over 16 weeks in increments too small to trigger weekly alerts, root cause was gradual document staleness that no single alert was designed to catch.",
            "Weekly trend monitoring demonstrated in the app — the weekly tab shows a 4-week context precision decline with a flag at week 4 illustrating what silent degradation looks like. This is educational content; no automated trend monitoring runs against real data.",
            "Weekly trend review owned by PM — all health metrics plotted as 4 week rolling trends, any metric showing 3 consecutive weeks of directional movement triggers investigation regardless of alert threshold, monthly trend review presented to product leadership with pipeline health narrative.",
        ),
    ]
    render_pm_matrix("Observability", rows_data)
    render_nav(next_label="You're done! 🎉", next_disabled=True, pipeline="online", show_jump=True)

    # ── End screen ────────────────────────────────────────────────────────────
    st.markdown("---")
    st.components.v1.html("""
<div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
     background:linear-gradient(135deg,#0d1f0f 0%,#0d1a2e 100%);
     border:1px solid #2a4a2a;border-radius:16px;padding:32px 28px;text-align:center;">

  <div style="font-size:36px;margin-bottom:8px;">🎉</div>
  <div style="font-size:22px;font-weight:700;color:#ffffff;margin-bottom:8px;">
    You've walked through the full enterprise RAG pipeline
  </div>
  <div style="font-size:13px;color:#a0c0a0;margin-bottom:24px;line-height:1.7;">
    15 steps. Two pipelines. Every layer an enterprise team ships in production.
  </div>

  <!-- what you covered -->
  <div style="display:flex;gap:12px;justify-content:center;flex-wrap:wrap;margin-bottom:24px;">

    <div style="background:#1a3a6e;border:1px solid #4285F4;border-radius:10px;padding:12px 16px;min-width:180px;">
      <div style="font-size:11px;font-weight:700;color:#a8c8ff;margin-bottom:8px;">📦 Offline pipeline</div>
      <div style="font-size:10px;color:#c8deff;line-height:1.8;text-align:left;">
        ✓ Document ingestion + routing<br>
        ✓ Parsing + cleaning<br>
        ✓ Chunking strategies<br>
        ✓ Dense embeddings (Google TE4)<br>
        ✓ Metadata tagging<br>
        ✓ HNSW vector indexing
      </div>
    </div>

    <div style="background:#0d3d2a;border:1px solid #1D9E75;border-radius:10px;padding:12px 16px;min-width:180px;">
      <div style="font-size:11px;font-weight:700;color:#6fcfaa;margin-bottom:8px;">🔍 Online pipeline</div>
      <div style="font-size:10px;color:#c0f0dc;line-height:1.8;text-align:left;">
        ✓ HyDE query understanding<br>
        ✓ Query embedding<br>
        ✓ Hybrid search (BM25 + dense + RRF)<br>
        ✓ Cohere cross-encoder re-ranking<br>
        ✓ Sandwich context ordering<br>
        ✓ Multi-LLM generation
      </div>
    </div>

    <div style="background:#3d2000;border:1px solid #BA7517;border-radius:10px;padding:12px 16px;min-width:180px;">
      <div style="font-size:11px;font-weight:700;color:#f0b84a;margin-bottom:8px;">📐 Evaluation + observability</div>
      <div style="font-size:10px;color:#ffe0a0;line-height:1.8;text-align:left;">
        ✓ Rule-based grounding (every response)<br>
        ✓ RAGAS LLM-as-judge (sampled)<br>
        ✓ Faithfulness · relevancy · precision<br>
        ✓ Drift detection (3 types)<br>
        ✓ Closed feedback loop<br>
        ✓ Observability dashboards
      </div>
    </div>

  </div>

  <div style="font-size:12px;color:#80a080;line-height:1.8;">
    You now understand what every enterprise AI team builds — and why each layer exists.
  </div>

</div>
""", height=380)

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("🔍 Try a different query", use_container_width=True, type="primary"):
            for k in ["query", "results"]:
                if k in st.session_state:
                    del st.session_state[k]
            go_to("s07_query_understanding")
    with col2:
        if st.button("📦 Revisit offline pipeline", use_container_width=True):
            go_to("s01_ingestion")
    with col3:
        if st.button("🔄 Start over from scratch", use_container_width=True):
            reset_session()
    with col4:
        if st.button("👋 End session", use_container_width=True):
            st.session_state["show_goodbye"] = True
            st.rerun()

    if st.session_state.get("show_goodbye"):
        st.components.v1.html("""
<div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
     background:linear-gradient(135deg,#0d1a2e 0%,#1a0d2e 100%);
     border:1px solid #4a3a6a;border-radius:16px;padding:40px 28px;text-align:center;margin-top:16px;">
  <div style="font-size:48px;margin-bottom:12px;">🙏</div>
  <div style="font-size:22px;font-weight:700;color:#ffffff;margin-bottom:10px;">
    Thank you for exploring Behind The RAG
  </div>
  <div style="font-size:13px;color:#b0a0d0;line-height:1.9;margin-bottom:20px;max-width:480px;margin-left:auto;margin-right:auto;">
    You've walked through every layer of an enterprise RAG system — <br>
    from raw documents to grounded, evaluated responses.<br><br>
    You can safely close this tab now. 👋
  </div>
  <div style="font-size:11px;color:#7060a0;">
    Part of the <strong style="color:#9B8FD0;">Behind The Series</strong> · built to make enterprise AI transparent
  </div>
</div>
""", height=300)
        st.stop()
