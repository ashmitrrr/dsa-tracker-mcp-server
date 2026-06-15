# dsa-tracker-mcp
mcp-name: io.github.ashmitrrr/dsa-tracker-mcp-server

[![PyPI](https://img.shields.io/pypi/v/dsa-tracker-mcp)](https://pypi.org/project/dsa-tracker-mcp/)

This is an MCP server for tracking your progress through your DSA questions and comes loaded with a default list of NeetCode 150 (any custom DSA problem list can be switched per user) with built-in spaced repetition. Built with [FastMCP](https://github.com/modelcontextprotocol/python-sdk) and SQLite.

Talk to it naturally from Claude: "what should I work on next", "log that I solved Two Sum, confidence 4, took 12 minutes", "how's my progress", "show me my history on Contains Duplicate".

## Features

- **Spaced repetition** — problems you struggle with come back sooner, problems you nail come back later. Schedule is based on how you rated each attempt (gave up / struggled / solved) and your confidence (1-5).
- **List-agnostic** — ships with the full NeetCode 150 (150 problems, 18 categories) but can load any custom problem list via a JSON file.
- **Fuzzy matching** — log an attempt with a loosely-typed problem name ("two sum", "contains dupe") and it'll match the right problem.
- **Stats & streaks** — solved counts, per-category breakdown, daily streak, total time spent.

## Tools

| Tool | Description |
|---|---|
| `log_attempt` | Log an attempt at a problem (status, confidence 1-5, time spent). Schedules the next review. |
| `get_next_problem` | Get what to work on next: an overdue review, or the next new problem in order. Optional category filter. |
| `get_stats` | Overall progress summary — solved counts, per-category breakdown, streak, total time. |
| `search_problems` | Search/filter problems by name, category, difficulty, or status. |
| `get_problem_history` | All logged attempts for a given problem, chronological. |

## Resources

- `dsa://progress` — current progress snapshot
- `dsa://problem-list` — full list of tracked problems

## Prompts

- `daily_review` — generates a daily review session based on what's due
- `explain_pattern(category)` — explains the core pattern/approach for a given category

## Installation

dsa-tracker-mcp is published on [PyPI](https://pypi.org/project/dsa-tracker-mcp/), no manual cloning or virtual environments needed. The recommended way to run it is with [uv](https://docs.astral.sh/uv/), which downloads and runs the package on demand.

### Claude Desktop

Add to your `claude_desktop_config.json` (Settings → Developer → Edit Config):

```json
{
  "mcpServers": {
    "dsa-tracker": {
      "command": "uvx",
      "args": ["dsa-tracker-mcp"]
    }
  }
}
```

Restart Claude Desktop completely after saving.

### Alternative: pip install

If you'd rather install it directly:

```bash
pip install dsa-tracker-mcp
```

Then point your config at the installed console script:

```json
{
  "mcpServers": {
    "dsa-tracker": {
      "command": "dsa-tracker-mcp"
    }
  }
}
```

### From source

```bash
git clone https://github.com/ashmitrrr/dsa-tracker-mcp-server.git
cd dsa-tracker-mcp-server
python3 -m venv .venv
source .venv/bin/activate   # on Windows: .venv\Scripts\activate
pip install -e .
```

## Environment variables (optional)

| Variable | Default | Description |
|---|---|---|
| `DSA_TRACKER_DB` | `~/.dsa_tracker_mcp/progress.db` | Path to the SQLite database |
| `DSA_TRACKER_PROBLEMS_FILE` | (none, uses built-in NeetCode 150) | Path to a JSON file with a custom problem list |

To set these with `uvx`, add an `env` block to your config:

```json
{
  "mcpServers": {
    "dsa-tracker": {
      "command": "uvx",
      "args": ["dsa-tracker-mcp"],
      "env": {
        "DSA_TRACKER_PROBLEMS_FILE": "/absolute/path/to/my-problems.json"
      }
    }
  }
}
```

### Custom problem list format

```json
[
  {
    "name": "Two Sum",
    "category": "Arrays & Hashing",
    "difficulty": "Easy",
    "url": "https://leetcode.com/problems/two-sum/"
  }
]
```

`url` and `difficulty` are optional and will be auto-filled where possible. `order_index` is assigned automatically based on list order.

## Spaced repetition logic

| Outcome | Next review |
|---|---|
| Gave up | 1 day |
| Struggled, confidence ≤ 2 | 2 days |
| Struggled, confidence ≥ 3 | 4 days |
| Solved, confidence ≤ 3 | 7 days |
| Solved, confidence ≥ 4 | 21 days |

`get_next_problem` prioritizes overdue reviews before suggesting new problems.

## Example prompts

- "What should I work on next?"
- "I just solved Valid Anagram, confidence 5, took 6 minutes, log it"
- "How's my progress on Trees?"
- "Show me my history on Two Sum"
- "Give me a daily review"

## License

MIT — see [LICENSE](LICENSE).