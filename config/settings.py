from __future__ import annotations

import os
from pathlib import Path

# Project root is the parent of this file's directory
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent

# Paths
DB_PATH: Path = PROJECT_ROOT / "data" / "leads.db"
LOG_PATH: Path = PROJECT_ROOT / "logs" / "pipeline.log"
SOURCES_YAML: Path = PROJECT_ROOT / "config" / "sources.yaml"
SCORING_YAML: Path = PROJECT_ROOT / "config" / "scoring.yaml"
CHAINS_YAML: Path = PROJECT_ROOT / "config" / "chains.yaml"

# Tavily API key — injected into env automatically from ~/.claude/settings.json
TAVILY_API_KEY: str = os.environ.get("TAVILY_API_KEY", "")
