import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "data.db"

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS documents (
        cid TEXT PRIMARY KEY,
        sha256 TEXT,
        title TEXT,
        description TEXT,
        license TEXT,
        content_type TEXT,
        path TEXT,
        ingested_at TEXT
    );
    """)

    cur.execute("""
    CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts
    USING fts5(cid, title, description, text);
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS claims (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        summary TEXT NOT NULL,
        method TEXT,
        status TEXT DEFAULT 'pending',
        evidence_cids TEXT
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS votes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        claim_id INTEGER,
        reviewer TEXT,
        decision TEXT,
        notes TEXT,
        created_at TEXT
    );
    """)

    conn.commit()
    conn.close()
