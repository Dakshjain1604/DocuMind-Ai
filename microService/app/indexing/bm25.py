"""BM25 index over chunk text.

Lives in the indexing layer (not app/retrieval/search.py) because its on-disk
format — the tokenized corpus pickled to bm25_corpus.pkl — is produced by
app/indexing/store.py and consumed by retrieval. Placing it here lets the
which-side-writes-the-file decision sit with the code that owns the file.
"""
from __future__ import annotations

import pickle
import re
from pathlib import Path

from rank_bm25 import BM25Okapi


_token_re = re.compile(r"\w+")


def _tokenize(text: str) -> list[str]:
    return [t.lower() for t in _token_re.findall(text)]


class BM25Index:
    """In-memory BM25 over chunk text."""

    def __init__(self, tokenized_corpus: list[list[str]]) -> None:
        self._tokens = tokenized_corpus
        self._bm25 = BM25Okapi(tokenized_corpus) if tokenized_corpus else None

    @classmethod
    def build(cls, corpus: list[str]) -> "BM25Index":
        return cls([_tokenize(t) for t in corpus])

    def search(self, query: str, *, top_k: int = 10) -> list[tuple[int, float]]:
        if self._bm25 is None:
            return []
        q = _tokenize(query)
        scores = self._bm25.get_scores(q)
        ranked = sorted(enumerate(scores), key=lambda kv: kv[1], reverse=True)
        return ranked[:top_k]

    def save(self, path: str | Path) -> None:
        Path(path).write_bytes(pickle.dumps(self._tokens))

    @classmethod
    def load(cls, path: str | Path) -> "BM25Index":
        return cls(pickle.loads(Path(path).read_bytes()))