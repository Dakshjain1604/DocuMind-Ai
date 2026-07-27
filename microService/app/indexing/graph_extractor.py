"""LLM-based entity + relationship extraction per chunk."""
from __future__ import annotations
import asyncio
import json
from dataclasses import dataclass, field
from typing import Any
from langchain_core.documents import Document

from app.config.settings import get_settings
from app.core.llm import LLMClient, _is_retriable, get_llm
from app.core.observability import log_event
from app.prompts import EXTRACTION_PROMPT


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
            result = await asyncio.wait_for(
                client.complete(
                    role="extract",
                    messages=messages,
                    temperature=0.0,
                    response_format={"type": "json_object"},
                ),
                timeout=5.0,
            )
            data = json.loads(result.content)
            return ExtractionResult(
                entities=data.get("entities", []),
                relationships=data.get("relationships", []),
            )
        except asyncio.TimeoutError:
            log_event("chunk_extraction_timeout", chunk_id=doc.metadata.get("chunk_id"))
            return ExtractionResult(entities=[], relationships=[])
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            last_err = e
            messages[0]["content"] = "You output ONLY valid JSON. No prose, no markdown fences."
        except Exception as e:
            if _is_retriable(e) and attempt == 0:
                last_err = e
                continue
            return ExtractionResult(entities=[], relationships=[])
    return ExtractionResult(entities=[], relationships=[])


async def extract_graph(chunks: list[Document], *, concurrency: int | None = None) -> GraphBuild:
    """Run extraction concurrently. Backwards-compatible wrapper that returns
    the final GraphBuild (no progress/warning events)."""
    final: GraphBuild | None = None
    async for kind, payload in extract_graph_streaming(chunks, concurrency=concurrency):
        if kind == "result":
            final = payload  # type: ignore[assignment]
    assert final is not None
    return final


async def extract_graph_streaming(chunks: list[Document], *, concurrency: int | None = None):
    """Streaming variant — yields ('progress', {done, total}) per completed
    chunk, ('warning', {chunk_id, error}) as soon as a chunk's extraction
    fails (not buried until the end), then a single ('result', GraphBuild)."""
    if not chunks:
        yield "result", GraphBuild()
        return

    if concurrency is None:
        concurrency = get_settings().graph_concurrency

    client = get_llm()
    sem = asyncio.Semaphore(concurrency)

    async def run(doc: Document):
        async with sem:
            try:
                return doc, await _extract_one(client, doc)
            except Exception as e:
                return doc, e

    tasks = [asyncio.create_task(run(c)) for c in chunks]
    total = len(tasks)
    done = 0
    results: list[tuple[Document, ExtractionResult | Exception]] = []
    for fut in asyncio.as_completed(tasks):
        doc, r = await fut
        results.append((doc, r))
        done += 1
        if isinstance(r, Exception):
            cid = doc.metadata.get("chunk_id")
            log_event("chunk_extraction_failed", chunk_id=cid, error_type=type(r).__name__, error=str(r))
            yield "warning", {"chunk_id": cid, "error": str(r)}
        yield "progress", {"done": done, "total": total}

    build = GraphBuild()
    entity_map: dict[str, dict] = {}
    rel_map: dict[tuple[str, str, str], dict] = {}
    
    for doc, r in results:
        cid = doc.metadata.get("chunk_id")
        if isinstance(r, Exception):
            build.warnings.append(f"chunk {cid}: {r}")
            continue
        for e in r.entities:
            eid = e.get("id")
            if not eid:
                continue
            if eid in entity_map:
                if cid not in entity_map[eid]["source_chunks"]:
                    entity_map[eid]["source_chunks"].append(cid)
            else:
                e["source_chunks"] = [cid]
                entity_map[eid] = e
                build.entities.append(e)
        for rel in r.relationships:
            src = rel.get("src", "")
            dst = rel.get("dst", "")
            rtype = rel.get("type", "")
            key = (src, dst, rtype)
            if key in rel_map:
                if cid not in rel_map[key]["source_chunks"]:
                    rel_map[key]["source_chunks"].append(cid)
            else:
                rel["source_chunks"] = [cid]
                rel_map[key] = rel
                build.relationships.append(rel)
    yield "result", build
