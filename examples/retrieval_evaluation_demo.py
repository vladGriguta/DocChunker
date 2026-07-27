"""
Retrieval evaluation example for the DocChunker library.

This example demonstrates how to:
1. Build a small evaluation dataset (queries + relevance criteria)
2. Evaluate how well the produced chunks support retrieval (BM25, no ML deps)
3. Compare several chunking configurations empirically to pick parameters
"""

import sys
from pathlib import Path

# Add parent directory to sys.path to import docchunker
sys.path.append(str(Path(__file__).parent.parent))

from docchunker import (
    Bm25Retriever,
    DocChunker,
    EvalDataset,
    EvalQuery,
    KeywordRetriever,
    RetrievalEvaluator,
    compare_configs,
)


def build_dataset(document_path: Path) -> EvalDataset:
    """Build a small evaluation dataset against data/unittests/nested_lists.docx.

    Each query pairs realistic user phrasing with a relevance criterion:
    either an exact substring the relevant chunk must contain, or a set of
    expected keywords (a chunk is relevant when it contains at least
    `keyword_threshold` of them).

    Datasets can also be loaded from JSON/YAML via EvalDataset.from_file().
    """
    return EvalDataset(
        document_path=document_path,
        queries=[
            EvalQuery(
                id="password-recovery",
                query="how does password recovery work",
                expected_substring="Password recovery",
            ),
            EvalQuery(
                id="frontend-team",
                query="which department does the frontend team belong to",
                expected_keywords=["Frontend Team", "Engineering"],
            ),
            EvalQuery(
                id="testing-checklist",
                query="what is in the testing checklist",
                expected_keywords=["Testing Checklist", "Test case"],
            ),
            EvalQuery(
                id="implementation-steps",
                query="implementation steps for core features",
                expected_substring="Implement Core Features",
            ),
        ],
    )


def main():
    root_dir = Path(__file__).parent.parent
    document_path = root_dir / "data" / "unittests" / "nested_lists.docx"

    if not document_path.exists():
        print(f"Document not found: {document_path}")
        return

    print("=== DocChunker Retrieval Evaluation Example ===")
    print(f"Document: {document_path.name}")

    dataset = build_dataset(document_path)
    print(f"Dataset: {len(dataset)} queries")

    # --- 1. Evaluate a single configuration with BM25 -----------------------
    print("\n--- BM25 retriever, chunk_size=500 ---")
    evaluator = RetrievalEvaluator(
        chunker=DocChunker(chunk_size=500),
        retriever=Bm25Retriever(),
    )
    report = evaluator.evaluate(dataset, k=5)
    print(report)

    # --- 2. Same configuration, keyword-overlap baseline --------------------
    print("\n--- KeywordRetriever baseline, chunk_size=500 ---")
    baseline_evaluator = RetrievalEvaluator(
        chunker=DocChunker(chunk_size=500),
        retriever=KeywordRetriever(),
    )
    baseline_report = baseline_evaluator.evaluate(dataset, k=5)
    print(f"hit_rate@5: {baseline_report.hit_rate:.2f}  MRR: {baseline_report.mrr:.3f}")

    # --- 3. Compare chunking configurations empirically ---------------------
    # This is the point of the framework: pick chunk_size / overlap based on
    # measured retrieval quality instead of guessing.
    print("\n--- Config comparison (BM25, k=5) ---")
    comparison = compare_configs(
        document_path,
        dataset,
        configs=[
            {"chunk_size": 300},
            {"chunk_size": 500},
            {"chunk_size": 1000},
            {"chunk_size": 500, "num_overlapping_elements": 1},
            {"chunk_size": 1000, "num_overlapping_elements": 2},
        ],
        retriever_factory=Bm25Retriever,
        k=5,
    )
    print(comparison)

    best_config, best_report = comparison.best()
    print(f"\nBest config: {best_config} "
          f"(hit_rate@5={best_report.hit_rate:.2f}, MRR={best_report.mrr:.3f})")

    # To evaluate with your own embedding-based retriever, implement the
    # Retriever protocol (index/retrieve) and pass it to RetrievalEvaluator --
    # no changes to DocChunker required.


if __name__ == "__main__":
    main()
