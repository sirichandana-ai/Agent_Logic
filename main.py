import argparse
import json
import sys
from pathlib import Path

from invoice_agent.agent.agent_core import process_invoice
from invoice_agent.agent.input_parser.universal_parser import parse_input


def _wrap_legacy_result(result, raw_text):
    """Keep CLI output stable even if an older process_invoice returns only rows."""
    if isinstance(result, dict) and "rows" in result and "summary" in result:
        return result

    if isinstance(result, list):
        rows = result
        totals = parse_input(raw_text).get("totals", {})

        invoice_subtotal = round(sum((r.get("subtotal") or 0) for r in rows), 2)
        invoice_gst_total = round(sum((r.get("gst_amount") or 0) for r in rows), 2)
        rounding = totals.get("rounding")
        computed_rounding = round(float(rounding or 0), 2)
        invoice_total = round(invoice_subtotal + invoice_gst_total - abs(computed_rounding), 2)

        return {
            "rows": rows,
            "summary": {
                "invoice_subtotal": invoice_subtotal,
                "invoice_gst_total": invoice_gst_total,
                "rounding": rounding,
                "invoice_total": invoice_total,
                "invoice_net_payable": invoice_total,
                "flags": [],
            },
        }

    return {"rows": [], "summary": {"invoice_subtotal": 0.0, "invoice_gst_total": 0.0, "rounding": None, "invoice_total": 0.0, "invoice_net_payable": 0.0, "flags": ["Unexpected process_invoice output shape"]}}


def main():
    parser = argparse.ArgumentParser(description="Process invoice markdown/json into validated rows.")
    parser.add_argument("input_file", help="Path to OCR markdown (.md/.txt) or json file")
    parser.add_argument("-o", "--output", help="Optional output json path")
    args = parser.parse_args()

    raw_text = Path(args.input_file).read_text(encoding="utf-8")
    result = process_invoice(raw_text)
    result = _wrap_legacy_result(result, raw_text)

    output = json.dumps(result, indent=2, ensure_ascii=False)
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
    sys.stdout.buffer.write(output.encode("utf-8"))
    sys.stdout.buffer.write(b"\n")


if __name__ == "__main__":
    main()
