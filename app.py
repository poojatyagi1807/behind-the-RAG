"""
Behind The RAG
──────────────
A visual walkthrough of how enterprise RAG systems work.
Every step. Every decision. Enterprise detail at every layer.

Run: streamlit run app.py
"""

import streamlit as st

st.set_page_config(
    page_title="Behind The RAG",
    page_icon="🔍",
    layout="centered",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
/* Hide Streamlit deploy/share toolbar only — not the sidebar toggle */
[data-testid="stToolbar"] { display: none; }
[data-testid="stDecoration"] { display: none; }
/* Always keep sidebar collapse/expand button accessible */
[data-testid="stSidebarCollapsedControl"] { display: flex !important; visibility: visible !important; }
.block-container {padding-top: 1rem; max-width: 820px;}
</style>
""", unsafe_allow_html=True)

from state import init_state
init_state()

# ── Sidebar — API keys + settings ────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🔍 Behind The RAG")
    st.markdown("---")

    st.markdown("**LLM Provider**")
    provider = st.radio(
        "Choose your LLM",
        options=["gemini", "claude", "openai"],
        format_func=lambda p: {"gemini": "🟢 Gemini (free)", "claude": "🟠 Claude", "openai": "🔵 OpenAI"}[p],
        horizontal=False,
        key="llm_provider",
        label_visibility="collapsed",
    )

    # Model catalogue — sourced from official provider docs (June 2026)
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
            ("gpt-4o-mini",   "GPT-4o Mini · fast · affordable · recommended"),
            ("gpt-4o",        "GPT-4o · powerful"),
            ("gpt-5.4-mini",  "GPT-5.4 Mini · latest · coding + agents"),
            ("gpt-5.4",       "GPT-5.4 · latest frontier · highest cost"),
        ],
    }
    DEFAULT_MODELS = {
        "gemini": "gemini-2.5-flash",
        "claude": "claude-sonnet-4-6",
        "openai": "gpt-4o-mini",
    }

    st.markdown("**API Keys**")

    if provider == "gemini":
        gemini_key = st.text_input(
            "Gemini API key", type="password",
            value=st.session_state.gemini_key or "",
            placeholder="AIza...",
            help="Free key from aistudio.google.com",
        )
        if gemini_key and gemini_key != st.session_state.gemini_key:
            st.session_state.gemini_key = gemini_key
            st.session_state.llm_client = None
            st.rerun()

    elif provider == "claude":
        anthropic_key = st.text_input(
            "Anthropic API key", type="password",
            value=st.session_state.anthropic_key or "",
            placeholder="sk-ant-...",
            help="Get key from console.anthropic.com",
        )
        if anthropic_key and anthropic_key != st.session_state.anthropic_key:
            st.session_state.anthropic_key = anthropic_key
            st.session_state.llm_client = None
            st.rerun()

    elif provider == "openai":
        openai_key = st.text_input(
            "OpenAI API key", type="password",
            value=st.session_state.openai_key or "",
            placeholder="sk-...",
            help="Get key from platform.openai.com",
        )
        if openai_key and openai_key != st.session_state.openai_key:
            st.session_state.openai_key = openai_key
            st.session_state.llm_client = None
            st.rerun()

    # Model picker — dropdown of valid models + optional custom entry
    catalogue = MODEL_CATALOGUE[provider]
    model_ids   = [m[0] for m in catalogue]
    model_labels = [m[1] for m in catalogue]

    current_override = st.session_state.get(f"model_override_{provider}", DEFAULT_MODELS[provider])
    # If the stored override is in the catalogue, pre-select it; else fall back to default
    if current_override in model_ids:
        current_idx = model_ids.index(current_override)
    else:
        current_idx = model_ids.index(DEFAULT_MODELS[provider]) if DEFAULT_MODELS[provider] in model_ids else 0

    st.markdown("**Model**")
    selected_label = st.selectbox(
        "Choose model",
        options=model_labels,
        index=current_idx,
        label_visibility="collapsed",
        help="All models shown are currently available for this provider.",
    )
    selected_model = model_ids[model_labels.index(selected_label)]

    if selected_model != current_override:
        st.session_state[f"model_override_{provider}"] = selected_model
        if "results" in st.session_state:
            st.session_state.results.pop("generation", None)
            st.session_state.results.pop("judge", None)
        st.rerun()

    cohere_key = st.text_input(
        "Cohere API key",
        type="password",
        value=st.session_state.cohere_key or "",
        placeholder="Optional — enables live re-ranking",
        help="Free key from cohere.com — enables live re-ranking on custom queries",
    )
    if cohere_key and cohere_key != st.session_state.cohere_key:
        st.session_state.cohere_key = cohere_key
        st.rerun()

    st.markdown("---")
    st.markdown("**Navigation**")

    if st.button("🏠 Start over", use_container_width=True):
        from state import reset_session
        reset_session()

    if st.session_state.active_pipeline == "offline":
        if st.button("🔍 Jump to online pipeline", use_container_width=True):
            st.session_state.active_pipeline = "online"
            st.session_state.step = "s07_query_understanding"
            st.rerun()

    if st.session_state.active_pipeline == "online":
        if st.button("📦 Back to offline pipeline", use_container_width=True):
            st.session_state.active_pipeline = "offline"
            st.session_state.step = "s01_ingestion"
            st.rerun()

    st.markdown("---")
    st.markdown("**About**")
    st.markdown("""
Part of the [Behind The Series](https://github.com/poojatyagi1807).

Also see [Behind The Bot](https://behind-the-bot.streamlit.app) — 
AI customer support pipeline visualizer.
""")

# ── Route to correct step ─────────────────────────────────────────────────────
step = st.session_state.step

if step == "landing":
    from steps.s00_landing import render; render()

# ── Offline pipeline ──────────────────────────────────────────────────────────
elif step == "s00b_offline_intro":
    from steps.s00b_offline_intro import render; render()

elif step == "s01_ingestion":
    from steps.s01_ingestion import render; render()

elif step == "s02_parsing":
    from steps.s02_parsing import render; render()

elif step == "s03_chunking":
    from steps.s03_chunking import render; render()

elif step == "s04_embedding":
    from steps.s04_embedding import render; render()

elif step == "s05_metadata":
    from steps.s05_metadata import render; render()

elif step == "s06_indexing":
    from steps.s06_indexing import render; render()

elif step == "s06_summary":
    from steps.s06_summary import render; render()

# ── Online pipeline ───────────────────────────────────────────────────────────
elif step == "s07_query_understanding":
    from steps.s07_query_understanding import render; render()

elif step == "s08_query_embedding":
    from steps.s08_query_embedding import render; render()

elif step == "s09_vector_search":
    from steps.s09_vector_search import render; render()

elif step == "s10_reranking":
    from steps.s10_reranking import render; render()

elif step == "s11a_context_assembly":
    from steps.s11a_context_assembly import render; render()

elif step == "s11b_context_ordering":
    from steps.s11b_context_ordering import render; render()

elif step == "s12_generation":
    from steps.s12_generation import render; render()

elif step == "s13_grounding":
    from steps.s13_grounding import render; render()

elif step == "s14_judge":
    from steps.s14_judge import render; render()

elif step == "s15_observability":
    from steps.s15_observability import render; render()

else:
    st.error(f"Unknown step: {step}")
    if st.button("Go home"):
        st.session_state.step = "landing"
        st.rerun()
