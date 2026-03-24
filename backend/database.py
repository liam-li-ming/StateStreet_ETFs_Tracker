import sqlite3
from contextlib import contextmanager
from backend.config import DB_PATH

CREATE_CHANGES_TABLE = """
CREATE TABLE IF NOT EXISTS etf_composition_changes (
    id                   INTEGER PRIMARY KEY,
    etf_ticker           TEXT NOT NULL,
    date_from            TEXT NOT NULL,
    date_to              TEXT NOT NULL,
    change_type          TEXT NOT NULL,
    component_identifier TEXT NOT NULL,
    component_name       TEXT,
    component_ticker     TEXT,
    component_sector     TEXT,
    weight_old           REAL,
    weight_new           REAL,
    weight_delta         REAL,
    detected_at          TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(etf_ticker, date_from, date_to, change_type, component_identifier)
);
"""

CREATE_CHANGES_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_changes_etf_date ON etf_composition_changes(etf_ticker, date_to);",
    "CREATE INDEX IF NOT EXISTS idx_changes_date_to ON etf_composition_changes(date_to);",
    "CREATE INDEX IF NOT EXISTS idx_changes_type ON etf_composition_changes(change_type);",
]


def init_db():
    """Create the etf_composition_changes table if it doesn't exist."""
    with get_db() as conn:
        conn.execute(CREATE_CHANGES_TABLE)
        for idx_sql in CREATE_CHANGES_INDEXES:
            conn.execute(idx_sql)
        cols = {row[1] for row in conn.execute("PRAGMA table_info(etf_composition_changes)").fetchall()}
        if "shares_old" not in cols:
            conn.execute("ALTER TABLE etf_composition_changes ADD COLUMN shares_old REAL")
            conn.execute("ALTER TABLE etf_composition_changes ADD COLUMN shares_new REAL")
            conn.execute("DELETE FROM etf_composition_changes")
        # One-time cleanup: remove weight_change rows where shares didn't actually change
        stale = conn.execute(
            "SELECT 1 FROM etf_composition_changes "
            "WHERE change_type='weight_change' AND shares_old IS NOT NULL AND shares_new IS NOT NULL "
            "AND shares_old = shares_new LIMIT 1"
        ).fetchone()
        if stale:
            conn.execute("DELETE FROM etf_composition_changes WHERE change_type = 'weight_change'")
        conn.commit()


@contextmanager
def get_db():
    """Yield a sqlite3 connection with WAL mode and row_factory set."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    try:
        yield conn
    finally:
        conn.close()
