import os
from typing import Dict, Any, List

# In-memory storage (replace with persistent store / DB in production)
user_checklists: Dict[str, Dict[str, Any]] = {}


def vision_base_url() -> str:
    """Base URL for the vision service (resolves inside docker network)."""
    return os.getenv("AI_VISION_BASE_URL", "http://ai-vision:8000")


def extract_field(info_list: List, key: str) -> str:
    """Extract a value for a key from the info list structure [[k,v,k2,v2], ...]."""
    if not info_list:
        return ""
    for row in info_list:
        if not isinstance(row, list):
            continue
        if len(row) >= 2 and row[0] == key:
            return row[1] or ""
        if len(row) >= 4 and row[2] == key:
            return row[3] or ""
    return ""


def get_user_checklist(user_key: str = "default_user") -> Dict[str, Any]:
    return user_checklists.get(user_key, {})


def save_user_checklist(data: Dict[str, Any], user_key: str = "default_user") -> None:
    user_checklists[user_key] = data
