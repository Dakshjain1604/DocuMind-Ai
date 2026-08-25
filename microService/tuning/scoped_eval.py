"""Scoped retrieval ablation — a small, meaningful comparison instead of the
full 288-config grid in sweep.py.

Holds chunking fixed at production defaults (RAG_CHUNK_SIZE=1500,
RAG_CHUNK_OVERLAP=200) and walks the pipeline from naive vector-only search up
to the full production config (hybrid RRF fusion + cross-encoder rerank +
multi-query rewrite), isolating what each stage actually buys in Recall@K/MRR
against the 40-question eval set (real gold chunk ids over a real 470-page
technical book). Reuses sweep.py's index-building and per-question evaluation
so the numbers are computed exactly the same way the full sweep would.

Run from the repo root: microService/.venv/bin/python microService/tuning/scoped_eval.py
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))  # microService/tuning, for `import sweep`
sys.path.insert(0, str(Path(__file__).parent.parent))  # microService/, for `app.*`

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

# Isolated from both the real app's persist dir (microService/local_chroma)
# and its default relative-path fallback — this eval must never write into a
# directory the live app also reads from.
import os  # noqa: E402

os.environ["RAG_PERSIST_DIR"] = str(Path(__file__).parent / "eval_chroma")

import sweep  # noqa: E402

# NVIDIA's hosted embedding model (nvidia/nv-embedqa-e5-v5) reached end of
# life on 2026-08-25 (mid-way through building this eval — see the 410 Gone
# response). Force the local HuggingFace embedder instead: it's free,
# reproducible without an external API, and matches what RAG_EMBED_MODEL
# falls back to when no provider embedding is configured.
from langchain_huggingface import HuggingFaceEmbeddings  # noqa: E402
from app.core.embeddings import detect_device  # noqa: E402

_local_embeddings = HuggingFaceEmbeddings(
    model_name="BAAI/bge-small-en-v1.5",
    model_kwargs={"device": detect_device()},
    encode_kwargs={"normalize_embeddings": True, "batch_size": 32},
)
sweep.get_embeddings = lambda: _local_embeddings

RESULTS_PATH = Path("microService/tuning/results/scoped_ablation.json")
REPORT_PATH = Path("microService/tuning/results/scoped_ablation.md")

# Must match build_eval_set.py's chunking exactly (chunk_size=1000,
# chunk_overlap=150) — gold_chunk_id in eval_set.jsonl is a chunk_id assigned
# under that specific chunking, not a stable content identifier. Using a
# different chunk_size silently produces a different chunk_id numbering and
# every recall number degenerates to 0 (found this the hard way — the first
# run used production defaults, 1500/200, and scored exactly 0.0 everywhere).
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150

STAGES: list[tuple[str, sweep.SweepConfig]] = [
    (
        "1. Vector-only (naive RAG baseline)",
        sweep.SweepConfig(
            chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP,
            per_retriever_top_k=10, fused_top_k=15,
            vector_weight=1.0, bm25_weight=0.0, graph_weight=0.0,
            rerank_mode="off", multi_query_n=0,
        ),
    ),
    (
        "2. + hybrid fusion (vector + BM25 + graph, RRF)",
        sweep.SweepConfig(
            chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP,
            per_retriever_top_k=10, fused_top_k=15,
            vector_weight=1.0, bm25_weight=1.0, graph_weight=0.5,
            rerank_mode="off", multi_query_n=0,
        ),
    ),
    (
        "3. + cross-encoder rerank",
        sweep.SweepConfig(
            chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP,
            per_retriever_top_k=10, fused_top_k=15,
            vector_weight=1.0, bm25_weight=1.0, graph_weight=0.5,
            rerank_mode="cross_encoder", multi_query_n=0,
        ),
    ),
    (
        "4. + multi-query rewrite (full production config)",
        sweep.SweepConfig(
            chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP,
            per_retriever_top_k=10, fused_top_k=15,
            vector_weight=1.0, bm25_weight=1.0, graph_weight=0.5,
            rerank_mode="cross_encoder", multi_query_n=3,
        ),
    ),
]


async def main() -> None:
    print("Loading PDF and eval set...")
    docs = sweep.load_pdf_documents(sweep.PDF_PATH)
    with open(sweep.PDF_PATH, "rb") as f:
        file_bytes = f.read()
    eval_questions = sweep.load_eval_set(sweep.EVAL_SET_PATH)
    smoke_n = os.environ.get("SCOPED_EVAL_SMOKE_N")
    if smoke_n:
        eval_questions = eval_questions[: int(smoke_n)]
        print(f"SCOPED_EVAL_SMOKE_N set — using only {len(eval_questions)} questions")

    print(f"\nBuilding index once (chunk_size={CHUNK_SIZE}, chunk_overlap={CHUNK_OVERLAP})...")
    await sweep.build_index(docs, CHUNK_SIZE, CHUNK_OVERLAP, file_bytes)

    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    results = []
    for label, config in STAGES:
        print(f"\n--- {label} ---")
        result = await sweep.run_single_config(config, docs, eval_questions, file_bytes)
        print(
            f"  Recall@5={result.recall_at_5:.3f}  Recall@10={result.recall_at_10:.3f}  "
            f"Recall@15={result.recall_at_15:.3f}  MRR={result.mrr:.3f}  "
            f"nDCG@10={result.ndcg_at_10:.3f}  avg_latency_ms={result.avg_latency_ms:.0f}"
        )
        results.append({"stage": label, **result.to_dict()})
        with open(RESULTS_PATH, "w") as f:
            json.dump(results, f, indent=2)

    lines = [
        "# Scoped retrieval ablation",
        "",
        f"Eval set: `{sweep.EVAL_SET_PATH}` ({len(eval_questions)} questions, real gold chunk ids "
        "from a 535-page technical book, generated by an LLM from randomly sampled chunks). "
        f"Chunking fixed at chunk_size={CHUNK_SIZE}, chunk_overlap={CHUNK_OVERLAP} (matching how "
        "the eval set's gold_chunk_id values were assigned). Each stage adds exactly one pipeline "
        "capability on top of the previous one; stage 4 matches the app's production retrieval "
        "config (RRF weights, rerank mode, multi-query count) at the time of this run.",
        "",
        "| Stage | Recall@5 | Recall@10 | Recall@15 | MRR | nDCG@10 | Avg latency (ms) |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in results:
        lines.append(
            f"| {r['stage']} | {r['recall_at_5']:.3f} | {r['recall_at_10']:.3f} | "
            f"{r['recall_at_15']:.3f} | {r['mrr']:.3f} | {r['ndcg_at_10']:.3f} | "
            f"{r['avg_latency_ms']:.0f} |"
        )
    REPORT_PATH.write_text("\n".join(lines) + "\n")
    print(f"\nWrote {RESULTS_PATH} and {REPORT_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
