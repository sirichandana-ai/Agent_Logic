import json
from typing import Any, Dict


def parse_json_input(text: str) -> Dict[str, Any]:
    data = json.loads(text)
    return {
        "items": data.get("items", []),
        "gst_summary": data.get("gst_summary", {}),
        "totals": data.get("totals", {}),
    }
