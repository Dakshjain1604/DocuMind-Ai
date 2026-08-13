# API Documentation

The backend service is a FastAPI application running on port 8000 by default. It provides REST and Server-Sent Event (SSE) endpoints.

## Base URL
`http://localhost:8000`

---

## 1. Documents

### List Documents
`GET /documents`
Returns a list of all indexed documents in the persistent store.

**Response:**
```json
{
  "success": true,
  "data": {
    "total": 1,
    "documents": [
      {
        "doc_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "name": "document.pdf",
        "indexed_at": "2024-03-24T12:00:00Z"
      }
    ]
  }
}
```

### Delete Document
`DELETE /documents/{doc_hash}`
Deletes a document's artifacts (Chroma, BM25, graph, etc.) using its unique hash.

### Get Knowledge Graph
`GET /graph/{doc_hash}`
Returns the NetworkX graph extracted from the document, serialized as node-link data.

### Index Document
`POST /index`
Accepts a batch of documents (Multipart Form Data, `files`) and streams the indexing progress using SSE (Server-Sent Events).

---

## 2. Query

### Submit Query
`POST /query`
Answers a question against an indexed document.

**Request Body (JSON):**
```json
{
  "doc_hash": "...",
  "query": "What is the main topic?",
  "history": []
}
```
**Response:** SSE Stream
Yields the generated answer chunks and passage-level citations dynamically.

---

## 3. Telemetry

### Service Information
`GET /`
Returns service identity and configuration details (provider, embed model, rerank mode).

### Health Check
`GET /health`
Liveness probe checking if the persistent directory is writable.

### Telemetry Stats
`GET /telemetry/stats`
Returns aggregated statistics from the local SQLite trace store.

### Trace Lookup
`GET /trace/{request_id}`
Retrieves trace details (latency, token usage, context chunks) for a specific request ID.

---

## 4. Studio & Masterclass

The application also offers specialized extraction endpoints for Studio and Masterclass features, such as generating slide decks, summaries, quizzes, or chapter breakdowns. These endpoints (`/studio/*`, `/masterclass/*`) operate over SSE and require a `doc_hash` to run against previously indexed context.
