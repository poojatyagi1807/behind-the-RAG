"""
Document loader — loads all 5 KB documents on first run.
Called from the online pipeline steps that need retrieval.
"""

import os
import streamlit as st
from knowledge_base.kb import build_knowledge_base, DOCUMENTS
from state import embed_text


def _maybe_build_hnsw(chunks):
    """
    Build usearch HNSW index if embeddings are ready and index not yet built.
    Called on both the early-return path and the full-build path so HNSW is
    never missed due to a cached early return.
    """
    if (
        st.session_state.get("kb_embeddings_loaded")
        and not st.session_state.get("kb_hnsw")
        and chunks
        and len(getattr(chunks[0], "embedding", [])) > 0
    ):
        try:
            from usearch.index import Index as USearchIndex
            import numpy as np
            dim = len(chunks[0].embedding)
            hnsw = USearchIndex(ndim=dim, metric="cos")
            vectors = np.array([c.embedding for c in chunks], dtype=np.float32)
            keys = np.arange(len(chunks), dtype=np.int64)
            hnsw.add(keys, vectors)
            st.session_state.kb_hnsw = hnsw
        except Exception:
            pass  # usearch unavailable — search falls back to brute-force cosine


def load_knowledge_base():
    """
    Load all 5 documents, embed with fastembed, build HNSW index.
    Stores everything in session state — only runs once per session.
    """
    if st.session_state.get("kb_loaded") and st.session_state.get("kb_chunks"):
        # KB already built — still attempt HNSW in case it wasn't ready last time
        _maybe_build_hnsw(st.session_state.kb_chunks)
        return st.session_state.kb_chunks, st.session_state.kb_tfidf

    kb_dir = os.path.dirname(__file__)
    file_map = {
        "rag_paper": "rag_paper.txt",
        "langchain_docs": "langchain_docs.txt",
        "lilian_weng": "lilian_weng.txt",
        "ragas_docs": "ragas_docs.txt",
        "pinecone_guide": "pinecone_guide.txt",
    }

    raw_texts = {}
    missing = []
    for doc_id, filename in file_map.items():
        filepath = os.path.join(kb_dir, filename)
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                raw_texts[doc_id] = f.read()
        else:
            missing.append(filename)

    if missing:
        st.warning(f"Missing knowledge base files: {', '.join(missing)}")

    if not raw_texts:
        return [], None

    chunking = st.session_state.get("selected_chunking", "fixed_token")
    cleaning = st.session_state.get("selected_cleaning", "standard")

    chunks, index = build_knowledge_base(raw_texts, chunking, cleaning)
    st.session_state.kb_chunks = chunks
    st.session_state.kb_tfidf = index
    st.session_state.kb_loaded = True

    # Batch-embed all chunks with all-MiniLM-L6-v2 (local, no API key needed).
    # Runs once per session — kb_embeddings_loaded flag prevents re-embedding on reruns.
    if not st.session_state.get("kb_embeddings_loaded"):
        embedded = 0
        last_provider = None
        for chunk in chunks:
            vec, provider = embed_text(chunk.text)
            if vec is None:
                break   # Package unavailable — stop, leave all embeddings empty
            chunk.embedding = vec
            chunk.embedding_model = provider
            last_provider = provider
            embedded += 1
        if embedded == len(chunks) and chunks:
            st.session_state.kb_embeddings_loaded = True
            st.session_state.kb_embedding_provider = last_provider or "local"

    # Build HNSW index from neural embeddings.
    _maybe_build_hnsw(chunks)

    return chunks, index
