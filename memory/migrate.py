"""
Run this script to initialize or verify the agent_memory schema.

Usage:
    python memory/migrate.py

Reads EMBEDDING_DIM from .env (via config/settings.py) and creates the
agent_memory table with the correct VECTOR(N) column dimension.
If the table already exists, it checks that the live column dimension
matches EMBEDDING_DIM and exits with an error if they differ.
"""

import sys
from pathlib import Path

import psycopg2

from config import settings

TEMPLATE_PATH = Path(__file__).parent / "sql" / "schema_template.sql"


def get_live_dim(conn) -> int | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT character_maximum_length
            FROM information_schema.columns
            WHERE table_name = 'agent_memory'
              AND column_name = 'primary_embedding'
            """,
        )
        row = cur.fetchone()
        # pgvector stores dimension in udt_name or atttypmod; query pg_attribute directly
        if row is None:
            return None

    # information_schema doesn't expose vector dimension — use pg_attribute
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT atttypmod
            FROM pg_attribute
            JOIN pg_class ON pg_attribute.attrelid = pg_class.oid
            WHERE pg_class.relname = 'agent_memory'
              AND pg_attribute.attname = 'primary_embedding'
            """,
        )
        row = cur.fetchone()
        # atttypmod for vector is the dimension (stored directly)
        return row[0] if row else None


def main() -> None:
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    ddl = template.replace("{embedding_dim}", str(settings.EMBEDDING_DIM))

    conn = psycopg2.connect(settings.database_url)
    try:
        live_dim = get_live_dim(conn)

        if live_dim is not None and live_dim != settings.EMBEDDING_DIM:
            print(
                f"ERROR: agent_memory table exists with VECTOR({live_dim}), "
                f"but EMBEDDING_DIM={settings.EMBEDDING_DIM}.\n"
                "The schema column dimension must match the embedding model output.\n"
                "To change dimensions, drop and recreate the table (this deletes all memories)."
            )
            sys.exit(1)

        with conn.cursor() as cur:
            cur.execute(ddl)
        conn.commit()

        action = "verified" if live_dim is not None else "created"
        print(f"OK: agent_memory {action} with VECTOR({settings.EMBEDDING_DIM})")
    except Exception as exc:
        conn.rollback()
        print(f"ERROR: {exc}")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
