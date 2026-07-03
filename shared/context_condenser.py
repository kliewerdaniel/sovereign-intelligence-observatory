"""Token-Aware Context Condenser

Estimates token counts for recipe context elements and
truncates/summarizes when the active window is exceeded.
"""

import os
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

TOKENIZER_MODEL = os.getenv("TOKENIZER_MODEL", "cl100k_base")
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "8192"))
CONTEXT_WINDOW_RATIO = float(os.getenv("CONTEXT_WINDOW_RATIO", "0.85"))


class ContextTruncationError(Exception):
    """Raised when truncation cannot bring the context under the token limit."""


class TokenAwareContextCondenser:
    """Streaming token calculator with semantic truncation.

    Uses tiktoken when available; falls back to a whitespace heuristic
    (len(text.split())) for local-only environments.
    """

    def __init__(
        self,
        tokenizer_model: str = TOKENIZER_MODEL,
        max_tokens: int = MAX_TOKENS,
        context_window_ratio: float = CONTEXT_WINDOW_RATIO,
    ):
        self.tokenizer_model = tokenizer_model
        self.max_tokens = max_tokens
        self.window_threshold = int(max_tokens * context_window_ratio)
        self._encoder = None
        self._tiktoken_available = False
        self._init_tokenizer()

    def _init_tokenizer(self) -> None:
        try:
            import tiktoken
            self._encoder = tiktoken.get_encoding(self.tokenizer_model)
            self._tiktoken_available = True
        except (ImportError, KeyError):
            logger.debug(
                "tiktoken not available or model '%s' not found; "
                "falling back to whitespace heuristic",
                self.tokenizer_model,
            )
            self._tiktoken_available = False

    def estimate_tokens(self, text: str) -> int:
        if not text:
            return 0
        if self._tiktoken_available and self._encoder is not None:
            return len(self._encoder.encode(text))
        return len(text.split())

    def condense(
        self,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Reduce context to fit within the token window.

        Strategy:
          1. Flatten all recipe contexts, compute total tokens.
          2. If below threshold, return as-is.
          3. Otherwise, drop oldest recipe contexts until within threshold.
          4. If still over threshold after dropping all, raise ContextTruncationError.
        """
        tokens = self._compute_structure_tokens(context)
        total = tokens.get("total", 0)

        if total <= self.window_threshold:
            return {"condensed": context, "truncated_count": 0, "token_savings": 0}

        condensed = self._drop_oldest_recipes(context, total)
        new_total = self._compute_total(condensed)

        if new_total > self.max_tokens:
            summarized = self._summarize_context(condensed)
            final_total = self._compute_total(summarized)
            if final_total > self.max_tokens:
                raise ContextTruncationError(
                    f"Context at {final_total} tokens exceeds max {self.max_tokens} "
                    "even after summarization. Consider increasing MAX_TOKENS or "
                    "reducing input size."
                )
            condensed = summarized

        final_tokens = self._compute_total(condensed)
        return {
            "condensed": condensed,
            "truncated_count": len(context.get("recipe_contexts", [])) - len(condensed.get("recipe_contexts", [])),
            "token_savings": total - final_tokens,
        }

    def _compute_structure_tokens(self, context: Dict[str, Any]) -> Dict[str, int]:
        """Return per-section token counts for debug/visibility."""
        result: Dict[str, int] = {"total": 0}
        for key, value in context.items():
            if key == "recipe_contexts":
                recipe_tokens = 0
                for recipe in value:
                    recipe_tokens += self.estimate_tokens(str(recipe))
                result["recipe_contexts"] = recipe_tokens
                result["total"] += recipe_tokens
            else:
                section_tokens = self.estimate_tokens(str(value))
                result[key] = section_tokens
                result["total"] += section_tokens
        return result

    def _compute_total(self, context: Dict[str, Any]) -> int:
        return sum(self.estimate_tokens(str(v)) for v in context.values())

    def _drop_oldest_recipes(
        self, context: Dict[str, Any], current_total: int
    ) -> Dict[str, Any]:
        """Drop recipe contexts from the front until under the threshold."""
        recipes = list(context.get("recipe_contexts", []))
        remaining = current_total
        drop_count = 0
        while recipes and remaining > self.window_threshold:
            dropped = recipes.pop(0)
            remaining -= self.estimate_tokens(str(dropped))
            drop_count += 1

        new_context = {k: v for k, v in context.items() if k != "recipe_contexts"}
        new_context["recipe_contexts"] = recipes
        logger.debug(
            "Dropped %d oldest recipe contexts (%d tokens saved)",
            drop_count,
            current_total - remaining,
        )
        return new_context

    def _summarize_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Produce a compact representation of the context.

        Falls back to keeping only the most recent recipe context and
        compressing other sections to their estimated token count as a
        single-line metadata summary.
        """
        summarized: Dict[str, Any] = {}
        for key, value in context.items():
            if key == "recipe_contexts":
                recipes = list(value)
                if recipes:
                    summarized["recipe_contexts"] = [recipes[-1]]
                else:
                    summarized["recipe_contexts"] = []
            else:
                text = str(value)
                tokens = self.estimate_tokens(text)
                if tokens > 50:
                    summarized[key] = f"[{tokens} tokens — truncated]"
                else:
                    summarized[key] = text
        return summarized
