from __future__ import annotations

import hashlib
import numpy as np
from sqlalchemy.orm import Session

from app.db.models.embedding import Embedding


class VectorRepository:
    """Repository interface for vector embeddings storage and similarity search."""

    def __init__(self, db: Session):
        self.db = db

    def upsert_embedding(
        self,
        kind: str,
        ref_id: str,
        model: str,
        vector: list[float],
        text_hash: str | None = None,
        raw_text: str | None = None,
    ) -> Embedding:
        if not text_hash and raw_text:
            text_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
        elif not text_hash:
            text_hash = hashlib.sha256(repr(vector).encode("utf-8")).hexdigest()

        existing = (
            self.db.query(Embedding)
            .filter(Embedding.kind == kind, Embedding.ref_id == ref_id)
            .first()
        )
        if existing:
            existing.model = model
            existing.vector = vector
            existing.text_hash = text_hash
            self.db.commit()
            self.db.refresh(existing)
            return existing

        embedding = Embedding(
            kind=kind,
            ref_id=ref_id,
            model=model,
            vector=vector,
            text_hash=text_hash,
        )
        self.db.add(embedding)
        self.db.commit()
        self.db.refresh(embedding)
        return embedding

    def get_by_ref(self, kind: str, ref_id: str) -> Embedding | None:
        return (
            self.db.query(Embedding)
            .filter(Embedding.kind == kind, Embedding.ref_id == ref_id)
            .first()
        )

    def list_by_kind(self, kind: str) -> list[Embedding]:
        return self.db.query(Embedding).filter(Embedding.kind == kind).all()

    def find_nearest(
        self, kind: str, query_vector: list[float], limit: int = 5
    ) -> list[tuple[Embedding, float]]:
        bind = self.db.get_bind()
        if bind.dialect.name == "postgresql":
            results = (
                self.db.query(Embedding, Embedding.vector.cosine_distance(query_vector).label("distance"))
                .filter(Embedding.kind == kind)
                .order_by("distance")
                .limit(limit)
                .all()
            )
            return [(r[0], float(r[1])) for r in results]

        # In-memory numpy cosine distance fallback for SQLite
        all_embeddings = self.db.query(Embedding).filter(Embedding.kind == kind).all()
        if not all_embeddings:
            return []

        q_vec = np.asarray(query_vector, dtype=float)
        q_norm = np.linalg.norm(q_vec)
        scored: list[tuple[Embedding, float]] = []
        for emb in all_embeddings:
            if emb.vector is None:
                continue
            e_vec = np.asarray(emb.vector, dtype=float)
            e_norm = np.linalg.norm(e_vec)
            if q_norm > 0 and e_norm > 0:
                cosine_sim = float(np.dot(q_vec, e_vec) / (q_norm * e_norm))
                dist = 1.0 - cosine_sim
            else:
                dist = 1.0
            scored.append((emb, dist))

        scored.sort(key=lambda x: x[1])
        return scored[:limit]
