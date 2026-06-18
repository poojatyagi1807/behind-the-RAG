"""
Config — recommended queries and pre-calculated dropdown content.
"""

RECOMMENDED_QUERIES = [
    "How does RAG prevent hallucination?",
    "What is the difference between sparse and dense embeddings?",
    "How does chunking strategy affect retrieval quality?",
    "What metrics should I use to evaluate a RAG system?",
    "How does re-ranking improve retrieval precision?",
    "What is HyDE and when should I use it?",
    "How do enterprises handle knowledge base updates in RAG?",
    "What is lost in the middle and how do I fix it?",
]

# Pre-calculated results for offline pipeline dropdowns
LOADER_COMPARISON = {
    "simple_text": {
        "label": "Simple text loader",
        "description": "Fetches raw text, strips basic HTML. Fast, loses structure.",
        "loses": ["Table structure", "Code formatting", "Figure references"],
        "keeps": ["Prose content", "Basic paragraphs"],
        "enterprise_tool": "Basic web scraper / urllib",
    },
    "pdf_aware": {
        "label": "PDF-aware parser",
        "description": "Preserves tables, headers, multi-column layouts.",
        "loses": ["Scanned images", "Handwritten text"],
        "keeps": ["Tables as structured data", "Section headers", "Formatted lists"],
        "enterprise_tool": "AWS Textract, Azure Document Intelligence",
    },
    "html_scraper": {
        "label": "HTML scraper",
        "description": "Strips tags, preserves semantic structure and heading hierarchy.",
        "loses": ["JavaScript-rendered content", "Dynamic elements"],
        "keeps": ["Heading hierarchy", "Semantic structure", "Link context"],
        "enterprise_tool": "BeautifulSoup, Unstructured.io",
    },
    "code_aware": {
        "label": "Code-aware loader",
        "description": "Separates code blocks from prose, preserves syntax.",
        "loses": ["Some inline formatting"],
        "keeps": ["Code blocks intact", "Function signatures", "Docstrings"],
        "enterprise_tool": "AST-aware parser, GitHub Copilot loader",
    },
}

CLEANING_COMPARISON = {
    "standard": {
        "label": "Standard cleaning",
        "description": "Strip citations, clean whitespace, extract basic metadata.",
        "removes": ["[1][2] citations", "Excessive whitespace", "HTML tags"],
        "keeps": ["Code blocks", "Tables", "Section headers"],
    },
    "aggressive": {
        "label": "Aggressive cleaning",
        "description": "Remove all formatting, citations, headers — plain text only.",
        "removes": ["All citations", "All headers", "Code blocks → [CODE BLOCK]", "Tables → [TABLE]"],
        "keeps": ["Core prose content only"],
    },
    "structure_preserving": {
        "label": "Structure-preserving",
        "description": "Keep tables, code, headers as rich metadata.",
        "removes": ["Noise whitespace only"],
        "keeps": ["All structure", "Code blocks", "Tables as JSON", "Headers"],
    },
}

CHUNKING_SCENARIOS = {
    "fixed_token": {
        "abstract": "Uniform documents, quick prototyping, tight latency budget.",
        "scenario": "A startup building RAG over 10,000 customer support tickets needs it live by Friday. Every ticket is roughly the same length. Fixed token gets to 80% quality in one afternoon.",
        "avoid": "Documents with clear semantic boundaries — you will split important sentences.",
    },
    "recursive": {
        "abstract": "Mixed document lengths, general purpose RAG, most production systems.",
        "scenario": "Notion's help center has articles from 200 to 8,000 words. Recursive handles both without manual rules per article type. This is why it is the default in LangChain.",
        "avoid": "Very long sentences that carry multiple ideas — misses cross-sentence context.",
    },
    "semantic": {
        "abstract": "High accuracy requirements, complex multi-part questions, premium products.",
        "scenario": "Goldman Sachs builds an internal research assistant over 50,000 analyst reports. Questions are complex, high stakes. Wrong answer costs credibility. Semantic chunking is worth the extra compute and indexing time.",
        "avoid": "Real-time indexing required — too slow for streaming ingestion.",
    },
    "hierarchical": {
        "abstract": "Structured documents — legal contracts, technical specs, research papers.",
        "scenario": "A law firm indexes 20 years of contracts. A lawyer asks 'what are the termination clauses in our enterprise agreements?' Parent chunk retrieves the right contract section. Child chunk retrieves the exact clause. One query, two levels of precision.",
        "avoid": "Unstructured documents with no clear hierarchy — creates meaningless parent chunks.",
    },
}

EMBEDDING_COMPARISON = {
    "google_te4": {
        "label": "Google text-embedding-004",
        "type": "Dense",
        "dims": "768",
        "understands": "Semantic meaning, paraphrase, context, multilingual",
        "struggles": "Very niche domain jargon without fine-tuning",
        "cost": "Free tier — Gemini API key required",
        "best_for": "Production-quality RAG with Google ecosystem",
    },
    "tfidf": {
        "label": "TF-IDF",
        "type": "Sparse",
        "dims": "50K+",
        "understands": "Exact keywords, domain terms",
        "struggles": "Synonyms, paraphrasing, semantic meaning",
        "cost": "Free — local",
        "best_for": "Quick prototyping, structured documents",
    },
    "openai": {
        "label": "OpenAI text-embedding-3-small",
        "type": "Dense",
        "dims": "1,536",
        "understands": "Meaning behind words, paraphrase, context",
        "struggles": "Very domain-specific jargon without fine-tuning",
        "cost": "$0.02 / 1M tokens",
        "best_for": "General purpose production RAG",
    },
    "cohere": {
        "label": "Cohere embed-english-v3",
        "type": "Dense",
        "dims": "1,024",
        "understands": "Meaning, context, grounding, multilingual",
        "struggles": "Cost at very high volume",
        "best_for": "Enterprise multilingual, high precision",
        "cost": "$0.10 / 1M tokens",
    },
    "sentence_transformers": {
        "label": "all-MiniLM-L6-v2 (Sentence Transformers)",
        "type": "Dense",
        "dims": "384",
        "understands": "Semantic meaning, paraphrase, context",
        "struggles": "Long documents, rare technical terms",
        "cost": "Free — local, no API key required",
        "best_for": "Self-hosted RAG, no API key needed — used in this app",
        "active": True,
    },
}

INDEX_COMPARISON = {
    "flat": {
        "label": "Flat index",
        "definition": "Compares the query vector against every single chunk, one by one. No shortcuts — brute force exact search.",
        "accuracy": "100%",
        "speed": "Slow at scale",
        "memory": "High",
        "scale": "< 100K chunks",
        "best_for": "Testing, benchmarking, truth baseline",
    },
    "hnsw": {
        "label": "HNSW — Hierarchical Navigable Small World",
        "definition": "Builds a layered graph of vectors. Search starts at the top (few nodes, long jumps) and drills down layer by layer to find the nearest chunk. Skips most comparisons.",
        "accuracy": "95-99%",
        "speed": "Fast",
        "memory": "Medium",
        "scale": "< 50M chunks",
        "best_for": "Production default — best recall vs speed ratio",
    },
    "ivf": {
        "label": "IVF — Inverted File Index",
        "definition": "Clusters all vectors into buckets at build time. At query time, only searches the nearest clusters — ignores the rest entirely.",
        "accuracy": "85-95%",
        "speed": "Fastest",
        "memory": "Low",
        "scale": "50M+ chunks",
        "best_for": "Billion-scale corpora, memory-constrained",
    },
}

METADATA_SCHEMA = [
    {"field": "chunk_id", "example": "rag_paper_chunk_047", "purpose": "Unique identifier for tracing"},
    {"field": "source", "example": "Lewis et al. RAG Paper (arXiv:2005.11401)", "purpose": "Attribution and citation"},
    {"field": "document_type", "example": "research_paper", "purpose": "Filter by content type"},
    {"field": "section", "example": "Results — Open Domain QA", "purpose": "Filter by document section"},
    {"field": "has_code", "example": "False", "purpose": "Route code queries to code chunks"},
    {"field": "has_tables", "example": "True", "purpose": "Find structured comparative data"},
    {"field": "has_citations", "example": "True", "purpose": "Identify academic vs practical sources"},
    {"field": "chunk_position", "example": "middle", "purpose": "Prefer early/late for context-setting"},
    {"field": "word_count", "example": "187", "purpose": "Token budget planning"},
    # Access control
    {"field": "allowed_roles", "example": '["analyst", "manager", "executive"]', "purpose": "Row-level security — chunk only returned if querying user's role is in this list"},
    {"field": "department", "example": '"finance"', "purpose": "Department-scoped retrieval — HR queries only surface HR-owned chunks"},
    {"field": "clearance_level", "example": "2", "purpose": "Numeric clearance gate — chunk only retrieved if user clearance ≥ chunk level"},
    # Freshness & versioning
    {"field": "created_at", "example": '"2024-11-01T09:30:00Z"', "purpose": "Prefer recent chunks when recency matters — date-range filter at query time"},
    {"field": "updated_at", "example": '"2025-03-15T14:22:00Z"', "purpose": "Detect stale content — flag chunks not updated in N days for re-indexing"},
    {"field": "version", "example": '"v2.1"', "purpose": "Multi-version knowledge bases — filter to specific policy or product version"},
]
