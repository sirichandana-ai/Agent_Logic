def is_major_difference(a, b):
    if a is None or b is None:
        return False
    diff = abs(a - b)
    if diff <= 1:
        return False
    return diff / max(abs(a), abs(b), 1) > 0.01


def aggregate_invoice(rows, provided_totals, gst_summary=None):
    flags = []

    computed_subtotal = round(sum(r.get("subtotal", {}).get("value", 0) or 0 for r in rows), 2)
    computed_gst_total = round(sum(r.get("gst_amount", {}).get("value", 0) or 0 for r in rows), 2)

    provided_subtotal = provided_totals.get("subtotal")
    provided_gst = provided_totals.get("gst_amount")
    provided_rounding = provided_totals.get("rounding")
    provided_net = provided_totals.get("net_payable")

    computed_rounding = round(float(provided_rounding or 0), 2)
    computed_invoice_total = round(computed_subtotal + computed_gst_total - abs(computed_rounding), 2)

    if provided_subtotal is not None and is_major_difference(provided_subtotal, computed_subtotal):
        flags.append("Invoice subtotal auto-corrected from row totals")

    if provided_gst is not None and is_major_difference(provided_gst, computed_gst_total):
        flags.append("Invoice GST total auto-corrected from row totals")

    if provided_net is not None and is_major_difference(provided_net, computed_invoice_total):
        flags.append("Invoice net payable auto-corrected from subtotal, GST, and rounding")

    if gst_summary:
        row_bucket_totals = {}
        for row in rows:
            gst = row.get("gst_percent", {}).get("value")
            taxable = row.get("subtotal", {}).get("value") or 0
            try:
                bucket = f"{int(round(float(gst)))}%"
            except Exception:
                continue
            row_bucket_totals[bucket] = round(row_bucket_totals.get(bucket, 0) + float(taxable), 2)

        mismatch = False
        for bucket, summary_values in gst_summary.items():
            summary_taxable = round(float(summary_values.get("taxable_value", 0) or 0), 2)
            row_taxable = round(float(row_bucket_totals.get(bucket, 0) or 0), 2)
            if abs(summary_taxable - row_taxable) > 1:
                mismatch = True
                break
        if mismatch:
            flags.append("GST bucket not matching row totals")

    return {
        "invoice_subtotal": computed_subtotal,
        "invoice_gst_total": computed_gst_total,
        "rounding": provided_rounding,
        "invoice_total": computed_invoice_total,
        "invoice_net_payable": computed_invoice_total,
        "flags": flags,
    }
