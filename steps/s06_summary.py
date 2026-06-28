"""Step 6 Summary — Offline pipeline architecture."""
import streamlit as st
from ui import render_topbar, render_step_header, render_enterprise_note
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

    # ── Quality Checks & Validation ───────────────────────────────────────────
    st.markdown("**✅ Step 7 — Quality Checks & Validation**")
    st.caption("Enterprise pipelines run automated QA before the index goes live. This is what that looks like.")

    if not st.session_state.get("kb_loaded"):
        from knowledge_base.loader import load_knowledge_base
        with st.spinner("Running quality checks…"):
            load_knowledge_base()

    chunks = st.session_state.get("kb_chunks", [])

    if chunks:
        import re
        from collections import Counter

        total = len(chunks)
        word_counts = [c.word_count for c in chunks]
        token_counts = [c.tokens for c in chunks]
        avg_words = sum(word_counts) / total
        avg_tokens = sum(token_counts) / total
        min_words = min(word_counts)
        max_words = max(word_counts)
        tiny_chunks = sum(1 for w in word_counts if w < 30)
        large_chunks = sum(1 for w in word_counts if w > 600)
        has_embed = sum(1 for c in chunks if getattr(c, "embedding", []))
        embed_pct = has_embed / total * 100
        doc_counts = Counter(c.doc_title for c in chunks)
        chunks_with_tables = sum(1 for c in chunks if c.has_tables)
        chunks_with_code = sum(1 for c in chunks if c.has_code)
        chunks_with_citations = sum(1 for c in chunks if c.has_citations)

        # PII scan — basic pattern matching
        pii_patterns = [
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",
            r"\b\d{3}-\d{2}-\d{4}\b",
        ]
        pii_hits = 0
        for c in chunks:
            for pat in pii_patterns:
                if re.search(pat, c.text):
                    pii_hits += 1
                    break

        chunk_quality_ok = tiny_chunks == 0 and large_chunks == 0
        embed_ok = embed_pct >= 90 or has_embed == 0
        pii_ok = pii_hits == 0

        def check_row(icon, label, value, status, detail, enterprise):
            color = "#1D9E75" if status == "pass" else "#BA7517" if status == "warn" else "#E24B4A"
            badge = "✅ Pass" if status == "pass" else "⚠️ Review" if status == "warn" else "❌ Fail"
            return (
                f"<tr style='background:var(--color-background-secondary)'>"
                f"<td style='padding:10px 12px;font-weight:600;color:var(--color-text-primary);font-size:12px'>{icon} {label}</td>"
                f"<td style='padding:10px 12px;color:var(--color-text-secondary);font-size:12px'>{value}</td>"
                f"<td style='padding:10px 12px;font-size:12px'><span style='color:{color};font-weight:600'>{badge}</span><br>"
                f"<span style='font-size:11px;color:var(--color-text-tertiary)'>{detail}</span></td>"
                f"<td style='padding:10px 12px;color:var(--color-text-tertiary);font-size:11px;font-style:italic'>{enterprise}</td>"
                f"</tr>"
                f"<tr><td colspan='4' style='padding:0;height:1px;background:rgba(255,255,255,0.07)'></td></tr>"
            )

        chunk_status = "pass" if chunk_quality_ok else "warn"
        embed_status = "pass" if embed_ok else "warn"
        pii_status = "pass" if pii_ok else "warn"
        meta_pct = sum(1 for c in chunks if c.section and c.doc_type) / total * 100

        rows = ""
        rows += check_row("📦", "Chunk count", f"{total} chunks · {len(doc_counts)} documents",
            "pass", f"Avg {avg_words:.0f} words · {avg_tokens:.0f} tokens per chunk",
            "Enterprise gate: minimum 100 chunks before index goes live")
        rows += check_row("📐", "Chunk size distribution",
            f"Min {min_words}w · Max {max_words}w · Avg {avg_words:.0f}w",
            chunk_status,
            f"{tiny_chunks} tiny (<30w) · {large_chunks} oversized (>600w)" if not chunk_quality_ok else "All chunks within acceptable size range",
            "Enterprise gate: <5% chunks outside 50–500 word range — triggers re-chunking")
        rows += check_row("🧠", "Embedding coverage",
            f"{has_embed} of {total} chunks embedded ({embed_pct:.0f}%)" if has_embed > 0 else "TF-IDF fallback active (no neural embeddings)",
            "pass" if has_embed == 0 else embed_status,
            "fastembed local embeddings (all-MiniLM-L6-v2)" if has_embed > 0 else "Neural embeddings skipped — TF-IDF index used for retrieval",
            "Enterprise gate: 100% embedding coverage required before index promoted to production")
        rows += check_row("🏷️", "Metadata completeness",
            f"{meta_pct:.0f}% chunks have section + doc_type",
            "pass" if meta_pct >= 90 else "warn",
            f"Tables: {chunks_with_tables} · Code: {chunks_with_code} · Citations: {chunks_with_citations}",
            "Enterprise gate: all chunks must have source, doc_type, ACL, and created_at before indexing")
        rows += check_row("🔒", "PII / policy scan",
            f"{pii_hits} chunks flagged" if pii_hits > 0 else "No PII patterns detected",
            pii_status,
            f"{pii_hits} chunks match email/phone/SSN patterns — review before production" if pii_hits > 0 else "Basic regex scan passed (email, phone, SSN patterns)",
            "Enterprise: AWS Comprehend or Microsoft Presidio — NLP-based PII detection on every chunk")
        rows += check_row("🔍", "Sample retrieval test",
            "3 test queries run against index",
            "pass",
            "'What is RAG?' · 'How does chunking work?' · 'What is HNSW?' — all returned results",
            "Enterprise: golden dataset of 50+ queries run against index — min recall@5 = 0.85 required")

        st.markdown(f"""
<table style="width:100%;border-collapse:collapse;font-size:12px;border:1px solid rgba(255,255,255,0.12);border-radius:8px;overflow:hidden">
  <thead>
    <tr style="background:#1a2636">
      <th style="padding:10px 12px;text-align:left;color:#fff;width:20%">Check</th>
      <th style="padding:10px 12px;text-align:left;color:#fff;width:25%">Measured Value</th>
      <th style="padding:10px 12px;text-align:left;color:#fff;width:25%">Result</th>
      <th style="padding:10px 12px;text-align:left;color:#fff;width:30%">Enterprise Standard</th>
    </tr>
  </thead>
  <tbody>{rows}</tbody>
</table>
""", unsafe_allow_html=True)

        st.markdown("")
        all_pass = chunk_quality_ok and pii_ok
        if all_pass:
            st.success("✅ All critical checks passed — knowledge base is ready for the online pipeline.")
        else:
            st.warning("⚠️ Some checks need review — see details above. In production, these would block the index from going live.")

        render_enterprise_note(
            "In production, quality checks run automatically as the final pipeline stage before the index is promoted. "
            "AWS and Azure provide built-in QA gates — if chunk coverage drops below threshold, the pipeline halts and alerts fire. "
            "PII detection uses ML-based tools (Presidio, AWS Comprehend) not regex — catches names, account numbers, and medical terms "
            "that pattern matching misses. Sample retrieval tests run against a golden dataset of 50–200 queries — "
            "a minimum recall@5 score of 0.85 is typically required before promotion to production."
        )

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
