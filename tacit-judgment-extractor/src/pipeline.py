"""Tacit Judgment Extractor - Analysis Pipeline Engine

Records expert session states and uses local LLM inferences to
extract tacit patterns into actionable decision trees.
"""

import logging
import time
from typing import Optional, List, Dict, Any
from uuid import uuid4

from .models import (
    SessionState, DecisionNode, PatternAnalysis, DecisionTreeExport, AnalyticResult,
)
from .database import TacitJudgmentDatabase
from shared.ollama_client import OllamaClient
from shared.config import Settings

logger = logging.getLogger(__name__)


PATTERN_EXTRACTION_PROMPT = """Analyze the following expert decision session and extract tacit patterns.

Expert domain: {domain}
Session text:
{session_text}

For each pattern, identify:
1. The type of heuristic or rule being applied
2. The conditions under which it applies
3. The confidence level (0.0 to 1.0)
4. Specific extracted rules in IF-THEN form

Output as a structured analysis."""


DECISION_TREE_PROMPT = """Convert the following expert session into a decision tree.

Domain: {domain}
Session with corrections:
{session_text_with_corrections}

Previously identified patterns:
{patterns_text}

Create decision nodes where each node has:
- condition: the decision criterion
- action: the resulting action or judgment
- confidence: how reliably this rule applies (0.0-1.0)
- rationale: why this rule exists

Output as structured JSON decision tree."""


class TacitJudgmentPipeline:
    """Orchestrates the extraction of tacit knowledge from expert sessions."""

    def __init__(
        self,
        db: TacitJudgmentDatabase,
        ollama: Optional[OllamaClient] = None,
        settings: Optional[Settings] = None,
    ):
        self.db = db
        self.ollama = ollama
        self.settings = settings or Settings.from_env()

    async def analyze_session(
        self, session_id: str
    ) -> AnalyticResult:
        """Run the full analysis pipeline on a recorded session."""
        start_time = time.monotonic()
        await self.db.update_session_status(session_id, SessionState.ANALYZING.value)
        session = await self.db.get_session(session_id)
        if session is None:
            raise ValueError(f"Session not found: {session_id}")

        patterns = await self._extract_patterns(session)
        decision_tree = None
        if patterns:
            decision_tree = await self._build_decision_tree(session, patterns)
        await self.db.update_session_status(session_id, SessionState.COMPLETE.value)

        elapsed_ms = int((time.monotonic() - start_time) * 1000)
        return AnalyticResult(
            session_id=session_id,
            patterns=patterns,
            decision_tree=decision_tree,
            analysis_duration_ms=elapsed_ms,
        )

    async def _extract_patterns(
        self, session: Dict[str, Any]
    ) -> List[PatternAnalysis]:
        """Use local LLM to extract tacit patterns from session text."""
        if self.ollama is None or not self.settings.enable_ollama:
            return self._fallback_pattern_extraction(session)

        prompt = PATTERN_EXTRACTION_PROMPT.format(
            domain=session.get("domain", "general"),
            session_text=session.get("session_text", ""),
        )

        response = await self.ollama.generate(
            prompt=prompt,
            system="You are an expert knowledge engineer extracting decision patterns.",
            options={"temperature": 0.3},
        )

        if response is None:
            logger.warning("Ollama unavailable; using rule-based pattern extraction")
            return self._fallback_pattern_extraction(session)

        basic_patterns = self._fallback_pattern_extraction(session)

        llm_pattern = PatternAnalysis(
            pattern_id=f"pattern-llm-{uuid4().hex[:8]}",
            session_id=session["session_id"],
            pattern_type="llm_extracted",
            confidence=0.7,
            description=response[:500],
            extracted_rules=[response[:200]] if len(response) > 50 else [],
        )
        basic_patterns.append(llm_pattern)

        for pattern in basic_patterns:
            await self.db.add_pattern_analysis(session["session_id"], pattern)

        return basic_patterns

    def _fallback_pattern_extraction(
        self, session: Dict[str, Any]
    ) -> List[PatternAnalysis]:
        """Rule-based fallback when Ollama is unavailable."""
        text = session.get("session_text", "")
        lines = text.split("\n")
        patterns = []
        domain = session.get("domain", "general")

        keywords = {
            "if": "conditional_rule",
            "when": "conditional_rule",
            "always": "invariant_rule",
            "never": "invariant_rule",
            "depends": "contextual_heuristic",
            "usually": "probabilistic_heuristic",
            "threshold": "threshold_rule",
        }

        for i, line in enumerate(lines):
            lower = line.lower().strip()
            for keyword, ptype in keywords.items():
                if keyword in lower:
                    patterns.append(PatternAnalysis(
                        pattern_id=f"pattern-{uuid4().hex[:8]}",
                        session_id=session["session_id"],
                        pattern_type=ptype,
                        confidence=0.4,
                        description=f"Line {i + 1} contained '{keyword}' indicator in {domain} context",
                        extracted_rules=[line.strip()],
                    ))
                    break

        return patterns

    async def _build_decision_tree(
        self, session: Dict[str, Any], patterns: List[PatternAnalysis]
    ) -> Optional[DecisionTreeExport]:
        """Build a structured decision tree from extracted patterns."""
        nodes: List[DecisionNode] = []
        corrections = session.get("corrections", [])

        if self.ollama is not None and self.settings.enable_ollama:
            corrections_text = "\n".join(
                f"Original: {c.get('original_text', '')} -> Corrected: {c.get('corrected_text', '')}"
                for c in corrections
            )
            patterns_text = "\n".join(
                f"- {p.pattern_type}: {p.description[:200]}"
                for p in patterns
            )

            prompt = DECISION_TREE_PROMPT.format(
                domain=session.get("domain", "general"),
                session_text_with_corrections=corrections_text or session.get("session_text", ""),
                patterns_text=patterns_text or "No patterns identified.",
            )

            response = await self.ollama.generate(
                prompt=prompt,
                system="You are a decision tree builder. Output JSON only.",
                options={"temperature": 0.2},
            )

            if response:
                logger.debug("LLM decision tree response received (%d chars)", len(response))

        root_id = f"node-root-{uuid4().hex[:8]}"
        nodes.append(DecisionNode(
            node_id=root_id,
            condition=f"Analyze {session.get('domain', 'general')} judgment",
            action="Begin expert decision process",
            confidence=1.0,
            rationale="Root node for decision tree extraction",
            children=[],
        ))

        for i, pattern in enumerate(patterns):
            node_id = f"node-{uuid4().hex[:8]}"
            if nodes:
                nodes[0].children.append(node_id)
            nodes.append(DecisionNode(
                node_id=node_id,
                parent_id=root_id if nodes else None,
                condition=f"Pattern: {pattern.pattern_type} (confidence: {pattern.confidence:.2f})",
                action=f"Apply rule: {pattern.description[:200]}",
                confidence=pattern.confidence,
                rationale=f"Extracted from {pattern.pattern_type} analysis",
                children=[],
            ))

        for node in nodes:
            await self.db.add_decision_node(session["session_id"], node)

        export = DecisionTreeExport(
            tree_id=f"tree-{uuid4().hex[:8]}",
            session_id=session["session_id"],
            domain=session.get("domain", "general"),
            expert_id=session.get("expert_id", "unknown"),
            nodes=nodes,
        )
        await self.db.export_decision_tree(export)
        return export
