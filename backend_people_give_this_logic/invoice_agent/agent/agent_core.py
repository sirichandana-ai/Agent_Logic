from invoice_agent.agent.input_parser.universal_parser import parse_input
from invoice_agent.agent.mapper.database_mapper import map_to_database_rows
from invoice_agent.agent.reasoning.invoice_aggregator import aggregate_invoice
from invoice_agent.agent.reasoning.row_calculator import calculate_row
from invoice_agent.agent.resolver.column_aliases import CANONICAL_FIELDS
from invoice_agent.agent.resolver.item_normalizer import normalize_item_row


def enforce_schema(items):
    for item in items:
        for field in CANONICAL_FIELDS:
            item.setdefault(field, None)
    return items


def process_invoice(raw_text: str):
    parsed_data = parse_input(raw_text)
    items = enforce_schema(parsed_data.get("items", []))
    gst_summary = parsed_data.get("gst_summary", {})
    totals = parsed_data.get("totals", {})

    processed_rows = []
    for raw_row in items:
        normalized, norm_flags = normalize_item_row(raw_row, gst_summary)
        normalized["_gst_summary"] = gst_summary

        calculated, calc_flags = calculate_row(normalized)
        calculated.pop("_gst_summary", None)

        row_flags = norm_flags + calc_flags
        calculated["status"] = "⚠ Needs Review" if row_flags else "✔ Verified"
        calculated["flags"] = row_flags
        processed_rows.append(calculated)

    return {
        "rows": map_to_database_rows(processed_rows),
        "summary": aggregate_invoice(processed_rows, totals, gst_summary),
    }
