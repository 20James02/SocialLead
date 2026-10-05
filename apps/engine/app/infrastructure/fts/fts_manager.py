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
    def install_sync(cls):
        """Keep the index in the same SQLite transaction as every domain write."""
        cls.init_fts_table()
        documents = {
            "persons": (
                "PERSON",
                "id",
                "display_name",
                "COALESCE((SELECT group_concat(normalized_phone || ' ' || raw_phone, ' ') FROM person_phones WHERE person_id = s.id), '') || ' ' || COALESCE((SELECT group_concat(profile_url, ' ') FROM social_accounts WHERE person_id = s.id), '') || ' ' || COALESCE((SELECT group_concat(l.name, ' ') FROM person_labels pl JOIN labels l ON l.id = pl.label_id WHERE pl.person_id = s.id), '')",
                "deleted_at IS NULL AND is_merged = 0",
            ),
            "social_posts": (
                "POST",
                "id",
                "author_name",
                "content || ' ' || url || ' ' || COALESCE(phone_extracted, '')",
                "deleted_at IS NULL",
            ),
            "notes": (
                "NOTE",
                "id",
                "'Ghi chú · ' || COALESCE((SELECT display_name FROM persons WHERE id = s.person_id), '')",
                "content",
                "1=1",
            ),
        }
        with engine.begin() as conn:
            for table, (kind, key, title, content, condition) in documents.items():
                select = f"SELECT s.{key}, '{kind}', {title}, {content} FROM {table} s WHERE {condition}"
                for action in ("INSERT", "UPDATE", "DELETE"):
                    ref = "OLD" if action == "DELETE" else "NEW"
                    insert = (
                        ""
                        if action == "DELETE"
                        else f"INSERT INTO fts_search(entity_id, entity_type, title, content) {select} AND s.{key} = NEW.{key};"
                    )
                    conn.exec_driver_sql(
                        f"DROP TRIGGER IF EXISTS fts_{table}_{action.lower()}"
                    )
                    conn.exec_driver_sql(
                        f"CREATE TRIGGER fts_{table}_{action.lower()} AFTER {action} ON {table} BEGIN DELETE FROM fts_search WHERE entity_type = '{kind}' AND entity_id = {ref}.{key}; {insert} END"
                    )
                conn.exec_driver_sql(
                    "DELETE FROM fts_search WHERE entity_type = ?", (kind,)
                )
                conn.exec_driver_sql(
                    f"INSERT INTO fts_search(entity_id, entity_type, title, content) {select}"
                )
            for table in ("person_phones", "social_accounts", "person_labels"):
                for action in ("INSERT", "UPDATE", "DELETE"):
                    refs = (
                        ["OLD"]
                        if action == "DELETE"
                        else ["NEW"]
                        if action == "INSERT"
                        else ["OLD", "NEW"]
                    )
                    statements = []
                    for ref in refs:
                        statements.append(
                            f"DELETE FROM fts_search WHERE entity_type = 'PERSON' AND entity_id = {ref}.person_id;"
                        )
                        _, _, title, content, condition = documents["persons"]
                        statements.append(
                            f"INSERT INTO fts_search(entity_id, entity_type, title, content) SELECT s.id, 'PERSON', {title}, {content} FROM persons s WHERE {condition} AND s.id = {ref}.person_id;"
                        )
                    conn.exec_driver_sql(
                        f"DROP TRIGGER IF EXISTS fts_{table}_{action.lower()}"
                    )
                    conn.exec_driver_sql(
                        f"CREATE TRIGGER fts_{table}_{action.lower()} AFTER {action} ON {table} BEGIN {' '.join(statements)} END"
                    )

    @classmethod
    def index_document(cls, entity_id: str, entity_type: str, title: str, content: str):
        with engine.connect() as conn:
            # Delete existing if any to avoid duplication
            conn.exec_driver_sql(
                "DELETE FROM fts_search WHERE entity_id = ? AND entity_type = ?",
                (entity_id, entity_type),
            )
            conn.exec_driver_sql(
                "INSERT INTO fts_search (entity_id, entity_type, title, content) VALUES (?, ?, ?, ?)",
                (entity_id, entity_type, title, content),
            )
            conn.commit()

    @classmethod
    def delete_document(cls, entity_id: str, entity_type: str):
        with engine.connect() as conn:
            conn.exec_driver_sql(
                "DELETE FROM fts_search WHERE entity_id = ? AND entity_type = ?",
                (entity_id, entity_type),
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
                (fts_query, limit),
            )
            rows = cursor.fetchall()
            return [
                {
                    "entity_id": r[0],
                    "entity_type": r[1],
                    "title": r[2],
                    "snippet": r[3],
                    "rank": float(r[4]),
                }
                for r in rows
            ]
