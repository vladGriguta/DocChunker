"""
Evaluation dataset models: queries with relevance criteria against a document.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class EvalQuery:
    """A single retrieval evaluation query.

    A retrieved chunk is considered relevant to this query if it contains
    ``expected_substring`` (case-insensitive), or if it contains at least a
    configurable fraction of ``expected_keywords`` (see
    ``RetrievalEvaluator.evaluate``'s ``keyword_threshold``).

    Args:
        query: The natural-language query text.
        expected_keywords: Keywords the relevant chunk is expected to contain.
        expected_substring: An exact substring the relevant chunk must contain.
        id: Optional identifier for reporting. Defaults to the query text.
    """

    query: str
    expected_keywords: list[str] = field(default_factory=list)
    expected_substring: str | None = None
    id: str | None = None

    def __post_init__(self) -> None:
        if not self.expected_keywords and self.expected_substring is None:
            raise ValueError(
                f"EvalQuery {self.query!r} needs expected_keywords and/or expected_substring"
            )
        if self.id is None:
            self.id = self.query

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvalQuery":
        return cls(
            query=data["query"],
            expected_keywords=list(data.get("expected_keywords", [])),
            expected_substring=data.get("expected_substring"),
            id=data.get("id"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "query": self.query,
            "expected_keywords": self.expected_keywords,
            "expected_substring": self.expected_substring,
        }


@dataclass
class EvalDataset:
    """A set of evaluation queries, optionally tied to a document path.

    Args:
        queries: The evaluation queries.
        document_path: Path to the document the queries are written against.
    """

    queries: list[EvalQuery]
    document_path: str | Path | None = None

    def __len__(self) -> int:
        return len(self.queries)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvalDataset":
        return cls(
            queries=[EvalQuery.from_dict(q) for q in data.get("queries", [])],
            document_path=data.get("document_path"),
        )

    @classmethod
    def from_file(cls, file_path: str | Path) -> "EvalDataset":
        """Load a dataset from a JSON or YAML file.

        Expected structure::

            {
              "document_path": "path/to/document.docx",   # optional
              "queries": [
                {"query": "...", "expected_keywords": ["..."],
                 "expected_substring": "...", "id": "..."}
              ]
            }
        """
        path = Path(file_path)
        with open(path, encoding="utf-8") as f:
            if path.suffix.lower() in (".yaml", ".yml"):
                data = yaml.safe_load(f)
            else:
                data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError(f"Invalid dataset file (expected a mapping): {path}")
        return cls.from_dict(data)

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_path": str(self.document_path) if self.document_path else None,
            "queries": [q.to_dict() for q in self.queries],
        }
