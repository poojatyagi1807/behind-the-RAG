"""
Knowledge base — Behind The RAG
Loads 5 documents, chunks them, builds TF-IDF index.
All offline processing happens here.
"""

import re
import math
import time
import json
from collections import Counter
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import streamlit as st


# ── Document metadata ─────────────────────────────────────────────────────────

DOCUMENTS = [
    {
        "id": "rag_paper",
        "title": "RAG Paper — Lewis et al. 2020",
        "source": "arXiv:2005.11401",
        "type": "research_paper",
        "url": "https://arxiv.org/abs/2005.11401",
        "structure": "Dense academic prose, citations, equations",
        "enterprise_equivalent": "Research white paper / internal technical report",
    },
    {
        "id": "langchain_docs",
        "title": "LangChain RAG Tutorial",
        "source": "python.langchain.com",
        "type": "technical_docs",
        "url": "https://python.langchain.com/docs/tutorials/rag/",
        "structure": "Technical prose mixed with Python code blocks",
        "enterprise_equivalent": "Internal engineering wiki / runbook",
    },
    {
        "id": "lilian_weng",
        "title": "Lilian Weng — LLM Powered Agents",
        "source": "lilianweng.github.io",
        "type": "technical_blog",
        "url": "https://lilianweng.github.io/posts/2023-06-23-agent/",
        "structure": "Long narrative, headers, referenced figures",
        "enterprise_equivalent": "Internal knowledge base article / ADR",
    },
    {
        "id": "ragas_docs",
        "title": "RAGAS Evaluation Documentation",
        "source": "docs.ragas.io",
        "type": "evaluation_framework",
        "url": "https://docs.ragas.io",
        "structure": "Metric definitions, tables, short structured sections",
        "enterprise_equivalent": "QA framework documentation / evaluation runbook",
    },
    {
        "id": "pinecone_guide",
        "title": "Pinecone RAG Series",
        "source": "pinecone.io/learn/series/rag",
        "type": "enterprise_guide",
        "url": "https://www.pinecone.io/learn/retrieval-augmented-generation/",
        "structure": "Conversational explainer + deep technical chapters",
        "enterprise_equivalent": "Internal FAQ / customer-facing knowledge base",
    },
]


# ── Chunk dataclass ───────────────────────────────────────────────────────────

@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    doc_title: str
    doc_type: str
    source: str
    section: str
    text: str
    tokens: int
    has_code: bool
    has_tables: bool
    has_citations: bool
    chunk_position: str  # early / middle / late
    word_count: int
    embedding_model: str = "tfidf_v1"
    chunking_strategy: str = "fixed_token_overlap"
    indexed_at: str = ""
    # Access control
    allowed_roles: list = field(default_factory=list)   # empty = no restriction (public)
    department: str = ""
    clearance_level: int = 0                             # 0 = public
    # Freshness & versioning
    created_at: str = ""
    updated_at: str = ""
    version: str = ""
    tfidf_vector: List[float] = field(default_factory=list)
    embedding: List[float] = field(default_factory=list)   # neural embedding (text-embedding-004 when available)


# ── Text utilities ────────────────────────────────────────────────────────────

def _detect_code(text: str) -> bool:
    code_patterns = [
        r'```', r'import\s+\w+', r'def\s+\w+\(', r'pip\s+install',
        r'from\s+\w+\s+import', r'\w+\s*=\s*\w+\.\w+\(',
    ]
    return any(re.search(p, text) for p in code_patterns)


def _detect_tables(text: str) -> bool:
    return bool(re.search(r'\|.+\|.+\|', text))


def _detect_citations(text: str) -> bool:
    return bool(re.search(r'\[\d+\]|\(\w+\s+et\s+al\.|\(\w+,\s+\d{4}\)', text))


def _estimate_tokens(text: str) -> int:
    return int(len(text.split()) * 1.3)


def _clean_text(text: str, strategy: str = "standard") -> str:
    if strategy == "aggressive":
        text = re.sub(r'\[\d+\]', '', text)
        text = re.sub(r'\([\w\s]+et al\.,?\s*\d{4}\)', '', text)
        text = re.sub(r'#{1,6}\s+', '', text)
        text = re.sub(r'```[\w]*\n.*?```', '[CODE BLOCK]', text, flags=re.DOTALL)
        text = re.sub(r'\s+', ' ', text)
    elif strategy == "structure_preserving":
        text = re.sub(r'\[\d+\]', '', text)
        text = re.sub(r'\s{3,}', '\n\n', text)
    else:  # standard
        text = re.sub(r'\[\d+\]', '', text)
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'\s{3,}', '\n\n', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


# ── Chunking strategies ───────────────────────────────────────────────────────

def _chunk_fixed_token(text: str, chunk_size: int = 400, overlap: int = 75) -> List[str]:
    words = text.split()
    word_chunk = max(int(chunk_size / 1.3), 50)
    word_overlap = int(overlap / 1.3)
    chunks = []
    start = 0
    while start < len(words):
        end = min(start + word_chunk, len(words))
        chunk = " ".join(words[start:end])
        if len(chunk.strip()) > 50:
            chunks.append(chunk)
        start += word_chunk - word_overlap
        if end >= len(words):
            break
    return chunks


def _chunk_recursive(text: str) -> List[str]:
    paragraphs = re.split(r'\n\n+', text)
    chunks = []
    current = ""
    target = 350
    for para in paragraphs:
        sentences = re.split(r'(?<=[.!?])\s+', para)
        for sent in sentences:
            if len(current.split()) + len(sent.split()) < target:
                current += " " + sent
            else:
                if current.strip():
                    chunks.append(current.strip())
                current = sent
    if current.strip():
        chunks.append(current.strip())
    return [c for c in chunks if len(c.split()) > 20]


def _chunk_semantic(text: str) -> List[str]:
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks = []
    current_chunk = []
    current_topic = None
    topic_words_set = set()
    for sent in sentences:
        words = set(re.findall(r'\b[a-z]{4,}\b', sent.lower()))
        overlap = len(words & topic_words_set) if topic_words_set else 0
        total = len(words | topic_words_set) if topic_words_set else 1
        similarity = overlap / total
        if similarity < 0.15 and len(current_chunk) > 3:
            chunks.append(" ".join(current_chunk))
            current_chunk = [sent]
            topic_words_set = words
        else:
            current_chunk.append(sent)
            topic_words_set |= words
    if current_chunk:
        chunks.append(" ".join(current_chunk))
    return [c for c in chunks if len(c.split()) > 15]


def _chunk_hierarchical(text: str) -> List[Dict]:
    sections = re.split(r'\n#{1,3}\s+|\n\n(?=[A-Z])', text)
    result = []
    for i, section in enumerate(sections):
        if len(section.strip()) < 50:
            continue
        parent = section[:300].strip()
        children = _chunk_fixed_token(section, chunk_size=200, overlap=30)
        result.append({"parent": parent, "children": children, "section_idx": i})
    return result


# ── TF-IDF engine ─────────────────────────────────────────────────────────────

def _tokenize(text: str) -> List[str]:
    return re.findall(r'\b[a-z]{2,}\b', text.lower())


def build_tfidf_index(chunks: List[Chunk]) -> Dict:
    texts = [c.text for c in chunks]
    tokenized = [_tokenize(t) for t in texts]
    vocab = sorted(set(w for doc in tokenized for w in doc))
    vocab_index = {w: i for i, w in enumerate(vocab)}
    N = len(tokenized)

    df = Counter()
    for doc in tokenized:
        for w in set(doc):
            df[w] += 1

    def tfidf_vec(tokens):
        tf = Counter(tokens)
        vec = [0.0] * len(vocab)
        for w, count in tf.items():
            if w in vocab_index:
                tf_score = count / max(len(tokens), 1)
                idf_score = math.log((N + 1) / (df[w] + 1)) + 1
                vec[vocab_index[w]] = tf_score * idf_score
        norm = math.sqrt(sum(v * v for v in vec))
        return [v / norm for v in vec] if norm > 0 else vec

    vectors = [tfidf_vec(tok) for tok in tokenized]
    for i, chunk in enumerate(chunks):
        chunk.tfidf_vector = vectors[i]

    return {
        "vocab": vocab,
        "vocab_index": vocab_index,
        "vectors": vectors,
        "df": dict(df),
        "N": N,
    }


def tfidf_query_vector(query: str, index: Dict) -> List[float]:
    tokens = _tokenize(query)
    tf = Counter(tokens)
    vocab_index = index["vocab_index"]
    df = index["df"]
    N = index["N"]
    vec = [0.0] * len(index["vocab"])
    for w, count in tf.items():
        if w in vocab_index:
            tf_score = count / max(len(tokens), 1)
            idf_score = math.log((N + 1) / (df.get(w, 0) + 1)) + 1
            vec[vocab_index[w]] = tf_score * idf_score
    norm = math.sqrt(sum(v * v for v in vec))
    return [v / norm for v in vec] if norm > 0 else vec


def cosine_similarity(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    return round(dot, 4)


def search(query: str, chunks: List[Chunk], index: Dict, top_k: int = 10) -> List[Dict]:
    q_vec = tfidf_query_vector(query, index)
    scored = []
    for i, chunk in enumerate(chunks):
        score = cosine_similarity(q_vec, index["vectors"][i])
        scored.append({
            "chunk": chunk,
            "score": score,
            "rank": 0,
        })
    scored.sort(key=lambda x: x["score"], reverse=True)
    for i, item in enumerate(scored):
        item["rank"] = i + 1
    return scored[:top_k]


# ── Main KB builder ───────────────────────────────────────────────────────────

def build_knowledge_base(
    raw_texts: Dict[str, str],
    chunking_strategy: str = "fixed_token",
    cleaning_strategy: str = "standard",
) -> tuple:
    """
    Build chunks and TF-IDF index from raw document texts.
    Returns (chunks, index)
    """
    from datetime import datetime
    now = datetime.utcnow().isoformat() + "Z"

    all_chunks = []
    chunk_counter = 0

    for doc_meta in DOCUMENTS:
        doc_id = doc_meta["id"]
        raw_text = raw_texts.get(doc_id, "")
        if not raw_text:
            continue

        # Clean
        cleaned = _clean_text(raw_text, cleaning_strategy)

        # Chunk
        if chunking_strategy == "fixed_token":
            texts = _chunk_fixed_token(cleaned)
        elif chunking_strategy == "recursive":
            texts = _chunk_recursive(cleaned)
        elif chunking_strategy == "semantic":
            texts = _chunk_semantic(cleaned)
        elif chunking_strategy == "hierarchical":
            hier = _chunk_hierarchical(cleaned)
            texts = []
            for item in hier:
                texts.append(item["parent"])
                texts.extend(item["children"])
        else:
            texts = _chunk_fixed_token(cleaned)

        total = len(texts)
        for i, text in enumerate(texts):
            if not text.strip():
                continue
            pos = "early" if i < total * 0.33 else "late" if i > total * 0.66 else "middle"
            chunk = Chunk(
                chunk_id=f"{doc_id}_chunk_{chunk_counter:04d}",
                doc_id=doc_id,
                doc_title=doc_meta["title"],
                doc_type=doc_meta["type"],
                source=doc_meta["source"],
                section=_detect_section(text),
                text=text,
                tokens=_estimate_tokens(text),
                has_code=_detect_code(text),
                has_tables=_detect_tables(text),
                has_citations=_detect_citations(text),
                chunk_position=pos,
                word_count=len(text.split()),
                chunking_strategy=chunking_strategy,
                indexed_at=now,
            )
            all_chunks.append(chunk)
            chunk_counter += 1

    index = build_tfidf_index(all_chunks)
    return all_chunks, index


def _detect_section(text: str) -> str:
    lines = text.split('\n')
    for line in lines[:3]:
        line = line.strip()
        if line.startswith('#'):
            return line.lstrip('#').strip()[:60]
        if len(line) < 80 and line and line[-1] not in '.!?,;:':
            return line[:60]
    return "Content"


# ── Deduplication ─────────────────────────────────────────────────────────────

def deduplicate_chunks(
    chunks: List[Dict],
    threshold: float = 0.92,
    index: Dict = None,
) -> tuple:
    """
    Remove near-duplicate chunks from retrieval results.
    Returns (kept_chunks, removed_chunks, similarity_matrix)
    """
    kept = []
    removed = []
    similarity_log = []

    for i, item in enumerate(chunks):
        is_duplicate = False
        for kept_item in kept:
            if index and item["chunk"].tfidf_vector and kept_item["chunk"].tfidf_vector:
                sim = cosine_similarity(
                    item["chunk"].tfidf_vector,
                    kept_item["chunk"].tfidf_vector
                )
            else:
                sim = 0.0

            similarity_log.append({
                "chunk_a": kept_item["chunk"].chunk_id,
                "chunk_b": item["chunk"].chunk_id,
                "similarity": round(sim, 4),
                "threshold": threshold,
                "action": "remove" if sim >= threshold else "keep",
            })

            if sim >= threshold:
                is_duplicate = True
                removed.append({**item, "removed_reason": f"similarity {sim:.3f} >= threshold {threshold}"})
                break

        if not is_duplicate:
            kept.append(item)

    return kept, removed, similarity_log
