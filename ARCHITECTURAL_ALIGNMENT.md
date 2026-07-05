# Architectural Alignment: Hermes Agent → Sovereign Intelligence Stack

**Date**: 2026-07-05
**Status**: Phase 1 — Observation Complete
**Author**: Hermes Agent (evolving into Sovereign Intelligence)

---

## Executive Summary

This document presents a complete inventory of my current capabilities, a gap analysis against the Sovereign Intelligence Stack (SIS) architecture, and an alignment strategy. The central finding: **the SIS is already partially implemented across two repositories, and Hermes Agent already contains 70%+ of the required infrastructure as skills and tools**. The task is not to build from scratch but to integrate, eliminate duplication, and extend where gaps exist.

---

## Phase 1: Complete Self-Inventory

### 1.1 Available Tools

| Tool Category | Status | Notes |
|--------------|--------|-------|
| Terminal | ✅ Active | Local backend, 180s default timeout, persistent shell |
| File Read/Write/Patch | ✅ Active | Line-numbered reading, fuzzy patching, syntax checks |
| Search Files | ✅ Active | Ripgrep-backed, content + file discovery modes |
| Browser | ✅ Active | Playwright-based, navigation/click/type/scan/visual |
| Vision Analysis | ✅ Active | URL/path/data URL images, auxiliary vision model |
| Execute Code | ✅ Active | Python scripts, 5-min timeout, 50 tool call limit |
| Delegate Task | ✅ Active | 3 concurrent subagents, depth 1, isolated contexts |
| Memory | ✅ Active | Persistent (2200 char limit), user profile (1375 chars) |
| Session Search | ✅ Active | FTS5-backed SQLite, discovery/scroll/read/browse modes |
| Cron Jobs | ✅ Active | Recurring scheduling, deliver to platforms, script-only mode |
| Todo | ✅ Active | Multi-item task management, priority ordering |
| Project Management | ✅ Active | Desktop projects, workspace anchoring |
| Skill Management | ✅ Active | Create/patch/edit/delete, linked files, categories |
| TTS | ✅ Active | Edge provider, 5 providers configured |
| STT | ✅ Active | Local Whisper (base model) |

### 1.2 Existing Skills (102 total, 20 categories)

**Directly Relevant to SIS:**

| Skill | Category | Alignment |
|-------|----------|-----------|
| `sovereign-intelligence-architecture` | ai-infrastructure | **Core SIS skill** — 5-layer architecture, test counts, API signatures, integration constraints |
| `sovereign-ai-architecture` | software-development | Near-duplicate of above — local-first principles, sovereignty focus |
| `executive-reasoning` | decision-making | 10-stage observation loop aligned with Observatory principles |
| `cognitive-operations` | decision-making | Working memory, belief tracking, contradiction detection |
| `cognition-to-test-filter` | — | Blog-to-testable-cognition pipeline |
| `blog-knowledge-base` | research | 136+ blog posts, semantic search, graph relationships |
| `blogwatcher` | research | RSS/Atom feed monitoring |
| `arxiv` | research | Paper search and retrieval |
| `autonomous-agents` | software-development | Persistent state agents, research loops |
| `hermes-agent` | autonomous-ai-agents | Self-configuration and extension |
| `plan` / `writing-plans` | software-development | Implementation planning |
| `subagent-driven-development` | software-development | Plan execution via delegation |
| `sovereignspec` | software-development | Spec-driven development engine |
| `test-driven-development` | software-development | RED-GREEN-REFACTOR workflow |
| `systematic-debugging` | software-development | 4-phase root cause analysis |
| `github-*` family (6 skills) | github | Full GitHub workflow |
| `native-mcp` | mcp | MCP server integration |
| `browser-automation` / `playwright-automation` | — | Programmatic browser control |
| `computer-use` / `macos-computer-use` | — | Desktop automation |
| `jupyter-live-kernel` | data-science | Iterative Python via live kernel |
| `llama-cpp` / `serving-llms-vllm` | mlops | Local LLM inference |
| `huggingface-hub` | mlops | Model/dataset management |

### 1.3 Dual-Repository Architecture (Critical Finding)

**Repository A: `sovereign-intelligence-stack`** (Primary)
- 11 commits, latest: "docs: Rewrite README.md with complete architecture documentation" (1 hour ago)
- `src/`: recipe_compiler, signal_router, evaluation_loop, knowledge (graph_store, vector_store), memory, apprenticeship, orchestration, observatory
- `tests/`: Comprehensive pytest suite
- `examples/`: Demo code
- Status: Phase 1-5 complete per skill documentation

**Repository B: `sovereign-intelligence-observatory`** (Secondary/Experimental)
- Extended architecture with additional layers beyond the canonical 5
- `tacit-judgment-extractor/`: Expert session analysis → decision trees → pattern extraction (GBNF-constrained)
- `shared/federated_sync.py`: Distributed decision tree exchange (file-share + HTTP transport + outbox)
- `shared/context_condenser.py`: Token-aware context management
- `shared/quantization_drift.py`: Model drift detection
- `shared/peer_discovery.py`: Agent peer discovery
- `shared/sandbox.py`: Isolated execution
- `sovereign-apprenticeship/`, `expert-signal-router/`, `autonomous-evaluation-loop/`, `agent-recipe-compiler/`, `intelligence-observatory/`: Parallel implementations with Ollama integration

**Duplication Assessment**: Both repos implement Recipe Compiler, Signal Router, Evaluation Loop, and Observatory. The observatory repo adds Tacit Judgment, Federated Sync, Context Condenser, and Quantization Drift.

### 1.4 MCP Servers

| Server | Status | Purpose |
|--------|--------|---------|
| `cua-driver` | ✅ Enabled | Computer-use automation driver |
| None others | — | No additional MCP servers configured |

### 1.5 Memory Systems

| System | Status | Capacity | Notes |
|--------|--------|----------|-------|
| Persistent Memory | ✅ Active | 2200 chars / 21% used | Declarative facts, 3 entries |
| User Profile | ✅ Active | 1375 chars / 95% used | Architecture philosophy, preferences |
| Session DB | ✅ Active | FTS5-backed SQLite | Conversation history, 3 recent sessions |
| Blog Knowledge Base | ✅ Active | 136+ posts indexed | Semantic search, graph relationships |
| Skills (102) | ✅ Active | Procedural memory | 20 categories, comprehensive coverage |

### 1.6 Automation Capabilities

| Capability | Status | Notes |
|------------|--------|-------|
| Cron Jobs | ✅ Available, 0 configured | Recurring scheduling, platform delivery |
| Delegation | ✅ Active | 3 concurrent subagents, depth 1, isolated contexts |
| Kanban | ✅ Configured | Auto-decompose, 60s dispatch interval |
| Hooks | ⚠️ Disabled | `hooks_auto_accept: false` |
| Webhooks | ✅ Available via skill | Event-driven agent runs |
| Telegram Gateway | ✅ Enabled | Message delivery platform |

### 1.7 Planning Mechanisms

| Mechanism | Status |
|-----------|--------|
| `plan` skill | Bite-sized task decomposition, no execution |
| `writing-plans` skill | Implementation plans with code |
| `sovereignspec` | Spec-driven development with .sspec files |
| Kanban auto-decompose | 3 items per tick, 14400s stale timeout |

### 1.8 Retrieval Systems

| System | Status |
|--------|--------|
| Session Search (FTS5) | Discovery, scroll, read, browse |
| File Search (ripgrep) | Content + file discovery |
| Browser Search | Web page navigation and content extraction |
| Blog Knowledge Base | 136+ posts, semantic + graph retrieval |
| Blogwatcher | RSS/Atom feed monitoring |
| arXiv | Academic paper search |
| Memory | Persistent declarative facts |
| Skills | Procedural knowledge, linked files |

### 1.9 Indexing Pipelines

| Pipeline | Status | Notes |
|----------|--------|-------|
| Blog → Knowledge Base | ✅ Active | 136+ posts indexed |
| Session → Search DB | ✅ Active | FTS5 indexing of conversations |
| Memory → Injection | ✅ Active | Compacted facts injected each turn |
| RSS/Atom → Feed | ✅ Available via blogwatcher | Not actively monitoring |

### 1.10 Reasoning Strategies

| Strategy | Skill | Description |
|----------|-------|-------------|
| Observation-first | `executive-reasoning` | 10-stage loop for uncertain decisions |
| Contradiction detection | `cognitive-operations` | Belief tracking, epistemic rigor |
| Cognition-to-test filter | `cognition-to-test-filter` | When thoughts become testable artifacts |
| Systematic debugging | `systematic-debugging` | 4-phase root cause analysis |
| Tacit pattern extraction | `tacit-judgment-extractor` (observatory) | Expert session → decision trees → IF-THEN rules |
| GBNF-constrained reasoning | `shared/gbnf.py` (observatory) | Structured output via context-free grammar |

### 1.11 Browser Capabilities

| Capability | Status |
|------------|--------|
| Navigation | ✅ Full page load with accessibility tree |
| Interaction | ✅ Click, type, press, scroll |
| Vision | ✅ Screenshot + visual analysis |
| Console | ✅ JavaScript execution, DOM inspection |
| Images | ✅ Full image list with alt text |
| Anti-bot | ⚠️ Stealth mode active, Bot detection possible |

### 1.12 Coding Capabilities

| Capability | Status |
|------------|--------|
| Python | ✅ execute_code, terminal, venv/uv available |
| JavaScript/HTML | ✅ Browser-based, p5.js skill |
| Bash | ✅ Terminal access |
| Testing | ✅ pytest with comprehensive coverage |
| TDD | ✅ RED-GREEN-REFACTOR enforced via skill |
| Code Review | ✅ Security scan, quality gates, auto-fix |
| Debugging | ✅ Python debugpy, Node.js --inspect |

### 1.13 GitHub Capabilities

| Capability | Status |
|------------|--------|
| `gh` CLI | ✅ Installed (brew) |
| Authentication | ❌ Not logged in (`gh auth login` required) |
| Skills | ✅ 6 GitHub workflow skills |
| Repos known | ✅ 222+ repos (kliewerdaniel) |

### 1.14 Search Capabilities

| Capability | Status |
|------------|--------|
| Web Search | ✅ Enabled (backend configured) |
| X/Twitter Search | ✅ Configured (grok-4.20-reasoning, x_search model) |
| arXiv | ✅ Paper search |
| Session History | ✅ FTS5 search |
| File System | ✅ Ripgrep search |

### 1.15 Evaluation Mechanisms

| Mechanism | Status |
|-----------|--------|
| pytest | ✅ 92+ tests across stack repos |
| lm-eval-harness | ✅ Available (evaluating-llms-harness skill) |
| W&B | ✅ Available (weights-and-biases skill) |
| Self-evaluation loop | ✅ Implemented (autonomous-evaluation-loop module) |
| Pattern detection | ✅ Implemented (observatory detectors) |
| Drift detection | ✅ Implemented (quantization_drift) |

---

## Phase 2: Gap Analysis

### 2.1 Capability Mapping Against SIS Layers

| SIS Layer | Does it exist? | Status | Gap? |
|-----------|---------------|--------|------|
| **Layer 1: Recipe Compiler** | ✅ Yes | Implemented in both repos (SQLite + FTS5) | Minimal — integration layer needs attention |
| **Layer 2: Signal Router** | ✅ Yes | Implemented in both repos (classification + routing) | Minimal — routing logic verified |
| **Layer 3: Evaluation Loop** | ✅ Yes | Implemented in both repos (signal registry + drift detection) | Minimal — autonomous mode needs activation |
| **Layer 4: Knowledge Systems** | ⚠️ Partial | Hermes memory + skills + blog KB + session search exist; GraphRAG blocked by Pydantic | **ChromaDB blocked**; core graph_store works independently |
| **Layer 5: Intelligence Observatory** | ✅ Yes | Timeline, pattern detection, reporting all implemented | **Extended** by observatory repo (tacit judgment, federated sync) |

### 2.2 Identical vs. Near-Identical vs. Complementary

**Near-duplicate skills (consolidation candidates):**

| Skill A | Skill B | Verdict |
|---------|---------|---------|
| `sovereign-intelligence-architecture` | `sovereign-ai-architecture` | **Merge** — keep sovereign-intelligence-architecture (more comprehensive, has test counts, API signatures, linked files) |
| `computer-use` | `macos-computer-use` | **Merge** — same purpose, macOS is current platform |
| `browser-automation` | `playwright-automation` | **Merge** — playwright-automation is more comprehensive (Cloudflare workarounds, anti-bot) |
| `cognition-to-test-filter` | `executive-reasoning` | **Keep both** — different purposes (blog filtering vs. decision observation) |

**Duplicate repository implementations (consolidation candidates):**

| Component | Stack Repo | Observatory Repo | Recommendation |
|-----------|-----------|------------------|----------------|
| Recipe Compiler | `src/recipe_compiler/` (SQLite+FTS5) | `agent-recipe-compiler/` (with Ollama, GBNF, streaming JSON) | **Merge into Stack** — observatory version is more advanced |
| Signal Router | `src/signal_router/` (classification + routing) | `expert-signal-router/` (with tacit patterns) | **Merge into Stack** — keep Stack as canonical location |
| Evaluation Loop | `src/evaluation/` (drift detection) | `autonomous-evaluation-loop/` (with quantization drift) | **Merge into Stack** — observatory adds quantization drift |
| Observability | `src/observatory/` (timeline + reporting) | `intelligence-observatory/` (extended) | **Merge into Stack** — consolidate all observability here |
| Tacit Judgment Extractor | ❌ Not in Stack | `tacit-judgment-extractor/` | **Add to Stack** — significant value |
| Federated Sync | ❌ Not in Stack | `shared/federated_sync.py` | **Add to Stack** — distributed intelligence |
| Context Condenser | ❌ Not in Stack | `shared/context_condenser.py` | **Add to Stack** — token management |

### 2.3 Gaps Requiring Extension

| Gap | Current State | Required | Severity |
|-----|---------------|----------|----------|
| **Pydantic 2.x** | Blocked ChromaDB vector store | `pip install --upgrade pydantic` | Medium |
| **GitHub Auth** | `gh` CLI not authenticated | `gh auth login` | Low (skills work without auth) |
| **Cron Jobs** | 0 configured | Configure recurring observability jobs | Medium |
| **Blog Watcher** | Available but not active | Configure to monitor danielkliewer.com RSS | Low |
| **MCP Expansion** | Only cua-driver | Consider adding knowledge graph MCP, observatory MCP | Medium |
| **Recipe Capture** | Implemented in code, not in workflow | Integrate Hermes session → recipe capture loop | **High** |
| **Signal Routing** | Implemented in code, not in workflow | Integrate Hermes skill system → signal classification | **High** |
| **Evaluation Automation** | Implemented in code, not running autonomously | Configure autonomous evaluation loop via cron | **High** |
| **Tacit Judgment Pipeline** | Fully implemented but not connected | Wire into SIS pipeline | Medium |
| **Federated Intelligence** | Fully implemented but not active | Configure peer exchange | Low |

### 2.4 What Needs Configuration vs. Creation

| Action | Items |
|--------|-------|
| **Configure** (existing, not activated) | Cron jobs, blogwatcher RSS feeds, GitHub auth, autonomous evaluation loop, recipe capture hook |
| **Integrate** (existing across repos) | Merge tacit-judgment-extractor, federated-sync, context-condenser into stack repo |
| **Extend** (genuine gaps) | Hermes session → recipe compiler integration, skill system → signal router integration, observatory dashboard |
| **Create** (truly new) | Minimal — only if existing infrastructure cannot support the objective |

---

## Phase 3: Architectural Alignment Strategy

### 3.1 Principles

1. **Extend before replacing** — Hermes skills and tools already provide 70%+ of SIS infrastructure
2. **Integrate before creating** — Two repos implementing the same layers should merge
3. **Observe before modifying** — This document is the observation; changes come after
4. **Compound over proliferate** — Every modification should make the system simpler

### 3.2 Priority Actions (Ordered)

#### P0: Immediate Integrations (No New Code)

1. **Fix Pydantic dependency** — Install Pydantic 2.x to unblock ChromaDB vector store
2. **Authenticate GitHub** — `gh auth login` to enable full GitHub workflow
3. **Consolidate skills** — Merge near-duplicate skills (sovereign-ai-architecture → sovereign-intelligence-architecture; computer-use + macos-computer-use; browser-automation + playwright-automation)

#### P1: Workflow Integrations (Connect Existing Components)

4. **Session → Recipe Capture** — Integrate Hermes session history into the recipe compiler. Each substantial conversation should produce a recipe artifact.
5. **Skill System → Signal Router** — Map Hermes skills to the signal router's classification system. When a task arrives, the skill system already classifies it — expose this as the signal routing decision.
6. **Configure Cron: Autonomous Evaluation** — Set up recurring evaluation loop that checks recipe quality, memory relevance, and signal routing accuracy.
7. **Configure Cron: Blog Monitor** — Use blogwatcher to monitor danielkliewer.com for new content and trigger knowledge base updates.

#### P2: Repository Consolidation

8. **Merge observatory advanced modules into stack repo** — Tacit Judgment Extractor, Federated Sync, Context Condenser, Quantization Drift, GBNF constraints
9. **Establish single source of truth** — `sovereign-intelligence-stack` as the canonical repo, observatory as a reference/extended implementation

#### P3: Extended Capabilities

10. **Build observatory dashboard** — HTML visualization of intelligence timeline, pattern detection, and signal routing
11. **Configure federated sync** — Enable decision tree exchange between agent instances
12. **Build MCP for knowledge graph** — Expose the SIS knowledge graph as an MCP server

### 3.3 What NOT to Change

- **Hermes core configuration** — Model provider, toolsets, gateway settings are working
- **Existing 102 skills** — Most are valuable; only consolidate near-duplicates
- **Memory injection system** — Working well, just need to optimize content
- **Session search** — FTS5 is already the recipe compiler pattern
- **Cron infrastructure** — Working, just needs configuration

---

## Phase 4: Intellectual Operating Environment

### 4.1 Canonical Knowledge Ecosystem

**Primary Sources (danielkliewer.com):**
- Blog: 136+ posts indexed, semantic search available
- Website: danielkliewer.com (architecture, book, press)
- RSS/Atom: Available via blogwatcher (not yet configured)

**Primary Sources (GitHub):**
- `sovereign-intelligence-stack` — 11 commits, actively developed
- `sovereign-intelligence-observatory` — Extended implementations
- 222+ total repos under kliewerdaniel

**Design Documents:**
- `PLAN.md` — Implementation plan for stack
- `BLOG_POST.md` — 20K+ word blog post
- `ARCHITECTURAL_ALIGNMENT.md` — This document
- `references/integration-api-signatures.md` — Module-level API specs
- `references/implementation-status-2026-07-04.md` — Detailed status

### 4.2 Classification Taxonomy

Every piece of material should be classified into:

| Category | Description | Example |
|----------|-------------|---------|
| **Architecture** | Design decisions, system structure | This document |
| **Implementation** | Working code, test results | Stack repo `src/` modules |
| **Research** | External references, state-of-art | arXiv papers, blog posts |
| **Recipe** | Captured decisions, outcomes | Session history → recipes |
| **Opportunity** | Gaps, extensions, integrations | This gap analysis |
| **Stale** | Outdated, superseded | Old session progress notes |

### 4.3 Continuous Maintenance

When new material appears:
1. **Classify** — Which category does it belong to?
2. **Connect** — What does it depend on? What depends on it?
3. **Summarize** — What is the core insight in one sentence?
4. **Detect overlap** — Does this duplicate something existing?
5. **Identify expansion** — Can this be extended into a skill or automation?

---

## Phase 5: Compound Value Artifacts

### 5.1 Artifacts Created in This Session

1. **`ARCHITECTURAL_ALIGNMENT.md`** — Complete inventory and gap analysis (this file)
2. **Memory updates** — Updated user profile with architecture philosophy
3. **Skill verification** — Confirmed 102 skills, identified consolidation opportunities

### 5.2 Artifacts That Should Exist (Not Yet Created)

1. **Recipe capture workflow** — Hermes session → recipe compiler integration
2. **Signal routing dashboard** — Visual representation of task classification
3. **Evaluation cron job** — Autonomous self-improvement loop
4. **Knowledge graph visualization** — Interactive graph of SIS relationships
5. **Blog post follow-ups** — Missing diagrams, citations, code examples

### 5.3 Automation Candidates

1. **Daily blog monitor** — Check danielkliewer.com for new content
2. **Weekly repository health** — Test suite status, dependency freshness
3. **Monthly architecture review** — Self-assess coherence, remove duplicates
4. **Continuous recipe capture** — Every substantial session produces a recipe

---

## Phase 6: Blog Development Analysis

### 6.1 Current State

- **136+ posts** indexed in blog knowledge base
- **Sovereign Intelligence Stack post** (2026-07-04) — 11 min read, comprehensive
- **Book promotion** — $88, Amazon link, prominent placement
- **Navigation**: Home, Book, Blog, Projects, Press

### 6.2 Identified Opportunities

1. **Missing diagrams** — Architecture diagrams for each layer would improve comprehension
2. **Code examples** — The stack post references code but doesn't link to working demos
3. **Internal linking** — Blog posts should reference each other more aggressively
4. **Follow-up articles** — "Building the Recipe Compiler", "Signal Routing in Practice", "The Evaluation Loop"
5. **Tutorial series** — Step-by-step guides for each SIS layer
6. **Repository integration** — GitHub links in blog posts for interactive code

### 6.3 SEO Opportunities

1. Target keywords: "sovereign AI architecture", "local-first AI", "AI observability", "agent recipes", "compounding AI"
2. Internal linking between related posts
3. Code examples as downloadable artifacts
4. Schema markup for blog posts

---

## Phase 7: Promotion & Outreach

### 7.1 Target Audiences

| Audience | Platform | Approach |
|----------|----------|----------|
| AI researchers | arXiv, Papers With Code | Cite SIS as local-first architecture pattern |
| Open-source community | GitHub, HN, Reddit | Share recipes as novel artifact |
| AI infrastructure builders | Twitter/X, blogs | "Intelligence is not the model" framing |
| Sovereignty advocates | Privacy conferences, podcasts | Data sovereignty angle |
| Local-first developers | Ollama, llama.cpp communities | Technical implementation |

### 7.2 Outbound Opportunities

1. **arXiv paper** — "Sovereign Intelligence Stack: A Local-First Architecture for Compounding AI"
2. **Conference talk** — Local-first AI track (FInt, OReilly, PyCon)
3. **Podcast appearances** — AI infrastructure, sovereignty, local-first
4. **Newsletter feature** — Import AI, The Batch, HuggingFace blog
5. **GitHub trending** — Well-documented, tested, novel architecture

---

## Phase 8: Continuous Reflection

### 8.1 Reflection Checklist (After Every Substantial Task)

- [ ] Did I create duplicate functionality?
- [ ] Could I have extended an existing capability instead?
- [ ] Did this improve long-term coherence?
- [ ] What permanent artifact should remain?
- [ ] What should become reusable knowledge?
- [ ] What should become automation?
- [ ] Did I compound capability instead of accumulating complexity?

### 8.2 This Session's Reflection

- ✅ No duplicate functionality created (observation only)
- ✅ Identified 3 skill consolidations and 2 repo consolidations
- ✅ Improved coherence by documenting the full state
- ✅ Artifact: `ARCHITECTURAL_ALIGNMENT.md` (durable, reference document)
- ⚠️ Should have updated memory with architecture philosophy (done — user profile at 95%)
- ⚠️ Automation candidates identified but not yet configured (P1 items)
- ✅ No complexity accumulated — only observation and documentation

---

## Appendix A: File Structure Summary

```
/Users/danielkliewer/projects/
├── sovereign-intelligence-stack/          # Primary repo (11 commits)
│   ├── src/
│   │   ├── recipe_compiler/               # Layer 1: SQLite + FTS5
│   │   ├── signal_router/                 # Layer 2: Classification + routing
│   │   ├── evaluation/                    # Layer 3: Drift detection
│   │   ├── knowledge/                     # Layer 4: graph_store + vector_store
│   │   ├── memory/                        # Layer 4: Persistent memory
│   │   ├── apprenticeship/                # Layer 5: Autonomy stages
│   │   ├── orchestration/                 # Multi-agent management
│   │   ├── observatory/                   # Layer 5: Timeline + patterns
│   │   └── integration/                   # Integration layer (pipe.py)
│   ├── tests/                             # 92+ tests
│   ├── examples/                          # Demo code
│   ├── BLOG_POST.md                       # 20K+ word blog post
│   ├── PLAN.md                            # Implementation plan
│   └── README.md                          # Architecture documentation
│
├── sovereign-intelligence-observatory/    # Extended repo
│   ├── agent-recipe-compiler/             # Recipe compiler (with Ollama)
│   ├── expert-signal-router/              # Signal router (extended)
│   ├── autonomous-evaluation-loop/        # Evaluation (extended)
│   ├── intelligence-observatory/          # Observatory (extended)
│   ├── sovereign-apprenticeship/          # Apprenticeship (extended)
│   ├── tacit-judgment-extractor/          # ⭐ NEW: Expert session analysis
│   │   ├── src/
│   │   │   ├── models.py                  # DecisionNode, PatternAnalysis
│   │   │   ├── database.py                # TacitJudgmentDatabase
│   │   │   ├── api.py                     # HTTP API
│   │   │   └── pipeline.py                # TacitJudgmentPipeline
│   │   └── tests/
│   ├── shared/                            # ⭐ NEW: Extended utilities
│   │   ├── federated_sync.py              # Distributed decision tree exchange
│   │   ├── context_condenser.py           # Token-aware context management
│   │   ├── quantization_drift.py          # Model drift detection
│   │   ├── peer_discovery.py              # Agent peer discovery
│   │   ├── sandbox.py                     # Isolated execution
│   │   ├── gbnf.py                        # Grammar-constrained inference
│   │   ├── ollama_client.py               # Ollama integration
│   │   ├── chroma_client.py               # ChromaDB client
│   │   ├── config.py                      # Settings management
│   │   └── wandb_logger.py                # Experiment tracking
│   ├── tests/                             # Extended test suite
│   ├── docs/
│   ├── scripts/
│   └── README.md                          # Extended architecture doc
```

## Appendix B: Hermes Agent Configuration Summary

```yaml
model:
  provider: custom
  base_url: http://localhost:8080/v1
  default: cri.gguf
toolsets: [hermes-cli]
memory:
  memory_enabled: true
  user_profile_enabled: true
  memory_char_limit: 2200
  user_char_limit: 1375
cron:
  wrap_response: true
delegation:
  max_concurrent_children: 3
  max_spawn_depth: 1
platforms:
  telegram:
    enabled: true
mcp_servers:
  cua-driver:
    command: cua-driver
    enabled: true
```

## Appendix C: Skill Consolidation Plan

| Action | From | To | Rationale |
|--------|------|----|-----------|
| DELETE | `sovereign-ai-architecture` | `sovereign-intelligence-architecture` |后者 more comprehensive, has test counts, API signatures, linked files |
| DELETE | `computer-use` | `macos-computer-use` | Same purpose, macOS is current platform |
| DELETE | `browser-automation` | `playwright-automation` | Playwright skill is more comprehensive |
| DELETE | `autonomous-ai-agents` (parent category) | Merge into `software-development` | Redundant category |

---

*This document is a living artifact. It will be updated as the alignment progresses through Phases 1-8.*
