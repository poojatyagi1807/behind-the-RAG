"""Step 1 — Document Ingestion + Parsing."""
import streamlit as st
from ui import (render_topbar, render_step_header, render_thinking_card,
                render_what_we_built, render_enterprise_note, render_risk_table, render_nav,
                render_pm_matrix)
from config.content import LOADER_COMPARISON
from knowledge_base.kb import DOCUMENTS

# ── Parsing before/after data ─────────────────────────────────────────────────

RAW_INPUT = """\
RESULTS — Open Domain QA Performance

RAG combines parametric memory with non-parametric retrieval,
allowing it to access knowledge without storing it in model weights.

Table 1: Benchmark Results on NaturalQuestions

| Model        | Exact Match | F1    |
|--------------|-------------|-------|
| T5-11B       | 34.5        | 45.1  |
| RAG-Sequence | 44.5        | 56.8  |
| RAG-Token    | 45.5        | 56.8  |

[Figure 2: Retrieval recall vs answer accuracy scatter plot.
Shows positive correlation between retrieval recall (x-axis)
and downstream QA accuracy (y-axis) across 5 datasets.]

See also: Lewis et al. [1], Karpukhin et al. [2], Guu et al. [3]
"""

SIMPLE_OUTPUT = """\
RESULTS Open Domain QA Performance RAG combines
parametric memory with non-parametric retrieval
allowing it to access knowledge without storing
it in model weights. Table 1 Benchmark Results
on NaturalQuestions Model Exact Match F1 T5-11B
34.5 45.1 RAG-Sequence 44.5 56.8 RAG-Token 45.5
56.8 Figure 2 Retrieval recall vs answer accuracy
scatter plot Shows positive correlation between
retrieval recall x-axis and downstream QA
accuracy y-axis across 5 datasets See also
Lewis et al 1 Karpukhin et al 2 Guu et al 3
"""

ENTERPRISE_PROSE = """\
RAG combines parametric memory with
non-parametric retrieval, allowing it
to access knowledge without storing
it in model weights.

[section="Results", type="prose",
 has_citations=false]
"""

ENTERPRISE_TABLE = """\
{
  "type": "table",
  "caption": "Benchmark Results — NaturalQuestions",
  "headers": ["Model", "Exact Match", "F1"],
  "rows": [
    ["T5-11B",       "34.5", "45.1"],
    ["RAG-Sequence", "44.5", "56.8"],
    ["RAG-Token",    "45.5", "56.8"]
  ],
  "chunk_separately": true
}
"""

ENTERPRISE_IMAGE = """\
[type: figure | id: fig_2]
Caption: "Retrieval recall vs answer accuracy scatter plot"

── Vision model output (GPT-4V / Claude Vision) ──────────
The figure is a scatter plot with retrieval recall on the
x-axis (0.0–1.0) and downstream QA accuracy on the y-axis
(0.0–1.0). Five datasets are plotted as distinct markers:
NaturalQuestions (blue), TriviaQA (orange), WebQuestions
(green), CuratedTrec (red), and MS-MARCO (purple).

A clear positive trend is visible across all datasets —
higher retrieval recall consistently correlates with higher
QA accuracy. The gain is strongest between recall 0.6–0.9,
where accuracy improves by ~15 points. A dashed reference
line marks RAG-Token at recall=0.85, accuracy=0.81.

Key finding: retrieval quality is the primary bottleneck.
Improving recall from 0.6 to 0.9 yields larger accuracy
gains than any generation-side improvement alone.
──────────────────────────────────────────────────────────
[embedded as a separate chunk · searchable via text query]
"""

# ── Routing table ─────────────────────────────────────────────────────────────

RISKS = [
    {"risk": "Figures not loaded", "example": "Research paper references Figure 3 — text loader misses it", "mitigation": "AWS Textract, Azure Document Intelligence extract images alongside text"},
    {"risk": "Stale content", "example": "Document updated in Confluence — index not refreshed for 3 months", "mitigation": "Change detection webhooks — AWS EventBridge triggers re-ingestion automatically"},
    {"risk": "Permission bleed", "example": "HR document indexed globally — any employee retrieves confidential data", "mitigation": "Document-level ACL metadata at ingestion — AWS Knowledge Base enforces per-user filtering at retrieval"},
    {"risk": "Table flattening", "example": "Financial report table converted to unstructured text — LLM can't reason over it correctly", "mitigation": "AWS Textract and Azure Document Intelligence preserve table structure as JSON — chunk tables separately"},
    {"risk": "PII leakage", "example": "Employee performance review indexed — personal data surfaces in responses", "mitigation": "Pre-ingestion PII scan with AWS Comprehend or Azure Presidio — redact or exclude before entering pipeline"},
    {"risk": "Classifier wrong type", "example": "A PDF invoice routed to wiki parser — structured data garbled", "mitigation": "Confidence threshold on classifier — low-confidence docs flagged for human review queue"},
]

ROUTING_TABLE = [
    {
        "type": "PDF / Scanned document",
        "detection": "MIME: application/pdf + image content signals",
        "workflow": "OCR pipeline",
        "tools": "AWS Textract, Azure Document Intelligence",
        "extra": "Runs layout analysis to detect tables, figures, multi-column text before extraction",
    },
    {
        "type": "Office docs (Word, Excel, PPT)",
        "detection": "MIME: application/vnd.openxmlformats",
        "workflow": "Office parser",
        "tools": "Apache Tika, Microsoft Graph API, Unstructured.io",
        "extra": "Preserves heading hierarchy, embedded tables, speaker notes in PPT",
    },
    {
        "type": "Web / HTML page",
        "detection": "MIME: text/html or URL pattern",
        "workflow": "HTML scraper",
        "tools": "BeautifulSoup, Playwright (JS-rendered), Confluence connector",
        "extra": "JS-heavy pages (React/Angular) need headless browser — static pages use lightweight parser",
    },
    {
        "type": "Code / Repo",
        "detection": "File extension (.py, .ts, .java) or GitHub/GitLab source",
        "workflow": "AST-aware parser",
        "tools": "Tree-sitter, GitHub Copilot loader, LlamaIndex code splitter",
        "extra": "Splits by function/class boundaries — preserves docstrings and type signatures",
    },
    {
        "type": "Structured data (CSV, JSON, DB)",
        "detection": "MIME: text/csv, application/json, DB connector",
        "workflow": "Schema-aware loader",
        "tools": "Pandas, SQLAlchemy, dbt, AWS Glue",
        "extra": "Each row or record becomes a chunk — schema fields become metadata filters",
    },
    {
        "type": "Email / Chat thread",
        "detection": "Source connector type (Gmail, Outlook, Slack)",
        "workflow": "Thread parser",
        "tools": "Microsoft Graph API, Slack API, Gmail API",
        "extra": "Threads are reconstructed before chunking — avoids splitting reply context",
    },
]


def render_enterprise_pipeline():
    """Full enterprise ingestion + parsing pipeline flow."""
    st.markdown("""
<div style="background:var(--color-background-secondary);border-radius:10px;
padding:16px 20px;margin:12px 0;font-size:12px;line-height:1.8">
<strong style="font-size:13px">Enterprise ingestion + parsing pipeline — end to end</strong>
<div style="margin-top:14px;display:flex;flex-wrap:wrap;align-items:center;gap:6px">

  <div style="background:#E8F5E9;border:1px solid #A5D6A7;border-radius:6px;
  padding:6px 12px;color:#1B5E20;font-weight:500;white-space:nowrap">
    📡 Source connectors<br>
    <span style="font-weight:normal;font-size:11px">S3, SharePoint, Confluence,<br>Notion, GDrive, Salesforce</span>
  </div>

  <div style="font-size:18px;color:#888">→</div>

  <div style="background:#E3F2FD;border:1px solid #90CAF9;border-radius:6px;
  padding:6px 12px;color:#0D47A1;font-weight:500;white-space:nowrap">
    🔍 Type classifier<br>
    <span style="font-weight:normal;font-size:11px">MIME type + content signals<br>ML model for ambiguous docs</span>
  </div>

  <div style="font-size:18px;color:#888">→</div>

  <div style="background:#FFF3E0;border:1px solid #FFCC80;border-radius:6px;
  padding:6px 12px;color:#E65100;font-weight:500;white-space:nowrap">
    🔀 Specialist parser<br>
    <span style="font-weight:normal;font-size:11px">OCR · AST · Office · HTML<br>per-type structure preserved</span>
  </div>

  <div style="font-size:18px;color:#888">→</div>

  <div style="background:#F3E5F5;border:1px solid #CE93D8;border-radius:6px;
  padding:6px 12px;color:#4A148C;font-weight:500;white-space:nowrap">
    🛡️ Quality &amp; compliance<br>
    <span style="font-weight:normal;font-size:11px">PII scan · readability score<br>dedup · language detection</span>
  </div>

  <div style="font-size:18px;color:#888">→</div>

  <div style="background:#E1F5EE;border:1px solid #A5D6A7;border-radius:6px;
  padding:6px 12px;color:#085041;font-weight:500;white-space:nowrap">
    🏷️ Metadata enrichment<br>
    <span style="font-weight:normal;font-size:11px">ACL · timestamps · auto-tags<br>entity extraction</span>
  </div>

  <div style="font-size:18px;color:#888">→</div>

  <div style="background:#E8F5E9;border:1px solid #A5D6A7;border-radius:6px;
  padding:6px 12px;color:#1B5E20;font-weight:500;white-space:nowrap">
    ✅ Ready for chunking<br>
    <span style="font-weight:normal;font-size:11px">Typed, clean, structured text<br>with full metadata attached</span>
  </div>

</div>
<div style="margin-top:10px;font-size:11px;color:#888">
  Orchestrated by Apache Airflow, AWS Glue, or Azure Data Factory — event-driven triggers on source change.
</div>
</div>
""", unsafe_allow_html=True)


def render():
    render_topbar()
    render_step_header("📄", "Document Ingestion + Parsing",
        "Documents arrive in any format. Before a single chunk is created, they're classified, routed, parsed, and cleaned.")

    render_thinking_card(
        "Documents come in every format — PDF, wiki, spreadsheet, code. "
        "Each format needs a different parser to extract the text cleanly. "
        "Poor parsing here means poor answers at every step downstream.",
        pipeline="offline"
    )

    # ── Our 5 documents ───────────────────────────────────────────────────────
    st.markdown("**Our knowledge base — 5 documents, 5 structures:**")
    for doc in DOCUMENTS:
        with st.expander(f"**{doc['title']}** — {doc['type'].replace('_',' ').title()}"):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Source:** {doc['source']}")
                st.markdown(f"**Structure:** {doc['structure']}")
            with col2:
                st.markdown(f"**Enterprise equivalent:** {doc['enterprise_equivalent']}")

    st.markdown("---")

    # ── Enterprise pipeline ───────────────────────────────────────────────────
    st.markdown("**How enterprises handle documents from ingestion to chunking-ready text:**")
    render_enterprise_pipeline()

    # ── What this app actually does ───────────────────────────────────────────
    st.markdown("""
<div style="background:#F0F4FF;border:1.5px solid #4A90D9;border-radius:10px;
padding:16px 20px;margin:4px 0 16px 0">
<div style="font-size:13px;font-weight:700;color:#0D47A1;margin-bottom:10px">
  🔧 What this app actually does — simple loader + basic cleaning
</div>
<div style="font-size:12px;color:#1a3a6e;line-height:1.6;margin-bottom:12px">
  We skip the enterprise pipeline above and load our 5 documents directly with Python's
  built-in file reader. Three cleaning passes run on every document before chunking:
</div>
<div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:14px">
  <div style="background:#dde8fc;border-radius:6px;padding:7px 12px;font-size:11px;color:#0D47A1;font-weight:500">
    1 · Strip HTML tags<br><span style="font-weight:normal">remove &lt;tags&gt; left by web-scraped sources</span>
  </div>
  <div style="background:#dde8fc;border-radius:6px;padding:7px 12px;font-size:11px;color:#0D47A1;font-weight:500">
    2 · Normalize whitespace<br><span style="font-weight:normal">collapse multiple spaces, tabs, newlines</span>
  </div>
  <div style="background:#dde8fc;border-radius:6px;padding:7px 12px;font-size:11px;color:#0D47A1;font-weight:500">
    3 · Drop near-empty lines<br><span style="font-weight:normal">remove lines shorter than 3 characters</span>
  </div>
</div>
</div>
""", unsafe_allow_html=True)


    st.markdown("**Document type → specialist parser — pick a type to see how it's routed:**")
    doc_type_selected = st.selectbox(
        "Document type",
        options=[r["type"] for r in ROUTING_TABLE],
        key="routing_selected",
    )
    route = next(r for r in ROUTING_TABLE if r["type"] == doc_type_selected)
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Detection signal**")
        st.markdown(f"<div style='font-size:12px;background:var(--color-background-secondary);"
                    f"padding:8px 10px;border-radius:6px'>{route['detection']}</div>",
                    unsafe_allow_html=True)
        st.markdown("**Routed to**")
        st.markdown(f"<div style='font-size:12px;background:var(--color-background-secondary);"
                    f"padding:8px 10px;border-radius:6px'>🔀 {route['workflow']}</div>",
                    unsafe_allow_html=True)
    with col2:
        st.markdown("**Enterprise tools**")
        st.markdown(f"<div style='font-size:12px;background:var(--color-background-secondary);"
                    f"padding:8px 10px;border-radius:6px'>{route['tools']}</div>",
                    unsafe_allow_html=True)
        st.markdown("**What the parser does**")
        st.markdown(f"<div style='font-size:12px;background:var(--color-background-secondary);"
                    f"padding:8px 10px;border-radius:6px'>{route['extra']}</div>",
                    unsafe_allow_html=True)

    st.markdown("---")

    # ── Before / after: naive vs enterprise parser ────────────────────────────
    st.markdown("**What the parser actually does — naive vs enterprise, same raw input:**")
    st.code(RAW_INPUT, language=None)
    st.caption("One PDF section containing prose, a benchmark table, and a figure. A naive loader treats this as one blob.")

    col_simple, col_vs, col_enterprise = st.columns([5, 1, 5])
    with col_simple:
        st.markdown("""
<div style="background:#FCEBEB;border:0.5px solid #F7C1C1;border-radius:8px;
padding:10px 14px;margin-bottom:8px;font-size:12px;font-weight:600;color:#501313">
⚠️ Simple parser (naive text loader)
</div>
""", unsafe_allow_html=True)
        st.code(SIMPLE_OUTPUT, language=None)
        st.caption("Table structure lost. Image reduced to caption text. Citations merged into prose. One undifferentiated blob — the LLM cannot reason over the table as data.")

    with col_vs:
        st.markdown("<div style='text-align:center;font-size:20px;padding-top:80px;color:#888'>vs</div>", unsafe_allow_html=True)

    with col_enterprise:
        st.markdown("""
<div style="background:#E1F5EE;border:0.5px solid #0F6E56;border-radius:8px;
padding:10px 14px;margin-bottom:8px;font-size:12px;font-weight:600;color:#085041">
✅ Enterprise parser (AWS Textract / Azure Document Intelligence)
</div>
""", unsafe_allow_html=True)
        st.markdown("<div style='font-size:11px;font-weight:700;color:#ffffff;margin-bottom:2px'>📝 Prose — clean, citations stripped</div>", unsafe_allow_html=True)
        st.code(ENTERPRISE_PROSE, language=None)
        st.markdown("<div style='font-size:11px;font-weight:700;color:#ffffff;margin-bottom:2px'>📊 Table — preserved as structured JSON</div>", unsafe_allow_html=True)
        st.code(ENTERPRISE_TABLE, language="json")
        st.markdown("<div style='font-size:11px;font-weight:700;color:#ffffff;margin-bottom:2px'>🖼️ Image — described, not discarded</div>", unsafe_allow_html=True)
        st.code(ENTERPRISE_IMAGE, language=None)
        st.caption("Three separate typed chunks. Table is queryable as data. Image is embedded via vision-generated description.")

    st.markdown("---")

    # ── Metadata per chunk ────────────────────────────────────────────────────
    st.markdown("**Metadata attached to every chunk after parsing:**")
    st.code("""{
  "source": "Lewis et al. RAG Paper (arXiv:2005.11401)",
  "document_type": "research_paper",
  "section": "Results — Open Domain QA",
  "has_code": false,
  "has_tables": true,
  "has_citations": true,
  "chunk_position": "middle",
  "word_count": 187,
  "indexed_at": "2024-05-01T09:23:41Z"
}""", language="json")
    st.caption("This metadata enables filtering at retrieval time — without it, retrieval is blind to source, type, and structure.")

    st.markdown("---")

    # ── PM Decision matrix ────────────────────────────────────────────────────
    render_pm_matrix("Document Ingestion + Parsing", [
        (
            "What goes in?",
            "Will more documents improve answers or add noise?",
            "Define document inclusion criteria and a quality bar before engineering starts.",
            "We picked 5 documents informally — a 2020 RAG paper, a blog post, LangChain docs, RAGAS docs, and a Pinecone guide. No inclusion criteria, no recency rule — so users of this app may be learning patterns the field already moved past.",
            "5 public RAG research documents, manually curated. Scope locked to RAG concepts only.",
            "Formal inclusion policy with document owner sign-off before any source is added to the index.",
        ),
        (
            "How fresh?",
            "How badly does a stale answer hurt your user?",
            "Set a sync frequency SLA tied to user tolerance for stale answers.",
            "We included the Lewis et al. RAG paper from 2020 with no freshness check. The field changed significantly between 2020 and 2024 — users of this app may be learning patterns that are already outdated.",
            "Static KB loaded once per session. No sync — appropriate for a fixed learning demo.",
            "Change-detection webhooks trigger re-ingestion automatically when source documents are updated.",
        ),
        (
            "Who sees what?",
            "Can a junior employee retrieve what a senior shouldn't share?",
            "Map user roles to document permissions before building the pipeline.",
            "We never defined an access policy — all content is public and all users see everything. It works for this demo, but the decision was never documented, so there's no plan if the content ever becomes sensitive.",
            "All 5 documents are public research. No ACL enforced — all users see all chunks.",
            "Document-level ACL metadata set at ingestion time; vector store enforces per-user filtering at retrieval.",
        ),
        (
            "Quality bar?",
            "What does a bad document do to user trust?",
            "Define a minimum quality checklist covering format, recency, and accuracy before indexing.",
            "We accepted all 5 documents at face value with no depth or readability check. The Lilian Weng blog and the RAG paper have very different technical depth — both got treated identically by the pipeline.",
            "Min line length ≥ 3 chars, HTML stripped, whitespace normalised. No readability score.",
            "Pre-ingestion quality gate: readability score, recency check, dedup hash, PII scan — all must pass.",
        ),
        (
            "Who maintains it?",
            "What happens to quality 6 months after launch when no one is watching?",
            "Assign a named owner and a review cadence before launch — not after quality degrades.",
            "We have no maintenance plan and no assigned owner. If LangChain or RAGAS releases a major update, the KB becomes silently stale with no one responsible for catching it.",
            "Single owner (the builder). No review cadence — static learning artifact, not a live KB.",
            "Named content owner + quarterly review cadence + staleness alerts when updated_at exceeds threshold.",
        ),
    ])

    st.markdown("---")

    render_what_we_built(
        "We load 5 public documents with a simple text loader and apply basic cleaning — "
        "strip HTML, normalize whitespace, extract structural markers. "
        "In production, this is a full ingestion + parsing pipeline: "
        "source connectors → type classifier → specialist parsers → quality & compliance → metadata enrichment. "
        "We keep it simple here so the focus stays on the retrieval-specific decisions downstream."
    )
    render_enterprise_note(
        "<strong>Source connectors</strong> — Dedicated connectors (SharePoint, Confluence, Notion, S3, Google Drive, Salesforce, Jira) "
        "stream documents into the pipeline with authentication and incremental sync built in. "
        "AWS Knowledge Base, Azure AI Search, and Vertex AI Search ship native connectors for this.<br><br>"
        "<strong>Type classification + specialist parsers</strong> — As documents arrive, a classifier detects type "
        "from MIME headers and content signals. Each type gets its own parser: "
        "OCR pipeline for scanned PDFs (AWS Textract), AST-aware parser for code (Tree-sitter), "
        "thread reconstructor for emails. Structure is <em>preserved</em>, not stripped.<br><br>"
        "<strong>Quality & compliance gate</strong> — PII detection (AWS Comprehend / Azure Presidio), "
        "deduplication, readability scoring, and ACL tagging run on every document. "
        "Documents that fail are quarantined or flagged for human review — not silently dropped.<br><br>"
        "<strong>Orchestration</strong> — The whole pipeline runs as a DAG in Apache Airflow, AWS Glue, or "
        "Azure Data Factory. Source change events trigger incremental re-ingestion — "
        "only changed documents are reprocessed, not the full corpus."
    )
    render_risk_table(RISKS)
    render_nav(next_label="Next: Chunking →", pipeline="offline")
