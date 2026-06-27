"""Glossary — key RAG terms explained in plain English."""
import streamlit as st

TERMS = [
    ("BM25", "retrieval",
     "A keyword-based ranking algorithm. Scores chunks by how often your query terms appear in them, weighted by how rare those terms are across the whole knowledge base. Fast, no AI needed, works great for exact-match searches. Named after 'Best Match 25' — the 25th iteration of the Okapi ranking function."),
    ("Chunking", "offline",
     "Splitting a long document into smaller pieces before embedding and indexing. You can't embed a 50-page PDF as one unit — the vector would average everything into meaningless noise. Chunks are typically 200–500 words with overlap between them so context isn't lost at boundaries."),
    ("Context window", "generation",
     "The maximum amount of text an LLM can 'see' at once. GPT-4o has a 128k token context window (~100k words). RAG systems fill part of that window with retrieved chunks, then ask the LLM to answer from those chunks only."),
    ("Cross-encoder", "retrieval",
     "A re-ranking model that reads the query and a candidate chunk together in one pass, scoring how relevant they are to each other. Much more accurate than bi-encoders but too slow to run on the full index — used only on the top 20–50 candidates after initial retrieval."),
    ("Dense retrieval", "retrieval",
     "Finding relevant chunks using semantic similarity between embedding vectors. A query about 'cost of running AI' will match a chunk about 'LLM inference pricing' even if none of those exact words overlap — because the embeddings are close in vector space. Contrast with sparse retrieval (BM25)."),
    ("Drift", "observability",
     "When your RAG pipeline gets gradually worse over time without any deliberate change. Three types: embedding drift (provider silently updates the model), data drift (the world changes but your knowledge base doesn't), and query drift (users start asking new types of questions you didn't design for)."),
    ("Embedding", "offline",
     "Converting text into a list of numbers (a vector) that captures its meaning. Similar texts produce vectors that are close together in space — so 'how do I reset my password' and 'forgot my login credentials' produce similar vectors even though the words don't match."),
    ("Faithfulness", "evaluation",
     "A RAGAS metric measuring what percentage of claims in the LLM's answer are traceable to the retrieved context. A faithfulness score of 0.90 means 90% of what the LLM said can be found in the chunks you gave it. Low faithfulness = hallucination."),
    ("Golden dataset", "evaluation",
     "A curated set of 100–200 real user questions with expert-validated ideal answers. Used as ground truth for offline evaluation — you run your pipeline against this fixed set before every release and compare RAGAS scores to detect regressions."),
    ("HyDE", "retrieval",
     "Hypothetical Document Embedding. Instead of embedding your raw query, you first ask an LLM to write a hypothetical answer to the question, then embed that. The hypothetical answer is longer, richer, and more specific — producing a better embedding that retrieves more relevant chunks. Especially useful for vague or short queries."),
    ("HNSW", "offline",
     "Hierarchical Navigable Small World — the standard algorithm for fast approximate nearest-neighbour search in vector databases. Builds a multi-layer graph where each node connects to its nearest neighbours. At query time, it navigates the graph to find the closest vectors without checking every single one. Used in Pinecone, Weaviate, usearch, and most production vector stores."),
    ("Hybrid search", "retrieval",
     "Combining dense (vector/semantic) search with sparse (BM25/keyword) search. Dense retrieval finds semantically similar content; BM25 finds exact keyword matches. Results are merged using RRF. Most enterprise RAG systems use hybrid search because each method catches what the other misses."),
    ("LLM-as-Judge", "evaluation",
     "Using a second LLM to evaluate the output of your RAG pipeline. The judge model scores the answer on dimensions like faithfulness, relevancy, and correctness. RAGAS is the most widely used framework for this. Key rule: never use the same model to evaluate its own output — self-evaluation inflates scores."),
    ("Metadata filtering", "retrieval",
     "Narrowing retrieval to chunks that match specific attributes before running vector search. Example: only retrieve chunks where document_type = 'policy' and department = 'HR'. Dramatically improves precision and enables access control (only return chunks the user is allowed to see)."),
    ("RAGAS", "evaluation",
     "Retrieval-Augmented Generation Assessment — the industry-standard framework for evaluating RAG pipelines. Measures 5 dimensions: faithfulness, answer relevancy, context precision, context recall, and answer correctness. Used at Spotify, NVIDIA, Databricks. Each metric pinpoints a different layer of the pipeline."),
    ("RAG", "core",
     "Retrieval-Augmented Generation. An AI architecture where the LLM does not answer from its training memory — it first retrieves relevant documents from a knowledge base, then generates an answer grounded in what it found. Dramatically reduces hallucination and keeps answers up to date."),
    ("Re-ranking", "retrieval",
     "A second-pass scoring step after initial retrieval. The vector search returns the top 20–50 candidates quickly but imprecisely. A re-ranker (usually a cross-encoder) re-scores those candidates more carefully, considering query and chunk together. Only the top 5–10 re-ranked results go to the LLM."),
    ("RLHF (in RAG)", "observability",
     "Reinforcement Learning from Human Feedback — in RAG context, using thumbs up/down signals, query retries, and citation clicks from real users to improve which chunks get retrieved and how they're ranked. Not the same as RLHF in LLM training (which adjusts model weights). RAG RLHF adjusts the retrieval layer based on what humans found useful."),
    ("RRF", "retrieval",
     "Reciprocal Rank Fusion — an algorithm for merging ranked lists from different retrieval methods (e.g. BM25 + dense search). Each result gets a score of 1/(rank + 60). Results appearing in multiple lists and at high ranks bubble to the top. Simple, parameter-free, and works well in practice."),
    ("Sandwich ordering", "generation",
     "A context assembly technique where the most relevant chunk goes first, less relevant chunks fill the middle, and the second-most-relevant chunk goes last. Exploits the 'lost in the middle' problem — LLMs pay more attention to the beginning and end of their context window. Patented by Anthropic."),
    ("Semantic similarity", "retrieval",
     "How 'close' two pieces of text are in meaning, measured by the distance between their embedding vectors. Cosine similarity is the most common metric — 1.0 means identical meaning, 0.0 means completely unrelated. RAG retrieval ranks chunks by semantic similarity to the query."),
    ("Sparse retrieval", "retrieval",
     "Finding relevant chunks using exact keyword matching, weighted by term frequency and rarity (TF-IDF, BM25). Fast, interpretable, no model needed. Misses synonyms and paraphrases. Usually combined with dense retrieval in hybrid search."),
    ("Top-K", "retrieval",
     "The number of chunks retrieved from the vector index per query. Typical values: 5–20. Higher K means more coverage but more noise in the context window and higher LLM cost. Lower K means faster, cheaper, but risks missing relevant information. A PM decision: what's the right trade-off for your domain?"),
    ("Vector database", "offline",
     "A database optimised for storing and searching embedding vectors. Unlike SQL databases that search by exact value, vector databases find the nearest neighbours to a query vector using approximate nearest-neighbour algorithms like HNSW. Examples: Pinecone, Weaviate, Qdrant, Chroma. This app uses usearch (lightweight, local)."),
]

CATEGORIES = {
    "core": ("🔍", "Core concept"),
    "offline": ("📦", "Offline pipeline"),
    "retrieval": ("🎯", "Retrieval"),
    "generation": ("⚡", "Generation"),
    "evaluation": ("📊", "Evaluation"),
    "observability": ("📡", "Observability"),
}

CATEGORY_COLORS = {
    "core": "#9B59B6",
    "offline": "#4285F4",
    "retrieval": "#0F6E56",
    "generation": "#BA7517",
    "evaluation": "#E24B4A",
    "observability": "#185FA5",
}


def render():
    st.markdown("""
<div style="margin-bottom:20px">
  <div style="font-size:22px;font-weight:600;color:var(--color-text-primary);margin-bottom:4px">
    📖 Glossary
  </div>
  <div style="font-size:13px;color:var(--color-text-tertiary)">
    Every RAG term used in this app — explained in plain English.
  </div>
</div>
""", unsafe_allow_html=True)

    # Filter by category
    all_cats = ["All"] + [CATEGORIES[k][1] for k in CATEGORIES]
    selected = st.selectbox("Filter by category", all_cats, label_visibility="collapsed")

    st.markdown("")

    for term, cat, definition in sorted(TERMS, key=lambda x: x[0]):
        cat_label = CATEGORIES[cat][1]
        if selected != "All" and cat_label != selected:
            continue
        icon, label = CATEGORIES[cat]
        color = CATEGORY_COLORS[cat]
        st.markdown(f"""
<div style="background:var(--color-background-secondary);border-radius:10px;
padding:14px 18px;margin-bottom:10px;border-left:3px solid {color}">
  <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">
    <span style="font-size:14px;font-weight:700;color:var(--color-text-primary)">{term}</span>
    <span style="font-size:10px;font-weight:600;color:{color};background:{color}18;
    padding:2px 7px;border-radius:4px">{icon} {label}</span>
  </div>
  <div style="font-size:12px;color:var(--color-text-secondary);line-height:1.7">{definition}</div>
</div>
""", unsafe_allow_html=True)

    st.markdown("---")
    if st.button("← Back", use_container_width=False):
        st.session_state.pop("show_glossary", None)
        st.rerun()
