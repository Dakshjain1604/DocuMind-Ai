"""Louvain community detection + LLM summarization."""
from __future__ import annotations
import asyncio
import networkx as nx
from community import community_louvain  # provided by python-louvain
from app.config.settings import get_settings
from app.core.llm import get_llm
from app.prompts import COMMUNITY_SUMMARY_PROMPT


def build_networkx_graph(entities: list[dict], relationships: list[dict]) -> nx.Graph:
    g = nx.Graph()
    for e in entities:
        g.add_node(e["id"], **{k: v for k, v in e.items() if k != "id"})
    for r in relationships:
        if r["src"] in g and r["dst"] in g:
            g.add_edge(
                r["src"],
                r["dst"],
                type=r.get("type", ""),
                description=r.get("description", ""),
                source_chunks=r.get("source_chunks", []),
            )
    return g


def detect_communities(g: nx.Graph) -> dict[str, int]:
    if g.number_of_nodes() < get_settings().min_nodes_for_communities:
        return {}
    return community_louvain.best_partition(g)


async def summarize_communities(
    g: nx.Graph,
    communities: dict[str, int],
    *,
    concurrency: int = 8,
    max_communities: int | None = None,
) -> dict[int, str]:
    """Backwards-compatible wrapper that returns the final summary dict."""
    final: dict[int, str] = {}
    async for kind, payload in summarize_communities_streaming(
        g, communities, concurrency=concurrency, max_communities=max_communities
    ):
        if kind == "result":
            final = payload  # type: ignore[assignment]
    return final


async def summarize_communities_streaming(
    g: nx.Graph,
    communities: dict[str, int],
    *,
    concurrency: int = 8,
    max_communities: int | None = None,
):
    """Streaming variant — yields ('progress', {done, total}) per completed
    community, then a single ('result', dict). Keeps SSE alive on long runs."""
    if not communities:
        yield "result", {}
        return

    by_comm: dict[int, list[str]] = {}
    for node, cid in communities.items():
        by_comm.setdefault(cid, []).append(node)

    # Cap to the N largest (most-connected) communities — singletons add little
    # signal and burn LLM budget. Skipped communities still show up in the graph,
    # they just won't have an LLM summary.
    if max_communities and len(by_comm) > max_communities:
        ranked = sorted(by_comm.items(), key=lambda kv: -len(kv[1]))
        by_comm = dict(ranked[:max_communities])

    client = get_llm()
    sem = asyncio.Semaphore(concurrency)

    async def one(cid: int, members: list[str]) -> tuple[int, str]:
        async with sem:
            edges = [
                f"{u} -[{d.get('type','related')}]- {v}"
                for u, v, d in g.subgraph(members).edges(data=True)
            ]
            try:
                r = await client.complete(
                    role="extract",
                    messages=[{"role": "user", "content": COMMUNITY_SUMMARY_PROMPT.format(
                        members=", ".join(members),
                        edges="\n".join(edges) or "(no edges)",
                    )}],
                    temperature=0.2,
                )
                return cid, r.content.strip()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                return cid, f"(summary unavailable: {e})"

    tasks = [asyncio.create_task(one(cid, m)) for cid, m in by_comm.items()]
    total = len(tasks)
    done = 0
    pairs: list[tuple[int, str]] = []
    for fut in asyncio.as_completed(tasks):
        pairs.append(await fut)
        done += 1
        yield "progress", {"done": done, "total": total}

    yield "result", dict(pairs)
