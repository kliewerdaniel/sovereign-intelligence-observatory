"""Central configuration for the observatory platform"""

import os
from typing import Optional
from dataclasses import dataclass, field


@dataclass
class Settings:
    ollama_base_url: str = field(
        default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    )
    ollama_model: str = field(
        default_factory=lambda: os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
    )
    chroma_host: str = field(
        default_factory=lambda: os.getenv("CHROMA_HOST", "localhost")
    )
    chroma_port: int = field(
        default_factory=lambda: int(os.getenv("CHROMA_PORT", "8000"))
    )
    chroma_collection: str = field(
        default_factory=lambda: os.getenv("CHROMA_COLLECTION", "observatory_recipes")
    )
    enable_ollama: bool = field(
        default_factory=lambda: os.getenv("ENABLE_OLLAMA", "true").lower() == "true"
    )
    enable_chroma: bool = field(
        default_factory=lambda: os.getenv("ENABLE_CHROMA", "true").lower() == "true"
    )

    @classmethod
    def from_env(cls) -> "Settings":
        return cls()
