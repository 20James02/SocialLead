import sqlite3
from typing import List, Dict, Any
from app.infrastructure.database.session import engine

class FTSManager:
    """
    Manages SQLite FTS5 Virtual Table for sub-second Full-Text Search.
    Supports Vietnamese unicode matching without stripping diacritics.
    """
    @classmethod
    def init_fts_table(cls):
        with engine.connect() as conn:
            conn.exec_driver_sql("""
                CREATE VIRTUAL TABLE IF NOT EXISTS fts_search USING fts5(
                    entity_id UNINDEXED,
                    entity_type UNINDEXED,
                    title,
                    content,
                    tokenize = 'unicode61 remove_diacritics 0'
                );
            """)
            conn.commit()

    @classmethod
    def index_document(cls, entity_id: str, entity_type: str, title: str, content: str):
        with engine.connect() as conn:
            # Delete existing if any to avoid duplication
            conn.exec_driver_sql(
                "DELETE FROM fts_search WHERE entity_id = ? AND entity_type = ?",
                (entity_id, entity_type)
            )
            conn.exec_driver_sql(
                "INSERT INTO fts_search (entity_id, entity_type, title, content) VALUES (?, ?, ?, ?)",
                (entity_id, entity_type, title, content)
            )
            conn.commit()

    @classmethod
    def delete_document(cls, entity_id: str, entity_type: str):
        with engine.connect() as conn:
            conn.exec_driver_sql(
                "DELETE FROM fts_search WHERE entity_id = ? AND entity_type = ?",
                (entity_id, entity_type)
            )
            conn.commit()

    @classmethod
    def search(cls, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        clean_q = query.replace('"', '""').strip()
        if not clean_q:
            return []
        
        # SQLite FTS5 query with wildcard prefix/contains
        tokens = [f'"{tok}"*' for tok in clean_q.split() if tok]
        fts_query = " ".join(tokens)
        
        with engine.connect() as conn:
            cursor = conn.exec_driver_sql(
                """
                SELECT entity_id, entity_type, title, snippet(fts_search, 3, '<b>', '</b>', '...', 15) as snippet, rank
                FROM fts_search
                WHERE fts_search MATCH ?
                ORDER BY rank
                LIMIT ?
                """,
                (fts_query, limit)
            )
            rows = cursor.fetchall()
            return [
                {
                    "entity_id": r[0],
                    "entity_type": r[1],
                    "title": r[2],
                    "snippet": r[3],
                    "rank": float(r[4])
                }
                for r in rows
            ]
