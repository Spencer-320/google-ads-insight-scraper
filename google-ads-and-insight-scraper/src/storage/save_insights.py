from __future__ import annotations

from pathlib import Path
from typing import Dict

from .exporters import write_json

def save_insights_records(insights: Dict, path: Path) -> None:
    """
    Persist insights dictionary to JSON.
    """
    write_json(path, insights, indent=2)