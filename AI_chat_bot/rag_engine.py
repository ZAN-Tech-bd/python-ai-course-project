"""Lightweight retrieval engine over a user-editable JSON knowledge base.

Uses character n-gram TF-IDF so retrieval works for both Bangla and English
text without needing a large multilingual embedding model.
"""

from __future__ import annotations

import json
import re
import uuid
from pathlib import Path
from typing import Any

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

DATA_PATH = Path(__file__).parent / "data" / "knowledge_base.json"

BANGLA_RANGE = re.compile(r"[ঀ-৿]")


def detect_language(text: str) -> str:
    """Return 'bn' if the text contains Bangla script, else 'en'."""
    return "bn" if BANGLA_RANGE.search(text or "") else "en"


class RagEngine:
    def __init__(self, data_path: Path = DATA_PATH):
        self.data_path = data_path
        self.entries: list[dict[str, Any]] = []
        self.vectorizer: TfidfVectorizer | None = None
        self.matrix = None
        self.load()

    # ---------- persistence ----------

    def load(self) -> None:
        if self.data_path.exists():
            with open(self.data_path, encoding="utf-8") as f:
                self.entries = json.load(f)
        else:
            self.entries = []
        self._reindex()

    def save(self) -> None:
        self.data_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.data_path, "w", encoding="utf-8") as f:
            json.dump(self.entries, f, ensure_ascii=False, indent=2)

    # ---------- indexing ----------

    def _entry_text(self, entry: dict[str, Any]) -> str:
        tags = " ".join(entry.get("tags", []))
        return f"{entry.get('title', '')} {entry.get('content', '')} {tags}"

    def _reindex(self) -> None:
        if not self.entries:
            self.vectorizer = None
            self.matrix = None
            return
        self.vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4), min_df=1)
        corpus = [self._entry_text(e) for e in self.entries]
        self.matrix = self.vectorizer.fit_transform(corpus)

    # ---------- CRUD ----------

    def add_entry(self, title: str, content: str, tags: list[str] | None = None) -> dict[str, Any]:
        entry = {
            "id": uuid.uuid4().hex[:8],
            "title": title.strip(),
            "content": content.strip(),
            "tags": tags or [],
        }
        self.entries.append(entry)
        self.save()
        self._reindex()
        return entry

    def delete_entry(self, entry_id: str) -> None:
        self.entries = [e for e in self.entries if e.get("id") != entry_id]
        self.save()
        self._reindex()

    def replace_all(self, entries: list[dict[str, Any]]) -> None:
        cleaned = []
        for e in entries:
            cleaned.append(
                {
                    "id": e.get("id") or uuid.uuid4().hex[:8],
                    "title": e.get("title", ""),
                    "content": e.get("content", ""),
                    "tags": e.get("tags", []),
                }
            )
        self.entries = cleaned
        self.save()
        self._reindex()

    def merge(self, entries: list[dict[str, Any]]) -> None:
        for e in entries:
            self.entries.append(
                {
                    "id": uuid.uuid4().hex[:8],
                    "title": e.get("title", ""),
                    "content": e.get("content", ""),
                    "tags": e.get("tags", []),
                }
            )
        self.save()
        self._reindex()

    # ---------- retrieval ----------

    def search(self, query: str, top_k: int = 3, min_score: float = 0.05):
        if not self.entries or self.vectorizer is None:
            return []
        query_vec = self.vectorizer.transform([query])
        scores = cosine_similarity(query_vec, self.matrix)[0]
        ranked = sorted(zip(self.entries, scores), key=lambda x: x[1], reverse=True)
        return [(entry, float(score)) for entry, score in ranked[:top_k] if score >= min_score]
