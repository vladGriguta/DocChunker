"""
Retrieval evaluation: score how well produced chunks support retrieval.
"""

import statistics
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from docchunker.chunker import DocChunker
from docchunker.evaluation.dataset import EvalDataset, EvalQuery
from docchunker.evaluation.retrievers import Bm25Retriever, Retriever
from docchunker.models.chunk import Chunk


def _chunk_matches_query(
    chunk: Chunk, query: EvalQuery, keyword_threshold: float
) -> bool:
    """True if the chunk satisfies the query's relevance criterion."""
    text = chunk.text.lower()
    if query.expected_substring is not None:
        if query.expected_substring.lower() in text:
            return True
    if query.expected_keywords:
        found = sum(1 for kw in query.expected_keywords if kw.lower() in text)
        if found / len(query.expected_keywords) >= keyword_threshold:
            return True
    return False


def _percentile(sorted_values: list[int], fraction: float) -> float:
    """Nearest-rank percentile over a pre-sorted list."""
    if not sorted_values:
        return 0.0
    index = min(len(sorted_values) - 1, max(0, round(fraction * (len(sorted_values) - 1))))
    return float(sorted_values[index])


@dataclass
class QueryResult:
    """Outcome of a single evaluation query.

    ``rank`` is the 1-based position of the first relevant chunk in the
    top-k results, or None if no relevant chunk was retrieved.
    """

    query_id: str
    query: str
    rank: int | None
    num_retrieved: int

    @property
    def hit(self) -> bool:
        return self.rank is not None

    @property
    def reciprocal_rank(self) -> float:
        return 1.0 / self.rank if self.rank is not None else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "query_id": self.query_id,
            "query": self.query,
            "rank": self.rank,
            "hit": self.hit,
            "reciprocal_rank": self.reciprocal_rank,
            "num_retrieved": self.num_retrieved,
        }


@dataclass
class EvalReport:
    """Aggregated retrieval evaluation results for one chunking run."""

    k: int
    results: list[QueryResult]
    num_chunks: int
    mean_chunk_size: float
    median_chunk_size: float
    p95_chunk_size: float

    @property
    def hit_rate(self) -> float:
        if not self.results:
            return 0.0
        return sum(1 for r in self.results if r.hit) / len(self.results)

    @property
    def mrr(self) -> float:
        if not self.results:
            return 0.0
        return sum(r.reciprocal_rank for r in self.results) / len(self.results)

    def to_dict(self) -> dict[str, Any]:
        return {
            "k": self.k,
            "hit_rate": self.hit_rate,
            "mrr": self.mrr,
            "num_queries": len(self.results),
            "num_chunks": self.num_chunks,
            "mean_chunk_size": self.mean_chunk_size,
            "median_chunk_size": self.median_chunk_size,
            "p95_chunk_size": self.p95_chunk_size,
            "results": [r.to_dict() for r in self.results],
        }

    def __str__(self) -> str:
        lines = [
            f"Retrieval evaluation (k={self.k}, {len(self.results)} queries)",
            f"  hit_rate@{self.k}: {self.hit_rate:.2f}",
            f"  MRR:        {self.mrr:.3f}",
            f"  chunks:     {self.num_chunks} "
            f"(mean {self.mean_chunk_size:.0f} / median {self.median_chunk_size:.0f}"
            f" / p95 {self.p95_chunk_size:.0f} chars)",
            "",
            f"  {'query':40} {'rank':>5}",
            f"  {'-' * 40} {'-' * 5}",
        ]
        for result in self.results:
            label = result.query_id if len(result.query_id) <= 40 else result.query_id[:37] + "..."
            rank = str(result.rank) if result.rank is not None else "miss"
            lines.append(f"  {label:40} {rank:>5}")
        return "\n".join(lines)


@dataclass
class ConfigComparison:
    """Result of ``compare_configs``: one (config, EvalReport) row per config."""

    k: int
    rows: list[tuple[dict[str, Any], EvalReport]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "k": self.k,
            "rows": [
                {"config": config, "report": report.to_dict()}
                for config, report in self.rows
            ],
        }

    def best(self) -> tuple[dict[str, Any], EvalReport]:
        """The row with the highest hit rate (MRR breaks ties)."""
        if not self.rows:
            raise ValueError("No configs were compared")
        return max(self.rows, key=lambda row: (row[1].hit_rate, row[1].mrr))

    def __str__(self) -> str:
        labels = [
            ", ".join(f"{key}={value}" for key, value in config.items())
            for config, _report in self.rows
        ]
        width = max([len("config")] + [len(label) for label in labels])
        header = (
            f"{'config':{width}} {'chunks':>6} {'mean_sz':>8} "
            f"{'hit_rate@' + str(self.k):>10} {'mrr':>6}"
        )
        lines = [header, "-" * len(header)]
        for label, (_config, report) in zip(labels, self.rows):
            lines.append(
                f"{label:{width}} {report.num_chunks:>6} "
                f"{report.mean_chunk_size:>8.0f} {report.hit_rate:>10.2f} "
                f"{report.mrr:>6.3f}"
            )
        return "\n".join(lines)


class RetrievalEvaluator:
    """Evaluates how well a chunker's output supports retrieval.

    Chunks the dataset's document with ``chunker``, indexes the chunks with
    ``retriever``, and checks for each query whether a relevant chunk appears
    in the top-k results.

    Args:
        chunker: The DocChunker configuration under evaluation.
        retriever: Any object implementing the ``Retriever`` protocol.
            Defaults to ``Bm25Retriever``. Plug in an embedding-based
            retriever here for semantic evaluation.
    """

    def __init__(self, chunker: DocChunker, retriever: Retriever | None = None):
        self.chunker = chunker
        self.retriever = retriever if retriever is not None else Bm25Retriever()

    def evaluate(
        self,
        dataset: EvalDataset,
        k: int = 5,
        keyword_threshold: float = 0.8,
        document_path: str | Path | None = None,
    ) -> EvalReport:
        """Chunk the document and evaluate all dataset queries.

        Args:
            dataset: Queries plus (optionally) the document path.
            k: Number of chunks to retrieve per query.
            keyword_threshold: Minimum fraction of ``expected_keywords`` a
                chunk must contain to count as relevant. Default: 0.8.
            document_path: Overrides ``dataset.document_path`` if given.

        Returns:
            An EvalReport with per-query ranks and aggregate metrics.
        """
        path = document_path if document_path is not None else dataset.document_path
        if path is None:
            raise ValueError(
                "No document to evaluate: set dataset.document_path or pass document_path"
            )
        chunks = self.chunker.process_document(path)
        return self.evaluate_chunks(chunks, dataset, k=k, keyword_threshold=keyword_threshold)

    def evaluate_chunks(
        self,
        chunks: list[Chunk],
        dataset: EvalDataset,
        k: int = 5,
        keyword_threshold: float = 0.8,
    ) -> EvalReport:
        """Evaluate dataset queries against pre-computed chunks."""
        self.retriever.index(chunks)
        results: list[QueryResult] = []
        for query in dataset.queries:
            retrieved = self.retriever.retrieve(query.query, k=k)
            rank: int | None = None
            for position, (chunk, _score) in enumerate(retrieved, start=1):
                if _chunk_matches_query(chunk, query, keyword_threshold):
                    rank = position
                    break
            results.append(
                QueryResult(
                    query_id=query.id or query.query,
                    query=query.query,
                    rank=rank,
                    num_retrieved=len(retrieved),
                )
            )

        sizes = sorted(len(chunk.text) for chunk in chunks)
        return EvalReport(
            k=k,
            results=results,
            num_chunks=len(chunks),
            mean_chunk_size=statistics.mean(sizes) if sizes else 0.0,
            median_chunk_size=statistics.median(sizes) if sizes else 0.0,
            p95_chunk_size=_percentile(sizes, 0.95),
        )


def compare_configs(
    document_path: str | Path,
    dataset: EvalDataset,
    configs: list[dict[str, Any]],
    retriever_factory: Callable[[], Retriever] = Bm25Retriever,
    k: int = 5,
    keyword_threshold: float = 0.8,
) -> ConfigComparison:
    """Run the evaluator across several DocChunker configurations.

    This is the main entry point for picking chunking parameters
    empirically: pass candidate configs and compare hit rate / MRR.

    Args:
        document_path: Document to chunk under each configuration.
        dataset: Evaluation queries.
        configs: DocChunker keyword-argument dicts, e.g.
            ``[{"chunk_size": 500}, {"chunk_size": 1000, "num_overlapping_elements": 1}]``.
        retriever_factory: Zero-argument callable producing a fresh Retriever
            per config. Default: ``Bm25Retriever``.
        k: Number of chunks to retrieve per query.
        keyword_threshold: See ``RetrievalEvaluator.evaluate``.

    Returns:
        A ConfigComparison; ``print()`` it for a summary table, or call
        ``.best()`` for the top-scoring config.
    """
    comparison = ConfigComparison(k=k)
    for config in configs:
        chunker = DocChunker(**config)
        evaluator = RetrievalEvaluator(chunker, retriever_factory())
        report = evaluator.evaluate(
            dataset, k=k, keyword_threshold=keyword_threshold, document_path=document_path
        )
        comparison.rows.append((config, report))
    return comparison
