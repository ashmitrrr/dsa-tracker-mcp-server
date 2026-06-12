#!/usr/bin/env python3
"""dsa_tracker_mcp — an MCP server for tracking DSA practice progress.

Tracks attempts at problems from a configurable problem list (NeetCode 150 by
default, see seed_problems.py), with spaced-repetition review scheduling.

Runs over stdio; designed for Claude Desktop. The SQLite database lives at
~/.dsa_tracker_mcp/progress.db unless overridden via the DSA_TRACKER_DB
environment variable.
"""

import os
import sqlite3
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from mcp.server.fastmcp import FastMCP

import seed_problems

# --- Database setup ---------------------------------------------------------

DEFAULT_DB_PATH = Path.home() / ".dsa_tracker_mcp" / "progress.db"
DB_PATH = Path(os.environ.get("DSA_TRACKER_DB", DEFAULT_DB_PATH))

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS problems (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT    NOT NULL UNIQUE,
    category     TEXT    NOT NULL,
    difficulty   TEXT    NOT NULL CHECK (difficulty IN ('Easy', 'Medium', 'Hard')),
    leetcode_url TEXT    NOT NULL,
    order_index  INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS attempts (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    problem_id         INTEGER NOT NULL REFERENCES problems(id),
    date               TEXT    NOT NULL,
    status             TEXT    NOT NULL CHECK (status IN ('solved', 'struggled', 'gave_up')),
    time_taken_minutes INTEGER,
    confidence         INTEGER CHECK (confidence BETWEEN 1 AND 5),
    notes              TEXT,
    next_review_date   TEXT
);

CREATE INDEX IF NOT EXISTS idx_attempts_problem_id ON attempts(problem_id);
CREATE INDEX IF NOT EXISTS idx_attempts_date ON attempts(date);
"""


def get_connection() -> sqlite3.Connection:
    """Open a connection to the tracker database.

    SQLite connections are cheap to open, so each tool call opens its own
    short-lived connection instead of sharing one across the (potentially
    concurrent) async tool handlers.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # rows behave like dicts: row["name"]
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    """Create the schema and seed the problem list on first run.

    Idempotent: tables use IF NOT EXISTS, and seeding only happens when the
    problems table is empty, so existing progress is never touched.
    """
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = get_connection()
    try:
        conn.executescript(SCHEMA_SQL)
        (count,) = conn.execute("SELECT COUNT(*) FROM problems").fetchone()
        if count == 0:
            conn.executemany(
                """
                INSERT INTO problems (name, category, difficulty, leetcode_url, order_index)
                VALUES (:name, :category, :difficulty, :leetcode_url, :order_index)
                """,
                seed_problems.iter_seed_problems(),
            )
        conn.commit()
    finally:
        conn.close()


# --- MCP server -------------------------------------------------------------


@asynccontextmanager
async def lifespan(_server: FastMCP) -> AsyncIterator[None]:
    """Initialize the database once when the server starts."""
    init_db()
    yield


mcp = FastMCP("dsa_tracker_mcp", lifespan=lifespan)


if __name__ == "__main__":
    mcp.run()  # stdio transport by default
