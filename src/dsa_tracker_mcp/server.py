#!/usr/bin/env python3
"""dsa_tracker_mcp — This is an MCP server for tracking DSA practice progress.

Tracks attempts at problems from a configurable problem list (NeetCode 150 by
default, see seed_problems.py), with spaced-repetition review scheduling.

Runs over stdio and designed for Claude Desktop. The SQLite database lives at
~/.dsa_tracker_mcp/progress.db unless overridden via the DSA_TRACKER_DB
environment variable. The problem list can be replaced by setting
DSA_TRACKER_PROBLEMS_FILE to a JSON file of your own problems — see
_load_problem_rows() below.
"""

import difflib
import json
import os
import sqlite3
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import date, timedelta
from enum import Enum
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field

from . import seed_problems

# DB setup

DEFAULT_DB_PATH = Path.home() / ".dsa_tracker_mcp" / "progress.db"
DB_PATH = Path(os.environ.get("DSA_TRACKER_DB", DEFAULT_DB_PATH))

PROBLEMS_FILE_ENV = "DSA_TRACKER_PROBLEMS_FILE"
VALID_DIFFICULTIES = {"Easy", "Medium", "Hard"}

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


def _load_problem_rows() -> list[dict]:
    """Return the problem rows to seed the database with.

    By default this is the bundled NeetCode 150 list from seed_problems.py.
    Set DSA_TRACKER_PROBLEMS_FILE to the path of a JSON file containing a list
    of objects with at least "name" and "category" keys (and optionally
    "difficulty", "leetcode_url", "order_index") to track a different list
    instead — Blind 75, Grind 75, or your own. Missing fields are filled in:
    difficulty defaults to "Medium" (invalid values are also normalized to
    "Medium"), leetcode_url is derived from the name via seed_problems.leetcode_url,
    and order_index follows the list's order if not given.
    """
    custom_path = os.environ.get(PROBLEMS_FILE_ENV)
    if not custom_path:
        return list(seed_problems.iter_seed_problems())

    with open(custom_path, encoding="utf-8") as f:
        raw = json.load(f)

    rows = []
    for index, item in enumerate(raw, start=1):
        name = item["name"]
        difficulty = item.get("difficulty", "Medium")
        if difficulty not in VALID_DIFFICULTIES:
            difficulty = "Medium"
        rows.append(
            {
                "name": name,
                "category": item.get("category", "Uncategorized"),
                "difficulty": difficulty,
                "leetcode_url": item.get("leetcode_url") or seed_problems.leetcode_url(name),
                "order_index": item.get("order_index", index),
            }
        )
    return rows


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
                _load_problem_rows(),
            )
        conn.commit()
    finally:
        conn.close()


# Spaced repetition


def _today() -> date:
    """Today's date, as a function so it's easy to override in tests."""
    return date.today()


def _next_review_date(status: str, confidence: Optional[int], from_date: date) -> str:
    """Compute the next review date for a logged attempt.

    Rules:
    - gave_up                          -> review in 1 day
    - struggled, confidence <= 2 (or unset, default 3 doesn't apply here) -> 2 days
    - struggled, confidence >= 3       -> 4 days
    - solved,    confidence <= 3        -> 7 days
    - solved,    confidence >= 4        -> 21 days

    If confidence is not provided, it's treated as 3.
    """
    c = confidence if confidence is not None else 3
    if status == "gave_up":
        days = 1
    elif status == "struggled":
        days = 2 if c <= 2 else 4
    else:  # solved
        days = 7 if c <= 3 else 21
    return (from_date + timedelta(days=days)).isoformat()


#Problem lookup & status helpers


def _find_problem(conn: sqlite3.Connection, name: str) -> Optional[sqlite3.Row]:
    """Find a problem by name.

    Exact match is case-insensitive (COLLATE NOCASE). If that fails, fall back
    to the closest fuzzy match so small typos still work.
    """
    row = conn.execute(
        "SELECT * FROM problems WHERE name = ? COLLATE NOCASE", (name,)
    ).fetchone()
    if row is not None:
        return row

    all_names = [r["name"] for r in conn.execute("SELECT name FROM problems")]
    close = difflib.get_close_matches(name, all_names, n=1, cutoff=0.6)
    if close:
        return conn.execute("SELECT * FROM problems WHERE name = ?", (close[0],)).fetchone()
    return None


def _suggest_names(conn: sqlite3.Connection, name: str, n: int = 3) -> list[str]:
    """Suggest close-match problem names for an error message."""
    all_names = [r["name"] for r in conn.execute("SELECT name FROM problems")]
    return difflib.get_close_matches(name, all_names, n=n, cutoff=0.4)


def _problems_with_status(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """All problems, each annotated with `last_status` and `ever_solved`,
    ordered by order_index. Shared by search_problems and the problem-list
    resource so the status logic lives in exactly one place.
    """
    return conn.execute(
        """
        SELECT p.*,
               (SELECT status FROM attempts WHERE problem_id = p.id ORDER BY id DESC LIMIT 1) AS last_status,
               EXISTS(SELECT 1 FROM attempts WHERE problem_id = p.id AND status = 'solved') AS ever_solved
        FROM problems p
        ORDER BY p.order_index
        """
    ).fetchall()


def _status_label(row: sqlite3.Row) -> str:
    """Derive a problem's current status: 'solved' if ever solved, else the
    most recent attempt's status, else 'not_started'.
    """
    if row["ever_solved"]:
        return "solved"
    return row["last_status"] or "not_started"


#Enums & Pydantic input models


class AttemptStatus(str, Enum):
    """Outcome of a single attempt at a problem."""

    SOLVED = "solved"
    STRUGGLED = "struggled"
    GAVE_UP = "gave_up"


class Difficulty(str, Enum):
    """LeetCode difficulty levels."""

    EASY = "Easy"
    MEDIUM = "Medium"
    HARD = "Hard"


class ProblemStatusFilter(str, Enum):
    """Status used to filter problems in search_problems, derived from logged attempts."""

    NOT_STARTED = "not_started"
    SOLVED = "solved"
    STRUGGLED = "struggled"
    GAVE_UP = "gave_up"


class LogAttemptInput(BaseModel):
    """Input model for log_attempt."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    problem_name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description=(
            "Name of the problem, e.g. 'Two Sum'. Matching is case-insensitive, "
            "and close matches are accepted if the exact name isn't found."
        ),
    )
    status: AttemptStatus = Field(..., description="Outcome of this attempt.")
    time_taken_minutes: Optional[int] = Field(
        default=None,
        ge=0,
        le=600,
        description="Time spent on this attempt, in minutes.",
    )
    confidence: Optional[int] = Field(
        default=None,
        ge=1,
        le=5,
        description=(
            "Self-rated confidence in the solution/approach, 1 (low) to 5 (high). "
            "Treated as 3 if not given. Affects when this problem is next suggested for review."
        ),
    )
    notes: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="Notes on approach, mistakes, or things to remember for next time.",
    )


class GetNextProblemInput(BaseModel):
    """Input model for get_next_problem."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    category: Optional[str] = Field(
        default=None,
        max_length=100,
        description=(
            "Limit the suggestion to this category, e.g. 'Sliding Window' "
            "(case-insensitive). Omit to consider all categories."
        ),
    )


class SearchProblemsInput(BaseModel):
    """Input model for search_problems."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    query: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Substring to match against problem names, case-insensitive.",
    )
    category: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Filter by category, case-insensitive (e.g. 'Trees').",
    )
    difficulty: Optional[Difficulty] = Field(
        default=None, description="Filter by difficulty."
    )
    status: Optional[ProblemStatusFilter] = Field(
        default=None,
        description="Filter by current status, derived from logged attempts.",
    )
    limit: Optional[int] = Field(
        default=30,
        ge=1,
        le=150,
        description="Maximum number of problems to return.",
    )


class GetProblemHistoryInput(BaseModel):
    """Input model for get_problem_history."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    problem_name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Name of the problem to look up. Case-insensitive; close matches are accepted.",
    )


# MCP SERVER


@asynccontextmanager
async def lifespan(_server: FastMCP) -> AsyncIterator[None]:
    """Initialize the database once when the server starts."""
    init_db()
    yield


mcp = FastMCP("dsa_tracker_mcp", lifespan=lifespan)


# Tools (T)


@mcp.tool(
    name="log_attempt",
    annotations={
        "title": "Log a DSA practice attempt",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False,
    },
)
async def log_attempt(params: LogAttemptInput) -> str:
    """Record an attempt at a DSA problem and schedule its next review.

    Looks up the problem by name (case-insensitive, with fuzzy fallback for
    typos), inserts an attempt row with today's date, and computes
    next_review_date from the status/confidence using the spaced-repetition
    rules in _next_review_date().

    Args:
        params (LogAttemptInput): problem_name, status, and optional
            time_taken_minutes, confidence, and notes.

    Returns:
        str: A short confirmation including the problem matched, the status
        logged, and the computed next review date. If no problem matches
        (even fuzzily), returns "Error: ..." with suggested close matches.
    """
    conn = get_connection()
    try:
        problem = _find_problem(conn, params.problem_name)
        if problem is None:
            suggestions = _suggest_names(conn, params.problem_name)
            hint = f" Did you mean: {', '.join(suggestions)}?" if suggestions else ""
            return f"Error: no problem found matching '{params.problem_name}'.{hint}"

        today = _today()
        next_review = _next_review_date(params.status.value, params.confidence, today)

        conn.execute(
            """
            INSERT INTO attempts
                (problem_id, date, status, time_taken_minutes, confidence, notes, next_review_date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                problem["id"],
                today.isoformat(),
                params.status.value,
                params.time_taken_minutes,
                params.confidence,
                params.notes,
                next_review,
            ),
        )
        conn.commit()

        lines = [
            f"Logged: {problem['name']} ({problem['category']}, {problem['difficulty']}) — {params.status.value}",
        ]
        if params.time_taken_minutes is not None:
            lines.append(f"Time: {params.time_taken_minutes} min")
        if params.confidence is not None:
            lines.append(f"Confidence: {params.confidence}/5")
        lines.append(f"Next review: {next_review}")
        if params.notes:
            lines.append(f"Notes: {params.notes}")
        return "\n".join(lines)
    finally:
        conn.close()


@mcp.tool(
    name="get_next_problem",
    annotations={
        "title": "Get the next DSA problem to work on",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False,
    },
)
async def get_next_problem(params: GetNextProblemInput) -> str:
    """Suggest what to work on next: an overdue review, or the next new problem.

    Priority order:
    1. The most overdue review (latest attempt's next_review_date <= today),
       optionally restricted to `category`.
    2. The lowest order_index problem with no attempts at all, optionally
       restricted to `category`.
    3. If neither applies, a message indicating there's nothing due or new
       right now.

    Args:
        params (GetNextProblemInput): optional category filter.

    Returns:
        str: The suggested problem (name, category, difficulty, URL) and why
        it was suggested (review vs. new), or a message if there's nothing
        to suggest.
    """
    conn = get_connection()
    try:
        sql_params: list = []
        category_clause = ""
        if params.category:
            category_clause = "AND p.category = ? COLLATE NOCASE"
            sql_params.append(params.category)

        review_row = conn.execute(
            f"""
            SELECT p.*, a.next_review_date, a.status AS last_status
            FROM problems p
            JOIN attempts a ON a.id = (
                SELECT id FROM attempts WHERE problem_id = p.id ORDER BY id DESC LIMIT 1
            )
            WHERE a.next_review_date IS NOT NULL
              AND a.next_review_date <= ?
              {category_clause}
            ORDER BY a.next_review_date ASC, p.order_index ASC
            LIMIT 1
            """,
            [_today().isoformat(), *sql_params],
        ).fetchone()

        if review_row:
            return (
                f"Review due: {review_row['name']} ({review_row['category']}, {review_row['difficulty']})\n"
                f"Last attempt: {review_row['last_status']} (due {review_row['next_review_date']})\n"
                f"{review_row['leetcode_url']}"
            )

        new_row = conn.execute(
            f"""
            SELECT p.* FROM problems p
            LEFT JOIN attempts a ON a.problem_id = p.id
            WHERE a.id IS NULL
              {category_clause}
            GROUP BY p.id
            ORDER BY p.order_index ASC
            LIMIT 1
            """,
            sql_params,
        ).fetchone()

        if new_row:
            return (
                f"New problem: {new_row['name']} ({new_row['category']}, {new_row['difficulty']})\n"
                f"{new_row['leetcode_url']}"
            )

        scope = f" in {params.category}" if params.category else ""
        return (
            f"Nothing new or due for review{scope} right now. "
            "If you'd like to revisit something anyway, use log_attempt on it directly."
        )
    finally:
        conn.close()


@mcp.tool(
    name="get_stats",
    annotations={
        "title": "Get overall DSA progress stats",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False,
    },
)
async def get_stats() -> str:
    """Summarize overall progress: solved counts, per-category breakdown,
    current streak, and total time spent.

    Returns:
        str: Markdown-ish summary with overall solved/total, current streak
        (consecutive days with at least one logged attempt, ending today or
        yesterday), total minutes logged across all attempts, and a
        solved/total breakdown per category in order_index order.
    """
    conn = get_connection()
    try:
        total = conn.execute("SELECT COUNT(*) FROM problems").fetchone()[0]
        solved = conn.execute(
            "SELECT COUNT(DISTINCT problem_id) FROM attempts WHERE status = 'solved'"
        ).fetchone()[0]

        categories = conn.execute(
            """
            SELECT p.category,
                   COUNT(*) AS total,
                   COUNT(DISTINCT CASE WHEN a.status = 'solved' THEN p.id END) AS solved
            FROM problems p
            LEFT JOIN attempts a ON a.problem_id = p.id
            GROUP BY p.category
            ORDER BY MIN(p.order_index)
            """
        ).fetchall()

        total_minutes = conn.execute(
            "SELECT COALESCE(SUM(time_taken_minutes), 0) FROM attempts"
        ).fetchone()[0]

        attempt_dates = {
            date.fromisoformat(r["date"]) for r in conn.execute("SELECT DISTINCT date FROM attempts")
        }
        streak = 0
        cursor = _today()
        if cursor not in attempt_dates:
            cursor -= timedelta(days=1)
        while cursor in attempt_dates:
            streak += 1
            cursor -= timedelta(days=1)

        lines = []
        if total:
            lines.append(f"Overall: {solved}/{total} solved ({solved / total:.0%})")
        else:
            lines.append("No problems loaded.")
        lines.append(f"Current streak: {streak} day{'s' if streak != 1 else ''}")
        lines.append(f"Total time logged: {total_minutes} min")
        lines.append("")
        lines.append("By category:")
        for row in categories:
            lines.append(f"- {row['category']}: {row['solved']}/{row['total']}")
        return "\n".join(lines)
    finally:
        conn.close()


@mcp.tool(
    name="search_problems",
    annotations={
        "title": "Search DSA problems",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def search_problems(params: SearchProblemsInput) -> str:
    """Search and filter problems by name, category, difficulty, and status.

    Status is derived from logged attempts: 'solved' if ever solved
    (regardless of earlier struggles), else the most recent attempt's status,
    else 'not_started'.

    Args:
        params (SearchProblemsInput): all filters are optional and combine
            with AND. `limit` caps the number of results (default 30, max 150).

    Returns:
        str: A count of matches and a list of "name [category, difficulty] —
        status" lines, or "No problems matched those filters." if empty.
    """
    conn = get_connection()
    try:
        rows = _problems_with_status(conn)

        results = []
        for row in rows:
            status = _status_label(row)

            if params.query and params.query.lower() not in row["name"].lower():
                continue
            if params.category and row["category"].lower() != params.category.lower():
                continue
            if params.difficulty and row["difficulty"] != params.difficulty.value:
                continue
            if params.status and status != params.status.value:
                continue

            results.append((row, status))

        if not results:
            return "No problems matched those filters."

        total_matches = len(results)
        shown = results[: params.limit]

        lines = [f"{len(shown)} of {total_matches} matching problems:"]
        for row, status in shown:
            lines.append(f"- {row['name']} [{row['category']}, {row['difficulty']}] — {status}")
        if total_matches > len(shown):
            lines.append(
                f"...and {total_matches - len(shown)} more. Narrow with category/difficulty/status to see more."
            )
        return "\n".join(lines)
    finally:
        conn.close()


@mcp.tool(
    name="get_problem_history",
    annotations={
        "title": "Get attempt history for a DSA problem",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def get_problem_history(params: GetProblemHistoryInput) -> str:
    """Show all logged attempts for a problem, in chronological order.

    Args:
        params (GetProblemHistoryInput): problem_name (case-insensitive,
            fuzzy fallback).

    Returns:
        str: The problem's name/category/difficulty plus each attempt's
        date, status, confidence, time, and notes — or "Error: ..." with
        suggestions if no problem matches.
    """
    conn = get_connection()
    try:
        problem = _find_problem(conn, params.problem_name)
        if problem is None:
            suggestions = _suggest_names(conn, params.problem_name)
            hint = f" Did you mean: {', '.join(suggestions)}?" if suggestions else ""
            return f"Error: no problem found matching '{params.problem_name}'.{hint}"

        attempts = conn.execute(
            "SELECT * FROM attempts WHERE problem_id = ? ORDER BY id ASC",
            (problem["id"],),
        ).fetchall()

        header = f"{problem['name']} ({problem['category']}, {problem['difficulty']})"
        if not attempts:
            return f"{header} — no attempts logged yet.\n{problem['leetcode_url']}"

        lines = [f"{header} — {len(attempts)} attempt(s):"]
        for a in attempts:
            parts = [a["date"], a["status"]]
            if a["confidence"] is not None:
                parts.append(f"confidence {a['confidence']}/5")
            if a["time_taken_minutes"] is not None:
                parts.append(f"{a['time_taken_minutes']} min")
            line = " — ".join(parts)
            if a["notes"]:
                line += f"\n  notes: {a['notes']}"
            lines.append(line)
        return "\n".join(lines)
    finally:
        conn.close()


# --- Resources -----------------------------------------------------------------


@mcp.resource("dsa://progress")
async def progress_resource() -> str:
    """Overall progress summary (same content as get_stats), exposed as a resource
    so it can be read without an explicit tool call."""
    return await get_stats()


@mcp.resource("dsa://problem-list")
async def problem_list_resource() -> str:
    """The full problem list grouped by category, each with a link and current status."""
    conn = get_connection()
    try:
        rows = _problems_with_status(conn)
    finally:
        conn.close()

    lines = ["# DSA problem list", ""]
    current_category = None
    for row in rows:
        if row["category"] != current_category:
            current_category = row["category"]
            lines.append(f"## {current_category}")
        status = _status_label(row).replace("_", " ")
        lines.append(f"- [{row['name']}]({row['leetcode_url']}) ({row['difficulty']}) — {status}")
    return "\n".join(lines)


# Prompts (P)


@mcp.prompt(
    name="daily_review",
    description="Get a recommendation for what to review and what to tackle next today.",
)
def daily_review() -> str:
    return (
        "Here is my current DSA progress and problem list (use the dsa://progress "
        "and dsa://problem-list resources, and get_next_problem if useful). Tell me "
        "what I should review today (anything overdue, with a guess at why I might "
        "have struggled with it before based on my notes) and suggest one new "
        "problem to tackle, with a one-line reason for each."
    )


@mcp.prompt(
    name="explain_pattern",
    description="Get a step-by-step explanation of a DSA pattern/category, with a worked example.",
)
def explain_pattern(category: str) -> str:
    return (
        f"Explain the core technique/pattern for the '{category}' category in my DSA "
        f"problem list (see dsa://problem-list for the problems in this category). "
        f"Walk through the underlying idea step by step, then work through one "
        f"example problem from this category in detail before I attempt the rest myself."
    )


def main():
    """Entry point for the dsa-tracker-mcp console script."""
    mcp.run()  # stdio transport by default


if __name__ == "__main__":
    main()