import re
from datetime import datetime


VALID_GST_BUCKETS = [5.0, 12.0, 18.0, 28.0]
BATCH_LIKE_RE = re.compile(r"^(?=.*[A-Z])(?=.*\d)[A-Z0-9/-]{4,}$")
EXPIRY_RE = re.compile(r"^(0?[1-9]|1[0-2])[/-](\d{2}|\d{4})$")
PACK_UNIT_RE = re.compile(r"\b\d+(?:\.\d+)?\s*(?:ML|GM|KG|G|LTR|L|X\d+|S)\b", re.IGNORECASE)


def is_major_difference(a, b):
    if a is None or b is None:
        return False
    diff = abs(a - b)
    if diff <= 1:
        return False
    return diff / max(abs(a), abs(b), 1) > 0.01


def _parse_expiry(expiry):
    if not expiry or not isinstance(expiry, str):
        return None

    value = expiry.strip()
    patterns = ["%m/%y", "%m/%Y", "%m-%y", "%m-%Y", "%y/%m", "%Y/%m"]
    for p in patterns:
        try:
            dt = datetime.strptime(value, p)
            # Normalize yy/mm patterns by swapping month-year when needed.
            if p in {"%y/%m", "%Y/%m"}:
                dt = datetime(year=dt.year, month=int(value.split("/")[1]), day=1)
            return dt
        except ValueError:
            continue
    return None


def _round_to_valid_gst_bucket(gst_percent):
    if gst_percent is None:
        return None, False
    nearest = min(VALID_GST_BUCKETS, key=lambda b: abs(gst_percent - b))
    if abs(gst_percent - nearest) <= 2.0:
        return nearest, abs(gst_percent - nearest) > 0.0
    return gst_percent, False


def _norm_text(value):
    if value is None:
        return None
    return str(value).strip() or None


def _normalize_product_name(name):
    if not name:
        return name
    tokens = []
    for tok in str(name).strip().split():
        upper_tok = tok.upper()
        # Keep pack-like tokens (5LTR, 10ML, 200GM) but drop batch-like blobs.
        if BATCH_LIKE_RE.match(upper_tok) and not PACK_UNIT_RE.search(upper_tok):
            continue
        tokens.append(upper_tok)
    return " ".join(tokens).strip() or None


def _normalize_company(company):
    if company is None:
        return None
    cleaned = re.sub(r"[^A-Za-z]", "", str(company)).upper()
    if not cleaned:
        return None
    return cleaned[:10]


def _normalize_batch(batch, pack):
    batch_val = _norm_text(batch)
    if not batch_val:
        return None
    batch_val = batch_val.upper()
    if pack:
        pack_val = str(pack).upper().replace(" ", "")
        if batch_val.startswith(pack_val) and len(batch_val) > len(pack_val):
            batch_val = batch_val[len(pack_val):]
    return batch_val or None


def calculate_row(normalized_row: dict):
    flags = []

    def safe_float(value):
        try:
            if value is None:
                return None
            return float(value)
        except Exception:
            return None

    # Normalize string fields first.
    hsn_raw = _norm_text(normalized_row["hsn"]["value"])
    product_raw = _norm_text(normalized_row["product_name"]["value"])
    company_raw = _norm_text(normalized_row["company"]["value"])
    batch_raw = _norm_text(normalized_row["batch"]["value"])
    expiry_raw = _norm_text(normalized_row["expiry"]["value"])
    pack_raw = _norm_text(normalized_row["pack"]["value"])

    normalized_row["product_name"] = {"value": _normalize_product_name(product_raw), "confidence": 0.9}
    normalized_row["company"] = {"value": _normalize_company(company_raw), "confidence": 0.8 if company_raw else 0.0}
    normalized_row["batch"] = {"value": _normalize_batch(batch_raw, pack_raw), "confidence": 0.8 if batch_raw else 0.0}
    normalized_row["pack"] = {"value": pack_raw.upper() if pack_raw else None, "confidence": 0.8 if pack_raw else 0.0}

    # Field validation and swap rules for batch/expiry.
    parsed_exp = _parse_expiry(expiry_raw)
    batch_looks_expiry = bool(batch_raw and EXPIRY_RE.match(batch_raw))
    expiry_looks_batch = bool(expiry_raw and BATCH_LIKE_RE.match(expiry_raw.upper()) and not EXPIRY_RE.match(expiry_raw))
    if batch_looks_expiry and expiry_looks_batch:
        normalized_row["batch"] = {"value": _normalize_batch(expiry_raw, pack_raw), "confidence": 0.8}
        normalized_row["expiry"] = {"value": batch_raw, "confidence": 0.8}
        parsed_exp = _parse_expiry(batch_raw)
        flags.append("Batch and expiry swapped based on format")
    else:
        normalized_row["expiry"] = {"value": expiry_raw, "confidence": 0.8 if expiry_raw else 0.0}

    if expiry_raw and parsed_exp is None:
        flags.append("Invalid expiry format")

    if hsn_raw and (not hsn_raw.isdigit() or not (4 <= len(hsn_raw) <= 8)):
        flags.append("Invalid HSN")

    qty = safe_float(normalized_row["quantity"]["value"])
    free_qty = safe_float(normalized_row["free_quantity"]["value"])
    rate = safe_float(normalized_row["rate"]["value"])
    gst_percent = safe_float(normalized_row["gst_percent"]["value"])
    discount = safe_float(normalized_row["discount_percent"]["value"]) or 0.0
    provided_amount = safe_float(normalized_row["amount"]["value"])
    mrp = safe_float(normalized_row["mrp"]["value"])

    if qty is None and rate not in (None, 0) and provided_amount is not None:
        qty = round(provided_amount / rate, 4)
        normalized_row["quantity"] = {"value": qty, "confidence": 0.7}
        flags.append("Quantity inferred from amount / rate")

    if rate is None and qty not in (None, 0) and provided_amount is not None:
        rate = round(provided_amount / qty, 4)
        normalized_row["rate"] = {"value": rate, "confidence": 0.7}
        flags.append("Rate inferred from amount / quantity")

    if qty is None:
        qty = 0.0
        flags.append("Missing quantity")
    if rate is None:
        rate = 0.0
        flags.append("Missing rate")

    if qty < 0:
        qty = abs(qty)
        normalized_row["quantity"] = {"value": qty, "confidence": 0.5}
        flags.append("Negative quantity corrected to absolute value")

    if free_qty is None:
        free_qty = 0.0
    if free_qty < 0:
        free_qty = abs(free_qty)
        flags.append("Negative free quantity corrected to absolute value")
    normalized_row["free_quantity"] = {"value": round(free_qty, 2), "confidence": 0.8}

    if rate <= 0:
        flags.append("Invalid rate")
    if mrp is not None and mrp <= 0:
        flags.append("Invalid MRP")

    if gst_percent is None:
        buckets = [k for k, v in normalized_row.get("_gst_summary", {}).items() if v.get("taxable_value", 0) > 0]
        if len(buckets) == 1:
            gst_percent = float(buckets[0].replace("%", ""))
            normalized_row["gst_percent"] = {"value": gst_percent, "confidence": 0.8}
            flags.append("GST inferred from summary bucket")
        else:
            gst_percent = 0.0
            flags.append("Missing GST percent")

    corrected_gst, changed = _round_to_valid_gst_bucket(gst_percent)
    if corrected_gst not in VALID_GST_BUCKETS:
        flags.append("Invalid GST bucket")
    else:
        if changed:
            flags.append("GST percent corrected to nearest valid bucket")
        gst_percent = corrected_gst
        normalized_row["gst_percent"] = {"value": gst_percent, "confidence": 0.85}

    if discount < 0:
        discount = 0.0
        normalized_row["discount_percent"] = {"value": discount, "confidence": 0.5}
        flags.append("Negative discount corrected to 0")

    subtotal = round(qty * rate, 2)

    if provided_amount is not None and is_major_difference(subtotal, provided_amount):
        qty_conf = normalized_row["quantity"].get("confidence", 0.0)
        rate_conf = normalized_row["rate"].get("confidence", 0.0)
        if qty_conf < rate_conf and rate != 0:
            qty = round(provided_amount / rate, 4)
            normalized_row["quantity"] = {"value": qty, "confidence": 0.6}
            subtotal = round(qty * rate, 2)
            flags.append("Quantity auto-corrected from amount / rate")
        else:
            normalized_row["amount"] = {"value": subtotal, "confidence": 0.6}
            flags.append("Amount auto-corrected from quantity × rate")

    gst_amount = round(subtotal * gst_percent / 100, 2)
    cgst = round(gst_amount / 2, 2)
    sgst = round(gst_amount / 2, 2)
    row_total = round(subtotal + gst_amount, 2)

    if mrp is not None and rate is not None and mrp > 0 and rate > mrp * 1.2:
        flags.append("Rate significantly higher than MRP")

    if qty == 0 and subtotal > 0:
        flags.append("Subtotal present but quantity is zero")

    normalized_row["hsn"] = {"value": hsn_raw, "confidence": normalized_row["hsn"].get("confidence", 0.0)}
    normalized_row["subtotal"] = {"value": subtotal, "confidence": 1.0}
    normalized_row["gst_amount"] = {"value": gst_amount, "confidence": 1.0}
    normalized_row["cgst"] = {"value": cgst, "confidence": 1.0}
    normalized_row["sgst"] = {"value": sgst, "confidence": 1.0}
    normalized_row["row_total"] = {"value": row_total, "confidence": 1.0}

    return normalized_row, flags
