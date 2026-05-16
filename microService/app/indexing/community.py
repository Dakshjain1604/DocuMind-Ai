"""Louvain community detection + LLM summarization."""
from __future__ import annotations
import asyncio
import networkx as nx
from community import community_louvain  # provided by python-louvain
from app.core.llm import get_llm


MIN_NODES_FOR_COMMUNITIES = 5


def build_networkx_graph(entities: list[dict], relationships: list[dict]) -> nx.Graph:
    g = nx.Graph()
    for e in entities:
        g.add_node(e["id"], **{k: v for k, v in e.items() if k != "id"})
    for r in relationships:
        if r["src"] in g and r["dst"] in g:
            g.add_edge(r["src"], r["dst"], type=r.get("type", ""), description=r.get("description", ""))
    return g


def detect_communities(g: nx.Graph) -> dict[str, int]:
    if g.number_of_nodes() < MIN_NODES_FOR_COMMUNITIES:
        return {}
    return community_louvain.best_partition(g)


SUMMARY_PROMPT = """Summarize the following group of related concepts in 2-3 sentences.
Concepts:
{members}

Relationships:
{edges}

Summary:"""


async def summarize_communities(
    g: nx.Graph,
    communities: dict[str, int],
    *,
    concurrency: int = 8,
) -> dict[int, str]:
    if not communities:
        return {}
    by_comm: dict[int, list[str]] = {}
    for node, cid in communities.items():
        by_comm.setdefault(cid, []).append(node)

    client = get_llm()
    sem = asyncio.Semaphore(concurrency)

    async def one(cid: int, members: list[str]) -> tuple[int, str]:
        async with sem:
            edges = [
                f"{u} -[{d.get('type','related')}]- {v}"
                for u, v, d in g.subgraph(members).edges(data=True)
            ]
            r = await client.complete(
                role="extract",
                messages=[{"role": "user", "content": SUMMARY_PROMPT.format(
                    members=", ".join(members),
                    edges="\n".join(edges) or "(no edges)",
                )}],
                temperature=0.2,
            )
            return cid, r.content.strip()

    pairs = await asyncio.gather(*[one(cid, m) for cid, m in by_comm.items()])
    return dict(pairs)
