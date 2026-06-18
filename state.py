"""
State manager — Behind The RAG
Manages two independent pipeline flows:
  offline: steps 1-6
  online:  steps 7-15
Plus shared state (query, results, API keys).
"""

import streamlit as st

# ── Step definitions ──────────────────────────────────────────────────────────

OFFLINE_STEPS = [
    "landing",
    "s00b_offline_intro",
    "s01_ingestion",
    "s03_chunking",
    "s05_metadata",
    "s04_embedding",
    "s06_indexing",
    "s06_summary",
]

ONLINE_STEPS = [
    "landing",
    "s07_query_understanding",
    "s08_query_embedding",
    "s09_vector_search",
    "s10_reranking",
    "s11b_context_ordering",
    "s11a_context_assembly",
    "s12_generation",
    "s13_grounding",
    "s14_judge",
    "s15_observability",
]

ALL_STEPS = list(dict.fromkeys(OFFLINE_STEPS + ONLINE_STEPS))

# ── Init ──────────────────────────────────────────────────────────────────────

def init_state():
    defaults = {
        "step": "landing",
        "active_pipeline": None,       # "offline" or "online"
        "query": None,
        "gemini_key": None,
        "anthropic_key": None,
        "openai_key": None,
        "cohere_key": None,
        "llm_provider": "gemini",      # "gemini" | "claude" | "openai"
        "llm_client": None,
        "results": {},
        "errors": {},
        "kb_loaded": False,
        "kb_chunks": [],
        "kb_tfidf": None,
        "kb_hnsw": None,                # usearch HNSW index — built after embeddings are ready
        "kb_embeddings_loaded": False,   # True once all chunks have neural embeddings
        "kb_embedding_provider": "",     # "local" (fastembed) or "" if unavailable
        "offline_complete": False,
        # Dropdown selections
        "selected_loader": "simple_text",
        "selected_cleaning": "standard",
        "selected_chunking": "fixed_token",
        "selected_embedding": "tfidf",
        "selected_metadata": "standard",
        "selected_index": "hnsw",
        "selected_query_strategy": "hyde",
        "selected_reranking": "precalculated",
        "dedup_threshold": 0.92,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

    # Reset any stale model overrides that point to deprecated model names
    DEPRECATED_MODELS = {
        "claude-3-haiku-20240307", "claude-3-5-haiku-20241022",
        "claude-3-5-sonnet-20241022", "claude-3-opus-20240229",
        "claude-3-sonnet-20240229", "gemini-1.5-flash", "gemini-1.5-pro",
        "gemini-1.5-flash-8b", "gemini-2.0-flash", "gemini-2.0-flash-lite",
    }
    for provider in ("gemini", "claude", "openai"):
        override_key = f"model_override_{provider}"
        if st.session_state.get(override_key) in DEPRECATED_MODELS:
            st.session_state[override_key] = LLM_MODELS[provider]

# ── Navigation ────────────────────────────────────────────────────────────────

def go_to(step: str):
    st.session_state.step = step
    st.rerun()

def go_next_offline():
    current = st.session_state.step
    if current in OFFLINE_STEPS:
        idx = OFFLINE_STEPS.index(current)
        if idx < len(OFFLINE_STEPS) - 1:
            st.session_state.step = OFFLINE_STEPS[idx + 1]
            st.rerun()

def go_next_online():
    current = st.session_state.step
    if current in ONLINE_STEPS:
        idx = ONLINE_STEPS.index(current)
        if idx < len(ONLINE_STEPS) - 1:
            st.session_state.step = ONLINE_STEPS[idx + 1]
            st.rerun()

def go_back():
    current = st.session_state.step
    pipeline = st.session_state.active_pipeline
    steps = OFFLINE_STEPS if pipeline == "offline" else ONLINE_STEPS
    if current in steps:
        idx = steps.index(current)
        if idx > 1:
            st.session_state.step = steps[idx - 1]
            st.rerun()
        else:
            go_to("landing")

def jump_to_online():
    st.session_state.active_pipeline = "online"
    st.session_state.step = "s07_query_understanding"
    st.rerun()

def jump_to_offline():
    st.session_state.active_pipeline = "offline"
    st.session_state.step = "s01_ingestion"
    st.rerun()

# ── Progress ──────────────────────────────────────────────────────────────────

def progress_pct():
    current = st.session_state.step
    pipeline = st.session_state.active_pipeline
    if pipeline == "offline":
        steps = OFFLINE_STEPS
    elif pipeline == "online":
        steps = ONLINE_STEPS
    else:
        return 0
    if current not in steps:
        return 0
    idx = steps.index(current)
    return idx / (len(steps) - 1)

def current_step_num():
    current = st.session_state.step
    pipeline = st.session_state.active_pipeline
    steps = OFFLINE_STEPS if pipeline == "offline" else ONLINE_STEPS
    if current in steps:
        return steps.index(current)
    return 0

def total_steps():
    pipeline = st.session_state.active_pipeline
    return len(OFFLINE_STEPS) if pipeline == "offline" else len(ONLINE_STEPS)

# ── Results ───────────────────────────────────────────────────────────────────

def store_result(step: str, result):
    st.session_state.results[step] = result

def get_result(step: str):
    return st.session_state.results.get(step)

def store_error(step: str, error: str):
    st.session_state.errors[step] = error

# ── API keys ──────────────────────────────────────────────────────────────────

LLM_MODELS = {
    "gemini": "gemini-2.5-flash",
    "claude": "claude-sonnet-4-6",
    "openai": "gpt-4o-mini",
}

def get_llm_client():
    """Returns (client, provider) tuple. Client is provider-specific."""
    provider = st.session_state.get("llm_provider", "gemini")

    if provider == "gemini":
        key = st.session_state.gemini_key or st.secrets.get("GEMINI_API_KEY", None)
        if not key:
            return None, provider
        try:
            import google.generativeai as genai
            genai.configure(api_key=key)
            model = st.session_state.get(f"model_override_{provider}", LLM_MODELS["gemini"])
            client = genai.GenerativeModel(model)
            return client, provider
        except Exception:
            return None, provider

    elif provider == "claude":
        key = st.session_state.anthropic_key or st.secrets.get("ANTHROPIC_API_KEY", None)
        if not key:
            return None, provider
        try:
            import anthropic
            return anthropic.Anthropic(api_key=key), provider
        except Exception:
            return None, provider

    elif provider == "openai":
        key = st.session_state.openai_key or st.secrets.get("OPENAI_API_KEY", None)
        if not key:
            return None, provider
        try:
            import openai
            return openai.OpenAI(api_key=key), provider
        except Exception:
            return None, provider

    return None, provider


def has_llm_key():
    """Returns True if the currently selected provider has a key."""
    provider = st.session_state.get("llm_provider", "gemini")
    if provider == "gemini":
        return bool(st.session_state.gemini_key or st.secrets.get("GEMINI_API_KEY", None))
    elif provider == "claude":
        return bool(st.session_state.anthropic_key or st.secrets.get("ANTHROPIC_API_KEY", None))
    elif provider == "openai":
        return bool(st.session_state.openai_key or st.secrets.get("OPENAI_API_KEY", None))
    return False


def has_gemini_key():
    return bool(
        st.session_state.gemini_key or
        st.secrets.get("GEMINI_API_KEY", None)
    )

def has_cohere_key():
    return bool(st.session_state.cohere_key)


# ── Embedding utility (local, no API key required) ───────────────────────────

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"  # 384 dims, ONNX, no torch needed


def embed_text(text: str) -> tuple:
    """Embed text locally using fastembed (ONNX backend, no torch required).
    No API key needed. Model downloads ~25MB on first use, then cached.
    Returns (vector: list[float], 'local') or (None, None) if package unavailable."""
    try:
        from fastembed import TextEmbedding
        # Cache the model in session state — only loaded once per session
        if "fe_model" not in st.session_state:
            st.session_state["fe_model"] = TextEmbedding(EMBEDDING_MODEL)
        model = st.session_state["fe_model"]
        vector = list(model.embed([text]))[0].tolist()
        return vector, "local"
    except Exception:
        return None, None

def reset_session():
    keys_to_clear = [
        "step", "active_pipeline", "query", "llm_client",
        "results", "errors", "offline_complete",
        "selected_loader", "selected_cleaning", "selected_chunking",
        "selected_embedding", "selected_metadata", "selected_index",
        "selected_query_strategy", "selected_reranking", "dedup_threshold",
    ]
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()
