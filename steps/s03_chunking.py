"""Step 2 — Chunking."""
import streamlit as st
from ui import (render_topbar, render_step_header, render_thinking_card, render_pm_matrix,
                render_what_we_built, render_enterprise_note, render_risk_table, render_nav)

SAMPLE_PARAGRAPH = """Large pre-trained language models have been shown to store factual knowledge in their parameters. However, their ability to access and precisely manipulate knowledge is still limited. We explore retrieval-augmented generation — models which combine pre-trained parametric and non-parametric memory. The non-parametric memory is a dense vector index of Wikipedia, accessed with a pre-trained neural retriever."""

# Chunks per strategy — how the sample paragraph actually gets split
CHUNK_EXAMPLES = {
    "Fixed token + overlap": {
        "color": "#0F6E56",
        "rule": "Split every ~300 words. Each chunk overlaps the previous by ~75 tokens so no sentence is orphaned at a hard boundary.",
        "chunks": [
            ("Chunk 1", "Large pre-trained language models have been shown to store factual knowledge in their parameters. However, their ability to access and precisely manipulate"),
            ("Chunk 2 — overlaps chunk 1", "ability to access and precisely manipulate knowledge is still limited. We explore retrieval-augmented generation — models which combine pre-trained parametric"),
            ("Chunk 3 — overlaps chunk 2", "models which combine pre-trained parametric and non-parametric memory. The non-parametric memory is a dense vector index of Wikipedia, accessed with a pre-trained neural retriever."),
        ],
        "note": "Notice: chunk 2 starts mid-sentence ('ability to…'). The overlap preserves context across the boundary but the split point itself has no awareness of sentence structure.",
    },
    "Recursive": {
        "color": "#185FA5",
        "rule": "Try paragraph break → sentence break → token limit, in that order. Stop at the first natural boundary that fits the size budget.",
        "chunks": [
            ("Chunk 1 — ends at sentence boundary", "Large pre-trained language models have been shown to store factual knowledge in their parameters. However, their ability to access and precisely manipulate knowledge is still limited."),
            ("Chunk 2 — clean sentence boundary", "We explore retrieval-augmented generation — models which combine pre-trained parametric and non-parametric memory. The non-parametric memory is a dense vector index of Wikipedia, accessed with a pre-trained neural retriever."),
        ],
        "note": "Notice: both chunks end at a full stop. No mid-sentence splits. This is why Recursive is the safe default — it preserves readability without needing to understand meaning.",
    },
    "Semantic": {
        "color": "#854F0B",
        "rule": "Group sentences while their topic stays the same. Split when topic similarity drops below a threshold.",
        "chunks": [
            ("Chunk 1 — topic: LLM limitations", "Large pre-trained language models have been shown to store factual knowledge in their parameters. However, their ability to access and precisely manipulate knowledge is still limited."),
            ("Chunk 2 — topic: RAG approach", "We explore retrieval-augmented generation — models which combine pre-trained parametric and non-parametric memory."),
            ("Chunk 3 — topic: implementation detail", "The non-parametric memory is a dense vector index of Wikipedia, accessed with a pre-trained neural retriever."),
        ],
        "note": "Notice: the paragraph is split into 3 topic-coherent chunks instead of 2 size-based ones. Each chunk now answers a different question. More precise retrieval — but slower to build and harder to tune.",
    },
    "Hierarchical": {
        "color": "#534AB7",
        "rule": "Create one parent chunk summarising the full passage, then smaller child chunks for each detail. A query can match at either level.",
        "chunks": [
            ("Parent — full section summary", "Large pre-trained language models have been shown to store factual knowledge. We explore RAG combining parametric and non-parametric memory."),
            ("Child 1 — detail", "Large pre-trained language models have been shown to store factual knowledge in their parameters. However, their ability to access and precisely manipulate knowledge is still limited."),
            ("Child 2 — detail", "We explore retrieval-augmented generation — models which combine pre-trained parametric and non-parametric memory. The non-parametric memory is a dense vector index of Wikipedia."),
        ],
        "note": "Notice: the parent is a compressed summary — not a verbatim slice. A broad question matches the parent; a specific question matches the child. This doubles the chunk count but improves precision on structured documents.",
    },
}

RISKS = [
    {"risk": "Orphaned sentences", "example": '"Full refund if cancelled 5 days before" split — "5 days" in one chunk, "before check-in" in the next', "mitigation": "Overlap — each chunk shares 10-20% of tokens with adjacent chunks. Unstructured.io detects sentence boundaries before splitting"},
    {"risk": "Wrong strategy for document type", "example": "Semantic chunking on code — splits mid-function because topic shift detected inside a loop", "mitigation": "Content-type routing — detect document type at ingestion, apply matching chunking strategy automatically"},
    {"risk": "Chunk size mismatch", "example": "1,000 token chunks with embedding model trained on 512 tokens — later tokens underweighted", "mitigation": "Match chunk size to embedding model's optimal sequence length — OpenAI recommends 256-512 for text-embedding-3-small"},
    {"risk": "No versioning", "example": "Chunking strategy changed mid-production — old and new chunks coexist in index with incompatible boundaries", "mitigation": "Version your chunking config — tag every chunk with strategy and parameters. Re-index fully when strategy changes"},
]

BORDER = "1px solid rgba(0,0,0,0.12)"


def render():
    render_topbar()
    render_step_header("✂️", "Chunking",
        "The most important decision in the offline pipeline. Where you cut changes everything that follows.")

    render_thinking_card(
        "Cut too small — each chunk loses context. Cut too large — each chunk contains too much. "
        "There is no universally correct chunk size. The right strategy depends on your document "
        "structure, embedding model, and the types of questions your users ask.",
        pipeline="offline"
    )

    # ── Sample paragraph ──────────────────────────────────────────────────────
    st.markdown("**The same paragraph, split four different ways — pick a strategy to see exactly where it cuts:**")
    st.markdown(f"""
<div style="background:var(--color-background-secondary);border-radius:8px;
padding:12px 16px;font-size:12px;color:var(--color-text-secondary);margin-bottom:12px;
font-style:italic;line-height:1.7;border-left:3px solid #888">
{SAMPLE_PARAGRAPH}
</div>
""", unsafe_allow_html=True)

    # ── Tab-per-strategy chunk examples ──────────────────────────────────────
    tabs = st.tabs(list(CHUNK_EXAMPLES.keys()))
    for tab, (strategy, data) in zip(tabs, CHUNK_EXAMPLES.items()):
        with tab:
            st.markdown(f"""
<div style="font-size:11px;color:var(--color-text-secondary);padding:8px 0 10px 0;
border-bottom:{BORDER};margin-bottom:12px">
  <strong>Rule:</strong> {data['rule']}
</div>
""", unsafe_allow_html=True)
            for label, text in data["chunks"]:
                st.markdown(f"""
<div style="border-left:3px solid {data['color']};background:var(--color-background-secondary);
border-radius:0 6px 6px 0;padding:8px 12px;margin-bottom:8px">
  <div style="font-size:10px;font-weight:700;color:{data['color']};
  margin-bottom:4px;text-transform:uppercase;letter-spacing:.04em">{label}</div>
  <div style="font-size:12px;color:var(--color-text-primary);line-height:1.65">{text}</div>
</div>
""", unsafe_allow_html=True)
            st.markdown(f"""
<div style="font-size:11px;color:var(--color-text-tertiary);font-style:italic;
padding:8px 10px;background:var(--color-background-secondary);border-radius:6px;
border-left:3px solid {data['color']}40">
  💡 {data['note']}
</div>
""", unsafe_allow_html=True)

    st.markdown("---")

    # ── Strategy comparison table ─────────────────────────────────────────────
    st.markdown("**Strategy comparison — best for, avoid when, metric to watch:**")
    st.markdown(f"""
<style>
.st-row {{ display:grid;grid-template-columns:15% 20% 20% 20% 25%;width:100%;box-sizing:border-box }}
.st-row > div {{ padding:10px 12px;box-sizing:border-box;line-height:1.6;font-size:11px;
                color:var(--color-text-primary) }}
</style>
<div style="border-radius:8px;overflow:hidden;border:{BORDER};font-family:sans-serif">
  <div class="st-row" style="background:var(--color-background-primary);
  border-bottom:{BORDER}">
    <div style="font-weight:700;color:var(--color-text-secondary)">Strategy</div>
    <div style="font-weight:700;color:var(--color-text-secondary)">Best for</div>
    <div style="font-weight:700;color:var(--color-text-secondary)">Avoid when</div>
    <div style="font-weight:700;color:var(--color-text-secondary)">Metric to watch</div>
    <div style="font-weight:700;color:var(--color-text-secondary)">Real scenario</div>
  </div>
  <div class="st-row" style="background:var(--color-background-secondary)">
    <div style="font-weight:600;border-left:3px solid #0F6E56;padding-left:10px">Fixed token + overlap</div>
    <div>Uniform docs, quick prototyping, tight latency budget</div>
    <div>Legal or medical docs where mid-sentence splits break meaning</div>
    <div>Orphan rate · Overlap %</div>
    <div>Startup RAG over 10K support tickets — consistent length, needs to ship by Friday</div>
  </div>
  <div class="st-row" style="background:var(--color-background-primary)">
    <div style="font-weight:600;border-left:3px solid #185FA5;padding-left:10px">Recursive</div>
    <div>Mixed document lengths, general purpose RAG, most production systems</div>
    <div>Very long sentences carrying multiple ideas</div>
    <div>Avg chunk size variance · Orphan rate</div>
    <div>Notion help center — articles from 200 to 8,000 words. Default in LangChain.</div>
  </div>
  <div class="st-row" style="background:var(--color-background-secondary)">
    <div style="font-weight:600;border-left:3px solid #854F0B;padding-left:10px">Semantic</div>
    <div>High accuracy requirements, complex multi-part questions, premium products</div>
    <div>Real-time indexing — too slow for streaming ingestion</div>
    <div>Coherence score · Chunk size variance</div>
    <div>Goldman Sachs internal research assistant — wrong answer costs credibility</div>
  </div>
  <div class="st-row" style="background:var(--color-background-primary)">
    <div style="font-weight:600;border-left:3px solid #534AB7;padding-left:10px">Hierarchical</div>
    <div>Structured docs — legal contracts, technical specs, research papers</div>
    <div>Unstructured text with no clear hierarchy — creates meaningless parents</div>
    <div>Retrieval recall at parent vs child level</div>
    <div>Law firm — parent retrieves contract section, child retrieves exact clause</div>
  </div>
</div>
""", unsafe_allow_html=True)

    # ── What metrics to evaluate chunking quality ─────────────────────────────
    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
    st.markdown("**What to measure when comparing strategies on your documents:**")
    st.markdown(f"""
<div style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:10px;margin-top:4px">
  <div style="background:var(--color-background-secondary);border-radius:8px;
  padding:12px 14px;border:{BORDER}">
    <div style="font-size:11px;font-weight:700;color:var(--color-text-primary);margin-bottom:5px">
      Coherence score</div>
    <div style="font-size:11px;color:var(--color-text-secondary);line-height:1.6">
      Does each chunk express a complete thought? Sample 50 chunks, rate 1–5.
      Target avg ≥ 3.5 before moving to embedding.</div>
  </div>
  <div style="background:var(--color-background-secondary);border-radius:8px;
  padding:12px 14px;border:{BORDER}">
    <div style="font-size:11px;font-weight:700;color:var(--color-text-primary);margin-bottom:5px">
      Orphan rate</div>
    <div style="font-size:11px;color:var(--color-text-secondary);line-height:1.6">
      % of chunks that start or end mid-sentence. Target &lt;5% for factual domains.</div>
  </div>
  <div style="background:var(--color-background-secondary);border-radius:8px;
  padding:12px 14px;border:{BORDER}">
    <div style="font-size:11px;font-weight:700;color:var(--color-text-primary);margin-bottom:5px">
      Retrieval recall @ K</div>
    <div style="font-size:11px;color:var(--color-text-secondary);line-height:1.6">
      For a test set of known Q&amp;A pairs, does the right chunk appear in top-K?
      Run before and after changing strategy.</div>
  </div>
  <div style="background:var(--color-background-secondary);border-radius:8px;
  padding:12px 14px;border:{BORDER}">
    <div style="font-size:11px;font-weight:700;color:var(--color-text-primary);margin-bottom:5px">
      Chunk size variance</div>
    <div style="font-size:11px;color:var(--color-text-secondary);line-height:1.6">
      Wide variance (50–2,000 tokens) signals inconsistent splitting.
      Tight variance = more predictable embedding quality.</div>
  </div>
</div>
""", unsafe_allow_html=True)

    st.markdown("---")

    # ── PM Decision matrix ────────────────────────────────────────────────────
    render_pm_matrix("Chunking Strategy", [
        ("What is your user asking?",
         "Is your user looking for a single fact, a summary, or multi-step reasoning?",
         "Define top 5 user query types before deciding chunk strategy.",
         "Notion's AI gives truncated answers because chunks were optimised for search not summarisation.",
         "Explanatory queries only — users explore RAG concepts, not factual lookups.",
         "Run query log analysis on 1000+ real questions, segment by intent before chunking."),
        ("How structured is your content?",
         "Are all your documents consistent in format or wildly mixed?",
         "Map content types first — FAQs, contracts, emails, code each need a different strategy.",
         "Salesforce KB chunked support articles and code docs the same way — code answers came back broken mid-function.",
         "5 curated public docs, all plain text — single fixed-token strategy works across all.",
         "Each content type gets its own chunking pipeline with separate config and testing."),
        ("Does chunk boundary affect trust?",
         "If an answer is cut mid-sentence, does your user lose confidence?",
         "Define a boundary rule — chunk at paragraph or section level, never mid-sentence.",
         "A legal RAG tool returned half a contract clause — lawyers flagged it as unusable immediately.",
         "400-token budget, 75-token overlap, word-based split — boundaries not sentence-aware.",
         "Boundary rules defined in a shared config file, reviewed by PM and legal before deployment."),
        ("What metadata travels with the chunk?",
         "Does your user need source, date, author, or section to trust the answer?",
         "Decide metadata schema before ingestion — retrofitting it later is expensive.",
         "ServiceNow's AI showed answers without document dates — agents couldn't tell if the policy was current.",
         "9 fields: source, doc_type, section, has_code/tables/citations, chunk_position, word_count, indexed_at.",
         "Schema includes source, author, date, department, access tier — signed off by PM, security, and data governance."),
        ("Who validates chunk quality?",
         "Can an engineer alone tell if a chunk makes semantic sense in your domain?",
         "Assign a domain expert to review sample chunks before pipeline goes to production.",
         "A healthcare RAG chunked clinical guidelines mid-criteria — doctors got incomplete dosage instructions.",
         "Self-validated by the builder — curated docs make sense as plain text chunks.",
         "Subject matter expert assigned per content type with formal sign-off before pipeline moves to production."),
    ])

    st.markdown("---")

    render_what_we_built(
        "We used fixed token chunking with 400 token size and 75 token overlap — simple, "
        "fast, and good enough for our learning knowledge base."
    )
    render_enterprise_note(
        "Most production RAG systems use recursive character text splitting as their default — "
        "LangChain's RecursiveCharacterTextSplitter is the most widely deployed chunking strategy today. "
        "For specialized document types, Unstructured.io handles 25+ file types with structure-aware chunking. "
        "LlamaIndex's HierarchicalNodeParser is used for structured documents like legal contracts at companies "
        "like Glean and Notion. Chunk size decisions are made empirically — enterprises run retrieval quality "
        "benchmarks across chunk sizes before choosing."
    )
    render_risk_table(RISKS)
    render_nav(next_label="Next: Metadata Tagging →", pipeline="offline")
