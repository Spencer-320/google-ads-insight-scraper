from __future__ import annotations

from pathlib import Path
from typing import List, Dict

from .exporters import write_json

def save_ads_records(records: List[Dict], path: Path) -> None:
    """
    Persist list of ad records to JSON.
    """
    write_json(path, records, indent=2)