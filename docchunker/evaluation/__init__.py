"""
Retrieval evaluation framework: measure how well produced chunks support
retrieval, and compare DocChunker configurations empirically.
"""

from docchunker.evaluation.dataset import EvalDataset, EvalQuery
from docchunker.evaluation.evaluator import (
    ConfigComparison,
    EvalReport,
    QueryResult,
    RetrievalEvaluator,
    compare_configs,
)
from docchunker.evaluation.retrievers import Bm25Retriever, KeywordRetriever, Retriever

__all__ = [
    "Bm25Retriever",
    "ConfigComparison",
    "EvalDataset",
    "EvalQuery",
    "EvalReport",
    "KeywordRetriever",
    "QueryResult",
    "Retriever",
    "RetrievalEvaluator",
    "compare_configs",
]
