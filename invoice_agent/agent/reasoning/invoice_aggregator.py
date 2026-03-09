def is_major_difference(a, b):
    if a is None or b is None:
        return False
    diff = abs(a - b)
    if diff <= 1:
        return False
    return diff / max(abs(a), abs(b), 1) > 0.01


def aggregate_invoice(rows, provided_totals):
    flags = []

    computed_subtotal = round(sum(r.get("subtotal", {}).get("value", 0) or 0 for r in rows), 2)
    computed_gst_total = round(sum(r.get("gst_amount", {}).get("value", 0) or 0 for r in rows), 2)

    provided_subtotal = provided_totals.get("subtotal")
    provided_gst = provided_totals.get("gst_amount")
    provided_rounding = provided_totals.get("rounding")
    provided_net = provided_totals.get("net_payable")

    computed_rounding = round(float(provided_rounding or 0), 2)
    computed_net_payable = round(computed_subtotal + computed_gst_total - abs(computed_rounding), 2)

    if provided_subtotal is not None and is_major_difference(provided_subtotal, computed_subtotal):
        flags.append("Invoice subtotal auto-corrected from row totals")

    if provided_gst is not None and is_major_difference(provided_gst, computed_gst_total):
        flags.append("Invoice GST total auto-corrected from row totals")

    if provided_net is not None and is_major_difference(provided_net, computed_net_payable):
        flags.append("Invoice net payable auto-corrected from subtotal, GST, and rounding")

    return {
        "invoice_subtotal": computed_subtotal,
        "invoice_gst_total": computed_gst_total,
        "rounding": provided_rounding,
        "invoice_net_payable": computed_net_payable,
        "flags": flags,
    }
