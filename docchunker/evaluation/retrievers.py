"""
Lightweight lexical retrievers used to evaluate chunk quality.

Both built-in retrievers are dependency-free. To evaluate with an
embedding-based retriever (sentence-transformers, OpenAI embeddings, a vector
database, ...), implement the ``Retriever`` protocol -- ``index(chunks)`` and
``retrieve(query, k)`` -- and pass your instance to ``RetrievalEvaluator``.
No embedding dependency is required or bundled by DocChunker.
"""

import math
import re
from collections import Counter
from typing import Protocol, runtime_checkable

from docchunker.models.chunk import Chunk

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    """Lowercase word tokenizer shared by the built-in retrievers."""
    return _TOKEN_RE.findall(text.lower())


@runtime_checkable
class Retriever(Protocol):
    """Minimal retriever interface for retrieval evaluation.

    Any object with these two methods can be used with
    ``RetrievalEvaluator`` -- e.g. a wrapper around an embedding model or a
    vector store. Scores only need to be internally consistent (higher is
    more relevant); they are never compared across retrievers.
    """

    def index(self, chunks: list[Chunk]) -> None:
        """Build (or rebuild) the index over the given chunks."""
        ...

    def retrieve(self, query: str, k: int = 5) -> list[tuple[Chunk, float]]:
        """Return the top-k chunks with scores, best first."""
        ...


class Bm25Retriever:
    """BM25 (Okapi) ranking over chunk texts. No external dependencies.

    Args:
        k1: Term-frequency saturation parameter. Default: 1.5.
        b: Length-normalization parameter. Default: 0.75.
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self._chunks: list[Chunk] = []
        self._doc_term_counts: list[Counter[str]] = []
        self._doc_lengths: list[int] = []
        self._avg_doc_length: float = 0.0
        self._doc_freq: Counter[str] = Counter()

    def index(self, chunks: list[Chunk]) -> None:
        self._chunks = list(chunks)
        self._doc_term_counts = []
        self._doc_lengths = []
        self._doc_freq = Counter()
        for chunk in self._chunks:
            tokens = tokenize(chunk.text)
            counts = Counter(tokens)
            self._doc_term_counts.append(counts)
            self._doc_lengths.append(len(tokens))
            self._doc_freq.update(counts.keys())
        total = sum(self._doc_lengths)
        self._avg_doc_length = total / len(self._chunks) if self._chunks else 0.0

    def _idf(self, term: str) -> float:
        n = len(self._chunks)
        df = self._doc_freq.get(term, 0)
        return math.log((n - df + 0.5) / (df + 0.5) + 1.0)

    def retrieve(self, query: str, k: int = 5) -> list[tuple[Chunk, float]]:
        query_terms = tokenize(query)
        scored: list[tuple[Chunk, float]] = []
        for chunk, counts, length in zip(
            self._chunks, self._doc_term_counts, self._doc_lengths
        ):
            score = 0.0
            for term in query_terms:
                tf = counts.get(term, 0)
                if tf == 0:
                    continue
                norm = 1.0 - self.b + self.b * (length / self._avg_doc_length)
                score += self._idf(term) * tf * (self.k1 + 1) / (tf + self.k1 * norm)
            if score > 0.0:
                scored.append((chunk, score))
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return scored[:k]


class KeywordRetriever:
    """Baseline retriever scoring chunks by query-term overlap.

    The score is the fraction of unique query terms present in the chunk.
    Useful as a sanity baseline against BM25.
    """

    def __init__(self) -> None:
        self._chunks: list[Chunk] = []
        self._doc_terms: list[set[str]] = []

    def index(self, chunks: list[Chunk]) -> None:
        self._chunks = list(chunks)
        self._doc_terms = [set(tokenize(chunk.text)) for chunk in self._chunks]

    def retrieve(self, query: str, k: int = 5) -> list[tuple[Chunk, float]]:
        query_terms = set(tokenize(query))
        if not query_terms:
            return []
        scored: list[tuple[Chunk, float]] = []
        for chunk, terms in zip(self._chunks, self._doc_terms):
            overlap = len(query_terms & terms)
            if overlap:
                scored.append((chunk, overlap / len(query_terms)))
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return scored[:k]
