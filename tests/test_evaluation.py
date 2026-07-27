"""Tests for the retrieval evaluation framework."""

import json
from pathlib import Path

import pytest
import yaml

from docchunker import DocChunker
from docchunker.evaluation import (
    Bm25Retriever,
    EvalDataset,
    EvalQuery,
    KeywordRetriever,
    Retriever,
    RetrievalEvaluator,
    compare_configs,
)
from docchunker.models.chunk import Chunk


def make_chunk(text: str) -> Chunk:
    return Chunk(text=text, metadata={"node_type": "paragraph"})


SYNTHETIC_CHUNKS = [
    make_chunk("The quick brown fox jumps over the lazy dog in the forest."),
    make_chunk("Password recovery requires email verification and a reset token."),
    make_chunk("The engineering department contains the frontend team and backend team."),
    make_chunk("Quarterly revenue grew by twelve percent according to the finance report."),
    make_chunk("The dog slept all day. The dog is very lazy. Dog dog dog."),
]


class TestBm25Retriever:
    def test_ranks_relevant_chunk_first(self):
        retriever = Bm25Retriever()
        retriever.index(SYNTHETIC_CHUNKS)
        results = retriever.retrieve("password recovery reset token", k=3)
        assert results, "expected at least one result"
        top_chunk, top_score = results[0]
        assert "Password recovery" in top_chunk.text
        assert top_score > 0

    def test_scores_sorted_descending(self):
        retriever = Bm25Retriever()
        retriever.index(SYNTHETIC_CHUNKS)
        results = retriever.retrieve("the lazy dog", k=5)
        scores = [score for _, score in results]
        assert scores == sorted(scores, reverse=True)

    def test_no_match_returns_empty(self):
        retriever = Bm25Retriever()
        retriever.index(SYNTHETIC_CHUNKS)
        assert retriever.retrieve("zzz qqq xyzzy", k=5) == []

    def test_respects_k(self):
        retriever = Bm25Retriever()
        retriever.index(SYNTHETIC_CHUNKS)
        assert len(retriever.retrieve("the dog", k=1)) == 1

    def test_idf_downweights_common_terms(self):
        # "the" appears everywhere; "revenue" only in the finance chunk.
        retriever = Bm25Retriever()
        retriever.index(SYNTHETIC_CHUNKS)
        results = retriever.retrieve("the revenue", k=5)
        top_chunk, _ = results[0]
        assert "revenue" in top_chunk.text.lower()


class TestKeywordRetriever:
    def test_overlap_scoring(self):
        retriever = KeywordRetriever()
        retriever.index(SYNTHETIC_CHUNKS)
        results = retriever.retrieve("frontend team engineering", k=2)
        top_chunk, top_score = results[0]
        assert "frontend team" in top_chunk.text.lower()
        assert top_score == 1.0  # all three query terms present

    def test_satisfies_retriever_protocol(self):
        assert isinstance(KeywordRetriever(), Retriever)
        assert isinstance(Bm25Retriever(), Retriever)


class TestEvalQuery:
    def test_requires_a_relevance_criterion(self):
        with pytest.raises(ValueError):
            EvalQuery(query="no criteria")

    def test_id_defaults_to_query(self):
        query = EvalQuery(query="q1", expected_keywords=["a"])
        assert query.id == "q1"


class TestEvaluatorMath:
    """Hit/miss and MRR math on synthetic chunks."""

    def _evaluate(self, queries, k=3, keyword_threshold=0.8):
        dataset = EvalDataset(queries=queries)
        evaluator = RetrievalEvaluator(DocChunker(), Bm25Retriever())
        return evaluator.evaluate_chunks(
            SYNTHETIC_CHUNKS, dataset, k=k, keyword_threshold=keyword_threshold
        )

    def test_hit_at_rank_one(self):
        report = self._evaluate(
            [EvalQuery(query="password recovery token", expected_substring="reset token")]
        )
        assert report.results[0].rank == 1
        assert report.hit_rate == 1.0
        assert report.mrr == 1.0

    def test_miss(self):
        report = self._evaluate(
            [EvalQuery(query="password recovery", expected_substring="not in any chunk")]
        )
        assert report.results[0].rank is None
        assert report.hit_rate == 0.0
        assert report.mrr == 0.0

    def test_mrr_averages_reciprocal_ranks(self):
        report = self._evaluate(
            [
                # Hit at rank 1.
                EvalQuery(query="password recovery token", expected_substring="reset token"),
                # Miss: query matches chunks, but criterion never satisfied.
                EvalQuery(query="lazy dog", expected_substring="not present anywhere"),
            ]
        )
        assert report.hit_rate == 0.5
        assert report.mrr == pytest.approx(0.5)

    def test_rank_two_hit(self):
        # "dog dog dog" chunk outranks the fox chunk for this query;
        # the substring criterion only matches the fox chunk.
        report = self._evaluate(
            [EvalQuery(query="lazy dog", expected_substring="quick brown fox")]
        )
        assert report.results[0].rank == 2
        assert report.mrr == pytest.approx(0.5)

    def test_keyword_threshold(self):
        # 2 of 3 keywords present in the finance chunk (~0.67).
        query_kwargs = {
            "query": "quarterly revenue",
            "expected_keywords": ["revenue", "finance", "nonexistent"],
        }
        strict = self._evaluate([EvalQuery(**query_kwargs)], keyword_threshold=0.8)
        assert strict.results[0].rank is None
        lenient = self._evaluate([EvalQuery(**query_kwargs)], keyword_threshold=0.5)
        assert lenient.results[0].rank == 1

    def test_chunk_size_stats(self):
        report = self._evaluate(
            [EvalQuery(query="dog", expected_keywords=["dog"])]
        )
        sizes = [len(c.text) for c in SYNTHETIC_CHUNKS]
        assert report.num_chunks == len(SYNTHETIC_CHUNKS)
        assert report.mean_chunk_size == pytest.approx(sum(sizes) / len(sizes))
        assert min(sizes) <= report.median_chunk_size <= max(sizes)
        assert report.p95_chunk_size <= max(sizes)

    def test_report_serialization(self):
        report = self._evaluate(
            [EvalQuery(query="dog", expected_keywords=["dog"], id="dog-query")]
        )
        data = report.to_dict()
        assert set(data) >= {
            "k", "hit_rate", "mrr", "num_queries", "num_chunks",
            "mean_chunk_size", "median_chunk_size", "p95_chunk_size", "results",
        }
        assert data["results"][0]["query_id"] == "dog-query"
        text = str(report)
        assert "hit_rate" in text and "dog-query" in text


class TestDatasetLoading:
    PAYLOAD = {
        "document_path": "some/doc.docx",
        "queries": [
            {
                "id": "q1",
                "query": "how do I reset my password",
                "expected_substring": "Password recovery",
            },
            {
                "query": "team structure",
                "expected_keywords": ["frontend", "backend"],
            },
        ],
    }

    def _check(self, dataset: EvalDataset):
        assert dataset.document_path == "some/doc.docx"
        assert len(dataset) == 2
        assert dataset.queries[0].id == "q1"
        assert dataset.queries[0].expected_substring == "Password recovery"
        assert dataset.queries[1].expected_keywords == ["frontend", "backend"]

    def test_from_json(self, tmp_path: Path):
        path = tmp_path / "dataset.json"
        path.write_text(json.dumps(self.PAYLOAD), encoding="utf-8")
        self._check(EvalDataset.from_file(path))

    def test_from_yaml(self, tmp_path: Path):
        path = tmp_path / "dataset.yaml"
        path.write_text(yaml.safe_dump(self.PAYLOAD), encoding="utf-8")
        self._check(EvalDataset.from_file(path))

    def test_roundtrip(self):
        dataset = EvalDataset.from_dict(self.PAYLOAD)
        assert EvalDataset.from_dict(dataset.to_dict()).to_dict() == dataset.to_dict()

    def test_evaluate_without_document_path_raises(self):
        dataset = EvalDataset(queries=[EvalQuery(query="q", expected_keywords=["q"])])
        evaluator = RetrievalEvaluator(DocChunker())
        with pytest.raises(ValueError):
            evaluator.evaluate(dataset)


class TestEndToEnd:
    DOCUMENT = Path(__file__).parent.parent / "data" / "unittests" / "nested_lists.docx"

    DATASET = EvalDataset(
        queries=[
            EvalQuery(
                id="password-recovery",
                query="password recovery",
                expected_substring="Password recovery",
            ),
            EvalQuery(
                id="frontend-team",
                query="frontend team organizational structure",
                expected_keywords=["Frontend Team"],
            ),
            EvalQuery(
                id="unanswerable",
                query="giraffe astrophysics",
                expected_substring="this text does not appear in the document",
            ),
        ],
    )

    def test_evaluate_real_document(self):
        evaluator = RetrievalEvaluator(DocChunker(chunk_size=500), Bm25Retriever())
        report = evaluator.evaluate(self.DATASET, k=5, document_path=self.DOCUMENT)

        assert report.num_chunks > 0
        assert len(report.results) == 3
        assert 0.0 <= report.hit_rate <= 1.0
        assert 0.0 <= report.mrr <= 1.0
        for result in report.results:
            assert result.rank is None or 1 <= result.rank <= 5
        # The unanswerable query must never be a hit.
        by_id = {r.query_id: r for r in report.results}
        assert by_id["unanswerable"].rank is None
        # Report renders without error.
        assert "hit_rate" in str(report)

    def test_compare_configs(self):
        comparison = compare_configs(
            self.DOCUMENT,
            self.DATASET,
            configs=[
                {"chunk_size": 300},
                {"chunk_size": 1000, "num_overlapping_elements": 1},
            ],
            k=5,
        )
        assert len(comparison.rows) == 2
        for config, report in comparison.rows:
            assert "chunk_size" in config
            assert report.num_chunks > 0
        best_config, best_report = comparison.best()
        assert best_report.hit_rate == max(r.hit_rate for _, r in comparison.rows)
        table = str(comparison)
        assert "hit_rate@5" in table and "chunk_size=300" in table
