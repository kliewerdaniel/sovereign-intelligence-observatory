# Sovereign Intelligence Observatory

**Build intelligence you own. Observe it evolve. Own every decision.**

The Sovereign Intelligence Observatory is a complete local-first AI observability platform that tracks, analyzes, and optimizes agent intelligence across its entire lifecycle. Built on the philosophy that **"If the loop is the product, observability of the loop is the operating system."**

---

## The Book

This project implements concepts from **Sovereign AI: Building Local-First Intelligent Systems** by Daniel Kliewer.

**Get the book on Amazon ->** [Sovereign AI](https://www.amazon.com/dp/B0H6RB7D9J)

---

## Links

- **Website:** [danielkliewer.com](https://www.danielkliewer.com)
- **Book:** [Sovereign AI on Amazon](https://www.amazon.com/dp/B0H6RB7D9J)
- **Blog:** [danielkliewer.com/blog](https://www.danielkliewer.com/blog)
- **GitHub:** [kliewerdaniel](https://github.com/kliewerdaniel)

---

## The Problem

You don't own your AI. Your data isn't yours. You rent intelligence forever with no escape.

The cloud-based AI paradigm has created a generation of developers locked into vendor ecosystems, paying per token, with no visibility into how their AI systems actually work or evolve.

## The Solution

**Build intelligence you own.** Run locally. Build with sovereignty. Stay private. No limits.

The Sovereign Intelligence Observatory gives you complete visibility into your AI systems:
- **Observe** every agent decision
- **Track** intelligence evolution over time
- **Analyze** what works and what doesn't
- **Optimize** with data, not guesses

---

## Architecture

```
Agent
 |
 v
Recipe Compiler ----------------------------------------+
 |                                                      |
 v                                                      |
Expert Signal Router                                    |
 |                                                      |
 v                                                      |
Autonomous Evaluation Loop                              |
 |                                                      |
 v                                                      |
Tacit Judgment Extractor                                |
 |                                                      |
 v                                                      |
Sovereign Apprenticeship Engine                         |
 |                                                      |
 v                                                      |
Intelligence Observatory <------------------------------+
 |
 v
Intelligence Timeline
 |
 v
Actionable Insights
```

**Each layer produces data for the next. Nothing is wasted. Everything compounds.**

---

## Components

### 1. Agent Recipe Compiler

**The missing primitive.** Every agent run produces an invisible artifact -- a recipe. This system makes those artifacts explicit, versioned, and queryable.

**What it does:**
- Captures agent run data into structured recipe artifacts
- Stores in SQLite with full-text search (FTS5)
- Exposes HTTP API for recipe ingestion
- Supports chunked streaming JSON export for training data
- Optional ChromaDB integration for semantic recipe search

**Recipe format:**
```json
{
  "recipe_id": "recipe-20240101-120000-abc123",
  "objective": "classify_ai_paper",
  "model": "qwen3.5",
  "prompt_version": 5,
  "memory_version": 12,
  "retrieved_docs": ["doc_1", "doc_2"],
  "reasoning_patterns": ["compare", "retrieve", "synthesize"],
  "evaluation": {"score": 0.95, "reviewed_by": "expert"},
  "outcome": "accepted"
}
```

**Related blog post:** [Sovereign Memory Bank](https://www.danielkliewer.com/blog/2026-06-14-sovereign-memory-bank-a-deep-dive-into-autonomous-cognitive-memory-for-agent-systems/)

---

### 2. Expert Signal Router

**Decides who judges each output.** Recipes tell you what happened. The router decides who judges it.

**What it does:**
- Routes evaluation signals based on confidence thresholds
- Tiered system: auto-accepted -> cheap evaluation -> expert review
- Captures expert decisions as training examples
- Tracks pending reviews and expert feedback
- Dynamic calibration matrix adjusts thresholds based on historical error rate

**Routing logic:**
```
Agent Output
    |
    v
Confidence >= 0.95?
    |
    +-- YES -> Auto-accepted
    |
    +-- Confidence >= 0.80?
    |       |
    |       +-- YES -> Cheap evaluation
    |       |
    |       +-- NO -> Expert review required
    |
    v
Expert Review
    |
    v
Recipe updated for future fine-tuning
```

---

### 3. Autonomous Evaluation Loop

**Self-improving evaluation system.** Instead of evaluating outputs, you're evaluating recipes.

**What it does:**
- Defines evaluation signals as YAML specs with uncertainty bounds
- Auto-generates synthetic test cases based on production data
- Implements signal drift detection using KS (Kolmogorov-Smirnov) and PSI (Population Stability Index) statistics
- Rejects synthetic/degenerate inputs (exact duplicates, out-of-range scores)
- Tracks optimization cost vs capability gain
- Generates evaluation recipes for versioning and sharing

**Drift detection:**
- **KS D-statistic** -- measures distribution shape divergence (threshold: 0.3)
- **PSI** -- measures binned proportion shift (threshold: 0.25)
- Both must exceed threshold to trigger drift alert

---

### 4. Tacit Judgment Extractor

**Extracts unarticulated expertise** from expert decision-making sessions and converts it into trainable decision trees.

**What it does:**
- Records expert decision-making sessions (text-based)
- Uses local LLMs (Ollama) to identify tacit patterns in expert reasoning
- Generates structured decision trees capturing unarticulated expertise
- Exports decision trees as JSON schemas
- Rule-based fallback extraction when Ollama is unavailable
- LLM response parsing merges AI-suggested nodes with rule-based tree

---

### 5. Sovereign Apprenticeship Engine

**Solves the supervised-to-autonomous transition.** Most frameworks have two modes: manual and autonomous. Reality has dozens of stages.

**What it does:**
- Implements phased autonomy: 100% supervised -> approve dangerous -> approve novel -> approve uncertain -> fully autonomous
- Tracks daily action budgets with automatic reset
- Compute-weighted action costs (monitored actions cost 1.5x)
- Detects when to promote or demote autonomy levels
- Rollback freeze on demotion clears autonomy debt and resets budget
- Generates scaffolded training data from transitions
- Supervision ratio calculated per level (0.0 for autonomous, 0.8 for supervised)

**Autonomy levels:**
1. **Fully Supervised** -- 100% human oversight
2. **Approve Dangerous** -- Only dangerous actions reviewed
3. **Approve Novel** -- Only novel actions reviewed
4. **Approve Uncertain** -- Only uncertain actions reviewed
5. **Fully Autonomous** -- No human oversight

---

### 6. Intelligence Observatory

**The flagship. GitHub Insights, but for intelligence.**

**What it does:**
- Aggregates data from all other components into unified observability layer
- Generates Intelligence Timeline showing capability evolution
- Pre-aggregated weekly/monthly rollup views for fast dashboard queries
- Identifies obsolescent prompts using recency-weighted usage + trend scoring
- Identifies unused memories
- Correlates signals with expert quality
- Detects capability regressions and improvements
- Generates comprehensive intelligence reports

**Capabilities:**
- **Intelligence Timeline** -- Visualize how agent capabilities evolved over time
- **Timeline Rollups** -- Weekly and monthly pre-aggregated views
- **Obsolescent Prompt Detection** -- Find prompts no longer effective (low usage + low relevance)
- **Unused Memory Detection** -- Identify documents never retrieved
- **Signal Correlation Analysis** -- Determine which cheap signals predict expert quality
- **Capability Regression Detection** -- Alert when quality decreases
- **Capability Improvement Detection** -- Identify what drove quality increases

**Related blog post:** [Sovereign Memory Bank](https://www.danielkliewer.com/blog/2026-06-14-sovereign-memory-bank-a-deep-dive-into-autonomous-cognitive-memory-for-agent-systems/)

---

## Tech Stack

- **Language:** Python 3.9+
- **Database:** SQLite with FTS5 (full-text search)
- **API:** FastAPI
- **Serialization:** JSON, CSV
- **Testing:** pytest + pytest-asyncio (auto mode)
- **Package management:** uv

**Optional (graceful fallback if missing):**
- Ollama -- GBNF grammar validation for decision tree outputs
- ChromaDB -- semantic search on recipes
- Weights & Biases -- experiment tracking via `shared/wandb_logger.py`
- GBNF grammars -- structured LLM output via `shared/gbnf.py`

**Why no Jinja2?** Dashboard uses `string.Template` (stdlib) to avoid dependency bloat. `str.format` is dangerous because JS `{` characters cause runtime crashes.

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `ENABLE_CHROMA` | `false` | Enable ChromaDB semantic search (requires `chromadb` installed) |
| `WANDB_API_KEY` | *(none)* | Weights & Biases API key (logger skips if unset) |

### ChromaDB

ChromaDB is optional and guarded at dependency-injection time. Set `ENABLE_CHROMA=true` and install `chromadb`:
```bash
pip install chromadb
```
If `chromadb` is not installed, the system silently falls back to SQLite FTS5 search.

### GBNF Grammars

GBNF grammar files for structured LLM output generation live in `shared/gbnf.py`. The module supports `str`, `int`, `float`, `bool`, `Optional`, `List[T]`, `Dict[str, Any]`, and nested `BaseModel` sub-fields. Requires Ollama to be running locally.

### Weights & Biases

The `shared/wandb_logger.py` module wraps wandb with graceful `try/except` around imports and all API calls. If wandb is not installed or the API key is unset, all calls are no-ops.

### Timeline Rollup Frequencies

The Intelligence Observatory pre-aggregates timeline data at two granularities:
- **Weekly** -- `timeline_rollup_weekly` table, keyed by ISO week
- **Monthly** -- `timeline_rollup_monthly` table, keyed by YYYY-MM

Rollups refresh automatically on timeline data ingestion.

---

## Installation

```bash
# Clone the repository
git clone https://github.com/kliewerdaniel/sovereign-intelligence-observatory.git
cd sovereign-intelligence-observatory

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install fastapi uvicorn aiosqlite pydantic httpx pytest pytest-asyncio

# Run all tests (121 tests across 7 component suites)
./run_tests.sh
```

---

## API Endpoints

### Shared Infrastructure
- `GET /api/health` -- Health check (every component)

### Agent Recipe Compiler
- `POST /api/recipes` -- Capture new recipe
- `GET /api/recipes/{recipe_id}` -- Retrieve recipe by ID
- `GET /api/recipes` -- List recipes with filters
- `GET /api/recipes/search` -- Full-text search
- `GET /api/recipes/stats` -- Get statistics
- `GET /api/recipes/export` -- Export to JSON/CSV
- `GET /api/recipes/export/stream` -- Chunked streaming JSON export

### Expert Signal Router
- `POST /api/route/{recipe_id}` -- Route recipe evaluation
- `GET /api/pending-reviews` -- Get pending reviews
- `POST /api/review/{evaluation_id}` -- Record expert review
- `GET /api/signals/stats` -- Get signal statistics
- `GET /api/calibration/{objective}` -- Get calibration history

### Autonomous Evaluation Loop
- `POST /api/signals` -- Create evaluation signal
- `POST /api/evaluate/{recipe_id}` -- Run evaluation
- `GET /api/signals/drift/{signal_id}` -- Check signal drift
- `GET /api/evaluations/stats` -- Get evaluation statistics

### Tacit Judgment Extractor
- `POST /api/extract` -- Extract tacit judgment from session
- `GET /api/decision-tree/{session_id}` -- Get decision tree
- `POST /api/session` -- Begin new extraction session

### Sovereign Apprenticeship Engine
- `GET /api/agent/{agent_id}` -- Get agent state
- `POST /api/action/{agent_id}` -- Record action (returns budget info)
- `POST /api/promote/{agent_id}` -- Promote agent
- `GET /api/transitions/{agent_id}` -- Get transition history
- `GET /api/budget/{agent_id}` -- Get budget status

### Intelligence Observatory
- `POST /api/timeline` -- Update timeline
- `GET /api/timeline/{start_date}/{end_date}` -- Get timeline
- `GET /api/timeline/rollup/{granularity}` -- Get weekly/monthly rollup
- `POST /api/prompts/obsolescent` -- Update obsolescent prompt
- `GET /api/prompts/obsolescent` -- Get obsolescent prompts
- `POST /api/memories/unused` -- Update unused memory
- `GET /api/memories/unused` -- Get unused memories
- `POST /api/signals/correlation` -- Update signal correlation
- `GET /api/signals/correlations` -- Get signal correlations
- `POST /api/capability/change` -- Record capability change
- `GET /api/capability/changes` -- Get capability changes
- `GET /api/observatory/stats` -- Get observatory statistics
- `GET /api/observatory/report` -- Generate intelligence report
- `GET /dashboard` -- HTML dashboard (Chart.js v4)

---

## What This IS

- The observability layer for sovereign AI systems
- The "GitHub Insights" for intelligence evolution
- The analyzer that makes agent recipes actionable
- The system that turns raw recipe data into strategic insights
- The foundation for data-driven agent optimization

---

## Testing

All components have comprehensive pytest suites with FastAPI `TestClient`:

```bash
# Run all tests via the test runner
./run_tests.sh

# Or test individual components
pytest agent-recipe-compiler/tests/
cd expert-signal-router && pytest tests/
cd autonomous-evaluation-loop && pytest tests/
cd tacit-judgment-extractor && pytest tests/
cd sovereign-apprenticeship && pytest tests/
cd intelligence-observatory && pytest tests/
pytest tests/test_shared_infrastructure.py

# Expected: 121 tests, all passing, 0 warnings
```

**Test architecture:**
- Each component's `tests/conftest.py` adds its parent directory to `sys.path`
- Root `conftest.py` adds project root for `shared/` imports
- `pytest-asyncio` mode is `auto` -- no `@pytest.mark.asyncio` needed on fixture-based tests
- Import guards exist for all optional dependencies (ChromaDB, wandb, GBNF)

---

## Learning Resources

### From the Book

**Sovereign AI: Building Local-First Intelligent Systems** covers:
- Local LLMs (Ollama, llama.cpp)
- RAG Pipelines
- Knowledge Graphs
- AI Agents
- MCP Servers
- Full-Stack AI
- Persona Systems
- RLHF & Evaluation
- Security

**Buy the book ->** [Sovereign AI on Amazon](https://www.amazon.com/dp/B0H6RB7D9J)

### Related Blog Posts

- **[Sovereign Memory Bank](https://www.danielkliewer.com/blog/2026-06-14-sovereign-memory-bank-a-deep-dive-into-autonomous-cognitive-memory-for-agent-systems/)** -- How I built an autonomous cognitive memory system that transforms documents into evolving knowledge -- no cloud required.
- **[The Sovereignty Manifesto](https://www.danielkliewer.com/blog/2026-03-28-sovereignty-manifesto/)** -- Why data sovereignty is a fundamental right and why the future of AI is local.

### Related Projects

- **[SovereignSpec](https://github.com/kliewerdaniel/sovereignspec)** -- Spec-Driven Development engine for building sovereign systems
- **[SovereignBank](https://github.com/kliewerdaniel/sovereignbank)** -- Cognitive memory system for agents
- **[SynthInt](https://github.com/kliewerdaniel/synthint)** -- Dynamic Persona MoE RAG
- **[Workflow](https://github.com/kliewerdaniel/workflow)** -- Structured AI-Assisted Development Workflow

---

## Advanced Multi-Agent Concurrency

### Write-Ahead Logging (WAL)

All SQLite databases use **WAL journal mode** with `synchronous=NORMAL` for concurrent read/write performance. Each `AsyncDatabase` instance sets:

- `PRAGMA journal_mode=WAL` -- allows concurrent readers and a single writer without blocking.
- `PRAGMA synchronous=NORMAL` -- balances durability vs. write throughput (safe with WAL).
- `PRAGMA busy_timeout=5000` -- writer waits up to 5 seconds instead of immediately raising `SQLITE_BUSY`.
- `PRAGMA cache_size=-8000` -- 8 MB page cache per connection.

These pragmas are applied at every `connect()` call, so every component database (Recipe, Signal, Evaluation, Apprenticeship, Observatory, TJE) inherits them automatically. To override the busy timeout for a specific database:

```python
from shared.async_db import AsyncDatabase

# Higher timeout for batch ingestion
db = AsyncDatabase("recipes.db", busy_timeout=15000)
```

### Vector Engine Schema Versioning

The ChromaDB abstraction (`shared/chroma_client.py`) includes an `EmbeddingModelLedger` that stores the embedding model name and dimension in a dedicated `_embedding_ledger` Chroma collection. On startup:

1. The ledger checks if the current embedding model matches the one used to populate the collection.
2. If the model name or dimension **changed**, it sets `needs_reindex=true` on the collection metadata and logs a warning.
3. All subsequent add/query operations proceed through a `_ChromaCollectionProxy` that validates compatibility.

**Recovery steps when embedding dimensions change:**

1. Check the warning logs for `"Embedding model changed: was 'X' (dim=N), now 'Y' (dim=M)"`.
2. Delete the old Chroma collection and re-ingest all documents:
   ```python
   from shared.chroma_client import ChromaClient
   client = ChromaClient(embedding_model="new-model", embedding_dimension=768)
   # Re-add all documents via client.add_document(...)
   ```
3. The ledger auto-registers the new model on first document add.

### Defensive Stream Merging

The Tacit Judgment Extractor's `_parse_llm_tree_response()` method implements a three-phase lookahead token verification before building decision trees from local LLM output:

1. **Balanced-brace scan** -- scans for the outermost balanced `{}` or `[]` structure. If the stream was cut off mid-object, it truncates at the last complete brace.
2. **JSON decode with auto-wrap** -- attempts to parse as both a bare object and a wrapped array `[...]`.
3. **Schema conformance** -- every extracted node must have `condition`, `action`, `confidence`, and `rationale` fields. Nodes that don't pass are silently dropped.

This prevents corrupted or truncated LLM output from producing broken decision trees; the pipeline falls back to rule-based extraction when structural validation fails.

### Local Federated Sync

`shared/federated_sync.py` provides two transports for exchanging serialized decision trees between isolated agent instances:

**File-share transport** (`FileShareTransport`):
- Writes payloads as `.sio_federated` JSON files to a shared directory (NFS, SMB, local).
- Inbound files are discovered by glob, validated, and deleted after import.
- Self-imports are filtered by `source_agent_id`.

**Local HTTP transport** (`HttpTransport`):
- Push/pull over `POST /api/federated/ingest` and `GET /api/federated/ingest/latest`.
- Intended for agent instances on the same machine or LAN.
- Uses `httpx.AsyncClient` with a 10-second timeout.

Every payload carries a `schema_version: "decision-tree-exchange-v1"` tag; incompatible formats are rejected at deserialization time.

### WebSocket Telemetry Loop

The Intelligence Observatory exposes `ws://host:port/api/observatory/stream` via `intelligence-observatory/src/telemetry.py`. The `TelemetryManager`:

- Accepts WebSocket connections and maintains a set of active clients.
- Runs a background `asyncio` broadcast loop that pushes a JSON payload every 5 seconds.
- Each payload includes: `stats`, `timeline` (last 30 days), `obsolescent_count`, `drift_alerts` (regressions from last 7 days).
- Automatically starts the broadcast loop on first client connect and stops when all clients disconnect.
- Handles `WebSocketDisconnect` gracefully by removing dead connections.

### Concurrency Testing

The test suite includes `tests/test_concurrency.py` with stress tests for:
- 50 concurrent parallel writers to a single in-memory database.
- 20 concurrent readers interleaved with 30 concurrent writers.
- Deliberate `BEGIN IMMEDIATE` contention with 50ms sleep to exercise busy-timeout.
- Concurrent federated file exports from two agent instances (40 files in parallel).

---

## Production Hardening & Isolation

### Action Sandboxing

The `shared/sandbox.py` module provides a lightweight execution sandbox for TJE decision node actions. Every action runs in a forked subprocess with:

- **Blocklist validation** — 15+ dangerous patterns are rejected before execution (`import os`, `eval(`, `exec(`, `__import__`, `subprocess.`, `getattr(`, `.__class__`, etc.).
- **Resource limits** (best-effort per platform):
  - `RLIMIT_NPROC` — max child processes (default 0)
  - `RLIMIT_NOFILE` — max open file descriptors (default 16)
  - `RLIMIT_AS` — address space (default 64 MB)
  - `RLIMIT_CPU` — CPU seconds (default 5)
- **Timeout guard** — configurable per-action timeout (default 10s); kills on overrun.
- **Stripped environment** — only `PATH=/usr/bin:/bin` and `TMPDIR` are passed to the subprocess.

Usage:
```python
from shared.sandbox import ActionSandbox

sandbox = ActionSandbox(max_cpu=5, max_memory_mb=128, timeout_s=10)
result = await sandbox.execute(action_code, context={"recipe_id": "..."})
if result["success"]:
    print("Action executed safely")
```

### Vector Tenant Isolation

The `ChromaClient` isolates document collections per `agent_id` using a deterministic SHA-256 namespace appended to the collection name:

```
observatory_recipes___a1b2c3d4e5f6g7h8
```

- Each `agent_id` produces a unique 16-character hex suffix, preventing cross-tenant context leakage.
- If `agent_id` is `None`, the base collection name is used (backward compatible).
- No two agents can query each other's embeddings without explicitly sharing the same `agent_id`.

```python
# Agent-alpha gets collection "observatory_recipes___<sha256(alpha)>"
client_a = ChromaClient(agent_id="agent-alpha")

# Agent-beta gets a different collection
client_b = ChromaClient(agent_id="agent-beta")
```

### Background Maintenance Engine

`AsyncDatabase` includes a non-blocking periodic maintenance routine:

- **`PRAGMA optimize`** — safe to run concurrently with readers; a no-op if nothing needs optimisation.
- **Conditional `VACUUM`** — only runs when the database file exceeds `vacuum_threshold_mb` (default 100 MB). Skipped for in-memory databases.
- A **background task** (`start_periodic_maintenance(interval_s=3600)`) runs the loop and guards against overlapping runs via a sentinel flag.
- The maintenance task is automatically cancelled when `close()` is called.

```python
db = AsyncDatabase("recipes.db")
task = await db.start_periodic_maintenance(interval_s=3600, vacuum_threshold_mb=100)

# ... normal operations ...

await db.close()  # cancels maintenance task
```

### Transactional Outbox Queue

The `HttpTransport` in `shared/federated_sync.py` persists undeliverable payloads to a local SQLite `federated_outbox` table and retries with exponential backoff:

- **`OutboxStore`** — file-based SQLite queue using `sqlite3` directly (independent of component DB connections).
- **Exponential backoff** — delay = `2^retry_count` seconds base, with configurable `max_retries` (default 10).
- **Exhaustion** — when `retry_count >= max_retries`, the row is marked acknowledged (lost) and an error is logged.
- A background `asyncio` task (`_retry_loop`) polls due rows every second and retries up to 10 per batch.

```python
from shared.federated_sync import HttpTransport

transport = HttpTransport(
    agent_id="agent-a",
    backoff_base_s=2,    # delay = 2^retry_count
    max_retries=10,      # give up after 10 failed retries
)
await transport.push(payload, "http://peer:8000")
```

---

## Philosophy

> **"Intelligence is not the model. Intelligence is the accumulated decisions that shaped the model."**

Every agent run produces an invisible artifact -- a recipe -- that captures the complete context of how a decision was made. This system makes those artifacts explicit, versioned, and queryable.

**Recipes are Git commits for intelligence.**

---

## License

This project is part of the Sovereign AI ecosystem. See the book for full details on licensing and usage.

---

## Contributing

Contributions welcome! This is an open-source project built on sovereign principles:
- Local-first everything (no cloud APIs)
- Data sovereignty and privacy
- Open-source and reproducible
- Recipe-based debugging and evolution

---

## Connect

- **Website:** [danielkliewer.com](https://www.danielkliewer.com)
- **GitHub:** [@kliewerdaniel](https://github.com/kliewerdaniel)
- **Book:** [Sovereign AI on Amazon](https://www.amazon.com/dp/B0H6RB7D9J)

---

**If the loop is the product, observability of the loop is the operating system.**

*Build intelligence you own. Observe it evolve. Own every decision.*
