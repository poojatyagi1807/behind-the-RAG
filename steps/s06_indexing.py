"""Step 5 — Indexing."""
import streamlit as st
import streamlit.components.v1 as components
from ui import (render_topbar, render_step_header, render_thinking_card,
                render_what_we_built, render_enterprise_note, render_risk_table, render_nav, render_pm_matrix)
from config.content import INDEX_COMPARISON

RISKS = [
    {"risk": "Index drift", "example": "30% of documents updated over 6 months — old and new vectors coexist with incompatible chunk boundaries", "mitigation": "Change-triggered re-indexing — every document update fires a re-index event via AWS EventBridge or Kafka"},
    {"risk": "Wrong index type at scale", "example": "Flat index in development works at 10K chunks — deployed to production at 50M — query latency 10ms → 45 seconds", "mitigation": "Test index type at 10x expected production scale before deploying — HNSW or IVF mandatory above 1M chunks"},
    {"risk": "No index versioning", "example": "HNSW parameters changed mid-production — old and new index coexist — retrieval inconsistent", "mitigation": "Version your index configuration — blue-green index deployment, same approach as software releases"},
    {"risk": "No monitoring", "example": "Index degrading silently — recall dropping week over week — nobody notices until users complain", "mitigation": "Track p95 retrieval latency and recall@K weekly — alert when either degrades more than 5% from baseline"},
]

HNSW_HTML = """
<!DOCTYPE html>
<html>
<head>
<style>
  body { margin: 0; padding: 12px; background: #1a1a2e; font-family: -apple-system, sans-serif; color: #e0e0e0; }
  .layer {
    border-radius: 8px; padding: 12px 16px; margin-bottom: 6px;
  }
  .layer-label {
    font-size: 11px; font-weight: 700; margin-bottom: 10px; letter-spacing: 0.3px;
  }
  .nodes { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
  .node {
    width: 34px; height: 34px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 10px; font-weight: 700; flex-shrink: 0;
  }
  .node-unvisited { border: 2px solid; opacity: 0.45; background: transparent; }
  .node-visited   { background: #F4845F; border: 2px solid #C0392B; color: white; }
  .node-entry     { background: #F4845F; border: 2px solid #C0392B; color: white; }
  .node-result    { background: #1D9E75; border: 2px solid #0F6E56; color: white; width:44px; height:44px; border-radius:8px; flex-direction:column; text-align:center; }
  .edge { color: #F4845F; font-size: 20px; font-weight: 300; margin: 0 2px; }
  .skip { color: #555; font-size: 18px; margin: 0 2px; }
  .drop { text-align: left; padding: 2px 0 2px 26px; font-size: 12px; color: #F4845F; }

  /* layer colours */
  .l2 { background: rgba(74,144,217,0.12); border-left: 3px solid #4A90D9; }
  .l2 .layer-label { color: #6AABEA; }
  .l2 .node-unvisited { border-color: #4A90D9; color: #4A90D9; }

  .l1 { background: rgba(160,120,210,0.12); border-left: 3px solid #9B6FD0; }
  .l1 .layer-label { color: #B99EE0; }
  .l1 .node-unvisited { border-color: #9B6FD0; color: #9B6FD0; }

  .l0 { background: rgba(80,180,100,0.12); border-left: 3px solid #4CAF72; }
  .l0 .layer-label { color: #72CF90; }
  .l0 .node-unvisited { border-color: #4CAF72; color: #4CAF72; }

  .stat-bar {
    background: rgba(244,132,95,0.12); border: 1px solid rgba(244,132,95,0.3);
    border-radius: 6px; padding: 8px 14px; margin-top: 8px;
    font-size: 12px; color: #F4845F; font-weight: 600; text-align: center;
    letter-spacing: 0.3px;
  }
  .sub { font-size: 10px; color: #888; margin-top: 2px; font-weight: 400; }
  .zone-label {
    font-size: 10px; color: #F4845F; border: 1px dashed #F4845F;
    border-radius: 4px; padding: 2px 7px; margin-left: 4px;
  }
</style>
</head>
<body>

  <!-- Query -->
  <div style="background:#2a2a40;border:1px solid #F4845F;border-radius:8px;padding:10px 14px;margin-bottom:8px;font-size:12px;">
    <span style="color:#F4845F;font-weight:700">Query:</span>
    <span style="color:#fff;margin-left:8px">"What metrics should I use to evaluate RAG?"</span>
    <span style="color:#888;font-size:10px;margin-left:12px">→ embedded to 384-dim vector</span>
  </div>

  <!-- STEP 1: Metadata filter -->
  <div style="background:rgba(74,144,217,0.10);border:1px solid #4A90D9;border-radius:8px;padding:10px 14px;margin-bottom:8px;font-size:12px;">
    <div style="font-weight:700;color:#6AABEA;margin-bottom:6px">① Metadata filter applied first — before HNSW touches anything</div>
    <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
      <div style="background:#1a2636;border:1px solid #4A90D9;border-radius:6px;padding:5px 10px;font-size:11px;color:#fff">
        312 chunks<br><span style="color:#888;font-size:10px">full index</span>
      </div>
      <span style="color:#4A90D9;font-size:18px">→</span>
      <div style="background:#1a2636;border:1px dashed #4A90D9;border-radius:6px;padding:5px 10px;font-size:11px;color:#888">
        <span style="text-decoration:line-through">Chunking docs</span><br>
        <span style="text-decoration:line-through">RAG paper</span><br>
        <span style="text-decoration:line-through">Lilian Weng</span><br>
        <span style="text-decoration:line-through">Pinecone guide</span>
      </div>
      <span style="color:#4A90D9;font-size:18px">→</span>
      <div style="background:#1D9E75;border:1px solid #0F6E56;border-radius:6px;padding:5px 10px;font-size:11px;color:#fff">
        ✅ 45 chunks<br><span style="font-size:10px">RAGAS docs only</span><br>
        <span style="font-size:10px;color:#a0f0d0">doc_type = evaluation_framework</span>
      </div>
      <span style="color:#6AABEA;font-size:10px;max-width:180px">267 chunks excluded instantly — no vector math needed, just a metadata check</span>
    </div>
  </div>

  <div style="text-align:center;color:#F4845F;font-size:12px;margin:4px 0;">↓ &nbsp;HNSW now searches only within these 45 filtered chunks</div>

  <!-- LAYER 2 -->
  <div class="layer l2">
    <div class="layer-label">LAYER 2 — Coarse map &nbsp;·&nbsp; 3 topic clusters within RAGAS docs &nbsp;·&nbsp; long jumps</div>
    <div class="nodes" style="flex-wrap:wrap;gap:8px 4px">
      <div class="node node-entry">IN</div>
      <span class="edge">→</span>
      <div class="node node-unvisited" style="font-size:8px">Setup &amp;<br>Install</div>
      <span class="skip">✗</span>
      <div class="node node-visited" style="font-size:8px">Metrics &amp;<br>Scoring ✓</div>
      <span class="skip" style="opacity:0.3">✗</span>
      <div class="node node-unvisited" style="font-size:8px">Pipelines &amp;<br>Integration</div>
      <span style="color:#72CF90;font-size:10px;margin-left:8px">"Metrics &amp; Scoring" cluster is closest — 2 skipped</span>
    </div>
  </div>

  <div class="drop">↓ &nbsp;"Metrics &amp; Scoring" cluster found — drop to Layer 1</div>

  <!-- LAYER 1 -->
  <div class="layer l1">
    <div class="layer-label">LAYER 1 — Neighbourhood map &nbsp;·&nbsp; sub-topics within Metrics cluster &nbsp;·&nbsp; medium jumps</div>
    <div class="nodes" style="flex-wrap:wrap;gap:8px 4px">
      <div class="node node-unvisited" style="font-size:8px">Noise<br>detection</div>
      <span class="skip">✗</span>
      <div class="node node-unvisited" style="font-size:8px">Cost &amp;<br>latency</div>
      <span class="skip">✗</span>
      <div class="node node-visited" style="font-size:8px">Core<br>metrics ✓</div>
      <span class="edge">←</span>
      <div class="node node-visited" style="font-size:8px">Scoring<br>methods ✓</div>
      <span class="skip">✗</span>
      <div class="node node-unvisited" style="font-size:8px">Baseline<br>compare</div>
      <span style="color:#B99EE0;font-size:10px;margin-left:8px">"Core metrics" neighbourhood — 3 sub-clusters skipped</span>
    </div>
  </div>

  <div class="drop">↓ &nbsp;"Core metrics" neighbourhood found — drop to Layer 0 for exact scoring</div>

  <!-- LAYER 0 -->
  <div class="layer l0">
    <div class="layer-label">LAYER 0 — All 45 filtered chunks &nbsp;·&nbsp; short hops in neighbourhood &nbsp;·&nbsp; cosine similarity scored</div>
    <div class="nodes" style="flex-wrap:wrap;gap:6px">
      <div class="node node-unvisited" style="width:20px;height:20px;font-size:7px;opacity:0.3"></div>
      <div class="node node-unvisited" style="width:20px;height:20px;font-size:7px;opacity:0.3"></div>
      <div class="node node-unvisited" style="width:20px;height:20px;font-size:7px;opacity:0.3"></div>
      <span class="zone-label">search zone →</span>
      <div class="node node-result" style="font-size:7px;padding:2px">🥇<br><span style="font-size:6px">Faithfulness<br>0.91</span></div>
      <div class="node node-result" style="font-size:7px;padding:2px">🥈<br><span style="font-size:6px">Ans. Relevancy<br>0.88</span></div>
      <div class="node node-result" style="font-size:7px;padding:2px">🥉<br><span style="font-size:6px">Ctx. Precision<br>0.85</span></div>
      <div class="node node-visited" style="font-size:7px;padding:2px">4th<br><span style="font-size:6px">0.79</span></div>
      <div class="node node-visited" style="font-size:7px;padding:2px">5th<br><span style="font-size:6px">0.74</span></div>
      <span class="zone-label">← top-5 scored</span>
      <div class="node node-unvisited" style="width:20px;height:20px;font-size:7px;opacity:0.3"></div>
      <div class="node node-unvisited" style="width:20px;height:20px;font-size:7px;opacity:0.3"></div>
      <div class="node node-unvisited" style="width:20px;height:20px;font-size:7px;opacity:0.3"></div>
    </div>
    <div class="sub" style="margin-top:8px;color:#72CF90">
      Top-3: "Faithfulness measures claim-level grounding..." · "Answer Relevancy scores query alignment..." · "Context Precision ranks retrieved chunks..."
    </div>
    <div class="sub" style="margin-top:4px">Faded nodes = never compared. Only ~12 of 45 filtered chunks evaluated by HNSW.</div>
  </div>

  <div class="stat-bar">
    312 → 45 chunks (metadata filter) &nbsp;·&nbsp; 45 → ~12 compared (HNSW) &nbsp;·&nbsp; 300 chunks never touched &nbsp;·&nbsp; &lt;5ms total
  </div>

</body>
</html>
"""


def render():
    render_topbar()
    render_step_header("🗂️", "Indexing",
        "Store vectors in a structure that can be searched in milliseconds across millions of chunks.")

    render_thinking_card(
        "Without an index, finding the closest vector means comparing against every single chunk — "
        "one by one. At 300 chunks that takes milliseconds. At 300 million chunks it takes minutes. "
        "An index organizes vectors so search skips most comparisons and still finds the right answer.",
        pipeline="offline"
    )

    # ── Metadata vs Indexing clarification ───────────────────────────────────
    st.markdown(
        """
<div style="background:var(--color-background-secondary);border:1px solid var(--color-border-tertiary);
border-radius:8px;padding:14px 16px;margin-bottom:16px;font-size:12px;line-height:1.8">
<strong style="font-size:13px">🤔 Wait — didn't metadata already speed things up?</strong><br><br>
Yes — but they do <em>different jobs</em>. Here's a concrete example:<br><br>
<strong>Metadata</strong> is the bouncer — it decides <em>which shelf to look at</em>.<br>
Query: "What metrics should I use to evaluate RAG?" → metadata filter narrows 1,000,000 chunks
down to 40,000 chunks tagged <code>document_type = evaluation_framework</code>.<br><br>
<strong>Index (HNSW)</strong> is the speed engine — it decides <em>how fast to search that shelf</em>.<br>
Of those 40,000 remaining chunks, HNSW compares only ~300 and still finds the best match in &lt;5ms.
Without an index, 40,000 comparisons one-by-one would take seconds.<br><br>
<strong>Together:</strong> &nbsp;Metadata cuts the <em>scope</em>. &nbsp;Index cuts the <em>search time within that scope</em>.
Neither replaces the other.
</div>
""", unsafe_allow_html=True)

    # ── 1. Index types ────────────────────────────────────────────────────────
    st.markdown("**Three index types — pick based on your scale:**")

    for key, idx in INDEX_COMPARISON.items():
        is_default = key == "hnsw"
        border = "#F4845F" if is_default else "var(--color-border-tertiary)"
        badge = (
            " &nbsp;<span style='font-size:10px;background:#F4845F22;color:#F4845F;"
            "border-radius:4px;padding:1px 7px'>production default</span>"
            if is_default else ""
        )
        st.markdown(
            f"<div style='border:1px solid {border};border-radius:8px;"
            f"padding:12px 16px;margin-bottom:8px'>"
            f"<div style='font-size:13px;font-weight:600;color:var(--color-text-primary)'>"
            f"{idx['label']}{badge}</div>"
            f"<div style='font-size:12px;color:var(--color-text-secondary);margin:4px 0 8px'>"
            f"{idx['definition']}</div>"
            f"<div style='display:flex;gap:24px;font-size:11px;color:var(--color-text-tertiary)'>"
            f"<span>🎯 Accuracy: <strong>{idx['accuracy']}</strong></span>"
            f"<span>⚡ Speed: <strong>{idx['speed']}</strong></span>"
            f"<span>📦 Scale: <strong>{idx['scale']}</strong></span>"
            f"<span>💾 Memory: <strong>{idx['memory']}</strong></span>"
            f"</div>"
            f"<div style='font-size:11px;color:var(--color-text-tertiary);margin-top:4px'>"
            f"Best for: {idx['best_for']}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # ── 2. HNSW visual ────────────────────────────────────────────────────────
    st.markdown("**How HNSW navigates — query to answer in 3 layers:**")
    st.markdown(
        "<div style='font-size:12px;color:var(--color-text-secondary);margin-bottom:10px'>"
        "Using our real query: <em>\"What metrics should I use to evaluate RAG?\"</em> — "
        "the metadata filter runs first, then HNSW searches only the filtered subset."
        "</div>",
        unsafe_allow_html=True,
    )
    components.html(HNSW_HTML, height=600, scrolling=False)

    st.markdown("---")

    # ── 3. Re-indexing strategies ─────────────────────────────────────────────
    st.markdown("**When to re-index**")
    st.markdown(
        "<div style='font-size:12px;color:var(--color-text-secondary);margin-bottom:10px'>"
        "Re-indexing means re-embedding documents and rebuilding the vector index. "
        "You need it when the content, the embedding model, or the index structure changes — "
        "any mismatch between what's in the index and what's being queried degrades retrieval silently."
        "</div>",
        unsafe_allow_html=True,
    )
    st.markdown("""
| Trigger | Why it requires re-indexing |
|---|---|
| Documents added or updated | New content not searchable until indexed |
| Embedding model upgraded | Old vectors and new vectors are in different spaces — incompatible |
| Metadata schema changed | Filters reference fields that don't exist on old chunks |
| Index parameters tuned | HNSW `ef_construction` or `M` changed — must rebuild to take effect |
| Recall score drops | Silent index drift — stale chunks ranked above fresh ones |
""")
    st.markdown("**Re-indexing strategies:**")
    st.markdown("""
| Strategy | When | Trade-off |
|---|---|---|
| **Full re-index** | Embedding model changes, major schema update | Simple but expensive — re-embeds everything |
| **Incremental update** | New or edited documents only | Fast but risks drift if change tracking breaks |
| **Partition-based** | Re-index by department / data source | Best of both at enterprise scale |
""")

    st.markdown("---")
    st.markdown("**Our index — what just got built, in plain English:**")

    build_steps = [
        (
            "1 · Turn every chunk into a vector",
            "All 312 chunks get converted into 384-number vectors using the all-MiniLM-L6-v2 model. "
            "This happens once per session and is cached — it doesn't repeat on every query.",
            "#4A90D9",
        ),
        (
            "2 · Build the HNSW index",
            "Those 312 vectors are organized into the 3-layer HNSW structure shown above — "
            "coarse topic clusters at the top, sub-topic neighbourhoods in the middle, "
            "and all individual chunks at street level. This is a one-time build step. "
            "No external database, no server, no compilation — it runs entirely in memory inside this session.",
            "#9B59B6",
        ),
        (
            "3 · At query time",
            "The metadata filter runs first — narrowing 312 chunks down to only the relevant subset "
            "(e.g. 45 RAGAS evaluation chunks). HNSW then navigates that filtered set top-down: "
            "identify the right topic cluster, narrow to the closest sub-topic, score the final "
            "candidates — comparing only ~12 chunks instead of all 45. "
            "The closest matches by cosine similarity come back in under 5 milliseconds.",
            "#E67E22",
        ),
    ]

    for title, body, border in build_steps:
        st.markdown(
            f"<div style='border-left:3px solid {border};border-radius:0 8px 8px 0;"
            f"padding:10px 14px;margin-bottom:8px;font-size:12px;line-height:1.7;"
            f"background:var(--color-background-secondary);color:var(--color-text-secondary)'>"
            f"<strong style='color:var(--color-text-primary)'>{title}</strong><br>{body}</div>",
            unsafe_allow_html=True,
        )

    st.markdown(
        "<div style='display:flex;gap:18px;flex-wrap:wrap;font-size:11px;"
        "color:var(--color-text-tertiary);margin-top:6px'>"
        "<span>🗂️ Index type: <strong>HNSW · cosine space</strong></span>"
        "<span>📦 Total chunks: <strong>312</strong></span>"
        "<span>🔢 Dimensions: <strong>384</strong></span>"
        "<span>🏷️ Metadata fields: <strong>15 per chunk</strong></span>"
        "<span>⚡ Search latency: <strong>&lt;5ms</strong></span>"
        "</div>",
        unsafe_allow_html=True,
    )

    # ── PM Decision Matrix ────────────────────────────────────────────────────
    rows_data = [
        (
            "Which vector database?",
            "Does your team need a purpose-built vector DB or is an extension on your existing database good enough?",
            "Benchmark Pinecone, Weaviate, and pgvector against your query volume and latency SLA before committing.",
            "Notion started with a custom vector store — migrated to a purpose-built solution after scale broke their homegrown index, delaying features by a quarter.",
            "usearch — an in-memory HNSW library, not a database. No persistence, no client/server layer, no metadata-native filtering at the DB level.",
            "Formal vector DB evaluation against latency, scale, cost, and operational overhead — decision signed off by PM and engineering lead.",
        ),
        (
            "Managed vs self-hosted?",
            "Do you have the engineering bandwidth to operate and monitor a self-hosted vector DB in production?",
            "Default to managed for V1 — only move to self-hosted when cost or compliance demands it.",
            "A healthtech startup self-hosted Weaviate to meet HIPAA requirements — spent 3 engineer-months on infra before first query ran.",
            "Neither — usearch runs in-process inside the Streamlit session. No infra, no persistence, index rebuilds every session.",
            "Managed for speed to market, self-hosted when compliance, data residency, or cost at scale makes it necessary — decision logged with justification.",
        ),
        (
            "Retrieval latency SLA?",
            "What is the maximum wait time your user will tolerate before the answer feels broken?",
            "Define a p95 latency target before indexing strategy is chosen — indexing directly affects query speed.",
            "Intercom's AI assistant had no latency SLA defined — engineers optimized for accuracy, users experienced 8 second response times and disengaged.",
            "No latency SLA defined — single-user demo session. Actual measured latency is <5ms per query (shown live on this page).",
            "p95 latency target defined by PM based on user research — indexing strategy and approximate nearest neighbor settings chosen to meet it.",
        ),
        (
            "How large will your index grow?",
            "What is your document volume today and what does it look like in 12 months?",
            "Project index size at 12 month volume before selecting a database — migration at scale is expensive.",
            "A legal tech company chose Chroma for MVP — at 10 million chunks it collapsed under load, emergency migration to Pinecone cost 6 engineer-weeks.",
            "Fixed at 312 chunks from 5 documents — static knowledge base, no growth planning, index rebuilt from scratch each session.",
            "Index size projected at 1x, 10x, 50x volume — database selected to handle 50x without architecture change.",
        ),
        (
            "Hybrid search from day one?",
            "Will keyword search alongside vector search improve answer accuracy for your specific user queries?",
            "Decide hybrid search scope in V1 planning — retrofitting keyword index later duplicates engineering effort.",
            "Elasticsearch added vector search on top of existing keyword index — teams that had not planned for hybrid from day one had to re-architect their entire retrieval layer.",
            "Vector search (HNSW) only by default. TF-IDF exists as a fallback if embeddings are unavailable — not combined with vector scores as true hybrid ranking.",
            "Hybrid search evaluated against top query types in discovery — if keyword match improves accuracy on 20% or more of queries, it is a V1 requirement not V2.",
        ),
    ]

    render_pm_matrix("Indexing", rows_data)

    render_what_we_built(
        "We embed all 312 chunks with all-MiniLM-L6-v2 (fastembed, local ONNX — no API key, no GPU) "
        "and build a real HNSW index using hnswlib. "
        "At query time the same model embeds the query and HNSW finds the nearest neighbours in cosine space. "
        "The same index is used in the online pipeline for every search."
    )
    render_enterprise_note(
        "Pinecone, Weaviate, Qdrant, and pgvector are the most widely deployed vector databases in production. "
        "Pinecone is fully managed — no infrastructure, automatic scaling, built-in metadata filtering. "
        "Weaviate is open source and self-hostable — preferred for strict data residency requirements. "
        "pgvector runs inside PostgreSQL — popular for teams who want vector search without adding a new "
        "database to their stack. Hybrid indexing — HNSW for dense vectors, BM25 for sparse keyword search, "
        "combined at query time — is the current production standard at Elastic and Weaviate. "
        "Re-indexing pipelines run on Apache Airflow or AWS Step Functions — triggered by document change "
        "events, not on a schedule."
    )
    render_risk_table(RISKS)

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    render_key_takeaway("The index is not storage — it is the search engine. HNSW makes approximate nearest-neighbour search fast at scale. Without it, every query would scan every chunk. Index configuration choices (M, ef_construction) trade off speed against accuracy and memory.", pipeline="offline")
    render_nav(next_label="Next: Pipeline Summary →", pipeline="offline")
