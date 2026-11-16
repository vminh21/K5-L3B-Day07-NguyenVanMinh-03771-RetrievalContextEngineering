"""Store and search vectors using PostgreSQL + pgvector.

Schema:
- chunk_id: TEXT PRIMARY KEY
- strategy: TEXT (A, B, C)
- document_id: TEXT
- source: TEXT
- page: INT
- text: TEXT
- metadata: JSONB
- embedding: vector(dimensions)
"""

import json
import logging
from typing import Any

import psycopg
from psycopg.rows import dict_row

try:
    from .models import Chunk
except (ImportError, ValueError):
    try:
        from src.models import Chunk
    except ImportError:
        from models import Chunk

log = logging.getLogger(__name__)


class PgVectorStore:
    def __init__(self, database_url: str, dimensions: int) -> None:
        self.database_url = database_url
        self.dimensions = dimensions
        log.info("PgVectorStore initialized: dimensions=%d", self.dimensions)

    def _get_connection(self):
        return psycopg.connect(self.database_url, row_factory=dict_row)

    def create_schema(self) -> None:
        """Tạo bảng lưu trữ vector, metadata và các index phục vụ tìm kiếm."""
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                cur.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS chunks (
                        chunk_id TEXT PRIMARY KEY,
                        strategy TEXT NOT NULL,
                        document_id TEXT NOT NULL,
                        source TEXT NOT NULL,
                        page INT NOT NULL,
                        text TEXT NOT NULL,
                        metadata JSONB NOT NULL DEFAULT '{{}}'::jsonb,
                        embedding vector({self.dimensions}) NOT NULL
                    );
                    """
                )
                cur.execute(
                    "CREATE INDEX IF NOT EXISTS idx_chunks_strategy ON chunks (strategy);"
                )
                cur.execute(
                    "CREATE INDEX IF NOT EXISTS idx_chunks_metadata ON chunks USING gin (metadata);"
                )
            conn.commit()
        log.info("Database schema and indices created successfully (vector dim: %d)", self.dimensions)

    def upsert(self, strategy: str, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        """Ghi nhận chunks và vectors vào DB, chống duplicate (idempotent)."""
        if len(chunks) != len(vectors):
            raise ValueError(
                f"Chunks count ({len(chunks)}) does not match vectors count ({len(vectors)})"
            )
        if not chunks:
            return

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                upsert_sql = """
                    INSERT INTO chunks (chunk_id, strategy, document_id, source, page, text, metadata, embedding)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s::vector)
                    ON CONFLICT (chunk_id) DO UPDATE SET
                        text = EXCLUDED.text,
                        metadata = EXCLUDED.metadata,
                        embedding = EXCLUDED.embedding;
                """
                records = [
                    (
                        c.chunk_id,
                        strategy,
                        c.document_id,
                        c.source,
                        c.page,
                        c.text,
                        json.dumps(c.metadata),
                        str(vec),
                    )
                    for c, vec in zip(chunks, vectors)
                ]
                cur.executemany(upsert_sql, records)
            conn.commit()
        log.info("Upserted %d chunks for strategy '%s'", len(chunks), strategy)

    def search(
        self,
        strategy: str,
        query_vector: list[float],
        top_k: int = 3,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Tìm kiếm top-k chunk gần nhất theo Cosine Distance kết hợp Metadata Filtering."""
        conditions = ["strategy = %s"]
        where_params: list[Any] = [strategy]

        # Áp dụng Metadata Filters nếu có (cho Strategy C)
        if filters:
            for key, val in filters.items():
                if val is not None:
                    conditions.append("metadata->>%s = %s")
                    where_params.extend([key, str(val)])

        where_clause = " AND ".join(conditions)
        vec_str = str(query_vector)

        # Thứ tự các tham số %s trong câu lệnh SQL:
        # 1. vec_str (ở SELECT ... embedding <=> %s::vector)
        # 2. where_params (strategy, filters...)
        # 3. vec_str (ở ORDER BY embedding <=> %s::vector)
        # 4. top_k (ở LIMIT %s)
        params: list[Any] = [vec_str] + where_params + [vec_str, top_k]

        query_sql = f"""
            SELECT
                chunk_id,
                strategy,
                document_id,
                source,
                page,
                text,
                metadata,
                1.0 - (embedding <=> %s::vector) AS score
            FROM chunks
            WHERE {where_clause}
            ORDER BY embedding <=> %s::vector ASC
            LIMIT %s;
        """

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query_sql, params)
                rows = cur.fetchall()

        return [dict(r) for r in rows]
