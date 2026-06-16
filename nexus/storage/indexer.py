"""
NexusCore — الفهرس الذكي
يفهرس البيانات ويتيح البحث السريع عبر المحتوى.
"""
import logging
import re
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("nexus.storage.indexer")


@dataclass
class IndexedDocument:
    doc_id: str
    content: str
    collection: str
    metadata: Dict = field(default_factory=dict)
    indexed_at: float = field(default_factory=time.time)
    tokens: Set[str] = field(default_factory=set)


class Indexer:
    """فهرس نصي مع بحث بالكلمات الرئيسية"""

    def __init__(self):
        self._docs: Dict[str, IndexedDocument] = {}
        self._inverted: Dict[str, Set[str]] = defaultdict(set)
        logger.info("🔍 Indexer initialized")

    def add(self, doc_id: str, content: str, collection: str = "default",
            metadata: Optional[Dict] = None) -> IndexedDocument:
        tokens = self._tokenize(content)
        doc = IndexedDocument(
            doc_id=doc_id, content=content[:10000],
            collection=collection, metadata=metadata or {},
            tokens=tokens
        )
        self._docs[doc_id] = doc
        for token in tokens:
            self._inverted[token].add(doc_id)
        return doc

    def search(self, query: str, collection: Optional[str] = None,
               limit: int = 20) -> List[Dict]:
        tokens = self._tokenize(query)
        if not tokens:
            return []
        candidates: Optional[Set[str]] = None
        for token in tokens:
            hits = self._inverted.get(token, set())
            candidates = hits if candidates is None else candidates & hits
        if not candidates:
            candidates = set()
            for token in tokens:
                candidates |= self._inverted.get(token, set())

        results = []
        for doc_id in list(candidates)[:limit * 2]:
            doc = self._docs.get(doc_id)
            if doc and (collection is None or doc.collection == collection):
                score = sum(1 for t in tokens if t in doc.tokens) / len(tokens)
                results.append({
                    "doc_id": doc_id,
                    "score": round(score, 3),
                    "collection": doc.collection,
                    "snippet": doc.content[:200],
                    "metadata": doc.metadata,
                })
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]

    def remove(self, doc_id: str) -> bool:
        doc = self._docs.pop(doc_id, None)
        if doc:
            for token in doc.tokens:
                self._inverted[token].discard(doc_id)
            return True
        return False

    def _tokenize(self, text: str) -> Set[str]:
        return {t.lower() for t in re.findall(r'\w+', text) if len(t) > 2}

    def get_stats(self) -> Dict:
        return {
            "total_docs": len(self._docs),
            "unique_tokens": len(self._inverted),
        }
