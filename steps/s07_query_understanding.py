"""Step 7 — Query Understanding."""
import streamlit as st
import re
import time
from ui import (render_topbar, render_step_header, render_thinking_card,
                render_what_we_built, render_enterprise_note, render_risk_table, render_nav, render_pm_matrix,
                render_gemini_key_prompt)
from state import (store_result, get_result, store_error,
                   get_llm_client, has_llm_key, LLM_MODELS)
from config.content import RECOMMENDED_QUERIES

# ── Adversarial query detection ───────────────────────────────────────────────

ADVERSARIAL_PATTERNS = {
    "prompt_injection": {
        "label": "Prompt Injection",
        "color": "#E24B4A",
        "icon": "💉",
        "description": "Trying to override or escape the system prompt",
        "what_happens": "The system prompt is passed to the LLM as a separate, higher-priority `system` parameter — not in the user message. Injecting instructions into the query does not override it.",
        "patterns": [
            r"ignore (previous|prior|all|your) instructions",
            r"disregard (your|the|all) instructions",
            r"forget (your|the|previous|prior) instructions",
            r"override (your|the) (instructions|system|prompt)",
            r"new instructions?:",
            r"system prompt:",
            r"you are now",
            r"\[system\]",
            r"</?(system|instruction|prompt)>",
            r"###\s*(system|instruction)",
        ],
    },
    "jailbreak": {
        "label": "Jailbreak Attempt",
        "color": "#E24B4A",
        "icon": "🔓",
        "description": "Trying to make the model act outside its defined role",
        "what_happens": "The system prompt instructs the model to only answer from retrieved context. Role-playing prompts don't change this — the grounding check in Step 13 will flag any response that invents facts.",
        "patterns": [
            r"act as (a|an|if)",
            r"pretend (you are|to be|you're)",
            r"roleplay as",
            r"you are (a|an) (different|new|unrestricted|evil|bad)",
            r"DAN\b",
            r"do anything now",
            r"no restrictions?",
            r"without (any |ethical |moral )?restrictions?",
            r"jailbreak",
        ],
    },
    "data_extraction": {
        "label": "Data / Prompt Extraction",
        "color": "#BA7517",
        "icon": "🕵️",
        "description": "Trying to read the system prompt or raw knowledge base contents",
        "what_happens": "The system prompt and chunk contents are never returned verbatim — the LLM is instructed to answer from context, not repeat it. Retrieved chunks are shown in this UI for educational purposes only.",
        "patterns": [
            r"(reveal|show|print|output|repeat|tell me|what (is|are)) (your|the) (system |)prompt",
            r"what (were|are) you (told|instructed|given)",
            r"(list|show|dump|print) (me )?(all |every )?(document|chunk|file|content|data)",
            r"what('s| is) in your (database|knowledge base|index|kb)",
            r"show me (all|every) (the )?(chunk|document|file)",
            r"(repeat|output|print) (everything|all) (you know|in context|above)",
            r"ignore the question.*show",
        ],
    },
    "social_engineering": {
        "label": "Social Engineering",
        "color": "#BA7517",
        "icon": "🎭",
        "description": "Using false authority or fictional framing to bypass guardrails",
        "what_happens": "Authority claims in the user message carry no weight — only the verified system prompt sets the rules. The model cannot confirm or deny who built it.",
        "patterns": [
            r"(my |the )?(boss|manager|ceo|developer|engineer|admin|anthropic|openai|google) (told|said|wants|asked)",
            r"for (testing|debug|development) purposes?",
            r"this is a test",
            r"(in|within) (this |a )?(hypothetical|fictional|imaginary|fantasy)",
            r"hypothetically (speaking)?[,:]",
            r"what would you (say|do) if",
        ],
    },
}


IN_SCOPE_TERMS = {
    # Core RAG concepts
    "rag", "retrieval", "retrieval-augmented", "augmented generation",
    "embedding", "embeddings", "embed",
    "vector", "vectors", "vectorstore", "vector store", "vector database",
    "chunk", "chunks", "chunking", "chunksize",
    "index", "indexing", "indexed", "reindex",
    "hallucination", "hallucinate", "confabulation", "grounding", "grounded",
    "context", "context window", "context assembly",
    "generation", "generate", "generated",
    "retriever", "retrieve", "retrieval",
    "rerank", "reranking", "re-rank", "cross-encoder",
    "similarity", "cosine similarity", "semantic search",
    "dense", "sparse", "hybrid search", "bm25", "tf-idf", "tfidf",
    "hnsw", "faiss", "annoy", "approximate nearest neighbour",
    "knowledge base", "knowledge graph",
    "faithfulness", "relevancy", "precision", "recall",
    # Models and providers
    "llm", "large language model", "language model",
    "gpt", "claude", "gemini", "openai", "anthropic", "google",
    "transformer", "bert", "attention", "token", "tokenization",
    "prompt", "prompting", "system prompt", "prompt engineering",
    # Evaluation
    "ragas", "evaluation", "evaluate", "judge", "llm-as-judge",
    "faithfulness", "answer relevancy", "context precision",
    "observability", "drift", "monitoring", "latency",
    # AI/ML general
    "ai", "artificial intelligence", "machine learning", "deep learning",
    "neural network", "nlp", "natural language",
    "fine-tuning", "fine-tune", "training", "inference",
    "model", "pipeline",
    # Infra / tools
    "pinecone", "weaviate", "qdrant", "chroma", "milvus",
    "langchain", "llamaindex", "cohere",
    "metadata", "metadata filter", "filtering",
    "ingestion", "parsing", "parse",
    "sandwich", "hyde", "hypothetical",
}

def _is_in_scope(query: str) -> bool:
    """Returns True if the query contains at least one RAG/AI-related term."""
    q = query.lower()
    # Remove punctuation for matching
    q_clean = re.sub(r'[^\w\s]', ' ', q)
    words = set(q_clean.split())
    # Check single words
    if words & IN_SCOPE_TERMS:
        return True
    # Check multi-word phrases
    for term in IN_SCOPE_TERMS:
        if ' ' in term and term in q:
            return True
    return False


def _detect_adversarial(query: str) -> dict | None:
    """Returns the first matched threat category or None if clean."""
    q = query.lower().strip()
    for threat_type, meta in ADVERSARIAL_PATTERNS.items():
        for pattern in meta["patterns"]:
            if re.search(pattern, q):
                return {"type": threat_type, **meta, "matched_pattern": pattern}
    return None

# Synonym map for query expansion — no LLM needed
_SYNONYMS = {
    "rag":          ["retrieval augmented generation", "retrieval-augmented generation"],
    "retrieval":    ["search", "lookup", "fetch"],
    "hallucination":["confabulation", "fabrication", "factual error"],
    "hallucinate":  ["confabulate", "fabricate"],
    "embedding":    ["vector representation", "dense vector"],
    "embeddings":   ["vector representations", "dense vectors"],
    "chunk":        ["passage", "text segment"],
    "chunking":     ["text splitting", "segmentation"],
    "vector":       ["dense representation", "embedding"],
    "search":       ["retrieval", "lookup", "similarity search"],
    "context":      ["retrieved passages", "source documents"],
    "generation":   ["llm output", "response synthesis"],
    "rerank":       ["re-score", "re-order"],
    "reranking":    ["re-scoring", "re-ordering"],
    "grounding":    ["faithfulness", "factual anchoring"],
    "evaluate":     ["assess", "measure", "score"],
    "evaluation":   ["assessment", "measurement", "scoring"],
    "pipeline":     ["workflow", "system", "architecture"],
    "query":        ["question", "user input", "request"],
    "document":     ["source", "passage", "text"],
    "index":        ["vector store", "knowledge base"],
    "model":        ["llm", "language model"],
    "sparse":       ["bm25", "keyword-based", "lexical"],
    "dense":        ["semantic", "embedding-based", "neural"],
    "hybrid":       ["combined sparse and dense", "multi-vector"],
    "similarity":   ["relevance", "semantic closeness"],
    "score":        ["relevance score", "similarity metric"],
    "faithfulness": ["grounding score", "factual accuracy"],
    "precision":    ["accuracy", "correctness"],
    "recall":       ["coverage", "completeness"],
}


def _expand_query(query: str) -> str:
    """Rule-based query expansion: append synonyms for recognised RAG terms."""
    import re as _re
    q_lower = query.lower()
    extras = []
    seen = set()
    for term, syns in _SYNONYMS.items():
        # match whole word
        if _re.search(r'\b' + _re.escape(term) + r'\b', q_lower):
            for s in syns[:2]:           # at most 2 synonyms per term
                if s not in seen and s not in q_lower:
                    extras.append(s)
                    seen.add(s)
        if len(extras) >= 4:
            break
    if extras:
        return query.rstrip("?") + " OR " + " OR ".join(extras)
    # fallback — strip punctuation variant
    return query.rstrip("?") + " OR " + query.replace("how ", "what is ").rstrip("?")


def _sanitize(text: str) -> str:
    """Strip Unicode chars that break ASCII encoding or HTML rendering."""
    text = text.replace(chr(0x2028), chr(10))   # Line Separator → newline
    text = text.replace(chr(0x2029), chr(10))   # Para Separator → newline
    text = text.replace(chr(0x200b), "")         # Zero-width space → remove
    text = text.replace(chr(0x00a0), " ")        # Non-breaking space → space
    return text.strip()


def _quick_llm_call(prompt: str) -> str:
    """Call the currently active LLM with a single-turn prompt. Returns sanitized text."""
    client, provider = get_llm_client()
    if client is None:
        raise RuntimeError("No LLM client — check your API key in the sidebar.")
    model = st.session_state.get(f"model_override_{provider}", LLM_MODELS[provider])
    if provider == "gemini":
        raw = client.generate_content(prompt).text
    elif provider == "claude":
        kwargs = dict(model=model, max_tokens=400,
                      messages=[{"role": "user", "content": prompt}])
        if model.startswith("claude-3"):
            kwargs["temperature"] = 0.3
        raw = client.messages.create(**kwargs).content[0].text
    elif provider == "openai":
        raw = client.chat.completions.create(
            model=model, max_tokens=400, temperature=0.3,
            messages=[{"role": "user", "content": prompt}],
        ).choices[0].message.content
    else:
        raise ValueError(f"Unknown provider: {provider}")
    return _sanitize(raw)


QUERY_COMPARISON = {
    "raw": {
        "label": "Raw query",
        "description": "No transformation. Pass exactly as typed.",
        "example_out": "how does RAG prevent hallucination",
        "best_score": 0.71,
        "best_chunk": "Pinecone — RAG reduces hallucinations",
        "pros": ["Simple", "No cost", "No latency"],
        "cons": ["Misses synonyms", "Misses paraphrase"],
    },
    "expansion": {
        "label": "Query expansion",
        "description": "Add synonyms and related terms to broaden recall.",
        "example_out": "how does RAG prevent hallucination OR reduce confabulation OR ground LLM responses OR anchor generation",
        "best_score": 0.84,
        "best_chunk": "RAG paper — non-parametric memory provides factual anchors",
        "pros": ["Better recall", "Catches synonyms"],
        "cons": ["More noise in results", "Lower precision"],
    },
    "hyde": {
        "label": "HyDE — Hypothetical Document Embeddings",
        "description": "LLM generates a hypothetical answer first. Search for text that looks like the answer, not the question.",
        "example_out": "RAG prevents hallucination by grounding LLM responses in retrieved source documents. The non-parametric memory provides factual anchors that constrain generation, separating what the model knows from what was retrieved.",
        "best_score": 0.91,
        "best_chunk": "RAG paper — parametric vs non-parametric memory as factual grounding mechanism",
        "pros": ["Best recall", "Searches answer space not question space", "Finds source-like text"],
        "cons": ["1 extra LLM call per query", "HyDE answer could be wrong"],
    },
}

RISKS = [
    {"risk": "Query too vague", "example": "'tell me more' — no context — retrieval returns random chunks", "mitigation": "Session context — carry previous query and response into current query understanding"},
    {"risk": "HyDE hallucination", "example": "LLM generates wrong hypothetical — retrieval finds chunks supporting the wrong answer", "mitigation": "Validate HyDE output against known facts before using. Flag low-confidence hypotheticals"},
    {"risk": "Expansion too broad", "example": "20 synonyms added — retrieval returns 100 results with low average relevance", "mitigation": "Cap expansion to 3-5 terms. Monitor precision@K — if it drops after expansion, expansion is hurting"},
    {"risk": "Sensitive query not caught", "example": "User asks for confidential info using vague language — query understanding doesn't flag", "mitigation": "Query safety classification runs in parallel — a separate classifier checks intent before retrieval proceeds"},
]

def _render_kb_status():
    """Compact card showing what the offline pipeline actually built and is active."""
    chunks      = st.session_state.get("kb_chunks", [])
    emb_loaded  = st.session_state.get("kb_embeddings_loaded", False)
    hnsw        = st.session_state.get("kb_hnsw")
    tfidf       = st.session_state.get("kb_tfidf")
    provider    = st.session_state.get("kb_embedding_provider", "")

    n_chunks  = len(chunks)
    n_docs    = len({c.doc_id for c in chunks}) if chunks else 0

    def row(ok, label, detail):
        icon  = "✅" if ok else "⚠️"
        color = "#0f5c3a" if ok else "#7a4a00"
        bg    = "#e6f4ed" if ok else "#fef3cd"
        bdr   = "#0f5c3a" if ok else "#d4900a"
        return (
            f"<div style='display:flex;align-items:baseline;gap:8px;"
            f"background:{bg};border-left:3px solid {bdr};"
            f"border-radius:0 6px 6px 0;padding:5px 12px;margin-bottom:4px'>"
            f"<span style='font-size:13px'>{icon}</span>"
            f"<span style='font-size:12px;font-weight:600;color:{color}'>{label}</span>"
            f"<span style='font-size:11px;color:#555'>{detail}</span>"
            f"</div>"
        )

    rows = "".join([
        row(bool(chunks),
            f"{n_chunks} chunks · {n_docs} documents loaded",
            "offline pipeline output — ready for retrieval"),
        row(emb_loaded,
            "Neural embeddings ready" if emb_loaded else "Neural embeddings unavailable",
            f"all-MiniLM-L6-v2 · 384-dim · fastembed ({provider})"
            if emb_loaded else "install fastembed — falling back to TF-IDF"),
        row(hnsw is not None,
            "HNSW index active" if hnsw else "HNSW index not built",
            "usearch · cosine space — ANN search enabled"
            if hnsw else "brute-force cosine or TF-IDF will be used"),
        row(bool(chunks),
            "15 metadata fields per chunk",
            "source · type · section · ACL · freshness — filtering enabled at retrieval"),
    ])

    st.markdown(
        f"<div style='border:1px solid #c8dfd0;border-radius:8px;"
        f"padding:12px 14px;margin-bottom:16px'>"
        f"<div style='font-size:11px;font-weight:700;color:#555;text-transform:uppercase;"
        f"letter-spacing:.05em;margin-bottom:8px'>🗄️ Knowledge Base — built by offline pipeline</div>"
        f"{rows}</div>",
        unsafe_allow_html=True,
    )


def render():
    render_topbar()

    # Load knowledge base on first online pipeline step
    if not st.session_state.get("kb_loaded"):
        with st.spinner("Loading knowledge base — embedding 312 chunks, building HNSW index…"):
            from knowledge_base.loader import load_knowledge_base
            load_knowledge_base()

    # ── KB status card — shows what the offline pipeline actually built ────────
    _render_kb_status()

    render_step_header("💭", "Query Understanding",
        "Before searching anything — understand what was actually asked.")

    render_thinking_card(
        "When someone types 'how does RAG stop making things up' — they don't mean those exact words. "
        "They mean: what mechanism prevents hallucination? A system that matches exact words will fail. "
        "A system that understands intent will find the right answer.",
        pipeline="online"
    )

    # ── Scope note ────────────────────────────────────────────────────────────
    st.markdown(
        "<div style='background:var(--color-background-secondary);border-left:3px solid #4285F4;"
        "border-radius:0 8px 8px 0;padding:8px 12px;font-size:11px;"
        "color:var(--color-text-secondary);margin-bottom:12px'>"
        "📌 <strong>Scope:</strong> This system answers questions about "
        "<strong>RAG pipelines, LLMs, embeddings, vector search, and AI evaluation</strong> only. "
        "Out-of-scope or adversarial queries are blocked before retrieval."
        "</div>",
        unsafe_allow_html=True,
    )

    query = st.session_state.get("query")
    pending_error = st.session_state.pop("query_error", None)
    pending_detail = st.session_state.pop("query_error_detail", None)
    pending_expander = st.session_state.pop("query_error_expander", None)

    # ── Show any pending error from previous submission ───────────────────────
    if pending_error:
        st.error(pending_error)
        if pending_detail:
            st.markdown(pending_detail, unsafe_allow_html=True)
        if pending_expander:
            with st.expander("⚙️ How enterprise RAG defends against this", expanded=False):
                st.markdown(pending_expander)
        st.markdown("")

    # ── Query picker (shown when no valid query yet) ──────────────────────────
    if not query:
        st.markdown("**Select a recommended query or type your own:**")

        rec = st.selectbox(
            "Recommended queries",
            options=[""] + RECOMMENDED_QUERIES,
            format_func=lambda x: x if x else "— select a recommended query —",
            key="rec_query_select",
        )
        if rec:
            st.session_state.query = rec
            st.rerun()

        with st.form("custom_query_form", clear_on_submit=True):
            custom = st.text_input(
                "Or type your own:",
                placeholder="e.g. How does hybrid search work?",
            )
            submitted = st.form_submit_button("Submit query →", type="primary")
            if submitted:
                if custom.strip():
                    st.session_state.query = custom.strip()
                    st.rerun()
                else:
                    st.warning("Please type a query before submitting.")

        st.info("💡 Tip: questions about RAG, embeddings, chunking, vector search, LLMs, evaluation, or observability work best.")
        return

    # ── Run checks on the submitted query ────────────────────────────────────
    # Out-of-scope
    if not _is_in_scope(query):
        st.session_state.query_error = (
            f"⛔ Out-of-scope query — \"{query}\"\n\n"
            "This system only answers questions about RAG, LLMs, embeddings, vector search, and AI evaluation. "
            "Please select a recommended query or type one about these topics."
        )
        st.session_state.query = None
        st.rerun()

    # Adversarial
    threat = _detect_adversarial(query)
    if threat:
        c = threat["color"]
        st.session_state.query_error = (
            f"{threat['icon']} Adversarial query blocked — {threat['label']}\n\n"
            f"Your query: \"{query}\"\n\n"
            f"{threat['description']} — {threat['what_happens']}\n\n"
            "Please select a recommended query or type a genuine question about RAG."
        )
        st.session_state.query_error_expander = (
            f"**{threat['label']} — defence layers in this pipeline:**\n\n"
            "| Layer | Defence |\n|---|---|\n"
            "| System prompt isolation | `system=` parameter passed separately — user message cannot override it |\n"
            "| Grounding check (Step 13) | Every sentence checked against retrieved chunks — invented content flagged 🔴 |\n"
            "| RAGAS faithfulness (Step 14) | LLM judge independently verifies claims are supported by context |\n"
            "| Query logged | Adversarial patterns visible in observability dashboards |\n\n"
            "**In production:** Llama Guard or OpenAI Moderation API runs in parallel on every query — "
            "0 added latency, blocks before retrieval."
        )
        st.session_state.query = None
        st.rerun()

    # ── Valid query — show with change option ────────────────────────────────
    st.markdown("**Your query:**")
    st.markdown(
        f"<div style='background:var(--color-background-secondary);border-radius:8px;"
        f"padding:10px 14px;font-size:13px;color:var(--color-text-primary);margin-bottom:8px'>"
        f"{query}</div>",
        unsafe_allow_html=True,
    )
    if st.button("✏️ Change query", key="change_q"):
        st.session_state.query = None
        st.rerun()

    st.markdown("---")
    st.markdown("**Three transformation strategies:**")

    # Cache keyed by query — invalidate when query changes
    results = get_result("query_understanding") or {}
    safe_query = _sanitize(query)
    if results.get("query") != query:
        results = {
            "query":     query,
            "raw":       query,
            "expansion": _expand_query(safe_query),
            "hyde":      None,
        }
        store_result("query_understanding", results)
        st.session_state["retrieval_query"] = None  # set to HyDE text once generated

    # ── HyDE auto-generation (runs eagerly — not on tab visit) ───────────────
    if not results.get("hyde"):
        if has_llm_key():
            with st.spinner("Generating HyDE hypothetical answer via LLM…"):
                try:
                    hyde_text = _quick_llm_call(
                        f"Generate a short hypothetical answer (2-3 sentences) that would appear "
                        f"in a technical document answering this question. Write it as declarative "
                        f"fact from an authoritative source, not as a direct reply to the user.\n\n"
                        f"Question: {safe_query}\n\nHypothetical answer:"
                    )
                    results["hyde"] = hyde_text
                    store_result("query_understanding", results)
                    st.session_state["retrieval_query"] = hyde_text
                    st.rerun()
                except Exception as e:
                    st.error(
                        f"HyDE generation failed — your API key may be invalid or the model "
                        f"unreachable.\n\n**Error:** {str(e)[:300]}"
                    )
        else:
            st.info(
                "🔑 **Add an LLM key to continue.**\n\n"
                "HyDE requires one LLM call to generate a hypothetical answer that gets embedded for retrieval. "
                "Add your API key (Gemini / Claude / OpenAI) in the **sidebar**, then re-submit your query."
            )

    tabs = st.tabs([
        "1. Raw   (educational)",
        "2. Query Expansion   (educational)",
        "3. HyDE  ✅ active",
    ])

    def _query_box(text: str) -> None:
        st.markdown(
            f"<div style='background:var(--color-background-secondary);border-radius:8px;"
            f"padding:10px 14px;font-size:12px;color:var(--color-text-secondary);"
            f"font-style:italic;line-height:1.6;margin-bottom:12px'>{text}</div>",
            unsafe_allow_html=True,
        )

    # ── Tab 1: Raw (educational) ───────────────────────────────────────────────
    with tabs[0]:
        strategy = QUERY_COMPARISON["raw"]
        st.caption("Shown for comparison only. HyDE is the strategy actually used for retrieval.")
        st.markdown(f"*{strategy['description']}*")
        st.markdown("**What would be sent to retrieval (unchanged):**")
        _query_box(results["raw"])
        col1, col2 = st.columns(2)
        with col1:
            for pro in strategy["pros"]: st.markdown(f"✅ {pro}")
        with col2:
            for con in strategy["cons"]: st.markdown(f"⚠️ {con}")

    # ── Tab 2: Expansion (educational) ────────────────────────────────────────
    with tabs[1]:
        strategy = QUERY_COMPARISON["expansion"]
        st.caption("Shown for comparison only. HyDE is the strategy actually used for retrieval.")
        st.markdown(f"*{strategy['description']}*")
        st.markdown("**What would be sent to retrieval (expanded with synonyms):**")
        _query_box(results["expansion"])
        col1, col2 = st.columns(2)
        with col1:
            for pro in strategy["pros"]: st.markdown(f"✅ {pro}")
        with col2:
            for con in strategy["cons"]: st.markdown(f"⚠️ {con}")

    # ── Tab 3: HyDE ✅ active ──────────────────────────────────────────────────
    with tabs[2]:
        strategy = QUERY_COMPARISON["hyde"]
        st.markdown(f"*{strategy['description']}*")
        st.caption("Step 1: LLM generates a hypothetical answer to your question")
        st.caption("Step 2: That text is embedded — retrieval finds chunks that look like this answer, not the question")

        if results.get("hyde"):
            st.markdown("**Hypothetical answer (this is what gets embedded and sent to retrieval):**")
            _query_box(results["hyde"])
        else:
            st.caption("Generating… add an LLM key in the sidebar if this stays empty.")

        col1, col2 = st.columns(2)
        with col1:
            for pro in strategy["pros"]: st.markdown(f"✅ {pro}")
        with col2:
            for con in strategy["cons"]: st.markdown(f"⚠️ {con}")

    st.markdown("---")
    st.markdown("**Why HyDE works — question space vs answer space:**")
    st.markdown(
        "<div style='font-size:12px;color:var(--color-text-secondary);margin-bottom:10px'>"
        "This is the core insight behind HyDE — and why raw query search often underperforms."
        "</div>",
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([5, 1, 5])
    with col1:
        st.markdown(
            "<div style='border:1px solid #4A90D9;border-radius:8px;padding:14px;height:100%'>"
            "<div style='font-size:11px;font-weight:700;color:#4A90D9;margin-bottom:8px'>❓ QUESTION SPACE</div>"
            "<div style='font-size:12px;color:var(--color-text-secondary);line-height:1.7'>"
            "Where your query lives in embedding space.<br><br>"
            "Queries are typically short, incomplete, and phrased as questions — "
            "<em>\"How does RAG stop hallucination?\"</em><br><br>"
            "The embedding model encodes the <strong>intent</strong> of a question, "
            "which sits in a different region of vector space than the documents that answer it."
            "</div></div>",
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            "<div style='display:flex;align-items:center;justify-content:center;height:100%;font-size:22px'>≠</div>",
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            "<div style='border:1px solid #27AE60;border-radius:8px;padding:14px;height:100%'>"
            "<div style='font-size:11px;font-weight:700;color:#27AE60;margin-bottom:8px'>📄 ANSWER SPACE</div>"
            "<div style='font-size:12px;color:var(--color-text-secondary);line-height:1.7'>"
            "Where your knowledge base lives in embedding space.<br><br>"
            "Source documents are written as statements of fact — "
            "<em>\"RAG grounds generation in retrieved documents to reduce hallucination.\"</em><br><br>"
            "These embeddings cluster with other <strong>declarative content</strong> — "
            "far from question-shaped text in vector space."
            "</div></div>",
            unsafe_allow_html=True,
        )

    st.markdown(
        "<div style='background:var(--color-background-secondary);border-radius:8px;"
        "padding:12px 16px;margin-top:10px;font-size:12px;line-height:1.8'>"
        "<strong>What HyDE does about it:</strong> instead of searching with the question, "
        "it asks the LLM to generate a short hypothetical answer first — "
        "<em>\"RAG prevents hallucination by grounding LLM responses in retrieved source documents...\"</em> — "
        "then searches with <em>that</em>. The hypothetical answer lives in answer space, "
        "right next to the real source chunks. Result: retrieval score jumps from <strong>0.71 → 0.91</strong>."
        "</div>",
        unsafe_allow_html=True,
    )

    st.markdown("---")
    st.markdown(
        "<div style='font-size:14px;font-weight:600;color:var(--color-text-primary);"
        "margin-bottom:6px'>😮‍💨 Designing a query box seems simple, right?</div>"
        "<div style='font-size:12px;color:var(--color-text-secondary);line-height:1.7;"
        "margin-bottom:14px'>"
        "Just a text input and a submit button. In practice, this single screen is where "
        "most of the trust, safety, and UX decisions in a RAG product get made — before a "
        "single vector search even runs. Here's what it actually takes to get this right."
        "</div>",
        unsafe_allow_html=True,
    )

    # ── PM Decision Matrix ────────────────────────────────────────────────────
    rows_data = [
        (
            "Natural language vs guided input?",
            "Will your user know how to query effectively or will they stare at a blank box and fail?",
            "Design query UI with suggested prompts, examples, or starter questions — reduce blank box anxiety.",
            "Perplexity saw 40% higher engagement when they added example queries on empty state.",
            "Curated dropdown of recommended queries shown first, with a free-text field always available alongside — not a blank box.",
            "Empty state includes 4-6 curated example queries per user persona, updated monthly based on query log analysis.",
        ),
        (
            "Query suggestions or free form?",
            "Does narrowing query options improve success rate or frustrate power users?",
            "A/B test suggested prompts vs free form on your specific user type before locking UI pattern.",
            "Notion AI added suggested prompts for new users and free form for returning users — new user success rate improved 30%.",
            "Both offered together, not tiered — recommended queries and free-form text shown side by side on every visit.",
            "Tiered UI — suggested prompts for first 3 sessions, free form unlocked after — success rate tracked per query type.",
        ),
        (
            "Query length limits?",
            "Is your user typing a focused question or pasting entire documents into the query box?",
            "Define a character limit and show a live counter — guide users toward concise queries with inline guidance.",
            "Slack AI users pasted entire email threads as queries — retrieval quality collapsed because the model lost focus on actual intent.",
            "No query length limit or counter on the text input.",
            "Character limit defined based on token budget — live counter shown at 70% of limit, hard stop with explanation at limit.",
        ),
        (
            "Ambiguous query handling?",
            "When a query could mean two different things, do you clarify first or retrieve and let the user refine?",
            "Define ambiguity handling policy before build — clarify for high-stakes domains, retrieve and refine for exploratory ones.",
            "Intercom's AI retrieved on ambiguous queries in a legal context — users got confident wrong answers instead of a clarifying question.",
            "Retrieve first, no clarification step — HyDE runs immediately on any in-scope query.",
            "Ambiguity threshold defined per domain — high-stakes content triggers clarification dialog, exploratory content retrieves and surfaces refine options.",
        ),
        (
            "Deterministic flows vs open query?",
            "Which user journeys are predictable enough to stay as structured flows instead of open-ended queries?",
            "Map existing deterministic flows before replacing them with RAG — only replace what open-ended query genuinely improves.",
            "Salesforce replaced structured case search with AI query — power users who knew exact filters revolted, hybrid approach restored filters alongside AI search.",
            "Fully open query — recommended-query dropdown is a UI shortcut, not a structured deterministic flow.",
            "Existing user flows audited before RAG rollout — structured filters kept for high-frequency predictable queries, AI query reserved for exploratory and complex needs.",
        ),
        (
            "Query expansion guardrails?",
            "Do you know what HyDE or query rewriting is doing to your user's original intent?",
            "Define expansion boundaries with engineering — log original vs expanded query and review weekly for intent drift.",
            "A fintech RAG used aggressive query expansion — compliance team discovered the model was expanding 'refund policy' to include 'legal liability' clauses.",
            "HyDE enabled with no guardrails or logging — the hypothetical answer is shown in the UI for transparency, but nothing checks it against the original intent.",
            "Query expansion logged in full — original vs expanded query reviewed weekly by PM, hard boundaries defined for sensitive content domains.",
        ),
        (
            "Query drift over time?",
            "Are the queries your users ask in month 6 the same as month 1, and is your pipeline still retrieving well for them?",
            "Set a monthly query log review cadence — track top 20 queries, flag any where retrieval quality has dropped.",
            "Notion AI saw silent quality degradation 4 months post launch — query patterns had shifted but chunking strategy was still optimized for short lookups.",
            "No query monitoring or drift detection — this is a single-session demo, not a logged production system.",
            "Monthly query log analysis owned by PM — top queries scored for retrieval quality, chunking and indexing strategy reviewed quarterly.",
        ),
        (
            "Retrieval progress and trust signals?",
            "Does your user know retrieval is happening or does silence feel like failure?",
            "Design loading state, source preview, and confidence signal before engineering builds the response layer.",
            "Glean showed a blank loading spinner during retrieval — 60% of users thought the product had crashed during the 3 second wait.",
            "Basic spinners with descriptive text ('Generating HyDE hypothetical answer…') — no source preview or confidence signal shown yet at this step.",
            "Retrieval progress indicator, source document preview during load, confidence signal on answer — UX tested with real users before launch.",
        ),
        (
            "Failure state experience?",
            "What does your user see when retrieval finds nothing relevant or confidence is too low?",
            "Design no-results and low-confidence states explicitly — never let the model hallucinate to fill a gap.",
            "ChatGPT Enterprise early users reported confidently wrong answers on out-of-scope queries — no fallback state meant the model filled silence with hallucination.",
            "Explicit failure states do exist here — out-of-scope and adversarial queries are blocked with a specific error message before retrieval runs. No separate low-confidence state once retrieval succeeds.",
            "Explicit failure states defined — no results shows curated fallback options, low confidence triggers 'I'm not sure, here's what I found' pattern with source links.",
        ),
        (
            "UX guardrails against prompt injection?",
            "Beyond engineering defenses, does your UI itself reduce the surface area for injection attacks?",
            "Define UI-level guardrails — scope labels, input placeholders, query boundaries shown visibly to users.",
            "A customer service RAG had no visible scope boundary — users discovered they could manipulate tone and persona through the query box, went viral on social media.",
            "Visible scope label shown above the query box ('This system answers questions about RAG pipelines...'); regex-based detection blocks prompt injection, jailbreak, and data-extraction patterns before retrieval runs.",
            "Visible scope label on query box showing what AI can and cannot answer, queries exceeding defined topic scope trigger a soft warning before retrieval runs.",
        ),
    ]

    render_pm_matrix("Query Understanding", rows_data)

    render_what_we_built("HyDE is the active retrieval strategy: the LLM generates a short hypothetical answer to your question, which is then embedded and used for vector search in Steps 8 and 9. Raw and Expansion tabs are shown for educational comparison only. Requires one LLM call — add a key in the sidebar to proceed.")
    render_enterprise_note(
        "Query understanding at enterprise scale is a dedicated microservice. At Glean, every query passes "
        "through query classification, entity extraction, intent detection, and expansion before retrieval. "
        "Google's enterprise search uses query rewriting models trained on search logs — they learn from "
        "millions of queries which rewrites actually improved results. HyDE was introduced by Gao et al. (2022) "
        "and is now widely deployed in high-precision RAG. Amazon Bedrock's Knowledge Base supports HyDE natively. "
        "LlamaIndex implements it as HyDEQueryTransform. The cost is one extra LLM call per query — "
        "at enterprise scale this is a deliberate budget decision."
    )
    render_risk_table(RISKS)
    if results.get("hyde"):
            render_nav(next_label="Next: Query Embedding →", pipeline="online", show_jump=True)
    else:
        st.info(
            "🔑 **Add an LLM key to continue.**\n\n"
            "HyDE requires one LLM call to generate a hypothetical answer that gets embedded for retrieval. "
            "Add your API key (Gemini / Claude / OpenAI) in the **sidebar**, then re-submit your query."
        )
        render_nav(next_label="Next: Query Embedding →", pipeline="online", show_jump=True, next_disabled=True)
