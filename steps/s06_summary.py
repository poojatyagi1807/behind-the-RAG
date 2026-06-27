"""Step 6 Summary — Offline pipeline architecture."""
import streamlit as st
from ui import render_topbar, render_step_header
from state import go_to, jump_to_online, go_back


def render():
    render_topbar()
    render_step_header("🎉", "Offline Pipeline Complete",
        "Five documents loaded, parsed, chunked, embedded, tagged, and indexed.")

    st.success("✅ Knowledge base built — 312 chunks · 5 documents · 15 metadata fields · HNSW indexed (hnswlib · 384-dim · cosine)")

    st.markdown("**What you just built:**")

    st.components.v1.html("""
<style>
  .pipe { font-family: sans-serif; max-width: 720px; margin: 0 auto; padding: 8px 0; }

  /* source row */
  .sources { display: flex; gap: 8px; justify-content: center; flex-wrap: wrap; margin-bottom: 4px; }
  .src-chip { background: #f0f4ff; border: 1px solid #c5d2f6; border-radius: 20px;
              padding: 4px 12px; font-size: 11px; color: #2d3a8c; font-weight: 500; }

  /* connector arrow */
  .conn { display: flex; flex-direction: column; align-items: center;
          margin: 2px 0; color: #888; font-size: 11px; gap: 1px; }
  .conn .label { font-size: 10px; color: #888; font-style: italic; }
  .arr { font-size: 18px; color: #aaa; line-height: 1; }

  /* step block */
  .step { border-radius: 10px; padding: 14px 18px; margin: 2px 0; border: 1.5px solid; }
  .step-num { font-size: 10px; font-weight: 700; letter-spacing: .06em;
              text-transform: uppercase; opacity: .7; margin-bottom: 3px; }
  .step-title { font-size: 14px; font-weight: 700; margin-bottom: 8px; }

  /* pills row — all pills sit on one line, sharing width equally */
  .step-body { display: flex; gap: 8px; flex-wrap: nowrap; align-items: stretch; }
  .pill { border-radius: 6px; padding: 5px 8px; font-size: 11px; font-weight: 500;
          border: 1px solid; flex: 1 1 0; min-width: 0; position: relative; }
  .pill-title { font-size: 9px; font-weight: 700; letter-spacing: .04em;
                text-transform: uppercase; opacity: .65; display: block; margin-bottom: 2px; }
  .pill-body { font-size: 10.5px; line-height: 1.4; color: #2d2d2d; }

  /* "not built" pill variant */
  .pill-nb { background: #f2f2f0 !important; border-color: #ccc !important; }
  .pill-nb .pill-body { color: #666; }
  .nb-badge { display: inline-block; font-size: 9px; font-weight: 700; color: #a05c00;
              background: #fef3cd; border: 1px solid #f0c060; border-radius: 4px;
              padding: 1px 5px; margin-bottom: 4px; letter-spacing: .02em; }
  /* "built" badge */
  .built-badge { display: inline-block; font-size: 9px; font-weight: 700; color: #1a5e36;
                 background: #d4f0e0; border: 1px solid #6fcf97; border-radius: 4px;
                 padding: 1px 5px; margin-bottom: 4px; letter-spacing: .02em; }
  /* "interactive demo" badge */
  .demo-badge { display: inline-block; font-size: 9px; font-weight: 700; color: #5a3e00;
                background: #fff3b0; border: 1px solid #e0c040; border-radius: 4px;
                padding: 1px 5px; margin-bottom: 4px; letter-spacing: .02em; }

  /* output tag */
  .out { font-size: 10px; font-weight: 600; margin-top: 8px; opacity: .75;
         padding: 2px 8px; border-radius: 4px; display: inline-block; }

  /* KB result box */
  .kb { border-radius: 10px; padding: 14px 18px; border: 2px solid #0F6E56;
        background: #E1F5EE; text-align: center; }
  .kb-title { font-size: 14px; font-weight: 700; color: #085041; margin-bottom: 6px; }
  .kb-stats { display: flex; gap: 16px; justify-content: center; flex-wrap: wrap; }
  .kb-stat { font-size: 12px; color: #0F6E56; font-weight: 500; }
</style>

<div class="pipe">

  <!-- SOURCE DOCUMENTS -->
  <div style="text-align:center;font-size:11px;color:#666;font-weight:600;
              text-transform:uppercase;letter-spacing:.05em;margin-bottom:6px">
    Source Documents
  </div>
  <div class="sources">
    <span class="src-chip">📄 PDF / Scanned</span>
    <span class="src-chip">🌐 HTML / Wiki</span>
    <span class="src-chip">💻 Code / Repo</span>
    <span class="src-chip">📊 Spreadsheet / DB</span>
    <span class="src-chip">💬 Email / Chat</span>
  </div>

  <div class="conn"><div class="arr">↓</div></div>

  <!-- STEP 1 -->
  <div class="step" style="background:#EBF4FD;border-color:#4A90D9">
    <div class="step-num" style="color:#1a5fa8">Step 1</div>
    <div class="step-title" style="color:#0D47A1">📄 Document Ingestion + Parsing</div>
    <div class="step-body">
      <div class="pill pill-nb">
        <span class="nb-badge">⚠ not built here</span>
        <span class="pill-title">Type Classifier</span>
        <span class="pill-body">MIME type + content signals<br>Routes each doc to specialist parser</span>
      </div>
      <div class="pill pill-nb">
        <span class="nb-badge">⚠ not built here</span>
        <span class="pill-title">Specialist Parsers</span>
        <span class="pill-body">PDF → OCR &nbsp;·&nbsp; Code → AST<br>HTML → scraper &nbsp;·&nbsp; Office → Tika</span>
      </div>
      <div class="pill pill-nb">
        <span class="nb-badge">⚠ not built here</span>
        <span class="pill-title">Quality &amp; Compliance Gate</span>
        <span class="pill-body">PII scan &nbsp;·&nbsp; dedup check<br>Readability score &nbsp;·&nbsp; language detect</span>
      </div>
      <div class="pill" style="background:#EBF4FD;border-color:#4A90D9">
        <span class="built-badge">✓ built</span>
        <span class="pill-title">Simple Text Loader</span>
        <span class="pill-body">Reads 5 .txt files · strip HTML<br>normalize whitespace · drop noise lines</span>
      </div>
    </div>
    <div class="out" style="background:#c5dff7;color:#0D47A1">
      Output → 5 cleaned plain-text documents ready for chunking
    </div>
  </div>

  <div class="conn"><div class="arr">↓</div><div class="label">5 cleaned plain-text documents</div></div>

  <!-- STEP 2 -->
  <div class="step" style="background:#F5EEFB;border-color:#9B59B6">
    <div class="step-num" style="color:#6a1b9a">Step 2</div>
    <div class="step-title" style="color:#4A148C">✂️ Chunking</div>
    <div class="step-body">
      <div class="pill" style="background:#fffbe6;border-color:#e0c040">
        <span class="demo-badge">👁 interactive demo</span>
        <span class="pill-title">Strategy Selector</span>
        <span class="pill-body">Fixed-token · Sentence · Semantic<br>Hierarchical — explore each, KB uses fixed-token</span>
      </div>
      <div class="pill" style="background:#ecdff7;border-color:#CE93D8">
        <span class="built-badge">✓ built</span>
        <span class="pill-title">Parameters (this app)</span>
        <span class="pill-body">400 tokens · 75 token overlap<br>Preserves sentence boundaries</span>
      </div>
      <div class="pill pill-nb">
        <span class="nb-badge">⚠ not built here</span>
        <span class="pill-title">Special Routing</span>
        <span class="pill-body">Code → AST boundaries<br>Tables → chunked as-is (no split)</span>
      </div>
    </div>
    <div class="out" style="background:#d9c8f0;color:#4A148C">
      Output → 312 chunks · each a self-contained retrieval unit
    </div>
  </div>

  <div class="conn"><div class="arr">↓</div><div class="label">312 text chunks</div></div>

  <!-- STEP 3 -->
  <div class="step" style="background:#FEF5EC;border-color:#E67E22">
    <div class="step-num" style="color:#a84a00">Step 3</div>
    <div class="step-title" style="color:#7B3F00">🏷️ Metadata Tagging</div>
    <div class="step-body">
      <div class="pill" style="background:#fde8cc;border-color:#FAD7A0">
        <span class="built-badge">✓ built</span>
        <span class="pill-title">Structural Auto-tagger</span>
        <span class="pill-body">source · doc type · section<br>has_code · has_tables · has_citations<br>position · word count · indexed_at</span>
      </div>
      <div class="pill pill-nb">
        <span class="nb-badge">⚠ not built here</span>
        <span class="pill-title">ACL Propagator</span>
        <span class="pill-body">allowed_roles · department · clearance_level<br>fields in schema · not enforced at query time</span>
      </div>
      <div class="pill pill-nb">
        <span class="nb-badge">⚠ not built here</span>
        <span class="pill-title">Freshness Stamps</span>
        <span class="pill-body">created_at · updated_at · version<br>fields in schema · not populated with real dates</span>
      </div>
    </div>
    <div class="out" style="background:#f9d5a3;color:#7B3F00">
      Output → 312 chunks · 15 metadata fields each · ready to filter at retrieval time
    </div>
  </div>

  <div class="conn"><div class="arr">↓</div><div class="label">chunks + 15 metadata fields</div></div>

  <!-- STEP 4 -->
  <div class="step" style="background:#EEEDFE;border-color:#7F77DD">
    <div class="step-num" style="color:#3730a3">Step 4</div>
    <div class="step-title" style="color:#2d2a8a">🔢 Embedding</div>
    <div class="step-body">
      <div class="pill" style="background:#dddcfc;border-color:#A5A0EE">
        <span class="built-badge">✓ built</span>
        <span class="pill-title">Embedding Model</span>
        <span class="pill-body">all-MiniLM-L6-v2 (local · ONNX)<br>No API key · 384 dimensions</span>
      </div>
      <div class="pill" style="background:#dddcfc;border-color:#A5A0EE">
        <span class="built-badge">✓ built</span>
        <span class="pill-title">Same Model, Queries Too</span>
        <span class="pill-body">Online pipeline uses identical model<br>Consistent vector space guaranteed</span>
      </div>
      <div class="pill pill-nb">
        <span class="nb-badge">⚠ not built here</span>
        <span class="pill-title">Embedding Registry</span>
        <span class="pill-body">Model version locked per index<br>Silent upgrades cause silent failures</span>
      </div>
    </div>
    <div class="out" style="background:#cac8f8;color:#2d2a8a">
      Output → 384-dim dense vector per chunk · meaning encoded as math
    </div>
  </div>

  <div class="conn"><div class="arr">↓</div><div class="label">384-dim vectors + metadata</div></div>

  <!-- STEP 5 -->
  <div class="step" style="background:#E1F5EE;border-color:#0F6E56">
    <div class="step-num" style="color:#085041">Step 5</div>
    <div class="step-title" style="color:#064033">🗄️ Vector Store Indexing</div>
    <div class="step-body">
      <div class="pill" style="background:#c8ece3;border-color:#6BCAAC">
        <span class="built-badge">✓ built</span>
        <span class="pill-title">Dense Index (HNSW)</span>
        <span class="pill-body">usearch · cosine space<br>384-dim fastembed vectors</span>
      </div>
      <div class="pill pill-nb">
        <span class="nb-badge">⚠ not built here</span>
        <span class="pill-title">Sparse Index (BM25)</span>
        <span class="pill-body">Keyword ranking combined via RRF<br>BM25 added on top in production</span>
      </div>
      <div class="pill" style="background:#c8ece3;border-color:#6BCAAC">
        <span class="built-badge">✓ built</span>
        <span class="pill-title">Metadata Index</span>
        <span class="pill-body">In-memory filtering on all fields<br>type · source · section filters</span>
      </div>
    </div>
    <div class="out" style="background:#a3d9c8;color:#064033">
      Output → Knowledge base · HNSW + BM25 searchable · metadata-filterable · 312 chunks ready
    </div>
  </div>

  <div class="conn"><div class="arr">↓</div></div>

  <!-- KB RESULT -->
  <div class="kb">
    <div class="kb-title">✅ Knowledge Base — Ready for Online Pipeline</div>
    <div class="kb-stats">
      <span class="kb-stat">312 chunks</span>
      <span class="kb-stat">5 documents</span>
      <span class="kb-stat">384-dim vectors</span>
      <span class="kb-stat">15 metadata fields</span>
      <span class="kb-stat">HNSW indexed · 384-dim</span>
    </div>
  </div>

</div>
""", height=1150)

    st.markdown("---")

    # ── Chunk Inspector ───────────────────────────────────────────────────────
    st.markdown("**🔬 Chunk Inspector — browse what's actually in the index**")
    st.caption("Every answer the online pipeline gives comes from one of these chunks. This is what retrieval searches through.")

    if not st.session_state.get("kb_loaded"):
        from knowledge_base.loader import load_knowledge_base
        with st.spinner("Loading knowledge base…"):
            load_knowledge_base()

    chunks = st.session_state.get("kb_chunks", [])

    if not chunks:
        st.info("Chunks not yet available — complete the offline pipeline first.")
    else:
        # ── Chunks per document ───────────────────────────────────────────────
        from collections import Counter
        doc_counts = Counter(c.doc_title for c in chunks)

        st.markdown("**Chunks per document:**")
        total = len(chunks)
        for doc, count in sorted(doc_counts.items(), key=lambda x: -x[1]):
            pct = count / total
            st.markdown(
                f"<div style='margin-bottom:6px'>"
                f"<div style='display:flex;justify-content:space-between;font-size:12px;"
                f"color:var(--color-text-primary);margin-bottom:3px'>"
                f"<span>{doc}</span><span style='color:var(--color-text-tertiary)'>{count} chunks</span></div>"
                f"<div style='height:6px;background:var(--color-background-secondary);border-radius:3px'>"
                f"<div style='height:6px;width:{pct*100:.0f}%;background:#185FA5;border-radius:3px'></div></div>"
                f"</div>",
                unsafe_allow_html=True
            )

        st.markdown("")

        # ── Filters ───────────────────────────────────────────────────────────
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            docs = ["All documents"] + sorted(doc_counts.keys())
            selected_doc = st.selectbox("Filter by document", docs, key="ci_doc")
        with col_f2:
            positions = ["All positions", "early", "middle", "late"]
            selected_pos = st.selectbox("Filter by position", positions, key="ci_pos")
        with col_f3:
            flags = ["All chunks", "Has tables", "Has code", "Has citations"]
            selected_flag = st.selectbox("Filter by content type", flags, key="ci_flag")

        # ── Apply filters ─────────────────────────────────────────────────────
        filtered = chunks
        if selected_doc != "All documents":
            filtered = [c for c in filtered if c.doc_title == selected_doc]
        if selected_pos != "All positions":
            filtered = [c for c in filtered if c.chunk_position == selected_pos]
        if selected_flag == "Has tables":
            filtered = [c for c in filtered if c.has_tables]
        elif selected_flag == "Has code":
            filtered = [c for c in filtered if c.has_code]
        elif selected_flag == "Has citations":
            filtered = [c for c in filtered if c.has_citations]

        st.caption(f"Showing {len(filtered)} of {total} chunks")

        # ── Chunk cards ───────────────────────────────────────────────────────
        page_size = 5
        page = st.session_state.get("ci_page", 0)
        total_pages = max(1, (len(filtered) + page_size - 1) // page_size)
        page = min(page, total_pages - 1)
        page_chunks = filtered[page * page_size:(page + 1) * page_size]

        for chunk in page_chunks:
            flags_html = ""
            if chunk.has_tables:
                flags_html += "<span style='background:#E3F2FD;color:#0D47A1;font-size:10px;padding:1px 6px;border-radius:4px;margin-right:4px'>📊 table</span>"
            if chunk.has_code:
                flags_html += "<span style='background:#F3E5F5;color:#4A148C;font-size:10px;padding:1px 6px;border-radius:4px;margin-right:4px'>💻 code</span>"
            if chunk.has_citations:
                flags_html += "<span style='background:#E8F5E9;color:#1B5E20;font-size:10px;padding:1px 6px;border-radius:4px;margin-right:4px'>📎 citations</span>"

            pos_color = {"early": "#0F6E56", "middle": "#185FA5", "late": "#9B59B6"}.get(chunk.chunk_position, "#888")

            st.markdown(f"""
<div style="background:var(--color-background-secondary);border-radius:10px;
padding:14px 16px;margin-bottom:10px;border-left:3px solid {pos_color}">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px;flex-wrap:wrap;gap:6px">
    <div>
      <span style="font-size:11px;font-weight:600;color:var(--color-text-primary)">{chunk.doc_title}</span>
      <span style="font-size:10px;color:var(--color-text-tertiary);margin-left:8px">§ {chunk.section}</span>
    </div>
    <div style="display:flex;gap:4px;align-items:center;flex-wrap:wrap">
      {flags_html}
      <span style="font-size:10px;color:{pos_color};background:{pos_color}18;padding:1px 6px;border-radius:4px">{chunk.chunk_position}</span>
    </div>
  </div>
  <div style="font-size:12px;color:var(--color-text-secondary);line-height:1.65;
  background:var(--color-background-primary);border-radius:6px;padding:10px 12px;margin-bottom:10px;
  font-family:inherit;white-space:pre-wrap">{chunk.text[:400]}{"…" if len(chunk.text) > 400 else ""}</div>
  <div style="display:flex;gap:16px;flex-wrap:wrap">
    <span style="font-size:10px;color:var(--color-text-tertiary)">🔤 {chunk.word_count} words · {chunk.tokens} tokens</span>
    <span style="font-size:10px;color:var(--color-text-tertiary)">📄 {chunk.doc_type}</span>
    <span style="font-size:10px;color:var(--color-text-tertiary)">🔑 {chunk.chunk_id}</span>
    <span style="font-size:10px;color:var(--color-text-tertiary)">🧠 {chunk.chunking_strategy}</span>
  </div>
</div>
""", unsafe_allow_html=True)

        # ── Pagination ────────────────────────────────────────────────────────
        if total_pages > 1:
            p_col1, p_col2, p_col3 = st.columns([1, 2, 1])
            with p_col1:
                if st.button("← Prev", disabled=(page == 0), key="ci_prev"):
                    st.session_state.ci_page = page - 1
                    st.rerun()
            with p_col2:
                st.markdown(
                    f"<div style='text-align:center;font-size:12px;color:var(--color-text-tertiary);padding-top:8px'>"
                    f"Page {page + 1} of {total_pages}</div>",
                    unsafe_allow_html=True
                )
            with p_col3:
                if st.button("Next →", disabled=(page == total_pages - 1), key="ci_next"):
                    st.session_state.ci_page = page + 1
                    st.rerun()

    st.markdown("---")
    st.markdown("*The offline pipeline runs once. The online pipeline uses what was built here — every query, every time.*")

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
    st.markdown("""
<div style="background:#fef3cd;border:1px solid #f0c060;border-radius:8px;
padding:10px 14px;margin-bottom:10px;font-size:12px;color:#7a4a00;line-height:1.6">
  🔑 <strong>The online pipeline requires an LLM API key</strong> — Gemini, OpenAI, Anthropic, or Cohere.
  You can enter it on the next screen. The offline pipeline you just built (embeddings, HNSW index, metadata) works without any API key.
</div>
""", unsafe_allow_html=True)

    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("← Back", use_container_width=True):
            go_back()
    with col2:
        if st.button("🔍 See it in action — Online Pipeline →", type="primary", use_container_width=True):
            jump_to_online()
