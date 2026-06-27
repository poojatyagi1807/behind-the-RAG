"""Step 0 — Landing: Perplexity intro + two pipeline choice."""
import streamlit as st
from state import go_to


def render():
    st.markdown("""
<div style="text-align:center;padding:48px 0 32px">
  <div style="font-size:34px;font-weight:500;color:var(--color-text-primary);
  letter-spacing:-0.02em;margin-bottom:8px">🔍 Behind The RAG</div>
  <div style="font-size:15px;color:var(--color-text-tertiary)">
    A visual walkthrough of how enterprise RAG systems actually work.
  </div>
  <div style="font-size:12px;color:var(--color-text-tertiary);margin-top:8px">
    ⏱ ~45 minutes &nbsp;·&nbsp; 15 steps &nbsp;·&nbsp; 2 pipelines
  </div>
</div>
""", unsafe_allow_html=True)

    col = st.columns([1, 2, 1])[1]
    with col:

        # ── What is RAG? ──────────────────────────────────────────────────────
        st.markdown("""
<div style="background:var(--color-background-secondary);border-radius:12px;
padding:22px 24px;margin-bottom:10px;
box-shadow:0 1px 4px rgba(0,0,0,0.06)">
  <div style="font-size:13px;font-weight:600;color:var(--color-text-primary);
  margin-bottom:10px">What is RAG?</div>
  <div style="font-size:13px;color:var(--color-text-secondary);line-height:1.75">
    You have used Perplexity. You type a question, it searches the web, finds
    the most relevant pages, and gives you an answer with numbered citations
    showing exactly where each fact came from.<br><br>
    That experience is RAG — Retrieval Augmented Generation. The AI does not
    answer from memory. It finds the right information first, then generates
    an answer grounded in what it found.<br><br>
    This is how every serious enterprise AI assistant works today: customer
    support bots, internal knowledge tools, legal document search, financial
    research assistants. All RAG underneath.
  </div>
</div>
""", unsafe_allow_html=True)

        # ── Why two pipelines? ────────────────────────────────────────────────
        st.markdown("""
<div style="background:var(--color-background-secondary);border-radius:12px;
padding:22px 24px;margin-bottom:10px;
box-shadow:0 1px 4px rgba(0,0,0,0.06)">
  <div style="font-size:13px;font-weight:600;color:var(--color-text-primary);
  margin-bottom:10px">Why two pipelines?</div>
  <div style="font-size:12px;color:var(--color-text-secondary);line-height:1.75;
  margin-bottom:14px">
    RAG does not just happen the moment you ask a question. It starts much earlier.
  </div>
  <div style="display:flex;gap:10px">
    <div style="flex:1;background:var(--color-background-primary);border-radius:8px;
    padding:14px 16px;border-left:3px solid #0F6E56">
      <div style="font-size:11px;font-weight:700;color:#0F6E56;letter-spacing:.04em;
      text-transform:uppercase;margin-bottom:6px">📦 Offline pipeline</div>
      <div style="font-size:11px;color:var(--color-text-secondary);line-height:1.65">
        Runs once, updates when docs change.<br>
        Documents get loaded, cleaned, chunked,<br>
        embedded, tagged, indexed.<br>
        <span style="color:var(--color-text-tertiary);font-style:italic">
        Like Perplexity indexing the web — invisible to users.</span>
      </div>
    </div>
    <div style="flex:1;background:var(--color-background-primary);border-radius:8px;
    padding:14px 16px;border-left:3px solid #185FA5">
      <div style="font-size:11px;font-weight:700;color:#185FA5;letter-spacing:.04em;
      text-transform:uppercase;margin-bottom:6px">🔍 Online pipeline</div>
      <div style="font-size:11px;color:var(--color-text-secondary);line-height:1.65">
        Runs every query, in milliseconds.<br>
        Question gets embedded, matched,<br>
        re-ranked, assembled, answered.<br>
        <span style="color:var(--color-text-tertiary);font-style:italic">
        What you see when Perplexity answers you.</span>
      </div>
    </div>
  </div>
  <div style="font-size:11px;color:var(--color-text-tertiary);font-style:italic;
  line-height:1.6;margin-top:12px">
    The offline pipeline is where most enterprise RAG systems silently fail.
    Bad chunking, wrong embedding model, missing metadata bake into the index
    and degrade every query that follows. This app makes both pipelines visible.
  </div>
</div>
""", unsafe_allow_html=True)

        # ── Decision matrix (opened outside narrow col for full width) ─────────

    with st.expander("🤔 Wait — do you actually need RAG? (decision matrix)"):
      wide = st.columns([1, 6, 1])[1]
      with wide:
        st.markdown("""
<style>
.dm { width:100%;box-sizing:border-box;border-radius:8px;overflow:hidden;font-size:11px;font-family:sans-serif }
.dm-row { display:grid;grid-template-columns:15% 13% 17% 29% 26%;width:100%;box-sizing:border-box }
.dm-row > div { padding:9px 12px;box-sizing:border-box;line-height:1.55 }
</style>
<div class="dm">
  <div class="dm-row" style="background:var(--color-background-primary);border-bottom:1.5px solid var(--color-border-tertiary)">
    <div style="font-weight:700;color:var(--color-text-secondary)">Tradeoff</div>
    <div style="font-weight:700;color:var(--color-text-secondary)">Option A</div>
    <div style="font-weight:700;color:var(--color-text-secondary)">Option B</div>
    <div style="font-weight:700;color:var(--color-text-secondary)">Ask Yourself</div>
    <div style="font-weight:700;color:var(--color-text-secondary)">Cost Consideration</div>
  </div>
  <div class="dm-row" style="background:var(--color-background-secondary)">
    <div style="font-weight:600;color:var(--color-text-primary)">Retrieval vs Grounding</div>
    <div style="color:var(--color-text-secondary)">Build RAG</div>
    <div style="color:var(--color-text-secondary)">Prompt engineering or few-shot</div>
    <div style="color:var(--color-text-tertiary);font-style:italic">Is the model failing because it lacks information, or guidance?</div>
    <div style="color:var(--color-text-secondary)">Prompt engineering is near-zero cost — exhaust this first</div>
  </div>
  <div class="dm-row" style="background:var(--color-background-primary)">
    <div style="font-weight:600;color:var(--color-text-primary)">Build vs Buy</div>
    <div style="color:var(--color-text-secondary)">Build custom RAG</div>
    <div style="color:var(--color-text-secondary)">LlamaIndex, LangChain, managed APIs</div>
    <div style="color:var(--color-text-tertiary);font-style:italic">Do you need control over every layer, or speed to market?</div>
    <div style="color:var(--color-text-secondary)">Custom = high engineering cost · Managed = ongoing fees</div>
  </div>
  <div class="dm-row" style="background:var(--color-background-secondary)">
    <div style="font-weight:600;color:var(--color-text-primary)">RAG vs Fine-tuning</div>
    <div style="color:var(--color-text-secondary)">Retrieve at query time</div>
    <div style="color:var(--color-text-secondary)">Bake knowledge into model weights</div>
    <div style="color:var(--color-text-tertiary);font-style:italic">Is your knowledge dynamic or static?</div>
    <div style="color:var(--color-text-secondary)">RAG = ongoing retrieval cost · Fine-tune = one-time training</div>
  </div>
  <div class="dm-row" style="background:var(--color-background-primary)">
    <div style="font-weight:600;color:var(--color-text-primary)">RAG vs Long Context</div>
    <div style="color:var(--color-text-secondary)">Build retrieval pipeline</div>
    <div style="color:var(--color-text-secondary)">Stuff everything into context window</div>
    <div style="color:var(--color-text-tertiary);font-style:italic">How large is your KB and how often does it change?</div>
    <div style="color:var(--color-text-secondary)">Long context = higher token cost per query, zero infra</div>
  </div>
  <div class="dm-row" style="background:var(--color-background-secondary)">
    <div style="font-weight:600;color:var(--color-text-primary)">Precision vs Simplicity</div>
    <div style="color:var(--color-text-secondary)">Full RAG pipeline</div>
    <div style="color:var(--color-text-secondary)">Keyword or basic semantic search</div>
    <div style="color:var(--color-text-tertiary);font-style:italic">Will approximate answers break user trust?</div>
    <div style="color:var(--color-text-secondary)">Full RAG = highest build and maintenance cost</div>
  </div>
  <div class="dm-row" style="background:var(--color-background-primary)">
    <div style="font-weight:600;color:var(--color-text-primary)">Own Infra vs Managed</div>
    <div style="color:var(--color-text-secondary)">Self-host vector DB</div>
    <div style="color:var(--color-text-secondary)">Pinecone, Weaviate cloud</div>
    <div style="color:var(--color-text-tertiary);font-style:italic">Do you have bandwidth to maintain infra at scale?</div>
    <div style="color:var(--color-text-secondary)">Self-host = engineering overhead · Managed = predictable subscription</div>
  </div>
</div>
""", unsafe_allow_html=True)

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ── Pipeline choice cards ─────────────────────────────────────────────
    with st.columns([1, 2, 1])[1]:
        c1, c2 = st.columns(2)

        with c1:
            st.markdown("""
<div style="background:#f0faf5;border-radius:12px;padding:18px;text-align:center;
box-shadow:0 1px 4px rgba(0,0,0,0.06)">
  <div style="font-size:24px;margin-bottom:6px">📦</div>
  <div style="font-size:13px;font-weight:600;color:#085041;margin-bottom:4px">
    Offline pipeline
  </div>
  <div style="font-size:10px;color:#0F6E56;line-height:1.5">
    How the knowledge base gets built<br>Steps 1 — 6
  </div>
</div>
""", unsafe_allow_html=True)
            st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
            if st.button("📦 Start offline pipeline", type="primary",
                         use_container_width=True, key="start_offline"):
                st.session_state.active_pipeline = "offline"
                go_to("s00b_offline_intro")

        with c2:
            st.markdown("""
<div style="background:#f0f5fc;border-radius:12px;padding:18px;text-align:center;
box-shadow:0 1px 4px rgba(0,0,0,0.06)">
  <div style="font-size:24px;margin-bottom:6px">🔍</div>
  <div style="font-size:13px;font-weight:600;color:#0C447C;margin-bottom:4px">
    Online pipeline
  </div>
  <div style="font-size:10px;color:#185FA5;line-height:1.5">
    Ask a question, watch retrieval<br>Steps 7 — 15
  </div>
  <div style="font-size:10px;color:#a05c00;background:#fef3cd;border-radius:4px;
  padding:3px 7px;margin-top:8px;line-height:1.5">
    🔑 Requires an LLM API key<br>(Gemini · OpenAI · Anthropic · Cohere)
  </div>
</div>
""", unsafe_allow_html=True)
            st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
            if st.button("🔍 Jump to online pipeline", type="primary", use_container_width=True,
                         key="start_online"):
                st.session_state.active_pipeline = "online"
                go_to("s07_query_understanding")

    st.markdown("<div style='height:48px'></div>", unsafe_allow_html=True)
    st.markdown("""
<div style="text-align:center;font-size:10px;color:var(--color-text-tertiary);
border-top:0.5px solid var(--color-border-tertiary);padding-top:12px">
  ⚠️ Learning demo, not a production system. Goal is to show each layer — not to give flawless answers.
</div>
""", unsafe_allow_html=True)
