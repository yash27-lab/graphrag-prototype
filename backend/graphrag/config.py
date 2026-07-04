"""Runtime configuration, sourced from environment variables."""

import os
from typing import List, Optional


class Settings:
    """Application settings.

    Every value has a sensible local-development default so the server can
    start with zero configuration; Docker and CI override via environment.
    """

    def __init__(self) -> None:
        self.persist_dir: str = os.getenv("PERSIST_DIR", "./data")
        self.gemini_api_key: Optional[str] = os.getenv("GEMINI_API_KEY")
        self.cors_origins: List[str] = [
            origin.strip()
            for origin in os.getenv(
                "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
            ).split(",")
            if origin.strip()
        ]
