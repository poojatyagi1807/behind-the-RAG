"""Step 0 — Landing: Perplexity intro + two pipeline choice."""
import streamlit as st
from state import go_to
from ui import render_pm_matrix


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
        render_pm_matrix("Do You Actually Need RAG?", [
            ("Retrieval vs Grounding", "Is the model failing because it lacks information, or guidance?", "Try prompt engineering or few-shot examples first — if that fixes it, you don't need RAG.", "A support bot gave wrong refund policy answers. Team built a full RAG pipeline. Root cause was a vague system prompt — a two-line fix would have worked.", "Prompt engineering is near-zero cost. Exhaust this before building retrieval infrastructure.", "Prompt engineering evaluated and documented before RAG scoped. RAG only approved if prompt-only approach fails on >15% of test cases."),
            ("Build vs Buy", "Do you need control over every layer, or speed to market?", "Evaluate managed RAG APIs (Amazon Bedrock Knowledge Bases, Azure AI Search, Google Vertex AI Search) before committing to a custom build.", "A fintech built a custom RAG pipeline over 4 months. Amazon Bedrock Knowledge Bases would have covered 90% of their needs in 2 weeks. Custom build was justified only by a compliance requirement that emerged in month 3.", "Custom build = high engineering cost and ongoing maintenance. Managed = predictable subscription but less control.", "Build vs buy decision documented with explicit justification. Custom build requires sign-off from engineering lead and PM on why managed solutions are insufficient."),
            ("RAG vs Fine-tuning", "Is your knowledge dynamic or does it change less than once a month?", "Use RAG for dynamic, frequently updated knowledge. Use fine-tuning to improve model behaviour, tone, or reasoning style — not to inject facts.", "A legal team fine-tuned a model on case law to make it 'know more law.' Model hallucinated confidently on cases outside training data. RAG with retrieval would have surfaced actual case text with citations.", "RAG = ongoing retrieval cost per query. Fine-tuning = one-time training cost but knowledge becomes stale.", "Use case classification required before model approach selected — dynamic knowledge defaults to RAG, behaviour/style changes default to fine-tuning."),
            ("RAG vs Long Context", "How large is your knowledge base and how often does it change?", "If your KB fits in a context window and changes rarely, long context may be simpler. If it's large, dynamic, or needs citations, build RAG.", "A team stuffed a 200-page policy document into every query context. At $0.01/1k tokens and 10k queries/day, monthly cost was $20k. RAG retrieval of 5 relevant chunks cost $200/month.", "Long context = higher token cost per query, zero infrastructure. RAG = lower per-query cost at scale, higher build cost.", "Cost modelling required before architecture decision — project query volume × token cost for both approaches before committing."),
            ("Precision vs Simplicity", "Will approximate or occasionally wrong answers break user trust in your domain?", "For internal tools and low-stakes queries, basic semantic search may be sufficient. For customer-facing or compliance use cases, invest in the full pipeline.", "Notion AI shipped a basic semantic search before adding re-ranking and hybrid retrieval. User satisfaction scores were 61%. After adding re-ranking, scores rose to 84%. The incremental complexity was worth it for their use case.", "Full RAG pipeline = highest build and maintenance cost. Basic semantic search = faster to ship, lower quality ceiling.", "Domain risk classification documented before pipeline scope decided — high-stakes domains (legal, medical, financial) default to full pipeline."),
            ("Own Infra vs Managed", "Do you have bandwidth to maintain vector database infrastructure at scale?", "Start with managed vector DB (Pinecone, Weaviate Cloud, Qdrant Cloud). Move to self-hosted only when cost or compliance requires it.", "A startup self-hosted Weaviate to save $200/month. Spent 3 engineer-weeks on cluster maintenance in the first quarter — opportunity cost far exceeded the savings.", "Self-hosted = engineering overhead and on-call burden. Managed = predictable subscription, faster to scale.", "Infrastructure decision reviewed at 6-month intervals — self-hosting only approved when managed cost exceeds $5k/month or compliance blocks cloud storage."),
        ])

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
