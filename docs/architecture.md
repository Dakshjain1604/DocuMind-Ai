# DocuMind Architecture

This document provides a high-level overview of the architectural design and components of DocuMind, a Hybrid GraphRAG document intelligence platform.

## 1. System Overview

DocuMind consists of two main independent services:

1.  **Frontend**: A Next.js 15 application (`frontend/`) using React, Tailwind CSS, and shadcn-ui. It acts as the presentation layer, handling user authentication, session management, and driving the various visualization consoles (chat, graph view, masterclass, etc.).
2.  **Backend**: A Python FastAPI microservice (`microService/`). It serves as the core engine handling document ingestion, orchestration of LLM requests, knowledge graph extraction, and hybrid retrieval.

The two systems communicate purely via REST APIs and Server-Sent Events (SSE) for streaming operations.

## 2. Core Workflows

### 2.1 Indexing Pipeline (`POST /index`)
The backend provides a content-addressed ingestion pipeline.
1.  **Deduplication**: Files are SHA-256 hashed on upload. If a hash already exists, the pipeline halts and returns the existing index reference.
2.  **Chunking**: Hierarchical chunking creates large parent sections and smaller child chunks. This supports "small-to-big" retrieval where semantic search matches a granular child chunk, but the LLM is fed the broader parent context.
3.  **Parallel Processing**:
    *   **Embeddings**: Chunks are embedded and stored in a local ChromaDB collection.
    *   **Graph Extraction**: An LLM extracts entities and relations from a sample of parent chunks. These are materialized as a NetworkX graph.
    *   **BM25 Corpus**: Text is tokenized and stored for keyword-based retrieval.
4.  **Community Detection**: Louvain algorithms partition the graph into communities, and an LLM summarizes each community to establish macro-level document context.
5.  **Persistence**: The state is serialized to disk (`local_chroma/`, `graph.json`, `bm25_corpus.pkl`, `parents.json`).

### 2.2 Retrieval Pipeline (`POST /query`)
Retrieval uses a highly parallelized, hybrid search strategy.
1.  **Query Rewriting**: The raw user query undergoes HyDE (Hypothetical Document Embeddings) expansion, keyword extraction, and query variant generation.
2.  **Hybrid Search**: Four distinct retrieval strategies are executed in parallel:
    *   Vector search against Chroma (per variant)
    *   BM25 keyword search
    *   Knowledge graph traversal (finding entities that match the query and exploring neighbors)
    *   Community summary matching
3.  **Fusion**: Results from all strategies are merged using Weighted Reciprocal Rank Fusion (RRF) (k=60).
4.  **Reranking**: The fused list is passed through a Cross-Encoder to heavily prune irrelevant chunks.
5.  **Small-to-Big resolution**: Child chunks are swapped out for their corresponding parent chunks.
6.  **Answer Generation**: The final context is provided to the LLM, and the answer is streamed back to the frontend over SSE along with precise passage-level citations.

## 3. Observability and Tracing

DocuMind uses a built-in telemetry store (SQLite) to log every stage of the pipeline.
*   **Latencies**: Time spent in chunking, embedding, extraction, search, and generation.
*   **Token Usage**: Both prompt and completion tokens are tracked across OpenRouter/Groq calls.
*   **Context**: The actual chunks retrieved and utilized are saved.

This data is exposed via `GET /trace/{request_id}` and powers the frontend Telemetry dashboard.

## 4. Frontend Architecture

The Next.js frontend employs the App Router.
*   **App Shell**: `/Dashboard` acts as a protected layout gated by middleware.
*   **State**: The frontend communicates with the backend via API route proxies (`/api/rag/*`) to avoid CORS complexities and hide API keys if any were managed by the frontend (though currently managed by the backend).
*   **Components**: Complex interactive components (Force-directed graphs, markdown streaming, citation tooltips) are isolated in `app/components/`.

## 5. Deployment Considerations

*   **Stateful Services**: The backend relies on the local filesystem (`RAG_PERSIST_DIR`) for its index storage. In a distributed environment, this would need to be replaced with a managed vector database (like Pinecone or hosted Chroma) and a shared object store (S3).
*   **Concurrency**: By default, the app is geared towards single-tenant local usage. Multi-tenant isolation requires tenant IDs embedded into Chroma metadata and graph serialization.
