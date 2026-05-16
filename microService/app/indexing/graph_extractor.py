"""LLM-based entity + relationship extraction per chunk."""
from __future__ import annotations
import asyncio
import json
from dataclasses import dataclass, field
from typing import Any
from langchain_core.documents import Document

from app.core.llm import LLMClient, get_llm

EXTRACTION_PROMPT = """You extract a knowledge graph from a passage of text.

Return ONLY valid JSON matching this schema:
{
  "entities":      [{"id": "string", "type": "string", "description": "string"}],
  "relationships": [{"src": "string", "dst": "string", "type": "string", "description": "string"}]
}

Rules:
- entity id is the canonical name (e.g. "Mitochondria", not "the mitochondria")
- type is one of: Person, Organization, Concept, Process, Thing, Place, Event
- only include relationships where BOTH endpoints appear in entities
- be conservative — only include entities/relations actually stated in the passage

Passage:
"""


@dataclass
class ExtractionResult:
    entities: list[dict[str, str]]
    relationships: list[dict[str, str]]


@dataclass
class GraphBuild:
    entities: list[dict[str, Any]] = field(default_factory=list)
    relationships: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


async def _extract_one(client: LLMClient, doc: Document) -> ExtractionResult:
    messages = [
        {"role": "system", "content": "You output strict JSON only."},
        {"role": "user", "content": EXTRACTION_PROMPT + doc.page_content},
    ]
    last_err: Exception | None = None
    for attempt in range(2):
        try:
            result = await client.complete(
                role="extract",
                messages=messages,
                temperature=0.0,
                response_format={"type": "json_object"},
            )
            data = json.loads(result.content)
            return ExtractionResult(
                entities=data.get("entities", []),
                relationships=data.get("relationships", []),
            )
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            last_err = e
            messages[0]["content"] = "You output ONLY valid JSON. No prose, no markdown fences."
    raise ValueError(f"Failed to parse extraction JSON after 2 attempts: {last_err}")


async def extract_graph(chunks: list[Document], *, concurrency: int = 8) -> GraphBuild:
    """Run extraction concurrently across chunks. Failed chunks are skipped, not fatal."""
    client = get_llm()
    sem = asyncio.Semaphore(concurrency)

    async def run(doc: Document) -> tuple[Document, ExtractionResult | Exception]:
        async with sem:
            try:
                r = await _extract_one(client, doc)
                return doc, r
            except Exception as e:
                return doc, e

    results = await asyncio.gather(*[run(c) for c in chunks])

    build = GraphBuild()
    seen_entities: set[str] = set()
    seen_rels: set[tuple[str, str, str]] = set()
    for doc, r in results:
        cid = doc.metadata.get("chunk_id")
        if isinstance(r, Exception):
            build.warnings.append(f"chunk {cid}: {r}")
            continue
        for e in r.entities:
            eid = e.get("id")
            if not eid or eid in seen_entities:
                continue
            seen_entities.add(eid)
            e["source_chunks"] = [cid]
            build.entities.append(e)
        for rel in r.relationships:
            key = (rel.get("src", ""), rel.get("dst", ""), rel.get("type", ""))
            if key in seen_rels:
                continue
            seen_rels.add(key)
            rel["source_chunks"] = [cid]
            build.relationships.append(rel)
    return build
