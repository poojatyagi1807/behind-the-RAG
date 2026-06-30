"""Step 3 — Metadata Tagging."""
import streamlit as st
from ui import (render_topbar, render_step_header, render_thinking_card,
                render_what_we_built, render_enterprise_note, render_risk_table, render_nav, render_pm_matrix)
from config.content import METADATA_SCHEMA

FILTER_EXAMPLES = {
    "no_filter": {
        "label": "No filter — pure semantic search",
        "results": [
            {"score": 0.87, "chunk": "Pinecone — RAG evaluation approaches", "doc": "Pinecone guide"},
            {"score": 0.84, "chunk": "RAGAS — faithfulness metric definition", "doc": "RAGAS docs"},
            {"score": 0.81, "chunk": "RAG paper — evaluation on NaturalQuestions", "doc": "RAG paper"},
        ],
    },
    "doc_type": {
        "label": "Filter: document_type = evaluation_framework",
        "results": [
            {"score": 0.92, "chunk": "RAGAS — faithfulness metric definition", "doc": "RAGAS docs"},
            {"score": 0.89, "chunk": "RAGAS — context recall explanation", "doc": "RAGAS docs"},
            {"score": 0.86, "chunk": "RAGAS — answer relevancy scoring", "doc": "RAGAS docs"},
        ],
    },
    "has_tables": {
        "label": "Filter: has_tables = True",
        "results": [
            {"score": 0.88, "chunk": "RAG paper — Table 1: benchmark results", "doc": "RAG paper"},
            {"score": 0.82, "chunk": "RAGAS — metric comparison table", "doc": "RAGAS docs"},
            {"score": 0.79, "chunk": "Pinecone — reranking performance comparison", "doc": "Pinecone guide"},
        ],
    },
    "early_position": {
        "label": "Filter: chunk_position = early",
        "results": [
            {"score": 0.85, "chunk": "RAG paper — Abstract: evaluation overview", "doc": "RAG paper"},
            {"score": 0.80, "chunk": "RAGAS — Introduction: why evaluation matters", "doc": "RAGAS docs"},
            {"score": 0.76, "chunk": "Pinecone guide — Introduction to RAG", "doc": "Pinecone guide"},
        ],
    },
}

RISKS = [
    {"risk": "No metadata — filter blind", "example": "User asks 'show me recent research' — no date metadata — system returns oldest paper ranked highest semantically", "mitigation": "Mandatory metadata schema at ingestion — chunks without required fields rejected before indexing"},
    {"risk": "Wrong filter kills recall", "example": "Developer filters document_type = research_paper — misses best answer in the tutorial", "mitigation": "Filter only when query intent is clear — use query classification to decide when to apply filters"},
    {"risk": "Stale metadata", "example": "Document updated but indexed_at not refreshed — retrieval returns outdated chunk believing it is current", "mitigation": "Metadata update pipeline runs alongside content re-indexing — never update one without the other"},
    {"risk": "Over-filtering", "example": "Too many filters simultaneously — search space collapses to zero results", "mitigation": "Fallback strategy — if filtered search returns zero results, retry with relaxed filters and log the event"},
]

def render():
    render_topbar()
    render_step_header("🏷️", "Metadata Tagging",
        "Vectors tell you what chunks are similar. Metadata tells you which ones are actually relevant.")

    render_thinking_card(
        "Metadata is extra information attached to each chunk — where it came from, what type it is, who can see it. "
        "A user asking for 'recent policy updates' can't be helped by a great vector search if there's no date field to filter on. "
        "Metadata is what turns retrieval from 'find similar text' to 'find the right text'.",
        pipeline="offline"
    )

    st.markdown("**Our metadata schema — every chunk gets tagged:**")
    rows = "| Field | Example value | Why it matters |\n|---|---|---|\n"
    rows += "\n".join(f"| `{r['field']}` | {r['example']} | {r['purpose']} |" for r in METADATA_SCHEMA)
    st.markdown(rows)

    st.markdown("---")

    # ── How the system decides which filter to apply ──────────────────────────
    st.markdown("**How the system actually uses metadata — query walkthrough**")
    st.markdown(
        "<div style='font-size:12px;color:var(--color-text-secondary);margin-bottom:10px'>"
        "Query: <em>'What metrics should I use to evaluate RAG?'</em>"
        "</div>",
        unsafe_allow_html=True,
    )

    steps = [
        (
            "1 · Query classifier reads intent",
            "The query contains 'metrics', 'evaluate', 'RAG' — classifier labels this as "
            "<strong>intent: evaluation</strong>. This is not a how-to question or a conceptual question. "
            "It is asking for structured measurement criteria.",
            "#4A90D9", "#4A90D9",
        ),
        (
            "2 · Metadata filter is selected",
            "The classifier maps <em>evaluation intent</em> → apply filter "
"<code>document_type = evaluation_framework</code>. "
            "This narrows the search corpus from all 5 documents down to just the RAGAS docs — "
            "the only source in the knowledge base dedicated to evaluation metrics.",
            "#9B59B6", "#9B59B6",
        ),
        (
            "3 · Semantic search runs on the filtered corpus",
            "Vector similarity now runs only against chunks from the RAGAS docs. "
            "The search space drops from ~200 chunks to ~40. "
            "Every result returned is from a document specifically about evaluation — "
            "no off-topic architecture chunks can rank higher than a relevant metrics chunk.",
            "#E67E22", "#E67E22",
        ),
        (
            "4 · Results are precise and grounded",
            "Top results: faithfulness definition, context recall explanation, answer relevancy scoring. "
            "Without the filter, a high-scoring chunk about RAG architecture from the RAG paper "
            "could surface above the actual metrics definition — semantically close, but wrong source.",
            "#27AE60", "#27AE60",
        ),
    ]

    for title, body, border, fg in steps:
        st.markdown(
            f"<div style='border-left:3px solid {border};border-radius:0 8px 8px 0;"
            f"padding:10px 14px;margin-bottom:8px;font-size:12px;line-height:1.7;"
            f"background:var(--color-background-secondary);color:var(--color-text-secondary)'>"
            f"<strong style='color:{fg}'>{title}</strong><br>{body}</div>",
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # ── Access control & freshness ────────────────────────────────────────────
    st.markdown("**Two metadata categories enterprises can't skip**")

    col_acl, col_fresh = st.columns(2)
    with col_acl:
        st.markdown("""
<div style="background:#FAEEDA;border:0.5px solid #FAC775;border-radius:8px;padding:14px;height:100%">
<div style="font-size:13px;font-weight:600;color:#4A2800;margin-bottom:8px">🔐 Access Control (ACL)</div>
<div style="font-size:12px;color:#6B3A00;line-height:1.7">
<strong>allowed_roles</strong> — which roles can see this chunk<br>
<strong>department</strong> — HR chunks only for HR queries<br>
<strong>clearance_level</strong> — numeric gate (user level ≥ chunk level)<br><br>
ACL filters run <em>before</em> vector search — the model never sees chunks the user can't access.
This is not optional in any regulated industry.
</div>
</div>
""", unsafe_allow_html=True)

    with col_fresh:
        st.markdown("""
<div style="background:#E6F1FB;border:0.5px solid #185FA5;border-radius:8px;padding:14px;height:100%">
<div style="font-size:13px;font-weight:600;color:#0C447C;margin-bottom:8px">⏱️ Freshness & Versioning</div>
<div style="font-size:12px;color:#184070;line-height:1.7">
<strong>created_at</strong> — when the chunk was first indexed<br>
<strong>updated_at</strong> — when content last changed<br>
<strong>version</strong> — policy version, product release, etc.<br><br>
Enables recency-boosting ("show me the latest guidance"),
staleness detection, and multi-version knowledge bases
(e.g. "v2 policy" vs "v3 policy").
</div>
</div>
""", unsafe_allow_html=True)

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # ── ACL and freshness — plain language summaries ──────────────────────────
    st.markdown(
        "<div style='font-size:12px;color:var(--color-text-secondary);margin-bottom:10px'>"
        "ACL filtering and freshness logic are automatically applied at query time — "
        "before the semantic search even runs. Here is how each works conceptually."
        "</div>",
        unsafe_allow_html=True,
    )

    with st.expander("**How ACL filtering works — keeping results within permission boundaries**"):
        st.markdown("""
<div style="font-size:12px;color:var(--color-text-secondary);line-height:1.75;padding:4px 0">

When a user submits a query, the system knows their identity — their role (analyst, manager, executive),
their department (finance, HR, legal), and their clearance level. Before running any vector search,
the system applies a filter that excludes all chunks the user is not allowed to see.

This means a junior analyst asking "what is our Q4 strategy?" will never surface an executive-only
strategy document — even if that document is semantically the closest match. The filtering happens
server-side, invisible to the user and to the language model. The model only ever receives chunks
that passed the permission check.

This is not optional in regulated industries. Healthcare, finance, and legal systems are legally
required to enforce access controls at the data layer — not just at the UI layer.

</div>
""", unsafe_allow_html=True)

    with st.expander("**How freshness filtering works — surfacing current information**"):
        st.markdown("""
<div style="font-size:12px;color:var(--color-text-secondary);line-height:1.75;padding:4px 0">

When a query contains words like "latest," "current," "recent," or "new," the system automatically
adds a date-range filter. Instead of searching all chunks, it restricts results to chunks updated
within the last 180 days (or a configurable window). This prevents a semantically strong but
outdated chunk from ranking above a current one.

Separately, a background job watches all chunks and flags any not updated in 90+ days as stale.
Those chunks are queued for re-indexing — so when the source document gets updated, the knowledge
base stays current.

The key design principle: metadata updates must always happen alongside content re-indexing.
Updating document text without refreshing the updated_at timestamp means the system will still
treat the chunk as stale.

</div>
""", unsafe_allow_html=True)

    st.markdown("---")

    # ── Enterprise vector stores — plain language ─────────────────────────────
    st.markdown("**How enterprise vector stores handle metadata filtering**")
    st.markdown(
        "<div style='font-size:12px;color:var(--color-text-secondary);margin-bottom:12px'>"
        "All major vector databases support metadata filtering natively. "
        "The pattern is the same everywhere: attach metadata fields at ingestion, "
        "then reference those fields as filter conditions at query time. "
        "The filter runs before the vector search — so the search space shrinks "
        "before any similarity calculation happens."
        "</div>",
        unsafe_allow_html=True,
    )

    filter_cards = [
        (
            "Pinecone",
            "Each chunk is stored with metadata fields alongside its vector. At query time you pass "
            "a filter condition (e.g., document_type = evaluation_framework) in the same request as "
            "the vector. Pinecone applies the filter first — only matching chunks are candidates for "
            "similarity ranking.",
        ),
        (
            "Weaviate",
            "Weaviate uses a where-filter alongside the vector query. The filter is a structured "
            "condition (field, operator, value). Like Pinecone, the filter narrows the search corpus "
            "before semantic ranking runs — not after.",
        ),
        (
            "AWS Knowledge Base / pgvector",
            "AWS Knowledge Base accepts filter configurations in the retrieve call. pgvector, "
            "which runs inside PostgreSQL, applies a standard SQL WHERE clause before computing "
            "vector distances — the classic SQL filter pattern, applied to vector search.",
        ),
        (
            "Query classifier — deciding when to filter",
            "No system filters every query. A lightweight classifier reads the user's intent first. "
            "Evaluation questions trigger a document_type filter. Broad conceptual questions get no "
            "filter — the full corpus is searched. The classifier prevents over-filtering, which "
            "would collapse results to zero.",
        ),
    ]

    for title, body in filter_cards:
        st.markdown(
            f"<div style='border-left:3px solid rgba(0,0,0,0.12);border-radius:0 8px 8px 0;"
            f"padding:10px 14px;margin-bottom:8px;font-size:12px;line-height:1.7;"
            f"background:var(--color-background-secondary);color:var(--color-text-secondary)'>"
            f"<strong style='color:var(--color-text-primary)'>{title}</strong><br>{body}</div>",
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # ── PM Decision Matrix ────────────────────────────────────────────────────
    rows_data = [
        (
            "What metadata builds user trust?",
            "Does your RAG answer show sources? Will users trust citations without knowing where they came from?",
            "Define citation fields at ingestion — at minimum, source name. Add date, author, and section for sensitive use cases.",
            "We show only the source document title as a citation and nothing else. A non-technical PM has no way to tell whether a chunk came from a peer-reviewed paper or a blog post — we never added a source type field.",
            "Source field (document title) shown as citation in search results.",
            "Author, confidence score, source URL, publication date, section — surfaced per result.",
        ),
        (
            "What metadata improves retrieval?",
            "Are users getting off-topic or stale results? Can a filter narrow the corpus before ranking?",
            "Add filter fields: document type, recency, department, content flags (has_tables, has_code).",
            "We defined a document_type field but never wired it to query filtering. A user asking 'how do I evaluate RAG?' gets results from all 5 documents — there's no automatic routing to the RAGAS docs where the answer actually lives.",
            "9 structural fields: doc_type, has_tables, has_code, chunk_position, section — used as pre-filters in the demo.",
            "50+ fields including owner, department, product line, geography — pre-filtering reduces corpus from millions to thousands.",
        ),
        (
            "Who generates the metadata?",
            "Do you have editors who can tag manually? Or is volume too large for human review?",
            "If volume is high, build auto-tagging at ingestion — LLM or NLP model extracts type, entities, and topics from content.",
            "We auto-generated metadata using heuristic rules at chunk time but never verified them. The has_tables and has_citations fields were set by pattern matching, not spot-checked against actual chunk content.",
            "Auto-generated at chunk time: content detection for has_tables/has_code/has_citations, document properties for source and type.",
            "Auto-tagging pipelines (Amazon Comprehend, Azure AI) run at ingestion, with human review queues for low-confidence tags.",
        ),
        (
            "How do you handle stale metadata?",
            "When a document is updated, does its metadata update automatically? Can a user trust a result labelled 'current'?",
            "Build metadata sync alongside content re-indexing. Updating text without refreshing updated_at is a silent failure.",
            "created_at and updated_at exist in the schema but are empty strings in every chunk. If we add a newer version of a document, there's no way to distinguish it from the old one — freshness filtering is broken by design.",
            "created_at and updated_at fields defined in schema but not populated. No staleness detection runs in this app.",
            "Freshness daemon runs nightly — stale chunks (>90 days unchanged) are flagged and queued for re-indexing automatically.",
        ),
        (
            "What does the user actually see?",
            "Do users understand why a result appeared? Can they evaluate trustworthiness without reading the full document?",
            "Surface metadata in the result card: source, date, section, type. Transparency increases confidence and reduces over-reliance.",
            "Users see only the source document title in search results — no type, no date, no section. We never asked what minimum provenance a learner needs to trust a retrieved answer.",
            "Source document title shown as citation. No section, date, or type visible to the user in this app.",
            "Source, date, section, author, confidence score, and department surfaced per result — provenance at a glance.",
        ),
    ]

    render_pm_matrix("Metadata Tagging", rows_data)

    render_what_we_built(
        "We tag each chunk right after chunking — before embedding — with 15 metadata fields: "
        "structural (source, type, section, code/table/citation flags, position, word count, timestamp), "
        "access control (allowed_roles, department, clearance_level), "
        "and freshness (created_at, updated_at, version). "
        "In production, ACL filters run server-side before vector search, "
        "and recency filters activate automatically for queries about 'latest' or 'current' content."
    )
    render_enterprise_note(
        "Enterprise metadata schemas are far richer — at Glean, every indexed document carries 50+ fields "
        "including owner, department, access control list, last modified, view count, and business unit. "
        "AWS Knowledge Base and Azure AI Search support metadata filtering natively — queries filter on any "
        "field before semantic search runs, reducing search corpus from millions to thousands in milliseconds. "
        "Temporal metadata is critical in fast-moving domains — financial RAG systems tag every chunk with "
        "fiscal quarter and automatically deprioritize chunks older than two quarters. "
        "Auto-tagging pipelines use LLMs to extract metadata at ingestion — Amazon Comprehend and "
        "Azure Cognitive Services do this at scale without manual labeling."
    )
    render_risk_table(RISKS)
    render_nav(next_label="Next: Embedding →", pipeline="offline", back=True)
