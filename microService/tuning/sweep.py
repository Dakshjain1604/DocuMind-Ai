"""Parameter sweep for GraphRAG retrieval tuning.

Runs a grid search over chunking and retrieval parameters, computing
Recall@K, MRR, and nDCG metrics for each configuration.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import pickle
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
from tqdm import tqdm

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from langchain_core.documents import Document
from langchain_chroma import Chroma

from app.core.chunker import chunk_documents
from app.core.embeddings import get_embeddings
from app.indexing.store import (
    doc_hash_from_bytes,
    doc_dir,
    chroma_dir,
    persist_artifacts,
    load_artifacts,
)
from app.retrieval.search import BM25Index, GraphIndex, reciprocal_rank_fusion, vector_search
from app.retrieval.reranker import rerank
from app.indexing.community import build_networkx_graph, detect_communities
from app.indexing.graph_extractor import extract_graph
from app.retrieval.rewriter import rewrite_query


# Configuration
PDF_PATH = Path("tmp/uploaded_files/AI Engineering.pdf")
EVAL_SET_PATH = Path("microService/tuning/eval_set.jsonl")
RESULTS_DIR = Path("microService/tuning/results")
CACHE_DIR = Path("microService/tuning/.index_cache")

# Parameter grid
CHUNK_SIZES = [500, 800, 1000, 1400]
CHUNK_OVERLAPS = [100, 200]
PER_RETRIEVER_TOP_KS = [10, 20]
FUSED_TOP_KS = [10, 15, 25]
RRF_WEIGHTS = [
    {"vector": 1.0, "bm25": 1.0, "graph": 1.0},
    {"vector": 1.0, "bm25": 0.7, "graph": 0.5},
    {"vector": 1.0, "bm25": 1.0, "graph": 0.3},
]
# "llm" is deliberately excluded from the grid — LLM-based rerank makes one
# extra API call per question per config, which multiplies badly across a
# grid this size and is rate-limit-sensitive on free models. cross_encoder
# is local/free/fast, so it's safe to sweep.
RERANK_MODES = ["off", "cross_encoder"]
MULTI_QUERY_NS = [0, 3]


@dataclass
class SweepConfig:
    """Configuration for a single sweep run."""
    chunk_size: int
    chunk_overlap: int
    per_retriever_top_k: int
    fused_top_k: int
    vector_weight: float
    bm25_weight: float
    graph_weight: float
    rrf_k: int = 60
    rerank_mode: str = "off"
    multi_query_n: int = 0

    def to_dict(self) -> dict:
        return asdict(self)

    def get_index_key(self) -> str:
        """Get cache key for index (chunking params only)."""
        return f"cs{self.chunk_size}_co{self.chunk_overlap}"

    def get_config_key(self) -> str:
        """Get unique key for this full configuration."""
        return (
            f"{self.get_index_key()}_"
            f"rtk{self.per_retriever_top_k}_"
            f"ftk{self.fused_top_k}_"
            f"vw{self.vector_weight:.1f}_"
            f"bw{self.bm25_weight:.1f}_"
            f"gw{self.graph_weight:.1f}_"
            f"rr{self.rerank_mode}_"
            f"mq{self.multi_query_n}"
        )


@dataclass
class SweepResult:
    """Results from a single sweep configuration."""
    config: SweepConfig
    recall_at_5: float
    recall_at_10: float
    recall_at_15: float
    mrr: float
    ndcg_at_10: float
    total_questions: int
    avg_latency_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            **self.config.to_dict(),
            "recall_at_5": self.recall_at_5,
            "recall_at_10": self.recall_at_10,
            "recall_at_15": self.recall_at_15,
            "mrr": self.mrr,
            "ndcg_at_10": self.ndcg_at_10,
            "total_questions": self.total_questions,
            "avg_latency_ms": self.avg_latency_ms,
        }


def load_pdf_documents(pdf_path: Path) -> list[Document]:
    """Load PDF and return list of Documents."""
    print(f"Loading PDF: {pdf_path}")
    
    try:
        from langchain_community.document_loaders import PyPDFLoader
        loader = PyPDFLoader(str(pdf_path))
        docs = loader.load()
        print(f"Loaded {len(docs)} pages")
        return docs
    except Exception as e:
        print(f"PyPDFLoader failed: {e}")
    
    try:
        import pypdf
        docs = []
        with open(pdf_path, "rb") as f:
            reader = pypdf.PdfReader(f)
            for i, page in enumerate(reader.pages):
                text = page.extract_text()
                if text.strip():
                    docs.append(Document(page_content=text, metadata={"page": i + 1}))
        print(f"Loaded {len(docs)} pages using pypdf")
        return docs
    except Exception as e:
        print(f"pypdf fallback failed: {e}")
        raise RuntimeError(f"Could not load PDF from {pdf_path}")


def load_eval_set(eval_path: Path) -> list[dict]:
    """Load evaluation questions from JSONL."""
    questions = []
    with open(eval_path) as f:
        for line in f:
            line = line.strip()
            if line:
                questions.append(json.loads(line))
    print(f"Loaded {len(questions)} evaluation questions")
    return questions


def compute_recall_at_k(retrieved_ids: list[int], gold_id: int, k: int) -> float:
    """Compute Recall@K (1.0 if gold_id in top-k, else 0.0)."""
    return 1.0 if gold_id in retrieved_ids[:k] else 0.0


def compute_mrr(retrieved_ids: list[int], gold_id: int) -> float:
    """Compute Mean Reciprocal Rank."""
    try:
        rank = retrieved_ids.index(gold_id) + 1
        return 1.0 / rank
    except ValueError:
        return 0.0


def compute_ndcg_at_k(retrieved_ids: list[int], gold_id: int, k: int) -> float:
    """Compute nDCG@K."""
    try:
        rank = retrieved_ids.index(gold_id) + 1
        if rank > k:
            return 0.0
        # DCG: 1 / log2(rank + 1)
        dcg = 1.0 / (1 + __import__('math').log2(rank + 1))
        # Ideal DCG (if gold was at rank 1): 1 / log2(2) = 1.0
        idcg = 1.0
        return dcg / idcg
    except ValueError:
        return 0.0


def get_index_cache_path(chunk_size: int, chunk_overlap: int) -> Path:
    """Get path for cached index."""
    key = f"cs{chunk_size}_co{chunk_overlap}"
    return CACHE_DIR / f"{key}.pkl"


def save_index_cache(
    chunk_size: int,
    chunk_overlap: int,
    chunks: list[Document],
    chroma: Chroma,
    bm25: BM25Index,
    graph: GraphIndex,
    chunks_by_id: dict[int, str],
) -> None:
    """Save built index to cache."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = get_index_cache_path(chunk_size, chunk_overlap)
    
    # Note: Chroma can't be pickled, so we save the directory path
    # The caller needs to ensure Chroma is persisted
    cache_data = {
        "chunks": chunks,
        "bm25_tokens": bm25._tokens,
        "graph_data": {
            "nodes": [{"id": n, **graph._nodes[n].copy()} for n in graph._nodes],
            "edges": [{"src": u, "dst": v} for u in graph._adj for v in graph._adj[u]],
            "communities": graph._comm,
            "community_summaries": graph._summaries,
        },
        "chunks_by_id": chunks_by_id,
    }
    
    with open(cache_path, "wb") as f:
        pickle.dump(cache_data, f)
    
    print(f"  Cached index to {cache_path}")


def load_index_cache(
    chunk_size: int,
    chunk_overlap: int,
    persist_dir: str,
) -> tuple[list[Document], Chroma, BM25Index, GraphIndex, dict[int, str]] | None:
    """Load cached index if it exists."""
    cache_path = get_index_cache_path(chunk_size, chunk_overlap)
    
    if not cache_path.exists():
        return None
    
    try:
        with open(cache_path, "rb") as f:
            cache_data = pickle.load(f)
        
        chunks = cache_data["chunks"]
        bm25 = BM25Index(cache_data["bm25_tokens"])
        
        # Rebuild GraphIndex from cached data
        graph_data = cache_data["graph_data"]
        graph = GraphIndex(graph_data)
        
        # Reload Chroma from persist directory
        chroma = Chroma(
            persist_directory=persist_dir,
            embedding_function=get_embeddings(),
        )
        
        chunks_by_id = cache_data["chunks_by_id"]
        
        print(f"  Loaded cached index from {cache_path}")
        return chunks, chroma, bm25, graph, chunks_by_id
    
    except Exception as e:
        print(f"  Failed to load cache: {e}")
        return None


async def build_index(
    docs: list[Document],
    chunk_size: int,
    chunk_overlap: int,
    file_bytes: bytes,
) -> tuple[list[Document], Chroma, BM25Index, GraphIndex, dict[int, str]]:
    """Build or load cached index for given chunking parameters."""
    h = doc_hash_from_bytes(file_bytes)
    persist_path = str(chroma_dir(h))
    
    # Try to load from cache first
    cached = load_index_cache(chunk_size, chunk_overlap, persist_path)
    if cached:
        return cached
    
    print(f"  Building index for chunk_size={chunk_size}, chunk_overlap={chunk_overlap}")
    
    # Chunk documents
    print(f"    Chunking with size={chunk_size}, overlap={chunk_overlap}")
    chunks = chunk_documents(docs, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    print(f"    Created {len(chunks)} chunks")
    
    # Build Chroma index
    print("    Building Chroma vector index...")
    chroma = Chroma.from_documents(
        documents=chunks,
        embedding=get_embeddings(),
        persist_directory=persist_path,
    )
    
    # Build BM25 index
    print("    Building BM25 index...")
    bm25 = BM25Index.build([c.page_content for c in chunks])
    
    # Build graph index (simplified for tuning - use fewer chunks for speed)
    print("    Building graph index...")
    max_graph_chunks = min(60, len(chunks))
    if len(chunks) > max_graph_chunks:
        step = len(chunks) / max_graph_chunks
        graph_chunks = [chunks[int(i * step)] for i in range(max_graph_chunks)]
    else:
        graph_chunks = chunks
    
    # Extract entities and relationships
    graph_build = await extract_graph(graph_chunks, concurrency=4)
    g = build_networkx_graph(graph_build.entities, graph_build.relationships)
    communities = detect_communities(g)
    
    # Create GraphIndex
    graph_data = {
        "nodes": [{"id": n, **g.nodes[n]} for n in g.nodes],
        "edges": [{"src": u, "dst": v, **g.edges[u, v]} for u, v in g.edges],
        "communities": communities,
        "community_summaries": {},  # Skip summaries for tuning speed
    }
    graph = GraphIndex(graph_data)
    
    # Build chunks_by_id mapping
    chunks_by_id: dict[int, str] = {}
    for chunk in chunks:
        cid = chunk.metadata.get("chunk_id")
        if cid is not None:
            chunks_by_id[int(cid)] = chunk.page_content
    
    # Cache the index
    save_index_cache(chunk_size, chunk_overlap, chunks, chroma, bm25, graph, chunks_by_id)
    
    return chunks, chroma, bm25, graph, chunks_by_id


async def run_single_config(
    config: SweepConfig,
    docs: list[Document],
    eval_questions: list[dict],
    file_bytes: bytes,
) -> SweepResult:
    """Run evaluation for a single configuration.

    Note: token/cost accounting is deliberately NOT tracked here (unlike the
    production orchestrator's trace) — rewrite_query() doesn't expose the
    underlying LLMResult, and threading it through would mean changing its
    return contract for every caller. Given this sweep targets free
    OpenRouter models, real cost is $0 either way; avg_latency_ms is the
    metric that actually differentiates configs (e.g. rerank on vs off).
    """

    # Build/load index
    chunks, chroma, bm25, graph, chunks_by_id = await build_index(
        docs, config.chunk_size, config.chunk_overlap, file_bytes
    )

    # rerank() and the rewriter's multi-query prompt read mode/N from
    # app.config.settings at call time — set the env vars once per config.
    os.environ["RAG_RERANK_MODE"] = config.rerank_mode
    os.environ["RAG_MULTI_QUERY_N"] = str(config.multi_query_n)

    # Track metrics
    recalls_at_5 = []
    recalls_at_10 = []
    recalls_at_15 = []
    mrrs = []
    ndcgs_at_10 = []
    latencies_ms = []

    for question_data in eval_questions:
        question = question_data["question"]
        gold_chunk_id = question_data["gold_chunk_id"]
        q_start = time.perf_counter()

        # Rewrite query (same as orchestrator)
        try:
            rq = await rewrite_query(question, n_variants=config.multi_query_n)
        except Exception:
            # If rewrite fails, use original question
            from dataclasses import dataclass, field
            @dataclass
            class SimpleRQ:
                hyde: str
                keywords: str
                entities_mentioned: list
                query_variants: list = field(default_factory=list)
            rq = SimpleRQ(hyde=question, keywords=question, entities_mentioned=[])

        # Vector leg: multi-query fan-out over hyde + variants (mirrors the
        # orchestrator's two-stage fusion), then bm25/graph as usual.
        variant_queries = [rq.hyde] + rq.query_variants[: config.multi_query_n]
        try:
            per_variant_ids = []
            for vq in variant_queries:
                vec_results = vector_search(chroma, vq, top_k=config.per_retriever_top_k)
                per_variant_ids.append([cid for cid, _ in vec_results])
            vec_ids = (
                per_variant_ids[0]
                if len(per_variant_ids) == 1
                else reciprocal_rank_fusion(per_variant_ids, k=config.rrf_k, top_k=config.per_retriever_top_k)
            )
        except Exception:
            vec_ids = []

        try:
            bm25_results = bm25.search(rq.keywords, top_k=config.per_retriever_top_k)
            bm25_ids = [cid for cid, _ in bm25_results]
        except Exception:
            bm25_ids = []

        try:
            matched = graph.match_entities(rq.entities_mentioned)
            graph_ids = graph.traverse_chunks(matched, hops=2) if matched else []
        except Exception:
            graph_ids = []

        # Fuse with weighted RRF
        rankings = [vec_ids, bm25_ids, graph_ids]
        weights = [config.vector_weight, config.bm25_weight, config.graph_weight]

        fused_ids = reciprocal_rank_fusion(
            rankings,
            k=config.rrf_k,
            top_k=config.fused_top_k,
            weights=weights,
        )

        # Rerank re-orders the fused list (top_k == len(fused_ids), so it
        # never truncates) — isolates ranking-quality effect from any
        # cutoff effect when measuring recall@10/@15 downstream.
        if config.rerank_mode != "off" and fused_ids:
            pairs = [(cid, chunks_by_id.get(cid, "")) for cid in fused_ids]
            fused_ids = await rerank(question, pairs, top_k=len(pairs))

        latencies_ms.append((time.perf_counter() - q_start) * 1000)

        # Compute metrics
        recalls_at_5.append(compute_recall_at_k(fused_ids, gold_chunk_id, 5))
        recalls_at_10.append(compute_recall_at_k(fused_ids, gold_chunk_id, 10))
        recalls_at_15.append(compute_recall_at_k(fused_ids, gold_chunk_id, 15))
        mrrs.append(compute_mrr(fused_ids, gold_chunk_id))
        ndcgs_at_10.append(compute_ndcg_at_k(fused_ids, gold_chunk_id, 10))

    # Aggregate results
    n = len(eval_questions)
    return SweepResult(
        config=config,
        recall_at_5=sum(recalls_at_5) / n,
        recall_at_10=sum(recalls_at_10) / n,
        recall_at_15=sum(recalls_at_15) / n,
        mrr=sum(mrrs) / n,
        ndcg_at_10=sum(ndcgs_at_10) / n,
        total_questions=n,
        avg_latency_ms=sum(latencies_ms) / n,
    )


def generate_configs() -> list[SweepConfig]:
    """Generate all configurations for the sweep."""
    configs = []
    for chunk_size in CHUNK_SIZES:
        for chunk_overlap in CHUNK_OVERLAPS:
            for per_retriever_top_k in PER_RETRIEVER_TOP_KS:
                for fused_top_k in FUSED_TOP_KS:
                    for weights in RRF_WEIGHTS:
                        for rerank_mode in RERANK_MODES:
                            for multi_query_n in MULTI_QUERY_NS:
                                configs.append(SweepConfig(
                                    chunk_size=chunk_size,
                                    chunk_overlap=chunk_overlap,
                                    per_retriever_top_k=per_retriever_top_k,
                                    fused_top_k=fused_top_k,
                                    vector_weight=weights["vector"],
                                    bm25_weight=weights["bm25"],
                                    graph_weight=weights["graph"],
                                    rerank_mode=rerank_mode,
                                    multi_query_n=multi_query_n,
                                ))
    return configs


async def run_sweep() -> list[SweepResult]:
    """Run the full parameter sweep."""
    print("=" * 70)
    print("GraphRAG Retrieval Parameter Sweep")
    print("=" * 70)
    
    # Load PDF
    print("\n1. Loading PDF...")
    docs = load_pdf_documents(PDF_PATH)
    
    # Read file bytes for hashing
    with open(PDF_PATH, "rb") as f:
        file_bytes = f.read()
    
    # Load eval set
    print("\n2. Loading evaluation set...")
    if not EVAL_SET_PATH.exists():
        print(f"ERROR: Evaluation set not found at {EVAL_SET_PATH}")
        print("Please run build_eval_set.py first")
        sys.exit(1)
    
    eval_questions = load_eval_set(EVAL_SET_PATH)
    
    # Generate configurations
    print("\n3. Generating sweep configurations...")
    configs = generate_configs()
    print(f"   Total configurations: {len(configs)}")
    print(f"   Unique chunking configs: {len(CHUNK_SIZES) * len(CHUNK_OVERLAPS)}")
    
    # Create results directory
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Run sweep
    print("\n4. Running sweep...")
    print("-" * 70)
    
    results: list[SweepResult] = []
    
    # Group by chunking config to avoid rebuilding indices
    chunking_groups: dict[str, list[SweepConfig]] = {}
    for config in configs:
        key = config.get_index_key()
        if key not in chunking_groups:
            chunking_groups[key] = []
        chunking_groups[key].append(config)
    
    total_configs = len(configs)
    pbar = tqdm(total=total_configs, desc="Sweeping configs")
    
    for chunking_key, group_configs in chunking_groups.items():
        # Build index once per chunking config
        first_config = group_configs[0]
        print(f"\nBuilding index for {chunking_key}...")
        
        # Pre-build the index (will be cached)
        await build_index(
            docs,
            first_config.chunk_size,
            first_config.chunk_overlap,
            file_bytes,
        )
        
        # Run all retrieval configs for this chunking
        for config in group_configs:
            result = await run_single_config(config, docs, eval_questions, file_bytes)
            results.append(result)
            
            # Save intermediate result
            result_path = RESULTS_DIR / f"{config.get_config_key()}.json"
            with open(result_path, "w") as f:
                json.dump(result.to_dict(), f, indent=2)
            
            pbar.update(1)
            pbar.set_postfix({
                "R@5": f"{result.recall_at_5:.3f}",
                "MRR": f"{result.mrr:.3f}",
                "lat_ms": f"{result.avg_latency_ms:.0f}",
            })
    
    pbar.close()
    
    print("\n" + "=" * 70)
    print(f"✓ Sweep complete! Evaluated {len(results)} configurations")
    print(f"  Results saved to: {RESULTS_DIR}")
    
    return results


if __name__ == "__main__":
    # Load OpenRouter credentials
    cred_path = Path.home() / ".neo" / "integrations" / "openrouter.env"
    if cred_path.exists():
        print(f"Loading credentials from {cred_path}")
        with open(cred_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ.setdefault(key, value)
    
    # Set default models if not configured
    if not os.environ.get("OPENROUTER_MODEL_REWRITE"):
        os.environ["OPENROUTER_MODEL_REWRITE"] = "anthropic/claude-haiku-4.5,openai/gpt-4o-mini"
    
    # Run sweep
    results = asyncio.run(run_sweep())
    
    # Save full results
    all_results_path = RESULTS_DIR / "all_results.json"
    with open(all_results_path, "w") as f:
        json.dump([r.to_dict() for r in results], f, indent=2)
    
    print(f"\nFull results saved to: {all_results_path}")
