# dsa-tracker-mcp

This is an MCP server for tracking your progress through your DSA questions and comes loaded with a default list of Neetcode  150 (any custom DSA problem list can be switched per user) with built-in spaced repetition. Built with [FastMCP](https://github.com/modelcontextprotocol/python-sdk) and SQLite.

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

```bash
git clone https://github.com/ashmitrrr/dsa-tracker-mcp.git
cd dsa-tracker-mcp
python3 -m venv .venv
source .venv/bin/activate   # on Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Configuration

### Claude Desktop

Add to your `claude_desktop_config.json` (Settings → Developer → Edit Config):

```json
{
  "mcpServers": {
    "dsa-tracker": {
      "command": "/absolute/path/to/dsa-tracker-mcp/.venv/bin/python",
      "args": ["/absolute/path/to/dsa-tracker-mcp/server.py"]
    }
  }
}
```

Restart Claude Desktop completely after saving.

### Environment variables (optional)

| Variable | Default | Description |
|---|---|---|
| `DSA_TRACKER_DB` | `~/.dsa_tracker_mcp/progress.db` | Path to the SQLite database |
| `DSA_TRACKER_PROBLEMS_FILE` | (none, uses built-in NeetCode 150) | Path to a JSON file with a custom problem list |

#### Custom problem list format

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