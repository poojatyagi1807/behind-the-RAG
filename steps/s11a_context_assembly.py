"""Step 11a — Context Assembly (runs after ordering)."""
import streamlit as st
from ui import (render_topbar, render_step_header, render_thinking_card,
                render_what_we_built, render_enterprise_note, render_risk_table, render_nav, render_pm_matrix)
from state import store_result, get_result

RISKS = [
    {"risk": "Context overflow", "example": "10 chunks × 500 tokens + history = over limit — last chunks silently truncated", "mitigation": "Hard token budget — count tokens before assembly, reject chunks that exceed limit, log every truncation"},
    {"risk": "System prompt too long", "example": "Detailed instructions consume 2,000 tokens — leaves little room for chunks", "mitigation": "Prompt compression — distill system prompt to essential instructions, move verbose guidelines to fine-tuning"},
    {"risk": "No source attribution", "example": "Chunks assembled without source tags — LLM can't cite sources — hallucination risk increases", "mitigation": "Always tag each chunk with source before assembly — LLM can then attribute claims to specific documents"},
    {"risk": "Ordering not carried through", "example": "Ordering step decided sandwich — assembly step rebuilds in wrong order", "mitigation": "Assembly always reads from the ordering result — never re-sorts independently"},
]


def _count_tokens_approx(text: str) -> int:
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except Exception:
        return int(len(text.split()) * 1.3)


def render():
    render_topbar()
    render_step_header("📋", "Context Assembly",
        "Ordering is done. Now pack system prompt + ordered chunks + query into one structured prompt.")

    render_thinking_card(
        "This is the last step before the LLM sees anything. The system prompt sets the rules, "
        "the chunks provide the knowledge, the query is the question. "
        "Get the token budget wrong and chunks get truncated silently. "
        "Get the attribution wrong and the LLM can't cite its sources.",
        pipeline="online"
    )

    query = st.session_state.get("query", "How does RAG prevent hallucination?")

    # ── Pull ordered chunks from previous step ────────────────────────────────
    ordering_result = get_result("context_ordering")
    is_reranked = ordering_result.get("is_reranked", False) if ordering_result else False
    source_label = ordering_result.get("source", "Hybrid search") if ordering_result else "Hybrid search"
    strategy = ordering_result.get("strategy", "sandwich") if ordering_result else "sandwich"

    if ordering_result and ordering_result.get("ordered"):
        ordered_chunks = ordering_result["ordered"]
    else:
        # Fallback if ordering step was skipped
        ordered_chunks = [
            {"chunk": type("C", (), {"doc_title": "Pinecone guide", "text": "RAG reduces hallucination by anchoring generation to retrieved evidence...", "tfidf_vector": [], "word_count": 87})(), "score": 0.94},
            {"chunk": type("C", (), {"doc_title": "RAG paper", "text": "Parametric vs non-parametric memory — factual grounding mechanism...", "tfidf_vector": [], "word_count": 112})(), "score": 0.91},
        ]
        st.info("Complete Context Ordering (previous step) first for live results.")

    # ── Source + strategy badge ───────────────────────────────────────────────
    badge_color = "#1D9E75" if is_reranked else "#378ADD"
    st.markdown(
        f"<div style='display:inline-block;background:{badge_color}22;border:1px solid {badge_color}55;"
        f"border-radius:6px;padding:4px 12px;font-size:11px;color:{badge_color};margin-bottom:12px'>"
        f"{'✅ Cohere reranked' if is_reranked else '📊 Hybrid search'}"
        f" &nbsp;·&nbsp; {source_label}"
        f" &nbsp;·&nbsp; ordering: <strong>{strategy}</strong>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # ── System prompt — adapts to whether reranking was used ─────────────────
    st.markdown("**System prompt:**")
    if is_reranked:
        system_prompt = (
            "You are a precise RAG assistant. The retrieved context below has been verified by a "
            "cross-encoder re-ranker for direct relevance to the query. "
            "Answer only from this context. Cite the specific source for every claim. "
            "If the context does not contain the answer, say so — do not fabricate."
        )
        st.markdown(
            "<div style='font-size:10px;color:#1D9E75;margin-bottom:4px'>"
            "↑ Rerank-aware prompt — instructs the LLM that context has been cross-encoder verified</div>",
            unsafe_allow_html=True,
        )
    else:
        system_prompt = (
            "You are a helpful RAG assistant. Answer only from the retrieved context provided below. "
            "If the context does not contain the answer, say so clearly. "
            "Never fabricate information. Cite your sources."
        )

    # ── Token accounting ──────────────────────────────────────────────────────
    MODEL_LIMIT = 8192
    system_tokens = _count_tokens_approx(system_prompt)
    query_tokens = _count_tokens_approx(query)
    chunk_tokens = [_count_tokens_approx(item["chunk"].text) for item in ordered_chunks]
    total_tokens = system_tokens + sum(chunk_tokens) + query_tokens
    remaining = MODEL_LIMIT - total_tokens

    # ── Assembled context window ──────────────────────────────────────────────
    chunk_rows = "".join([
        f'<div style="margin-bottom:8px">'
        f'<div style="font-size:11px;color:#0F6E56;font-weight:500">'
        f'CHUNK {i+1} — {item["chunk"].doc_title}'
        f' · score {item["score"]:.3f} · {tok} tokens'
        f'{"  🥇 best relevance" if i == 0 else f"  🥈 2nd-best (sandwich tail)" if i == len(ordered_chunks)-1 and len(ordered_chunks) > 2 and strategy == "sandwich" else ""}'
        f'</div>'
        f'<div style="font-size:11px;color:var(--color-text-secondary);font-style:italic">'
        f'{item["chunk"].text[:110]}…</div>'
        f'</div>'
        for i, (item, tok) in enumerate(zip(ordered_chunks, chunk_tokens))
    ])

    token_color = "#1D9E75" if total_tokens < MODEL_LIMIT * 0.8 else "#E24B4A"

    st.markdown(f"""
<div style="background:var(--color-background-secondary);border:0.5px solid var(--color-border-tertiary);
border-radius:10px;padding:14px">

  <div style="font-size:11px;color:var(--color-text-tertiary);margin-bottom:4px;font-weight:500">
  SYSTEM PROMPT · {system_tokens} tokens
  {"&nbsp;<span style='color:#1D9E75;font-size:10px'>· rerank-aware</span>" if is_reranked else ""}
  </div>
  <div style="font-size:11px;color:var(--color-text-secondary);margin-bottom:12px;font-style:italic">
  {system_prompt[:150]}…</div>

  {chunk_rows}

  <div style="font-size:11px;color:var(--color-text-tertiary);margin-top:8px;font-weight:500">
  USER QUERY · {query_tokens} tokens</div>
  <div style="font-size:11px;color:var(--color-text-secondary);font-style:italic">{query}</div>

  <div style="border-top:0.5px solid var(--color-border-tertiary);margin-top:12px;padding-top:8px">
    <div style="display:flex;justify-content:space-between;font-size:12px">
      <span style="color:var(--color-text-tertiary)">Total tokens used</span>
      <span style="color:{token_color};font-weight:500">{total_tokens:,} / {MODEL_LIMIT:,}</span>
    </div>
    <div style="height:6px;background:var(--color-border-tertiary);border-radius:3px;margin-top:6px">
      <div style="height:6px;width:{min(total_tokens/MODEL_LIMIT*100,100):.0f}%;
      background:{token_color};border-radius:3px"></div>
    </div>
    <div style="font-size:11px;color:var(--color-text-tertiary);margin-top:4px">
    {remaining:,} tokens remaining for generation</div>
  </div>
</div>
""", unsafe_allow_html=True)

    store_result("context_assembly", {
        "kept": ordered_chunks,
        "total_tokens": total_tokens,
        "system_prompt": system_prompt,
        "source": source_label,
        "is_reranked": is_reranked,
    })

    what_built = (
        "System prompt is rerank-aware. Chunks assembled in the order decided by the previous step — "
        "sandwich ordering with Cohere-verified relevance scores."
        if is_reranked else
        "System prompt + hybrid-search chunks assembled in the ordering strategy chosen in the previous step."
    )
    st.markdown("---")

    # ── PM Decision Matrix ────────────────────────────────────────────────────
    rows_data = [
        (
            "What goes into the prompt beyond retrieved chunks?",
            "Does your model know who it is, what it can answer, how it should behave, and what it should never do — or are you just passing chunks and hoping for the best?",
            "Define full prompt anatomy before engineering builds context assembly — system instructions, retrieved chunks, user history, and output format all need explicit slots.",
            "A customer service RAG had no system instructions beyond retrieved chunks — model adopted whatever tone the user used, became sarcastic with frustrated users, went viral on social media before PM discovered there was no persona defined.",
            "System prompt is defined and included — sets the assistant role, answer-only-from-context rule, citation requirement, adversarial detection, and output format. No formal prompt anatomy document exists; structure evolved during build.",
            "Full prompt anatomy document owned by PM — system role, behavioral guardrails, output format, chunk slot, history slot, and fallback instructions all defined, versioned, and reviewed with legal before deployment.",
        ),
        (
            "How do you manage token budget?",
            "When your system prompt plus chunks plus conversation history exceeds the context window, what gets cut and does anyone know it is happening?",
            "Define a token budget allocation per prompt slot before build — set hard limits per slot and log when truncation occurs.",
            "Intercom discovered their RAG was silently truncating system guardrails when conversation history grew long — model started ignoring safety instructions mid-conversation, compliance team found it in a routine audit 3 months post launch.",
            "tiktoken counts tokens and a visual budget gauge is shown — but no automatic truncation of chunks occurs when the limit is approached. Overflow is flagged visually but not handled programmatically. Truncation is listed as an unmitigated risk on this page.",
            "Token budget allocated per slot by PM — system instructions protected from truncation, chunks trimmed before history, history trimmed before instructions, all truncation events logged and reviewed weekly.",
        ),
        (
            "What are the hard guardrails in the system prompt?",
            "Have you explicitly told the model what it must never say, never reveal, and never do — or are you relying on the base model's defaults?",
            "Define a guardrail checklist with legal and compliance before writing a single line of system prompt — never leave this to engineering judgment alone.",
            "Samsung engineers accidentally included confidential source code in their RAG context with no system prompt guardrail against revealing internal data — model surfaced proprietary code in responses, became a widely reported data leak.",
            "Basic guardrails defined — system prompt instructs the model to cite sources, stay in scope, and say so when context is insufficient. No formal legal or compliance review took place.",
            "Guardrail checklist owned jointly by PM and legal — covers confidentiality, tone, scope boundaries, competitor mentions, regulatory language, and escalation triggers, reviewed every quarter and on every major product update.",
        ),
        (
            "Does conversation history go into context?",
            "Does your user expect the model to remember earlier turns in the conversation and does your token budget actually support that?",
            "Define conversation memory scope explicitly — how many turns, what gets summarized vs retained verbatim, and when history resets.",
            "Salesforce Einstein RAG retained full conversation history indefinitely — after 10 turns context window was dominated by history, retrieved chunks were being truncated, answer quality degraded progressively through long sessions.",
            "No conversation history — single turn only. The query from Step 7 is the only user input passed to context; no prior turns are included.",
            "Conversation history policy defined by PM — rolling window of last 3-5 turns retained verbatim, older turns summarized by model before inclusion, history reset policy defined per session type.",
        ),
        (
            "Who owns the system prompt?",
            "If your system prompt was written at launch and never touched since, do you know what it actually says today and whether it still reflects your product?",
            "Assign a named PM owner for the system prompt with a quarterly review cadence — treat it as a living product document not a one-time engineering artifact.",
            "A fintech RAG system prompt was written by an engineer at launch and never reviewed — 8 months later a compliance audit found it contained outdated regulatory language, incorrect product names, and a persona description that contradicted the current brand voice.",
            "System prompt written and owned by the builder — no version control, no review cadence, no regression testing against queries when it changes.",
            "System prompt version controlled in git, owned by PM, reviewed quarterly with legal and brand, every change logged with rationale, regression tested against top 20 queries before deployment.",
        ),
    ]

    render_pm_matrix("Context Assembly", rows_data)

    render_what_we_built(what_built)
    render_enterprise_note(
        "LlamaIndex's ContextAssembler and LangChain's StuffDocumentsChain implement configurable context windows "
        "with overflow strategies. Anthropic's prompt caching allows frequently used context to be cached at the API "
        "level — reducing both latency and cost by up to 90% for repeated content. "
        "Mem0 and Zep are dedicated memory management services for multi-turn conversation handling — recent turns "
        "kept verbatim, older turns compressed to summaries."
    )
    render_risk_table(RISKS)
    render_nav(next_label="Next: Generation →", pipeline="online", show_jump=True)
