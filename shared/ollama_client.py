"""Optional Ollama client for local LLM integration with graceful fallback"""

import json
import logging
from typing import Optional, Dict, Any, List
from urllib.parse import urljoin

import httpx

logger = logging.getLogger(__name__)


class OllamaClient:
    """HTTP client for a local Ollama instance.

    All methods gracefully handle connection failures so the platform
    remains operational when Ollama is not running.
    """

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "qwen2.5:3b", timeout: float = 60.0):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=httpx.Timeout(self.timeout))
        return self._client

    async def _post(self, path: str, payload: dict) -> Optional[Dict[str, Any]]:
        try:
            resp = await self.client.post(
                urljoin(f"{self.base_url}/", path),
                json=payload,
            )
            resp.raise_for_status()
            return resp.json()
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            logger.warning("Ollama not reachable at %s: %s", self.base_url, exc)
            return None
        except httpx.HTTPStatusError as exc:
            logger.warning("Ollama HTTP error %s: %s", exc.response.status_code, exc.response.text)
            return None

    async def health(self) -> bool:
        result = await self._post("api/generate", {"model": self.model, "prompt": "", "stream": False})
        return result is not None

    async def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        format: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """Generate text via Ollama. Returns None if unavailable."""
        payload: Dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }
        if system:
            payload["system"] = system
        if format:
            payload["format"] = format
        if options:
            payload["options"] = options

        result = await self._post("api/generate", payload)
        if result is None:
            return None
        return result.get("response", "")

    async def generate_with_grammar(
        self,
        prompt: str,
        gbnf_grammar: str,
        system: Optional[str] = None,
    ) -> Optional[str]:
        """Generate text constrained by a GBNF grammar. Falls back to plain generation."""
        return await self.generate(
            prompt=prompt,
            system=system,
            format=gbnf_grammar,
        )

    async def embed(self, text: str) -> Optional[List[float]]:
        """Get embedding vector for text. Returns None if unavailable."""
        result = await self._post("api/embeddings", {
            "model": self.model,
            "prompt": text,
        })
        if result is None:
            return None
        return result.get("embedding")

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    RECIPE_GBNF_GRAMMAR = """
root ::= recipe-object
recipe-object ::= "{" ws fields ws "}"
fields ::= field ("," ws field)*
field ::= recipe-id-field | objective-field | model-field | prompt-version-field | memory-version-field | retrieved-docs-field | reasoning-patterns-field | evaluation-field | outcome-field
recipe-id-field ::= "\"recipe_id\"" ws ":" ws string
objective-field ::= "\"objective\"" ws ":" ws string
model-field ::= "\"model\"" ws ":" ws string
prompt-version-field ::= "\"prompt_version\"" ws ":" ws number
memory-version-field ::= "\"memory_version\"" ws ":" ws number
retrieved-docs-field ::= "\"retrieved_docs\"" ws ":" ws array
reasoning-patterns-field ::= "\"reasoning_patterns\"" ws ":" ws array
evaluation-field ::= "\"evaluation\"" ws ":" ws eval-object
outcome-field ::= "\"outcome\"" ws ":" ws string
eval-object ::= "{" ws eval-fields ws "}"
eval-fields ::= eval-field ("," ws eval-field)*
eval-field ::= "\"score\"" ws ":" ws number | "\"reviewed_by\"" ws ":" ws string
array ::= "[" ws "]" | "[" ws string ("," ws string)* ws "]"
string ::= "\"" [^\"]* "\""
number ::= [0-9]+ "."? [0-9]*
ws ::= [ \t\n]*
"""
