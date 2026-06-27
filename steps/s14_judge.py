"""Step 14 — RAG Evaluation (RAGAS-inspired LLM-as-Judge)."""
import streamlit as st
import json
import time
from ui import (render_topbar, render_step_header, render_thinking_card,
                render_what_we_built, render_enterprise_note, render_risk_table, render_nav, render_pm_matrix, render_key_takeaway)
from state import store_result, get_result, has_llm_key, LLM_MODELS

PROVIDER_META = {
    "gemini": {"label": "Google Gemini", "color": "#4285F4", "icon": "🟢"},
    "claude": {"label": "Anthropic Claude", "color": "#D97706", "icon": "🟠"},
    "openai": {"label": "OpenAI", "color": "#10A37F", "icon": "🔵"},
}

RAGAS_METRICS = {
    "faithfulness": {
        "label": "Faithfulness",
        "ragas": "RAGAS faithfulness",
        "desc": "What % of response claims are supported by retrieved context? Measures hallucination.",
    },
    "answer_relevancy": {
        "label": "Answer Relevancy",
        "ragas": "RAGAS answer_relevancy",
        "desc": "Does the response actually answer the user's question?",
    },
    "context_precision": {
        "label": "Context Precision",
        "ragas": "RAGAS context_precision",
        "desc": "What fraction of retrieved chunks were actually useful for answering?",
    },
    "context_recall": {
        "label": "Context Recall",
        "ragas": "RAGAS context_recall",
        "desc": "Did retrieval find all the information needed to answer fully?",
    },
    "answer_correctness": {
        "label": "Answer Correctness",
        "ragas": "RAGAS answer_correctness",
        "desc": "Is the answer factually correct based on the source documents?",
    },
}

JUDGE_PROMPT = """You are an expert RAG pipeline evaluator using the RAGAS evaluation framework.
Evaluate the pipeline run below across 5 RAGAS dimensions.

IMPORTANT: You MUST output exactly this JSON structure and nothing else — no markdown, no explanation outside JSON:
{{
  "faithfulness": {{"score": 0.0, "explanation": "one sentence"}},
  "answer_relevancy": {{"score": 0.0, "explanation": "one sentence"}},
  "context_precision": {{"score": 0.0, "explanation": "one sentence"}},
  "context_recall": {{"score": 0.0, "explanation": "one sentence"}},
  "answer_correctness": {{"score": 0.0, "explanation": "one sentence"}},
  "overall_score": 0.0,
  "verdict": "<excellent|good|correct_reasoning_wrong_data|retrieval_failure|poor_response>",
  "what_went_well": "one sentence",
  "what_went_wrong": "one sentence",
  "pm_recommendations": ["rec1", "rec2", "rec3"],
  "severity": "<critical|moderate|minor|none>"
}}

All scores must be between 0.0 and 1.0."""

FALLBACK = {
    "faithfulness": {"score": 0.89, "explanation": "Most claims traceable to retrieved context with minor paraphrasing"},
    "answer_relevancy": {"score": 0.85, "explanation": "Response addresses the core question directly"},
    "context_precision": {"score": 0.76, "explanation": "Some retrieved chunks relevant but not all directly answer the query"},
    "context_recall": {"score": 0.82, "explanation": "Key information about the mechanism was retrieved"},
    "answer_correctness": {"score": 0.88, "explanation": "Factually correct based on source documents"},
    "overall_score": 0.84,
    "verdict": "good",
    "what_went_well": "Faithfulness strong — LLM stayed within retrieved context without fabricating",
    "what_went_wrong": "Context precision at 0.76 — some retrieved chunks were tangentially related",
    "pm_recommendations": [
        "Raise similarity threshold from 0.25 to 0.40 to filter low-relevance chunks",
        "Consider a domain-specific re-ranker trained on RAG query-answer pairs",
        "Monitor context precision weekly — if it drops below 0.70, re-chunk the knowledge base",
    ],
    "severity": "minor",
}

VERDICT_STYLE = {
    "excellent":                   ("#1D9E75", "#1D9E75"),
    "good":                        ("#1D9E75", "#1D9E75"),
    "correct_reasoning_wrong_data": ("#BA7517", "#BA7517"),
    "retrieval_failure":           ("#E24B4A", "#E24B4A"),
    "poor_response":               ("#E24B4A", "#E24B4A"),
}

RISKS = [
    {"risk": "Self-evaluation bias", "example": "Same model generates response and evaluates it — scores itself 0.95 consistently — real quality is 0.70", "mitigation": "Use a different or more capable model as judge — never same model evaluating its own output"},
    {"risk": "Metric gaming", "example": "Team optimises faithfulness score specifically — answer relevancy drops unnoticed", "mitigation": "Track all 5 RAGAS metrics together — optimising one at expense of others is a failure mode"},
    {"risk": "Evaluation cost ignored", "example": "Judge runs on every query — doubles LLM API cost — nobody budgeted for it", "mitigation": "Sample-based evaluation in production — 5-10% of queries, stratified by intent type"},
    {"risk": "No baseline established", "example": "Team runs evaluation but has no historical baseline — can't tell if 0.85 is good or regressing", "mitigation": "Establish baseline on day 1 — every score compared to baseline, not just absolute thresholds"},
]


def _call_judge(provider: str, judge_model: str, api_key: str, judge_input: str) -> dict:
    """Call the judge LLM using the provided api_key. Returns parsed JSON result."""
    full_prompt = JUDGE_PROMPT + "\n\nEvaluate this pipeline run:\n" + judge_input
    sys_msg = "You are an expert RAG evaluation assistant. Always respond with valid JSON only."

    if provider == "gemini":
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        judge_client = genai.GenerativeModel(judge_model)
        response = judge_client.generate_content(full_prompt)
        raw = response.text.strip()

    elif provider == "claude":
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        # Claude 4+ dropped temperature — only pass for Claude 3.x
        kwargs = dict(model=judge_model, max_tokens=1000, system=sys_msg,
                      messages=[{"role": "user", "content": full_prompt}])
        if judge_model.startswith("claude-3"):
            kwargs["temperature"] = 0.0
        response = client.messages.create(**kwargs)
        raw = response.content[0].text.strip()

    elif provider == "openai":
        import openai
        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=judge_model,
            max_tokens=1000,
            temperature=0.0,
            messages=[
                {"role": "system", "content": sys_msg},
                {"role": "user", "content": full_prompt},
            ],
        )
        raw = response.choices[0].message.content.strip()

    else:
        raise ValueError(f"Unknown provider: {provider}")

    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


def render():
    render_topbar()
    render_step_header("📊", "Evaluation II: RAGAS (LLM-as-Judge)",
        "A second LLM scores the full pipeline across 5 RAGAS dimensions — deeper than rule-based grounding.")

    render_thinking_card(
        "The previous step ran rule-based grounding on every single response — fast, free, no API call. "
        "This step goes deeper using a second LLM as the evaluator (RAGAS framework). "
        "Because it costs an API call, enterprises only run this on 5–10% of queries, sampled across intent types. "
        "Think of it as: Step 13 is your real-time quality gate on every response. "
        "Step 14 is your weekly audit that catches what the rule-based check missed.",
        pipeline="online"
    )

    # ── RAGAS framework explainer ─────────────────────────────────────────────
    st.markdown("**What is RAGAS?**")
    st.markdown("""
<div style="background:var(--color-background-secondary);border:0.5px solid var(--color-border-tertiary);
border-radius:10px;padding:14px;font-size:12px;line-height:1.8">
<strong>RAGAS</strong> (Retrieval-Augmented Generation Assessment) is the industry-standard framework for
evaluating RAG pipelines end-to-end. It measures 5 dimensions independently so you can pinpoint
<em>exactly</em> which layer is failing — retrieval, context quality, or generation.
<br><br>
Used in production at Spotify, NVIDIA, Databricks, and most enterprise AI teams.
</div>
""", unsafe_allow_html=True)

    st.markdown("")

    # ── Offline vs Online vs Golden Dataset ───────────────────────────────────
    st.markdown("**Three evaluation modes every PM must understand**")
    col_off, col_on, col_gold = st.columns(3)

    with col_off:
        st.markdown("""
<div style="background:var(--color-background-secondary);border-top:3px solid #1D9E75;
border-radius:0 0 8px 8px;padding:14px;height:100%">
<div style="font-size:13px;font-weight:700;color:#1D9E75;margin-bottom:8px">🏋️ Offline Evaluation</div>
<div style="font-size:12px;color:var(--color-text-secondary);line-height:1.7">
Run <strong>before deploying any change</strong> — new chunking strategy, different top-k, model upgrade, prompt edit.<br><br>
You run your golden dataset through the new pipeline and compare RAGAS scores to the previous version.<br><br>
Answers: <em>"Is this version better or worse than what's live?"</em><br><br>
Think of it as <strong>unit tests for your RAG pipeline</strong> — catches regressions before users see them.
</div>
</div>
""", unsafe_allow_html=True)

    with col_on:
        st.markdown("""
<div style="background:var(--color-background-secondary);border-top:3px solid #0A84FF;
border-radius:0 0 8px 8px;padding:14px;height:100%">
<div style="font-size:13px;font-weight:700;color:#0A84FF;margin-bottom:8px">📡 Online Evaluation</div>
<div style="font-size:12px;color:var(--color-text-secondary);line-height:1.7">
Runs <strong>in production on real user queries</strong> — continuously, after you've shipped.<br><br>
You sample 5–10% of live traffic and run RAGAS on those queries. Too expensive to run on everything.<br><br>
Signals to watch: RAGAS score trend week-over-week, thumbs up/down from users, query retry rate (user asked again = bad answer), latency drift.<br><br>
Answers: <em>"Is quality degrading as our knowledge base ages?"</em>
</div>
</div>
""", unsafe_allow_html=True)

    with col_gold:
        st.markdown("""
<div style="background:var(--color-background-secondary);border-top:3px solid #FF9500;
border-radius:0 0 8px 8px;padding:14px;height:100%">
<div style="font-size:13px;font-weight:700;color:#FF9500;margin-bottom:8px">🎯 Golden Dataset</div>
<div style="font-size:12px;color:var(--color-text-secondary);line-height:1.7">
A curated set of <strong>100–200 real user questions</strong> with expert-validated ideal answers.<br><br>
This is your ground truth. Every offline evaluation runs against this set. Without it, you have no baseline — a score of 0.85 means nothing if you don't know what 0.85 compares to.<br><br>
Built from: real user query logs, validated by domain experts, refreshed quarterly.<br><br>
<strong>PM owns this.</strong> Engineering builds the pipeline. PM owns the definition of "correct."
</div>
</div>
""", unsafe_allow_html=True)

    st.markdown("")
    st.markdown("""
<div style="background:var(--color-background-secondary);border-left:3px solid #BA7517;
border-radius:0 8px 8px 0;padding:12px 14px;font-size:12px;color:var(--color-text-secondary);line-height:1.6">
⚠️ <strong>What this step demos vs what production does:</strong> Right now we're running RAGAS on a single live query you just typed — this is useful for learning but not how production evaluation works. Real evaluation runs your golden dataset (hundreds of queries) through the pipeline offline before every release, then samples production traffic online to catch degradation over time.
</div>
""", unsafe_allow_html=True)

    st.markdown("---")

    # ── 5 metrics grid ────────────────────────────────────────────────────────
    cols = st.columns(5)
    metric_colors = ["#4285F4", "#1D9E75", "#BA7517", "#9B59B6", "#E24B4A"]
    for col, (key, meta), color in zip(cols, RAGAS_METRICS.items(), metric_colors):
        with col:
            st.markdown(
                f"<div style='background:{color}11;border:1px solid {color}33;border-radius:8px;"
                f"padding:8px;text-align:center'>"
                f"<div style='font-size:10px;font-weight:600;color:{color}'>{meta['label']}</div>"
                f"<div style='font-size:9px;color:var(--color-text-tertiary);margin-top:2px'>{meta['desc']}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

    st.markdown("---")

    # ── Provider and judge model selection ────────────────────────────────────
    MODEL_CATALOGUE = {
        "gemini": [
            ("gemini-2.5-flash",      "Gemini 2.5 Flash · balanced · free · recommended"),
            ("gemini-2.5-flash-lite", "Gemini 2.5 Flash Lite · fastest · free"),
            ("gemini-2.5-pro",        "Gemini 2.5 Pro · most capable · free"),
            ("gemini-3.5-flash",      "Gemini 3.5 Flash · agentic tasks · free"),
        ],
        "claude": [
            ("claude-sonnet-4-6",  "Claude Sonnet 4.6 · fast + smart · recommended"),
            ("claude-haiku-4-5",   "Claude Haiku 4.5 · fastest · most affordable"),
            ("claude-opus-4-8",    "Claude Opus 4.8 · most capable · highest cost"),
            ("claude-opus-4-7",    "Claude Opus 4.7 · very capable"),
            ("claude-sonnet-4-5",  "Claude Sonnet 4.5 · previous gen"),
        ],
        "openai": [
            ("gpt-4o-mini",  "GPT-4o Mini · fast · affordable · recommended"),
            ("gpt-4o",       "GPT-4o · powerful"),
            ("gpt-5.4-mini", "GPT-5.4 Mini · latest · coding + agents"),
            ("gpt-5.4",      "GPT-5.4 · latest frontier · highest cost"),
        ],
    }

    gen_result = get_result("generation")
    grounding  = get_result("grounding")
    vs_result  = get_result("vector_search")

    gen_provider = (gen_result or {}).get("provider", st.session_state.get("llm_provider", "gemini"))
    gen_model    = (gen_result or {}).get("model", LLM_MODELS.get(gen_provider, ""))
    meta         = PROVIDER_META.get(gen_provider, PROVIDER_META["gemini"])

    st.markdown("**Judge model configuration**")

    st.warning(
        f"⚠️ **Self-evaluation bias:** Response was generated with **{meta['icon']} {gen_model}**. "
        "Using the same model to evaluate its own output inflates scores. "
        "Best practice: pick a different (ideally more capable) model as judge.",
        icon=None,
    )

    use_same = st.radio(
        "Judge model",
        options=["same", "different"],
        format_func=lambda x: {
            "same": f"Use same model  ({meta['icon']} {gen_model})",
            "different": "Use a different judge model",
        }[x],
        key="judge_model_choice",
        horizontal=True,
    )

    if use_same == "same":
        judge_provider = gen_provider
        judge_model    = gen_model
        judge_key      = None   # reuse sidebar key
        st.markdown(
            f"<div style='font-size:11px;color:var(--color-text-tertiary);margin-top:4px'>"
            f"Judge: {meta['icon']} <strong>{judge_model}</strong> · same as generation — bias risk applies</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown("")
        col1, col2, col3 = st.columns([1, 1.4, 1.4])

        with col1:
            judge_provider = st.selectbox(
                "Provider",
                options=["gemini", "claude", "openai"],
                format_func=lambda p: {"gemini": "🟢 Gemini", "claude": "🟠 Claude", "openai": "🔵 OpenAI"}[p],
                key="judge_provider_select",
            )

        catalogue     = MODEL_CATALOGUE[judge_provider]
        model_ids     = [m[0] for m in catalogue]
        model_labels  = [m[1] for m in catalogue]

        with col2:
            selected_label = st.selectbox(
                "Model",
                options=model_labels,
                key=f"judge_model_select_{judge_provider}",
            )
            judge_model = model_ids[model_labels.index(selected_label)]

        judge_meta = PROVIDER_META[judge_provider]
        key_placeholders = {
            "gemini": ("Gemini API key", "AIza...", "aistudio.google.com (free)"),
            "claude": ("Anthropic API key", "sk-ant-...", "console.anthropic.com"),
            "openai": ("OpenAI API key", "sk-...", "platform.openai.com"),
        }
        key_label, key_placeholder, key_url = key_placeholders[judge_provider]

        # Use sidebar key if provider matches, otherwise ask for a dedicated key
        sidebar_key = {
            "gemini": st.session_state.get("gemini_key"),
            "claude": st.session_state.get("anthropic_key"),
            "openai": st.session_state.get("openai_key"),
        }.get(judge_provider)

        with col3:
            if sidebar_key:
                judge_key = sidebar_key
                st.markdown(
                    f"<div style='margin-top:28px;font-size:11px;color:#1D9E75'>"
                    f"✅ Using {judge_meta['icon']} key from sidebar</div>",
                    unsafe_allow_html=True,
                )
            else:
                judge_key_input = st.text_input(
                    key_label,
                    type="password",
                    placeholder=key_placeholder,
                    help=f"Get a key at {key_url}",
                    key="judge_key_input",
                )
                judge_key = judge_key_input.strip() if judge_key_input.strip() else None

        if not judge_key:
            st.info(
                f"Add your {judge_meta['icon']} {judge_meta['label']} API key above, "
                f"or paste it in the sidebar to use it here automatically. Get one at **{key_url}**."
            )
            render_nav(next_label="Next: Observability →", pipeline="online", show_jump=True)
            return

    # ── Key check for "same model" path — resolve the actual key ─────────────
    if use_same == "same":
        if not has_llm_key():
            st.info(f"Add your {meta['label']} API key in the sidebar to run evaluation.")
            render_nav(next_label="Next: Observability →", pipeline="online", show_jump=True)
            return
        judge_provider = gen_provider
        judge_key = {
            "gemini": st.session_state.get("gemini_key") or st.secrets.get("GEMINI_API_KEY"),
            "claude": st.session_state.get("anthropic_key") or st.secrets.get("ANTHROPIC_API_KEY"),
            "openai": st.session_state.get("openai_key") or st.secrets.get("OPENAI_API_KEY"),
        }.get(judge_provider)

    # ── Run evaluation ─────────────────────────────────────────────────────────
    result = get_result("judge")
    # Invalidate if judge model changed
    if result and result.get("judge_model") != judge_model:
        result = None

    if not result:
        if not gen_result:
            st.info("Complete the Generation step first to run evaluation.")
            render_nav(next_label="Next: Observability →", pipeline="online", show_jump=True)
            return

        context_text = " ".join(
            item["chunk"].text[:200] for item in gen_result.get("context_chunks", [])
        )
        grounding_score = (
            sum(1 for r in (grounding or []) if r.get("status") == "grounded")
            / max(len(grounding or [1]), 1)
        )
        best_score = (
            vs_result.get("scored", [{"score": 0}])[0].get("score", 0)
            if vs_result else 0
        )

        judge_input = f"""QUERY: {st.session_state.get("query", "")}
RESPONSE: {gen_result.get("response", "")}
GROUNDING SCORE (rule-based): {grounding_score:.2f}
BEST RETRIEVAL SCORE: {best_score:.3f}
CONTEXT PREVIEW: {context_text[:500]}
GENERATION MODEL: {gen_model}
JUDGE MODEL: {judge_model}
SAME MODEL EVALUATING ITSELF: {gen_model == judge_model}"""

        if st.button("▶ Run RAGAS Evaluation", type="primary"):
            with st.spinner(f"Evaluating with {judge_model}…"):
                try:
                    eval_result = _call_judge(judge_provider, judge_model, judge_key, judge_input)
                    eval_result["judge_model"] = judge_model
                    eval_result["gen_model"] = gen_model
                    eval_result["self_eval"] = (gen_model == judge_model)
                    store_result("judge", eval_result)
                    st.rerun()
                except Exception as e:
                    st.error(f"Evaluation failed: {str(e)}")
                    st.caption("Fix the error above and try again — no scores have been saved.")

        with st.expander("Show pre-computed sample scores instead", expanded=False):
            st.caption("These are example scores only — not from your actual pipeline run.")
            if st.button("Load sample scores", key="load_fallback"):
                fb = dict(FALLBACK)
                fb["judge_model"] = judge_model
                fb["gen_model"] = gen_model
                fb["self_eval"] = (gen_model == judge_model)
                fb["_fallback"] = True
                store_result("judge", fb)
                st.rerun()
        return

    # ── Show evaluation results ────────────────────────────────────────────────
    if result.get("_fallback"):
        st.warning("⚠️ These are **pre-computed sample scores**, not from your actual pipeline run. Click **🔄 Re-evaluate** below to run live evaluation.")

    if result.get("self_eval"):
        st.warning(
            f"⚠️ These scores were generated by **{result.get('judge_model')}** evaluating its own output. "
            "Scores may be inflated due to self-evaluation bias.",
            icon=None,
        )

    verdict = result.get("verdict", "good")
    verdict_color, _ = VERDICT_STYLE.get(verdict, ("#1D9E75", "#1D9E75"))
    verdict_labels = {
        "excellent": "✅ Excellent",
        "good": "✅ Good",
        "correct_reasoning_wrong_data": "⚠️ Correct reasoning, wrong data",
        "retrieval_failure": "❌ Retrieval failure",
        "poor_response": "❌ Poor response quality",
    }

    st.markdown(
        f"<div style='border-left:4px solid {verdict_color};padding:10px 14px;"
        f"background:{verdict_color}11;border-radius:0 8px 8px 0;margin-bottom:16px'>"
        f"<div style='font-size:14px;font-weight:500;color:{verdict_color}'>"
        f"{verdict_labels.get(verdict, verdict)}</div>"
        f"<div style='font-size:12px;color:var(--color-text-secondary);margin-top:4px'>"
        f"{result.get('what_went_wrong', '')}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # ── Faithfulness comparison: rule-based vs LLM ────────────────────────────
    grounding_score = (
        sum(1 for r in (grounding or []) if r.get("status") == "grounded")
        / max(len(grounding or [1]), 1)
    )
    ragas_faithfulness = result.get("faithfulness", {}).get("score", 0)
    gr_color  = "#1D9E75" if grounding_score >= 0.70 else "#BA7517" if grounding_score >= 0.50 else "#E24B4A"
    raf_color = "#1D9E75" if ragas_faithfulness >= 0.80 else "#BA7517" if ragas_faithfulness >= 0.60 else "#E24B4A"
    diff = abs(ragas_faithfulness - grounding_score)
    diff_note = (
        "✅ Rule-based and LLM scores agree — high confidence in faithfulness assessment."
        if diff < 0.15 else
        "⚠️ Scores differ. LLM likely caught paraphrased claims that word-overlap missed — "
        "or rule-based was too strict on valid rewording. LLM score is more reliable."
    )

    st.markdown("**Faithfulness: rule-based (previous step) vs RAGAS LLM-as-Judge (this step)**")
    st.caption("Both measure the same thing — did the LLM stay within retrieved context? — using different methods.")
    fa_col1, fa_col2, fa_col3 = st.columns([1, 1, 2])
    with fa_col1:
        st.markdown(
            f"<div style='text-align:center;padding:12px;background:{gr_color}11;"
            f"border:1px solid {gr_color}44;border-radius:8px'>"
            f"<div style='font-size:10px;color:var(--color-text-tertiary)'>📐 Rule-based grounding</div>"
            f"<div style='font-size:10px;color:var(--color-text-tertiary)'>(word overlap — prev step)</div>"
            f"<div style='font-size:24px;font-weight:700;color:{gr_color};margin-top:4px'>{grounding_score:.2f}</div>"
            f"</div>", unsafe_allow_html=True)
    with fa_col2:
        st.markdown(
            f"<div style='text-align:center;padding:12px;background:{raf_color}11;"
            f"border:1px solid {raf_color}44;border-radius:8px'>"
            f"<div style='font-size:10px;color:var(--color-text-tertiary)'>🧑‍⚖️ RAGAS Faithfulness</div>"
            f"<div style='font-size:10px;color:var(--color-text-tertiary)'>(LLM semantic check)</div>"
            f"<div style='font-size:24px;font-weight:700;color:{raf_color};margin-top:4px'>{ragas_faithfulness:.2f}</div>"
            f"</div>", unsafe_allow_html=True)
    with fa_col3:
        diff_color = "#1D9E75" if diff < 0.15 else "#BA7517"
        st.markdown(
            f"<div style='padding:12px;background:{diff_color}11;"
            f"border:1px solid {diff_color}44;border-radius:8px;height:100%'>"
            f"<div style='font-size:11px;color:{diff_color};font-weight:600'>Gap: {diff:.2f}</div>"
            f"<div style='font-size:11px;color:var(--color-text-secondary);margin-top:4px;line-height:1.5'>{diff_note}</div>"
            f"</div>", unsafe_allow_html=True)

    st.markdown("")

    # ── Remaining 4 RAGAS score cards (faithfulness already shown above) ──────
    st.markdown("**Remaining RAGAS dimensions:**")
    metrics = ["answer_relevancy", "context_precision", "context_recall", "answer_correctness"]
    labels  = ["Answer Relevancy", "Context Precision", "Context Recall", "Answer Correctness"]
    metric_tooltips = {
        "answer_relevancy":  "Does the response actually answer what the user asked?",
        "context_precision": "What fraction of retrieved chunks were actually useful?",
        "context_recall":    "Did retrieval find all the info needed to answer fully?",
        "answer_correctness":"Is the answer factually correct per the source documents?",
    }
    cols = st.columns(4)
    for col, key, label in zip(cols, metrics, labels):
        with col:
            score = result.get(key, {}).get("score", 0)
            color = "#1D9E75" if score >= 0.80 else "#BA7517" if score >= 0.60 else "#E24B4A"
            st.markdown(
                f"<div style='text-align:center;padding:10px;background:var(--color-background-secondary);"
                f"border-radius:8px;border:0.5px solid {color}44'>"
                f"<div style='font-size:10px;color:var(--color-text-tertiary);margin-bottom:2px'>{label}</div>"
                f"<div style='font-size:9px;color:var(--color-text-tertiary);margin-bottom:4px;font-style:italic'>{metric_tooltips[key]}</div>"
                f"<div style='font-size:20px;font-weight:600;color:{color}'>{score:.2f}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
            st.caption(result.get(key, {}).get("explanation", ""))

    # ── Overall summary row ───────────────────────────────────────────────────
    overall = result.get("overall_score", 0)
    overall_color = "#1D9E75" if overall >= 0.80 else "#BA7517" if overall >= 0.60 else "#E24B4A"

    st.markdown("")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(
            f"<div style='text-align:center;padding:12px;background:{overall_color}11;"
            f"border:1px solid {overall_color}44;border-radius:8px'>"
            f"<div style='font-size:11px;color:var(--color-text-tertiary)'>Overall RAGAS score</div>"
            f"<div style='font-size:26px;font-weight:700;color:{overall_color}'>{overall:.2f}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
    with c2:
        judge_display = result.get("judge_model", judge_model)
        bias_flag = result.get("self_eval", False)
        bias_color = "#BA7517" if bias_flag else "#1D9E75"
        bias_text  = "⚠️ Self-eval (bias risk)" if bias_flag else "✅ Different model"
        st.markdown(
            f"<div style='text-align:center;padding:12px;background:var(--color-background-secondary);"
            f"border:0.5px solid var(--color-border-tertiary);border-radius:8px'>"
            f"<div style='font-size:11px;color:var(--color-text-tertiary)'>Judge model</div>"
            f"<div style='font-size:13px;font-weight:600;color:var(--color-text-primary);margin:4px 0'>{judge_display}</div>"
            f"<div style='font-size:10px;color:{bias_color}'>{bias_text}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
    with c3:
        severity = result.get("severity", "none")
        sev_color = {"critical": "#E24B4A", "moderate": "#BA7517", "minor": "#4285F4", "none": "#1D9E75"}.get(severity, "#1D9E75")
        st.markdown(
            f"<div style='text-align:center;padding:12px;background:{sev_color}11;"
            f"border:1px solid {sev_color}44;border-radius:8px'>"
            f"<div style='font-size:11px;color:var(--color-text-tertiary)'>Severity</div>"
            f"<div style='font-size:26px;font-weight:700;color:{sev_color}'>{severity.title()}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

    # ── What went well + PM recs ──────────────────────────────────────────────
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(
            f"<div style='background:var(--color-background-secondary);border-left:3px solid #1D9E75;"
            f"border-radius:0 8px 8px 0;padding:12px'>"
            f"<div style='font-size:11px;font-weight:600;color:#1D9E75;margin-bottom:6px'>✅ What went well</div>"
            f"<div style='font-size:12px;color:var(--color-text-secondary)'>{result.get('what_went_well', '')}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
    with col2:
        recs = result.get("pm_recommendations", [])
        recs_html = "".join(
            f"<div style='font-size:11px;color:var(--color-text-secondary);margin-bottom:4px'>{i+1}. {r}</div>"
            for i, r in enumerate(recs)
        )
        st.markdown(
            f"<div style='background:var(--color-background-secondary);border-left:3px solid #4285F4;"
            f"border-radius:0 8px 8px 0;padding:12px'>"
            f"<div style='font-size:11px;font-weight:600;color:#4285F4;margin-bottom:6px'>📋 PM recommendations</div>"
            f"{recs_html}</div>",
            unsafe_allow_html=True,
        )

    if st.button("🔄 Re-evaluate", key="reeval"):
        store_result("judge", None)
        st.rerun()

    st.markdown("---")

    # ── PM Decision Matrix ────────────────────────────────────────────────────
    rows_data = [
        (
            "Which RAGAS metrics matter most?",
            "Does your domain fail more on faithfulness — model making things up — or context recall — pipeline missing the right chunks entirely — and do you know the difference?",
            "Rank RAGAS metrics by domain risk before running a single evaluation — faithfulness is non-negotiable for compliance, answer relevancy matters most for consumer products, context recall is critical for knowledge management.",
            "A legal tech RAG optimized for answer relevancy score — users rated answers as helpful but a compliance audit found faithfulness was at 0.61, meaning 40% of answers contained claims not traceable to retrieved context, product was pulled from pilot.",
            "All five RAGAS metrics evaluated — faithfulness, answer relevancy, context precision, context recall, and answer correctness. No formal priority ranking among them; all are shown equally with no domain-specific weighting.",
            "RAGAS metric priority ranking defined by PM per domain — compliance and legal rank faithfulness first, consumer products rank answer relevancy first, knowledge management ranks context recall first, priority documented before first evaluation run.",
        ),
        (
            "What score triggers action?",
            "Do you have defined thresholds for each RAGAS metric that automatically trigger investigation, pipeline change, or product rollback — or are scores just numbers in a dashboard nobody acts on?",
            "Define action thresholds per metric per domain risk tier before launch — scores without thresholds are vanity metrics.",
            "Glean ran RAGAS evaluations for 3 months post launch with no defined thresholds — data science team flagged a context precision drop from 0.82 to 0.71 in a weekly report, PM did not act because no one had defined what 0.71 meant for the business, issue compounded for 6 more weeks.",
            "No formal action thresholds — evaluation scores and PM recommendations are surfaced per run but there is no threshold that triggers an automated investigation, alert, or rollback.",
            "Action threshold matrix defined by PM per metric and domain — faithfulness below 0.85 triggers immediate investigation in compliance domains, context recall below 0.80 triggers chunking review, two consecutive weeks below threshold triggers formal incident process.",
        ),
        (
            "How do you build your evaluation dataset?",
            "Is your golden dataset a representative sample of real user queries with expert validated answers or a collection of easy questions an engineer wrote in an afternoon?",
            "Define golden dataset construction criteria before building evaluation pipeline — who selects queries, who validates answers, how many examples per query type, and how often the dataset is refreshed.",
            "A healthcare RAG built its golden dataset from synthetic queries generated by the model itself — evaluation scores looked excellent but real user queries exposed massive gaps, dataset had no examples of the ambiguous multi-step clinical questions users actually asked.",
            "No golden dataset — RAGAS evaluation runs on the single live query just processed. There is no curated query set, no expert-validated expected answers, and no representative coverage of query types.",
            "Golden dataset construction process owned by PM — minimum 200 queries sampled from real user logs per query type, answers validated by domain expert, dataset refreshed quarterly, new query patterns added within 30 days of appearing in query logs.",
        ),
        (
            "How do you explain RAGAS scores to stakeholders?",
            "Can you translate a faithfulness score of 0.73 into a business risk statement that a CPO or General Counsel will act on without asking what faithfulness means?",
            "Build a RAGAS to business risk translation layer before your first stakeholder review — executives need risk language not metric language.",
            "A fintech PM presented RAGAS scores in a quarterly business review — CFO asked what faithfulness meant, PM explained the technical definition, CFO disengaged, no budget was allocated to fix a pipeline that was generating ungrounded answers in customer facing financial summaries.",
            "RAGAS scores shown with explanations per metric and PM recommendations generated per run — no stakeholder translation layer mapping scores to business risk language for non-technical audiences.",
            "PM owns a one-page RAGAS business translation doc — faithfulness becomes answer accuracy risk, context recall becomes knowledge gap risk, answer relevancy becomes user experience risk, context precision becomes noise and cost risk, updated before every stakeholder review.",
        ),
        (
            "Offline vs online evaluation — what's your cadence?",
            "Do you know the difference between evaluating before a change ships (offline) and monitoring quality after it ships (online) — and have you decided how often to run each?",
            "Define your evaluation cadence before launch — offline evaluation before every pipeline change, online evaluation sampled continuously in production. Document who reviews results and how fast findings become roadmap items.",
            "A B2B SaaS company ran RAGAS evaluations only when users complained — by the time a faithfulness degradation was caught, it had been live for 11 weeks and affected 3 enterprise accounts. An offline evaluation before the KB refresh that caused it would have caught it in 20 minutes.",
            "This app runs RAGAS on a single live query per session — no offline evaluation against a golden dataset, no production sampling cadence. Useful for learning the mechanics; not representative of how production evaluation works.",
            "PM defines and owns the evaluation cadence — offline evaluation required before every pipeline change with sign-off gate, online evaluation runs on 5-10% of production traffic daily, weekly score review by PM, monthly golden dataset refresh reviewed by domain expert.",
        ),
        (
            "How does RAGAS connect to your roadmap?",
            "When a RAGAS metric drops, do you know which pipeline step caused it and does that finding automatically generate a roadmap item or disappear into a Slack thread?",
            "Build a RAGAS to pipeline step mapping before launch — each metric maps to specific upstream decisions, score drops should trigger named roadmap investigations not ad hoc debugging.",
            "Notion AI saw a sustained context precision drop over 6 weeks — data science flagged it in evaluation reports, engineering assumed PM was tracking it, PM assumed engineering was fixing it, no roadmap item was created, issue was discovered 3 months later during a user research session when participants complained about irrelevant answers.",
            "No formal RAGAS to roadmap feedback loop — scores are shown per session and PM recommendations are generated, but there is no mechanism connecting a score drop to a named investigation ticket or roadmap item.",
            "RAGAS to pipeline mapping document owned by PM — faithfulness drop maps to system prompt and generation review, context recall drop maps to chunking and indexing review, each metric threshold breach automatically generates a named investigation ticket assigned to PM within 24 hours.",
        ),
    ]

    render_pm_matrix("Evaluation II: RAGAS", rows_data)

    render_what_we_built(
        f"We run RAGAS-inspired LLM-as-Judge evaluation using <strong>{result.get('judge_model', judge_model)}</strong> "
        f"({'⚠️ same as generation — bias risk' if result.get('self_eval') else '✅ different from generation model'}). "
        "Combined with rule-based grounding from the previous step for a complete quality picture."
    )
    render_enterprise_note(
        "RAGAS (ragas.io) is the most widely adopted RAG evaluation framework — used at Spotify, NVIDIA, and Databricks. "
        "Patronus AI and TruLens run LLM-as-judge on production traffic — every response scored for faithfulness and relevancy. "
        "At Anthropic, Claude Opus judges Claude Sonnet outputs — never self-evaluation. "
        "The key product insight: evaluation is not a one-time benchmark — it's a continuous feedback loop. "
        "Teams that track RAGAS scores weekly catch retrieval degradation (knowledge base going stale) before users do."
    )
    render_risk_table(RISKS)
    render_key_takeaway("RAGAS gives you a vocabulary for RAG quality that engineering, PM, and leadership can share. Faithfulness drops → generation problem. Context recall drops → retrieval problem. Context precision drops → chunking or re-ranking problem. Each metric points to a specific layer — which is exactly what you need to make roadmap decisions.", pipeline="online")
    render_nav(next_label="Next: Observability →", pipeline="online", show_jump=True)
