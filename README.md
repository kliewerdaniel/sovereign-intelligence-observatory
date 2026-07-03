# 🧠 Sovereign Intelligence Observatory

**Build intelligence you own. Observe it evolve. Own every decision.**

The Sovereign Intelligence Observatory is a complete local-first AI observability platform that tracks, analyzes, and optimizes agent intelligence across its entire lifecycle. Built on the philosophy that **"If the loop is the product, observability of the loop is the operating system."**

---

## 📖 The Book

This project implements concepts from **Sovereign AI: Building Local-First Intelligent Systems** by Daniel Kliewer.

**Get the book on Amazon →** [Sovereign AI - $88](https://www.amazon.com/dp/B0H6RB7D9J)

**72 Pages | 11 Chapters | 10+ Projects**

---

## 🔗 Links

- **Website:** [danielkliewer.com](https://www.danielkliewer.com)
- **Book:** [Sovereign AI on Amazon](https://www.amazon.com/dp/B0H6RB7D9J)
- **Blog:** [danielkliewer.com/blog](https://www.danielkliewer.com/blog)
- **GitHub:** [kliewerdaniel](https://github.com/kliewerdaniel)
- **All 222 Repos →** [GitHub Projects](https://github.com/kliewerdaniel)

---

## 🎯 The Problem

You don't own your AI. Your data isn't yours. You rent intelligence forever with no escape.

The cloud-based AI paradigm has created a generation of developers who are locked into vendor ecosystems, paying per token, with no visibility into how their AI systems actually work or evolve.

## ✨ The Solution

**Build intelligence you own.** Run locally. Build with sovereignty. Stay private. No limits.

The Sovereign Intelligence Observatory gives you complete visibility into your AI systems:
- **Observe** every agent decision
- **Track** intelligence evolution over time
- **Analyze** what works and what doesn't
- **Optimize** with data, not guesses

---

## 🏗️ Architecture

```
Agent
 │
 ▼
Recipe Compiler ──────────────────────────────────────────┐
 │                                                        │
 ▼                                                        │
Expert Signal Router                                      │
 │                                                        │
 ▼                                                        │
Autonomous Evaluation Loop                                │
 │                                                        │
 ▼                                                        │
Sovereign Apprenticeship Engine                           │
 │                                                        │
 ▼                                                        │
**Intelligence Observatory** ◄─────────────────────────────┘
 │
 ▼
Intelligence Timeline
 │
 ▼
Actionable Insights
```

**Each layer produces data for the next. Nothing is wasted. Everything compounds.**

---

## 📦 Components

### 1. 🍳 Agent Recipe Compiler

**The missing primitive.** Every agent run produces an invisible artifact — a recipe. This system makes those artifacts explicit, versioned, and queryable.

**What it does:**
- Captures agent run data into structured recipe artifacts
- Stores in SQLite with full-text search (FTS5)
- Exposes HTTP API for recipe ingestion
- Supports recipe export to JSON/CSV for training data

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

**Skills needed:**
- SQLite database design
- FastAPI HTTP API development
- Python async programming
- Recipe schema design

**Related blog post:** [Sovereign Memory Bank](https://www.danielkliewer.com/blog/2026-06-14-sovereign-memory-bank-a-deep-dive-into-autonomous-cognitive-memory-for-agent-systems/)

---

### 2. 📡 Expert Signal Router

**Decides who judges each output.** Recipes tell you what happened. The router decides who judges it.

**What it does:**
- Routes evaluation signals based on confidence thresholds
- Tiered system: auto-accepted → cheap evaluation → expert review
- Captures expert decisions as training examples
- Tracks pending reviews and expert feedback

**Routing logic:**
```
Agent Output
    │
    ▼
Confidence ≥ 0.95?
    │
    ├── YES → Auto-accepted
    │
    ├── Confidence ≥ 0.80?
    │       │
    │       ├── YES → Cheap evaluation
    │       │
    │       └── NO → Expert review required
    │
    ▼
Expert Review
    │
    ▼
Recipe updated for future fine-tuning
```

**Skills needed:**
- Signal classification algorithms
- Expert review workflows
- Threshold-based routing

---

### 3. 🔄 Autonomous Evaluation Loop

**Self-improving evaluation system.** Instead of evaluating outputs, you're evaluating recipes.

**What it does:**
- Defines evaluation signals as YAML specs with uncertainty bounds
- Auto-generates synthetic test cases based on production data
- Implements signal drift detection
- Tracks optimization cost vs capability gain
- Generates evaluation recipes for versioning and sharing

**Skills needed:**
- Evaluation signal design
- Synthetic data generation
- Statistical analysis
- Drift detection algorithms

**Related blog post:** [Sovereign Memory Bank](https://www.danielkliewer.com/blog/2026-06-14-sovereign-memory-bank-a-deep-dive-into-autonomous-cognitive-memory-for-agent-systems/)

---

### 4. 🎓 Sovereign Apprenticeship Engine

**Solves the supervised-to-autonomous transition.** Most frameworks have two modes: manual and autonomous. Reality has dozens of stages.

**What it does:**
- Implements phased autonomy: 100% supervised → approve dangerous → approve novel → approve uncertain → fully autonomous
- Tracks autonomy budgets and debt
- Detects when to promote or demote autonomy levels
- Generates scaffolded training data from transitions

**Autonomy levels:**
1. **Fully Supervised** — 100% human oversight
2. **Approve Dangerous** — Only dangerous actions reviewed
3. **Approve Novel** — Only novel actions reviewed
4. **Approve Uncertain** — Only uncertain actions reviewed
5. **Fully Autonomous** — No human oversight

**Skills needed:**
- State machine design
- Budget tracking algorithms
- Quality threshold management
- Transition logic

---

### 5. 🔭 Intelligence Observatory

**The flagship. GitHub Insights, but for intelligence.**

**What it does:**
- Aggregates data from all other components into unified observability layer
- Generates Intelligence Timeline showing capability evolution
- Identifies obsolescent prompts and unused memories
- Correlates signals with expert quality
- Detects capability regressions and improvements
- Generates comprehensive intelligence reports

**Capabilities:**
- **Intelligence Timeline** — Visualize how agent capabilities evolved over time
- **Obsolescent Prompt Detection** — Find prompts that are no longer effective
- **Unused Memory Detection** — Identify documents never retrieved
- **Signal Correlation Analysis** — Determine which cheap signals predict expert quality
- **Capability Regression Detection** — Alert when quality decreases
- **Capability Improvement Detection** — Identify what drove quality increases

**Skills needed:**
- Data aggregation and analysis
- Time-series analysis
- Statistical correlation
- Report generation
- Dashboard design (optional)

**Related blog post:** [Sovereign Memory Bank](https://www.danielkliewer.com/blog/2026-06-14-sovereign-memory-bank-a-deep-dive-into-autonomous-cognitive-memory-for-agent-systems/)

---

## 🛠️ Tech Stack

- **Language:** Python 3.9+
- **Database:** SQLite with FTS5 (full-text search)
- **API:** FastAPI
- **Serialization:** JSON, CSV
- **Testing:** pytest
- **Package management:** uv

**Optional:**
- Ollama (for GBNF grammar validation)
- ChromaDB (for semantic search on recipes)
- Weights & Biases (for experiment tracking)

---

## 🚀 Installation

```bash
# Clone the repository
git clone https://github.com/kliewerdaniel/sovereign-intelligence-observatory.git
cd sovereign-intelligence-observatory

# Install dependencies
pip install fastapi uvicorn httpx pytest

# Run verification
python3 verify-recipe-compiler.py
python3 verify-signal-router.py
python3 verify-eval-loop.py
python3 verify-apprenticeship.py
python3 verify-observatory.py
```

---

## 📡 API Endpoints

### Agent Recipe Compiler
- `POST /api/recipes` — Capture new recipe
- `GET /api/recipes/{recipe_id}` — Retrieve recipe by ID
- `GET /api/recipes` — List recipes with filters
- `GET /api/recipes/search` — Full-text search
- `GET /api/recipes/stats` — Get statistics
- `GET /api/recipes/export` — Export to JSON/CSV

### Expert Signal Router
- `POST /api/route/{recipe_id}` — Route recipe evaluation
- `GET /api/pending-reviews` — Get pending reviews
- `POST /api/review/{evaluation_id}` — Record expert review
- `GET /api/signals/stats` — Get signal statistics

### Autonomous Evaluation Loop
- `POST /api/signals` — Create evaluation signal
- `POST /api/evaluate/{recipe_id}` — Run evaluation
- `GET /api/signals/drift/{signal_id}` — Check signal drift
- `GET /api/evaluations/stats` — Get evaluation statistics

### Sovereign Apprenticeship Engine
- `GET /api/agent/{agent_id}` — Get agent state
- `POST /api/action/{agent_id}` — Record action
- `POST /api/promote/{agent_id}` — Promote agent
- `GET /api/transitions/{agent_id}` — Get transition history
- `GET /api/budget/{agent_id}` — Get budget status

### Intelligence Observatory
- `POST /api/timeline` — Update timeline
- `GET /api/timeline/{start_date}/{end_date}` — Get timeline
- `POST /api/prompts/obsolescent` — Update obsolescent prompt
- `GET /api/prompts/obsolescent` — Get obsolescent prompts
- `POST /api/memories/unused` — Update unused memory
- `GET /api/memories/unused` — Get unused memories
- `POST /api/signals/correlation` — Update signal correlation
- `GET /api/signals/correlations` — Get signal correlations
- `POST /api/capability/change` — Record capability change
- `GET /api/capability/changes` — Get capability changes
- `GET /api/observatory/stats` — Get observatory statistics
- `GET /api/observatory/report` — Generate intelligence report

---

## 📊 What This Is NOT

- ❌ This is NOT an agent framework
- ❌ This is NOT a model training pipeline
- ❌ This is NOT a monitoring dashboard (though it generates reports)
- ❌ This is NOT a replacement for SovereignSpec (it feeds into it)

## ✅ What This IS

- ✅ The observability layer for sovereign AI systems
- ✅ The "GitHub Insights" for intelligence evolution
- ✅ The analyzer that makes agent recipes actionable
- ✅ The system that turns raw recipe data into strategic insights
- ✅ The foundation for data-driven agent optimization

---

## 🧪 Testing

All components are fully tested and verified:

```bash
# Test each component individually
python3 verify-recipe-compiler.py
python3 verify-signal-router.py
python3 verify-eval-loop.py
python3 verify-apprenticeship.py
python3 verify-observatory.py

# Expected output:
# ✅ Agent Recipe Compiler VERIFIED
# ✅ Expert Signal Router VERIFIED
# ✅ Autonomous Evaluation Loop VERIFIED
# ✅ Sovereign Apprenticeship Engine VERIFIED
# ✅ Intelligence Observatory VERIFIED
```

---

## 🎓 Learning Resources

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

**Buy the book →** [Sovereign AI on Amazon](https://www.amazon.com/dp/B0H6RB7D9J)

### Related Blog Posts

- **[Sovereign Memory Bank](https://www.danielkliewer.com/blog/2026-06-14-sovereign-memory-bank-a-deep-dive-into-autonomous-cognitive-memory-for-agent-systems/)** — How I built an autonomous cognitive memory system that transforms documents into evolving knowledge — no cloud required.
- **[The Sovereignty Manifesto](https://www.danielkliewer.com/blog/2026-03-28-sovereignty-manifesto/)** — Why data sovereignty is a fundamental right and why the future of AI is local.

### Related Projects

- **[SovereignSpec](https://github.com/kliewerdaniel/sovereignspec)** — Spec-Driven Development engine for building sovereign systems
- **[SovereignBank](https://github.com/kliewerdaniel/sovereignbank)** — Cognitive memory system for agents with seven-layer architecture
- **[SynthInt](https://github.com/kliewerdaniel/synthint)** — Dynamic Persona MoE RAG — sovereign synthetic intelligence
- **[Workflow](https://github.com/kliewerdaniel/workflow)** — Structured AI-Assisted Development Workflow

---

## 🔮 Future Extensions

### Tacit Judgment Extractor (6th Component)

*Coming soon.* Extracts unarticulated expertise from expert decision-making sessions and converts it into trainable model capabilities.

This is the hardest component — it borders on research rather than engineering. Build all other components first, as you'll need recipes and expert evaluations to learn from.

**What it does:**
- Records expert decision-making sessions (audio/video/text)
- Uses local LLMs to identify tacit patterns in expert reasoning
- Generates structured decision trees capturing unarticulated expertise
- Creates synthetic training examples from tacit patterns
- Builds domain-specific judgment models via fine-tuning

**Skills needed:**
- Audio/video processing
- Pattern recognition
- Fine-tuning workflows
- Research methodologies

---

## 💡 Philosophy

> **"Intelligence is not the model. Intelligence is the accumulated decisions that shaped the model."**

Every agent run produces an invisible artifact — a recipe — that captures the complete context of how a decision was made. This system makes those artifacts explicit, versioned, and queryable.

**Recipes are Git commits for intelligence.**

---

## 📄 License

This project is part of the Sovereign AI ecosystem. See the book for full details on licensing and usage.

---

## 🤝 Contributing

Contributions welcome! This is an open-source project built on sovereign principles:
- Local-first everything (no cloud APIs)
- Data sovereignty and privacy
- Open-source and reproducible
- Recipe-based debugging and evolution

---

## 🙏 Acknowledgments

Built with concepts from **Sovereign AI: Building Local-First Intelligent Systems** by Daniel Kliewer.

**Special thanks to:**
- The Sovereign AI community
- Open-source contributors
- Local-first AI advocates

---

## 📞 Connect

- **Website:** [danielkliewer.com](https://www.danielkliewer.com)
- **GitHub:** [@kliewerdaniel](https://github.com/kliewerdaniel)
- **Book:** [Sovereign AI on Amazon](https://www.amazon.com/dp/B0H6RB7D9J)

---

**If the loop is the product, observability of the loop is the operating system.**

*Build intelligence you own. Observe it evolve. Own every decision.*

---

<div align="center">

**[⭐ Star this repo](#)** | **[📖 Get the Book](https://www.amazon.com/dp/B0H6RB7D9J)** | **[🌐 Visit Website](https://www.danielkliewer.com)**

</div>
