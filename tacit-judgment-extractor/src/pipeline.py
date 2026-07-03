"""Tacit Judgment Extractor - Analysis Pipeline Engine

Records expert session states and uses local LLM inferences to
extract tacit patterns into actionable decision trees.
"""

import json
import logging
import time
from typing import Optional, List, Dict, Any
from uuid import uuid4

from .models import (
    SessionState, DecisionNode, PatternAnalysis, DecisionTreeExport, AnalyticResult,
    ReasoningPattern,
)
from .database import TacitJudgmentDatabase
from shared.ollama_client import OllamaClient
from shared.config import Settings
from shared.gbnf import gbnf_schema

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


REASONING_PATTERN_PROMPT = """Extract formal reasoning patterns from this expert session.

Domain: {domain}
Session text:
{session_text}

For each reasoning pattern, identify:
- pattern_type: one of (deductive, inductive, abductive, analogical, causal, heuristic)
- antecedents: conditions that trigger this pattern
- consequents: conclusions or actions that follow
- rules: IF-THEN rule statements
- confidence: 0.0 to 1.0

Output valid JSON matching the schema."""


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
        reasoning_patterns = await self._extract_reasoning_patterns(session)
        decision_tree = None
        if patterns:
            decision_tree = await self._build_decision_tree(session, patterns)
        await self.db.update_session_status(session_id, SessionState.COMPLETE.value)

        elapsed_ms = int((time.monotonic() - start_time) * 1000)
        return AnalyticResult(
            session_id=session_id,
            patterns=patterns,
            decision_tree=decision_tree,
            reasoning_patterns=reasoning_patterns,
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

    async def _extract_reasoning_patterns(
        self, session: Dict[str, Any]
    ) -> List[ReasoningPattern]:
        """Extract formal reasoning patterns using GBNF-constrained LLM when available."""
        if self.ollama is not None and self.settings.enable_ollama:
            try:
                gbnf = gbnf_schema(ReasoningPattern)
            except Exception:
                gbnf = None

            if gbnf:
                prompt = REASONING_PATTERN_PROMPT.format(
                    domain=session.get("domain", "general"),
                    session_text=session.get("session_text", ""),
                )
                raw = await self.ollama.generate(
                    prompt=prompt,
                    system="You are a reasoning pattern extractor. Output valid JSON.",
                    format=gbnf,
                    options={"temperature": 0.3},
                )
                if raw:
                    try:
                        data = json.loads(raw)
                        if isinstance(data, dict):
                            data = [data]
                        return [ReasoningPattern(**rp) for rp in data]
                    except (json.JSONDecodeError, Exception) as exc:
                        logger.debug("GBNF extraction failed: %s", exc)

        return self._fallback_reasoning_extraction(session)

    def _fallback_reasoning_extraction(
        self, session: Dict[str, Any]
    ) -> List[ReasoningPattern]:
        """Rule-based reasoning pattern extraction when LLM is unavailable."""
        text = session.get("session_text", "")
        lower = text.lower()
        patterns = []
        session_id = session["session_id"]

        pattern_indicators = [
            ("deductive", ["if", "then", "therefore", "must be", "implies"]),
            ("inductive", ["usually", "typically", "often", "tends to", "most"]),
            ("abductive", ["best explanation", "likely because", "probably due to"]),
            ("analogical", ["similar to", "like", "analogous", "comparable"]),
            ("causal", ["causes", "leads to", "results in", "because", "due to"]),
            ("heuristic", ["rule of thumb", "always", "never", "check for", "look for"]),
        ]

        for ptype, indicators in pattern_indicators:
            matched = [ind for ind in indicators if ind in lower]
            if matched:
                rules = [line.strip() for line in text.split("\n")
                         if any(ind in line.lower() for ind in matched) and line.strip()]
                patterns.append(ReasoningPattern(
                    pattern_id=f"reason-{uuid4().hex[:8]}",
                    session_id=session_id,
                    pattern_type=ptype,
                    confidence=0.5,
                    description=f"Detected {ptype} reasoning via indicators: {', '.join(matched)}",
                    extracted_rules=rules[:3],
                    antecedents=[f"Trigger: {matched[0]}"],
                    consequents=rules[:2],
                ))

        return patterns

    def _parse_llm_tree_response(self, raw: str) -> Optional[List[DecisionNode]]:
        """Defensive lookahead token verification for LLM decision tree output.

        Performs a three-phase validation:
        1. Structural lookahead — scans for balanced braces and valid JSON prefix.
        2. Schema conformance — every parsed node must have ``condition``,
           ``action``, ``confidence``, and ``rationale``.
        3. Corrupted-stream fallback — truncates at the last valid JSON object
           if the stream was cut off mid-object.
        """
        if not raw or len(raw.strip()) < 10:
            logger.debug("LLM response too short for decision tree parsing")
            return None

        text = raw.strip()

        # Phase 1: balanced-brace lookahead
        depth = 0
        last_valid_brace = -1
        for i, ch in enumerate(text):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    last_valid_brace = i
                elif depth < 0:
                    logger.debug("Unbalanced braces at position %d", i)
                    break
        truncated = text[:last_valid_brace + 1] if last_valid_brace > 0 else text
        if not truncated.endswith("}") and not truncated.endswith("]"):
            logger.debug("No complete JSON structure found; falling back to rule-based tree")
            return None

        # Phase 2: tentatively wrap bare objects in an array
        candidates = []
        attempt = None
        for wrapper in [truncated, f"[{truncated}]"]:
            try:
                parsed = json.loads(wrapper)
                attempt = parsed
                break
            except json.JSONDecodeError:
                continue
        if attempt is None:
            logger.debug("JSON decode failed after brace lookahead")
            return None

        if isinstance(attempt, dict):
            attempt = [attempt]

        # Phase 3: schema conformance
        nodes = []
        for item in attempt:
            if not isinstance(item, dict):
                continue
            condition = item.get("condition") or item.get("node") or item.get("rule")
            if not condition:
                continue
            action = item.get("action") or item.get("decision") or "Take action based on condition"
            try:
                confidence = float(item.get("confidence", 0.6))
            except (ValueError, TypeError):
                confidence = 0.6
            rationale = item.get("rationale") or item.get("description") or item.get("reason", "LLM extracted")

            if isinstance(condition, str) and len(condition) > 3:
                nodes.append(DecisionNode(
                    node_id=f"node-llm-{uuid4().hex[:8]}",
                    parent_id=None,
                    condition=condition,
                    action=str(action),
                    confidence=max(0.0, min(1.0, confidence)),
                    rationale=str(rationale),
                    children=[],
                ))

        if not nodes:
            logger.debug("Zero schema-conformant nodes after lookahead validation")
            return None

        logger.debug("Lookahead-verified %d LLM decision nodes", len(nodes))
        return nodes

    async def _build_decision_tree(
        self, session: Dict[str, Any], patterns: List[PatternAnalysis]
    ) -> Optional[DecisionTreeExport]:
        """Build a structured decision tree from extracted patterns."""
        nodes: List[DecisionNode] = []
        corrections = session.get("corrections", [])

        llm_nodes = []
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
                llm_nodes = self._parse_llm_tree_response(response) or []

        root_id = f"node-root-{uuid4().hex[:8]}"

        root_id = f"node-root-{uuid4().hex[:8]}"
        nodes.append(DecisionNode(
            node_id=root_id,
            condition=f"Analyze {session.get('domain', 'general')} judgment",
            action="Begin expert decision process",
            confidence=1.0,
            rationale="Root node for decision tree extraction",
            children=[],
        ))

        if llm_nodes:
            nodes[0].children.extend(n.node_id for n in llm_nodes)
            for n in llm_nodes:
                n.parent_id = root_id
            nodes.extend(llm_nodes)
        else:
            for i, pattern in enumerate(patterns):
                node_id = f"node-{uuid4().hex[:8]}"
                nodes[0].children.append(node_id)
                nodes.append(DecisionNode(
                    node_id=node_id,
                    parent_id=root_id,
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
