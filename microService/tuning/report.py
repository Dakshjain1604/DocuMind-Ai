"""Generate reports from sweep results.

Creates:
- tuning/results.csv (one row per config)
- tuning/results.md (sorted leaderboard, top 10)
- tuning/best_config.json (winning combo)
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Any

# Configuration
RESULTS_DIR = Path("microService/tuning/results")
OUTPUT_CSV = Path("microService/tuning/results.csv")
OUTPUT_MD = Path("microService/tuning/results.md")
OUTPUT_BEST_CONFIG = Path("microService/tuning/best_config.json")
APP_CONFIG_PATH = Path("microService/app/config/retrieval.json")

# Default configuration (current settings)
DEFAULT_CONFIG = {
    "chunk_size": 1000,
    "chunk_overlap": 150,
    "per_retriever_top_k": 10,
    "fused_top_k": 15,
    "vector_weight": 1.0,
    "bm25_weight": 1.0,
    "graph_weight": 1.0,
    "rrf_k": 60,
    "rerank_mode": "off",
    "multi_query_n": 0,
}


def load_results(results_dir: Path) -> list[dict]:
    """Load all sweep results from JSON files."""
    results = []
    
    if not results_dir.exists():
        print(f"ERROR: Results directory not found: {results_dir}")
        print("Please run sweep.py first")
        sys.exit(1)
    
    json_files = list(results_dir.glob("*.json"))
    
    if not json_files:
        print(f"ERROR: No result files found in {results_dir}")
        print("Please run sweep.py first")
        sys.exit(1)
    
    for json_file in json_files:
        if json_file.name == "all_results.json":
            continue  # Skip the combined file
        try:
            with open(json_file) as f:
                result = json.load(f)
                results.append(result)
        except Exception as e:
            print(f"Warning: Failed to load {json_file}: {e}")
    
    print(f"Loaded {len(results)} sweep results")
    return results


def compute_score(result: dict) -> float:
    """Compute composite score for ranking.
    
    Weights:
    - Recall@5: 0.4 (most important - top results matter)
    - MRR: 0.3 (rank quality matters)
    - nDCG@10: 0.3 (overall ranking quality)
    """
    return (
        0.4 * result.get("recall_at_5", 0) +
        0.3 * result.get("mrr", 0) +
        0.3 * result.get("ndcg_at_10", 0)
    )


def find_default_result(results: list[dict]) -> dict | None:
    """Find the result matching default configuration."""
    for result in results:
        if (
            result.get("chunk_size") == DEFAULT_CONFIG["chunk_size"] and
            result.get("chunk_overlap") == DEFAULT_CONFIG["chunk_overlap"] and
            result.get("per_retriever_top_k") == DEFAULT_CONFIG["per_retriever_top_k"] and
            result.get("fused_top_k") == DEFAULT_CONFIG["fused_top_k"] and
            abs(result.get("vector_weight", 1.0) - DEFAULT_CONFIG["vector_weight"]) < 0.01 and
            abs(result.get("bm25_weight", 1.0) - DEFAULT_CONFIG["bm25_weight"]) < 0.01 and
            abs(result.get("graph_weight", 1.0) - DEFAULT_CONFIG["graph_weight"]) < 0.01 and
            result.get("rerank_mode", "off") == DEFAULT_CONFIG["rerank_mode"] and
            result.get("multi_query_n", 0) == DEFAULT_CONFIG["multi_query_n"]
        ):
            return result
    return None


def generate_csv(results: list[dict], output_path: Path) -> None:
    """Generate CSV report."""
    if not results:
        print("No results to write")
        return
    
    # Define columns
    columns = [
        "chunk_size",
        "chunk_overlap",
        "per_retriever_top_k",
        "fused_top_k",
        "vector_weight",
        "bm25_weight",
        "graph_weight",
        "rrf_k",
        "rerank_mode",
        "multi_query_n",
        "recall_at_5",
        "recall_at_10",
        "recall_at_15",
        "mrr",
        "ndcg_at_10",
        "avg_latency_ms",
        "total_questions",
        "composite_score",
    ]
    
    # Sort by composite score
    sorted_results = sorted(results, key=compute_score, reverse=True)
    
    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        
        for result in sorted_results:
            row = {col: result.get(col, "") for col in columns}
            row["composite_score"] = round(compute_score(result), 4)
            writer.writerow(row)
    
    print(f"✓ CSV report saved: {output_path}")


def generate_markdown(results: list[dict], output_path: Path) -> None:
    """Generate Markdown leaderboard report."""
    if not results:
        print("No results to write")
        return
    
    # Sort by composite score
    sorted_results = sorted(results, key=compute_score, reverse=True)
    
    # Find default result
    default_result = find_default_result(results)
    
    lines = [
        "# GraphRAG Retrieval Parameter Sweep Results",
        "",
        "## Summary",
        "",
        f"- **Total Configurations Evaluated:** {len(results)}",
        f"- **Evaluation Questions:** {sorted_results[0].get('total_questions', 'N/A')}",
        "",
        "## Top 10 Configurations",
        "",
        "| Rank | Chunk Size | Overlap | Retriever K | Fused K | Weights (V/B/G) | Rerank | MQ-N | R@5 | R@10 | R@15 | MRR | nDCG@10 | Latency (ms) | Score |",
        "|------|------------|---------|-------------|---------|-----------------|--------|------|-----|------|------|-----|---------|--------------|-------|",
    ]

    for i, result in enumerate(sorted_results[:10], 1):
        weights = f"{result.get('vector_weight', 1.0):.1f}/{result.get('bm25_weight', 1.0):.1f}/{result.get('graph_weight', 1.0):.1f}"

        # Highlight if this is the best
        marker = " 🏆" if i == 1 else ""

        lines.append(
            f"| {i}{marker} | "
            f"{result.get('chunk_size', 'N/A')} | "
            f"{result.get('chunk_overlap', 'N/A')} | "
            f"{result.get('per_retriever_top_k', 'N/A')} | "
            f"{result.get('fused_top_k', 'N/A')} | "
            f"{weights} | "
            f"{result.get('rerank_mode', 'off')} | "
            f"{result.get('multi_query_n', 0)} | "
            f"{result.get('recall_at_5', 0):.3f} | "
            f"{result.get('recall_at_10', 0):.3f} | "
            f"{result.get('recall_at_15', 0):.3f} | "
            f"{result.get('mrr', 0):.3f} | "
            f"{result.get('ndcg_at_10', 0):.3f} | "
            f"{result.get('avg_latency_ms', 0):.0f} | "
            f"{compute_score(result):.3f} |"
        )
    
    # Add default comparison
    if default_result:
        lines.extend([
            "",
            "## Default Configuration Comparison",
            "",
            f"**Default Config:** chunk_size={DEFAULT_CONFIG['chunk_size']}, "
            f"chunk_overlap={DEFAULT_CONFIG['chunk_overlap']}, "
            f"per_retriever_top_k={DEFAULT_CONFIG['per_retriever_top_k']}, "
            f"fused_top_k={DEFAULT_CONFIG['fused_top_k']}, "
            f"weights=1.0/1.0/1.0",
            "",
            "| Metric | Default | Best | Delta |",
            "|--------|---------|------|-------|",
        ])
        
        best = sorted_results[0]
        
        metrics = [
            ("Recall@5", "recall_at_5"),
            ("Recall@10", "recall_at_10"),
            ("Recall@15", "recall_at_15"),
            ("MRR", "mrr"),
            ("nDCG@10", "ndcg_at_10"),
        ]
        
        for label, key in metrics:
            default_val = default_result.get(key, 0)
            best_val = best.get(key, 0)
            delta = best_val - default_val
            delta_str = f"+{delta:.3f}" if delta >= 0 else f"{delta:.3f}"
            lines.append(f"| {label} | {default_val:.3f} | {best_val:.3f} | {delta_str} |")
    
    # Add methodology
    lines.extend([
        "",
        "## Methodology",
        "",
        "### Parameter Grid",
        "",
        "- **chunk_size:** {500, 800, 1000, 1400}",
        "- **chunk_overlap:** {100, 200}",
        "- **per_retriever_top_k:** {10, 20}",
        "- **fused_top_k:** {10, 15, 25}",
        "- **RRF Weights:**",
        "  - (vector=1.0, bm25=1.0, graph=1.0)",
        "  - (vector=1.0, bm25=0.7, graph=0.5)",
        "  - (vector=1.0, bm25=1.0, graph=0.3)",
        "- **rerank_mode:** {off, cross_encoder} (llm excluded from the grid — rate-limit sensitive)",
        "- **multi_query_n:** {0, 3}",
        "",
        "### Metrics",
        "",
        "- **Recall@K:** Percentage of questions where gold chunk is in top-K results",
        "- **MRR:** Mean Reciprocal Rank of gold chunk in fused results",
        "- **nDCG@10:** Normalized Discounted Cumulative Gain at position 10",
        "- **avg_latency_ms:** Mean per-question wall-clock time (rewrite + retrieval + fusion + rerank)",
        "- **Composite Score:** 0.4*R@5 + 0.3*MRR + 0.3*nDCG@10 (latency reported alongside, not folded into ranking)",
        "",
        "### Evaluation Set",
        "",
        "Questions were LLM-generated from 40 random chunks of the target PDF using OpenRouter",
        "(tuning/build_eval_set.py). Each question is designed to have its answer contained in",
        "exactly one chunk.",
    ])
    
    with open(output_path, "w") as f:
        f.write("\n".join(lines))
    
    print(f"✓ Markdown report saved: {output_path}")


def generate_best_config(results: list[dict], output_path: Path) -> dict:
    """Generate best configuration JSON."""
    if not results:
        print("No results to process")
        return {}
    
    # Sort by composite score
    sorted_results = sorted(results, key=compute_score, reverse=True)
    best = sorted_results[0]
    
    best_config = {
        "chunk_size": best.get("chunk_size"),
        "chunk_overlap": best.get("chunk_overlap"),
        "per_retriever_top_k": best.get("per_retriever_top_k"),
        "fused_top_k": best.get("fused_top_k"),
        "vector_weight": best.get("vector_weight"),
        "bm25_weight": best.get("bm25_weight"),
        "graph_weight": best.get("graph_weight"),
        "rrf_k": best.get("rrf_k", 60),
        "rerank_mode": best.get("rerank_mode", "off"),
        "multi_query_n": best.get("multi_query_n", 0),
        "metrics": {
            "recall_at_5": best.get("recall_at_5"),
            "recall_at_10": best.get("recall_at_10"),
            "recall_at_15": best.get("recall_at_15"),
            "mrr": best.get("mrr"),
            "ndcg_at_10": best.get("ndcg_at_10"),
            "avg_latency_ms": best.get("avg_latency_ms"),
            "composite_score": compute_score(best),
        },
    }
    
    with open(output_path, "w") as f:
        json.dump(best_config, f, indent=2)
    
    print(f"✓ Best config saved: {output_path}")
    
    return best_config


def write_app_config(best_config: dict, output_path: Path) -> None:
    """Write winning config to app/config/retrieval.json."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Only include the parameters needed by the app (read back by
    # app.config.settings.get_settings() with env-var overrides taking
    # precedence over these values).
    app_config = {
        "chunk_size": best_config.get("chunk_size"),
        "chunk_overlap": best_config.get("chunk_overlap"),
        "per_retriever_top_k": best_config.get("per_retriever_top_k"),
        "fused_top_k": best_config.get("fused_top_k"),
        "vector_weight": best_config.get("vector_weight"),
        "bm25_weight": best_config.get("bm25_weight"),
        "graph_weight": best_config.get("graph_weight"),
        "rrf_k": best_config.get("rrf_k", 60),
        "rerank_mode": best_config.get("rerank_mode", "off"),
        "multi_query_n": best_config.get("multi_query_n", 0),
    }
    
    with open(output_path, "w") as f:
        json.dump(app_config, f, indent=2)
    
    print(f"✓ App config saved: {output_path}")


def print_winner(best_config: dict, results: list[dict]) -> None:
    """Print winning configuration to stdout."""
    print("\n" + "=" * 70)
    print("🏆 WINNING CONFIGURATION")
    print("=" * 70)
    
    print(f"\nChunk Size: {best_config['chunk_size']}")
    print(f"Chunk Overlap: {best_config['chunk_overlap']}")
    print(f"Per-Retriever Top-K: {best_config['per_retriever_top_k']}")
    print(f"Fused Top-K: {best_config['fused_top_k']}")
    print(f"RRF Weights: vector={best_config['vector_weight']}, "
          f"bm25={best_config['bm25_weight']}, graph={best_config['graph_weight']}")
    print(f"Rerank Mode: {best_config.get('rerank_mode', 'off')}")
    print(f"Multi-Query N: {best_config.get('multi_query_n', 0)}")

    print(f"\n📊 Performance Metrics:")
    metrics = best_config.get("metrics", {})
    print(f"  Recall@5:  {metrics.get('recall_at_5', 0):.3f}")
    print(f"  Recall@10: {metrics.get('recall_at_10', 0):.3f}")
    print(f"  Recall@15: {metrics.get('recall_at_15', 0):.3f}")
    print(f"  MRR:       {metrics.get('mrr', 0):.3f}")
    print(f"  nDCG@10:   {metrics.get('ndcg_at_10', 0):.3f}")
    print(f"  Avg Latency: {metrics.get('avg_latency_ms', 0):.0f}ms")
    
    # Compare with default
    default_result = find_default_result(results)
    if default_result:
        print(f"\n📈 Delta vs Default:")
        print(f"  Recall@5:  {metrics.get('recall_at_5', 0) - default_result.get('recall_at_5', 0):+.3f}")
        print(f"  MRR:       {metrics.get('mrr', 0) - default_result.get('mrr', 0):+.3f}")
        print(f"  nDCG@10:   {metrics.get('ndcg_at_10', 0) - default_result.get('ndcg_at_10', 0):+.3f}")
    
    print("\n" + "=" * 70)


def main() -> None:
    """Main entry point."""
    print("=" * 70)
    print("GraphRAG Tuning Report Generator")
    print("=" * 70)
    
    # Load results
    print("\n1. Loading sweep results...")
    results = load_results(RESULTS_DIR)
    
    if not results:
        print("No results found. Exiting.")
        sys.exit(1)
    
    # Generate CSV
    print("\n2. Generating CSV report...")
    generate_csv(results, OUTPUT_CSV)
    
    # Generate Markdown
    print("\n3. Generating Markdown leaderboard...")
    generate_markdown(results, OUTPUT_MD)
    
    # Generate best config
    print("\n4. Generating best configuration...")
    best_config = generate_best_config(results, OUTPUT_BEST_CONFIG)
    
    # Write app config
    print("\n5. Writing app configuration...")
    write_app_config(best_config, APP_CONFIG_PATH)
    
    # Print winner
    print_winner(best_config, results)
    
    print("\n✓ Report generation complete!")


if __name__ == "__main__":
    main()
