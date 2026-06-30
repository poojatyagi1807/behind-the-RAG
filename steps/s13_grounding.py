"""Step 13 — Response Grounding."""
import streamlit as st
import re
from ui import (render_topbar, render_step_header, render_thinking_card,
                render_what_we_built, render_enterprise_note, render_risk_table, render_nav, render_pm_matrix)
from state import store_result, get_result

RISKS = [
    {"risk": "Silent hallucination", "example": "Response looks grounded, reads fluently, but contains one fabricated specific — a wrong date", "mitigation": "Claim-level grounding — numbers and dates get special scrutiny beyond sentence-level check"},
    {"risk": "Threshold too strict", "example": "Grounding check rejects valid paraphrases — user gets 'I cannot answer' for clearly supported questions", "mitigation": "Calibrate threshold on validation set — measure false rejection rate alongside hallucination rate"},
    {"risk": "Source citation wrong", "example": "Response cites Pinecone for a claim that came from RAG paper", "mitigation": "Claim-to-chunk attribution — track which specific chunk each claim was grounded in"},
    {"risk": "Partial grounding accepted silently", "example": "Partial claims accumulate across multi-turn — response gradually drifts from retrieved facts", "mitigation": "Track partial grounding rate over conversation turns — alert when drift exceeds baseline"},
]


def _check_grounding(response: str, chunks: list) -> list:
    """Check each sentence against each chunk individually."""
    sentences = re.split(r'(?<=[.!?])\s+', response)
    results = []
    for sent in sentences:
        sent = sent.strip()
        if len(sent) < 20:
            continue
        sent_words = set(re.findall(r'\b[a-z]{4,}\b', sent.lower()))

        best_score = 0
        best_source = "—"
        per_chunk = []

        for item in chunks:
            chunk_text = item["chunk"].text
            chunk_words = set(re.findall(r'\b[a-z]{4,}\b', chunk_text.lower()))
            overlap = len(sent_words & chunk_words)
            total = len(sent_words)
            score = overlap / total if total > 0 else 0

            # Penalise if sentence contains numbers not in this chunk
            has_numbers = bool(re.findall(r'\$[\d,]+|\d+%|\d+ days|\d+ hours|\d+\.\d+', sent))
            if has_numbers:
                nums_sent = set(re.findall(r'\d+', sent))
                nums_chunk = set(re.findall(r'\d+', chunk_text))
                if len(nums_sent & nums_chunk) < len(nums_sent) * 0.5:
                    score = min(score, 0.4)

            per_chunk.append({"source": item["chunk"].doc_title, "score": round(score, 2)})
            if score > best_score:
                best_score = score
                best_source = item["chunk"].doc_title

        if best_score >= 0.6:
            status = "grounded"
        elif best_score >= 0.3:
            status = "partial"
        else:
            status = "ungrounded"

        results.append({
            "sentence": sent,
            "status": status,
            "score": round(best_score, 2),
            "best_source": best_source,
            "per_chunk": per_chunk,
        })
    return results


def render():
    render_topbar()
    render_step_header("🔍", "Evaluation I: Rule-based Grounding Score",
        "Did the LLM stay within what was retrieved? Fast, free, runs on every response.")

    render_thinking_card(
        "Did the LLM answer from the retrieved chunks, or did it make something up? "
        "This step checks every sentence in the answer against the chunks — no API call needed. "
        "A low grounding score means the LLM went beyond what was provided.",
        pipeline="online"
    )

    # ── Grounding vs RAGAS explainer ──────────────────────────────────────────
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown(
            "<div style='background:#4285F411;border:1px solid #4285F444;border-radius:10px;padding:12px 14px'>"
            "<div style='font-size:11px;font-weight:600;color:#4285F4;margin-bottom:6px'>📐 This step — Rule-based grounding</div>"
            "<div style='font-size:12px;color:var(--color-text-secondary);line-height:1.6'>"
            "Checks every sentence against retrieved chunks using <strong>word overlap</strong>. "
            "Fast, free, runs on every response in production. "
            "Misses semantic paraphrasing — <em>\"automobile\" won't match a chunk that says \"car\"</em>."
            "</div></div>",
            unsafe_allow_html=True,
        )
    with col_b:
        st.markdown(
            "<div style='background:#1D9E7511;border:1px solid #1D9E7544;border-radius:10px;padding:12px 14px'>"
            "<div style='font-size:11px;font-weight:600;color:#1D9E75;margin-bottom:6px'>🧑‍⚖️ Next step — RAGAS Faithfulness (LLM-as-Judge)</div>"
            "<div style='font-size:12px;color:var(--color-text-secondary);line-height:1.6'>"
            "Same question, answered by an LLM. Understands <strong>semantic meaning</strong> — "
            "catches paraphrases and subtle drift that word overlap misses. "
            "Costs an API call, so typically sampled (5–10% of queries)."
            "</div></div>",
            unsafe_allow_html=True,
        )
    st.markdown("")

    gen_result = get_result("generation")
    assembly = get_result("context_assembly")

    if not gen_result:
        st.info("Run the Generation step first to see grounding analysis.")
        render_nav(next_label="Next: Evaluation II — RAGAS →", pipeline="online", show_jump=True)
        return

    response = gen_result.get("response", "")
    context_chunks = gen_result.get("context_chunks", assembly.get("kept", []) if assembly else [])

    if not context_chunks:
        st.warning("No retrieved chunks found. Complete the earlier pipeline steps to see grounding.")
        render_nav(next_label="Next: Evaluation II — RAGAS →", pipeline="online", show_jump=True)
        return

    grounding_results = _check_grounding(response, context_chunks)
    store_result("grounding", grounding_results)

    grounded  = sum(1 for r in grounding_results if r["status"] == "grounded")
    partial   = sum(1 for r in grounding_results if r["status"] == "partial")
    ungrounded = sum(1 for r in grounding_results if r["status"] == "ungrounded")
    total = len(grounding_results)
    score = grounded / total if total > 0 else 0

    # ── Summary scorecard ─────────────────────────────────────────────────────
    score_color = "#1D9E75" if score >= 0.7 else "#BA7517" if score >= 0.5 else "#E24B4A"
    c0, c1, c2, c3 = st.columns(4)
    with c0:
        st.markdown(
            f"<div style='text-align:center;padding:12px;background:{score_color}11;"
            f"border:1px solid {score_color}44;border-radius:8px'>"
            f"<div style='font-size:10px;color:var(--color-text-tertiary)'>Grounding score</div>"
            f"<div style='font-size:26px;font-weight:700;color:{score_color}'>{score:.0%}</div>"
            f"</div>", unsafe_allow_html=True)
    with c1:
        st.markdown(
            "<div style='text-align:center;padding:12px;background:#1D9E7511;"
            "border:1px solid #1D9E7544;border-radius:8px'>"
            "<div style='font-size:10px;color:var(--color-text-tertiary)'>🟢 Grounded</div>"
            f"<div style='font-size:26px;font-weight:700;color:#1D9E75'>{grounded}</div>"
            "<div style='font-size:10px;color:var(--color-text-tertiary)'>supported by context</div>"
            "</div>", unsafe_allow_html=True)
    with c2:
        st.markdown(
            "<div style='text-align:center;padding:12px;background:#BA751711;"
            "border:1px solid #BA751744;border-radius:8px'>"
            "<div style='font-size:10px;color:var(--color-text-tertiary)'>🟡 Partial</div>"
            f"<div style='font-size:26px;font-weight:700;color:#BA7517'>{partial}</div>"
            "<div style='font-size:10px;color:var(--color-text-tertiary)'>loosely related</div>"
            "</div>", unsafe_allow_html=True)
    with c3:
        st.markdown(
            "<div style='text-align:center;padding:12px;background:#E24B4A11;"
            "border:1px solid #E24B4A44;border-radius:8px'>"
            "<div style='font-size:10px;color:var(--color-text-tertiary)'>🔴 Ungrounded</div>"
            f"<div style='font-size:26px;font-weight:700;color:#E24B4A'>{ungrounded}</div>"
            "<div style='font-size:10px;color:var(--color-text-tertiary)'>possible hallucination</div>"
            "</div>", unsafe_allow_html=True)

    st.markdown("")

    # ── Section 1: Retrieved chunks ───────────────────────────────────────────
    st.markdown("### 📄 What was retrieved")
    st.caption("These are the chunks the LLM was given as its only source of truth.")

    for i, item in enumerate(context_chunks):
        chunk = item["chunk"]
        score_val = item.get("score", 0)
        bar_color = "#1D9E75" if score_val >= 0.7 else "#BA7517" if score_val >= 0.4 else "#4285F4"
        with st.expander(f"Chunk {i+1} — {chunk.doc_title}  ·  relevance score {score_val:.3f}", expanded=(i == 0)):
            st.markdown(
                f"<div style='background:var(--color-background-secondary);"
                f"border-left:3px solid {bar_color};padding:10px 14px;"
                f"border-radius:0 8px 8px 0;font-size:12px;line-height:1.7;"
                f"color:var(--color-text-secondary)'>{chunk.text}</div>",
                unsafe_allow_html=True,
            )

    st.markdown("")

    # ── Section 2: Claim-by-claim table ───────────────────────────────────────
    st.markdown("### 🔬 Claim-by-claim grounding check")
    st.caption("Every sentence from the LLM response is checked against the retrieved chunks.")

    STATUS_ICON  = {"grounded": "🟢", "partial": "🟡", "ungrounded": "🔴"}
    STATUS_LABEL = {"grounded": "Grounded", "partial": "Partial", "ungrounded": "Ungrounded"}
    STATUS_MEANING = {
        "grounded":   "Supported — words and meaning found in retrieved context",
        "partial":    "Loosely related — some overlap but not directly supported",
        "ungrounded": "⚠️ Not found in context — possible hallucination",
    }
    STATUS_COLOR = {"grounded": "#1D9E75", "partial": "#BA7517", "ungrounded": "#E24B4A"}

    for i, r in enumerate(grounding_results):
        color  = STATUS_COLOR[r["status"]]
        icon   = STATUS_ICON[r["status"]]
        label  = STATUS_LABEL[r["status"]]
        meaning = STATUS_MEANING[r["status"]]

        st.markdown(
            f"<div style='border:0.5px solid {color}44;border-radius:10px;"
            f"padding:12px 14px;margin-bottom:10px;background:{color}08'>"

            # Claim text
            f"<div style='font-size:13px;color:var(--color-text-primary);"
            f"line-height:1.6;margin-bottom:8px'>"
            f"<strong style='color:var(--color-text-tertiary);font-size:11px'>CLAIM {i+1}</strong><br>"
            f"{r['sentence']}</div>"

            # Status row
            f"<div style='display:flex;align-items:center;gap:12px;flex-wrap:wrap'>"
            f"<span style='background:{color}22;border:1px solid {color}55;"
            f"border-radius:20px;padding:2px 10px;font-size:11px;font-weight:600;color:{color}'>"
            f"{icon} {label}</span>"
            f"<span style='font-size:11px;color:var(--color-text-tertiary)'>{meaning}</span>"
            f"<span style='font-size:11px;color:var(--color-text-tertiary);margin-left:auto'>"
            f"Best match score: <strong style='color:{color}'>{r['score']:.2f}</strong> "
            f"· from <em>{r['best_source']}</em></span>"
            f"</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

    # ── Section 3: Grounding threshold explainer ──────────────────────────────
    st.markdown("")
    st.markdown("### ⚙️ Grounding threshold — a product decision")
    st.caption("How strict should the grounding check be? This is a trade-off every RAG product team must make.")

    threshold = st.select_slider(
        "Threshold",
        options=["Strict (≥ 0.90)", "Standard (≥ 0.60)", "Permissive (≥ 0.30)"],
        value="Standard (≥ 0.60)",
        label_visibility="collapsed",
    )
    threshold_info = {
        "Strict (≥ 0.90)":    ("Legal, medical, financial RAG", "Very few claims pass — safe but may over-reject valid paraphrases", "#E24B4A"),
        "Standard (≥ 0.60)":  ("Enterprise knowledge management", "Balanced — catches hallucinations without being too aggressive", "#1D9E75"),
        "Permissive (≥ 0.30)": ("Creative or exploratory use cases", "Most claims pass — risky for factual domains", "#BA7517"),
    }
    use_case, note, tcolor = threshold_info[threshold]
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown(
            f"<div style='background:{tcolor}11;border:1px solid {tcolor}44;"
            f"border-radius:8px;padding:10px 14px'>"
            f"<div style='font-size:11px;color:{tcolor};font-weight:600'>Best for</div>"
            f"<div style='font-size:12px;color:var(--color-text-secondary);margin-top:2px'>{use_case}</div>"
            f"</div>", unsafe_allow_html=True)
    with col_b:
        st.markdown(
            f"<div style='background:var(--color-background-secondary);"
            f"border-radius:8px;padding:10px 14px'>"
            f"<div style='font-size:11px;color:var(--color-text-tertiary);font-weight:600'>Trade-off</div>"
            f"<div style='font-size:12px;color:var(--color-text-secondary);margin-top:2px'>{note}</div>"
            f"</div>", unsafe_allow_html=True)

    st.markdown("---")

    # ── PM Decision Matrix ────────────────────────────────────────────────────
    rows_data = [
        (
            "What is your grounding definition?",
            "Does every claim in the answer need to exist verbatim in retrieved context or is faithful paraphrasing acceptable in your domain?",
            "Define grounding criteria with legal and domain experts before building any evaluation — verbatim for compliance domains, faithful paraphrasing acceptable for exploratory ones.",
            "We define grounding as word-overlap between answer sentences and retrieved chunks. This flags paraphrases as ungrounded even when the answer is accurate. A PM should define grounding with example judgements before building the checker — not after.",
            "Grounding defined as word overlap between answer sentences and retrieved chunks — no formal verbatim vs paraphrase policy, and no explicit acknowledgment of what the threshold means for domain risk.",
            "Grounding definition documented per content domain — compliance and legal domains require verbatim traceability, knowledge and support domains accept faithful paraphrasing, definition signed off by legal before evaluation pipeline is built.",
        ),
        (
            "Who evaluates grounding?",
            "Can an automated scorer reliably judge whether an answer is grounded in your domain or does your content require human expert review?",
            "Define evaluation method per content type — automated scoring for high volume low stakes content, human expert review for low volume high stakes content.",
            "Automated word-overlap only — no human review of grounding scores. A PM should manually review 20 answers and score them alongside the automated result to validate that the automated definition matches human judgement of 'is this answer grounded?'",
            "Rule-based automated check only — word overlap between each answer sentence and retrieved chunks, no LLM involved at this step. No human review layer and no semantic understanding of paraphrasing.",
            "Hybrid evaluation defined by PM — automated scoring for all responses, human expert review sample of 5% weekly, 100% human review for flagged low confidence responses in high stakes domains.",
        ),
        (
            "What is your grounding threshold?",
            "Below what grounding score does an answer become too risky to show the user and what happens to it — suppression, flagging, or human escalation?",
            "Define grounding thresholds per domain risk tier before launch — never leave threshold as an engineering default.",
            "We show a warning when grounding drops below 60%. We chose 60% without measuring what score corresponds to a trustworthy answer for our use case. A PM should calibrate: at what grounding score do human reviewers consider an answer unreliable for a non-technical PM audience?",
            "A threshold slider exists (Strict ≥ 0.60, Standard ≥ 0.50, Permissive ≥ 0.30) — but it only controls how sentences are classified and displayed, not whether answers are suppressed. All answers are shown regardless of score.",
            "Grounding threshold defined per domain risk tier by PM and legal — high risk domains suppress below 0.85, medium risk flag below 0.75 with visible warning, low risk surface all with grounding score shown to admin dashboard.",
        ),
        (
            "How do you handle partially grounded answers?",
            "When some claims in an answer are grounded and some are not, do you show the answer with a warning, suppress it entirely, or route it to human review?",
            "Define partial grounding handling policy per domain before launch — partial suppression is technically complex, be explicit about which approach engineering should build.",
            "We show partial grounding scores per sentence but still display the full answer. A user might trust a sentence the checker flagged as ungrounded. A PM should have defined: sentences below the grounding threshold should be visually marked as unverified so users know which parts to treat with caution.",
            "Partial grounding detection exists — each sentence is tagged grounded, partial, or ungrounded and shown in the UI. But no suppression or warning is applied; the full answer is always shown regardless of partial or ungrounded claim count.",
            "Partial grounding policy defined by PM — ungrounded claims highlighted inline for exploratory domains, entire response suppressed and routed to human review for compliance domains, policy documented and tested before launch.",
        ),
        (
            "How often do you run grounding evaluation?",
            "Is your domain risk high enough to require real time grounding evaluation on every response or is a weekly audit sample sufficient?",
            "Define evaluation cadence per domain risk tier — real time evaluation adds latency and cost, weekly audit misses live failures in high stakes domains.",
            "We run grounding on every response in the demo. For a production version this adds latency. A PM should decide: is per-response grounding essential for this use case (educational trust), or would sampling every 5th response be sufficient to catch systematic issues?",
            "Grounding evaluation runs on every response automatically — triggered immediately after generation with no sampling. No monitoring cadence, aggregate trend tracking, or alert if grounding score drops across sessions.",
            "Evaluation cadence defined per domain risk tier by PM — high stakes domains run real time grounding check on every response, medium risk run daily automated sample, low risk run weekly audit with monthly PM review of aggregate scores.",
        ),
    ]

    render_pm_matrix("Evaluation I: Grounding", rows_data)

    render_what_we_built(
        "We split the LLM response into individual claims (sentences), then check each one against "
        "every retrieved chunk using word overlap scoring. Each claim is tagged Grounded, Partial, or "
        "Ungrounded based on its best match score across all chunks."
    )
    render_enterprise_note(
        "RAGAS faithfulness metric measures what % of claims are supported by retrieved context — "
        "scores below 0.85 are flagged for review at most enterprise deployments. "
        "Patronus AI and TruLens run grounding checks on every response in production, not just during evaluation. "
        "For regulated industries — healthcare, finance, legal — the EU AI Act explicitly requires "
        "traceability of AI-generated claims to source documents."
    )
    render_risk_table(RISKS)
    render_nav(next_label="Next: Evaluation II — RAGAS →", pipeline="online", show_jump=True)
