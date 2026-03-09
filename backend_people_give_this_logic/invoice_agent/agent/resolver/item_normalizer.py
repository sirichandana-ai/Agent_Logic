import re
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Tuple

from invoice_agent.agent.resolver.column_aliases import ALIASES, CANONICAL_FIELDS

NUMERIC_FIELDS = {
    "quantity",
    "free_quantity",
    "rate",
    "amount",
    "mrp",
    "gst_percent",
    "discount_percent",
    "cgst",
    "sgst",
    "igst",
}


def _clean_key(key: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(key).lower())


def _sim(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def _normalize_value(field: str, value: Any) -> Any:
    if field not in NUMERIC_FIELDS:
        return value.strip() if isinstance(value, str) else value

    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        raw = value.replace(",", "").strip()
        if not raw:
            return None
        try:
            return float(raw)
        except ValueError:
            return value.strip()
    return value


def match_field(raw_key: str) -> Tuple[Optional[str], float]:
    cleaned = _clean_key(raw_key)

    for field, aliases in ALIASES.items():
        if any(cleaned == _clean_key(a) for a in aliases):
            return field, 1.0

    for field, aliases in ALIASES.items():
        if any(_clean_key(a) in cleaned for a in aliases):
            return field, 0.9

    best_field, best_score = None, 0.0
    for field, aliases in ALIASES.items():
        for alias in aliases:
            score = _sim(cleaned, _clean_key(alias))
            if score > best_score:
                best_field, best_score = field, score

    if best_score >= 0.75:
        return best_field, 0.85
    return None, 0.0


def normalize_item_row(raw_row: Dict[str, Any], gst_summary: Dict[str, Any]) -> Tuple[Dict[str, Dict[str, Any]], List[str]]:
    normalized = {field: {"value": None, "confidence": 0.0} for field in CANONICAL_FIELDS}
    flags: List[str] = []

    for key, value in raw_row.items():
        if value is None:
            continue
        field, conf = match_field(key)
        if field:
            normalized[field] = {"value": _normalize_value(field, value), "confidence": conf}

    gst = normalized["gst_percent"]["value"]
    if gst is not None:
        try:
            bucket = f"{int(float(gst))}%"
            if gst_summary and bucket not in gst_summary:
                flags.append("GST bucket not found in summary")
        except Exception:
            flags.append("Invalid GST format")

    return normalized, flags
