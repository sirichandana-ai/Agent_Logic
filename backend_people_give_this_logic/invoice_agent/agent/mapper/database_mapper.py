def map_to_database_rows(processed_rows):
    db_rows = []
    for row in processed_rows:
        db_rows.append(
            {
                "hsn": row.get("hsn", {}).get("value"),
                "product_name": row.get("product_name", {}).get("value"),
                "company": row.get("company", {}).get("value"),
                "batch": row.get("batch", {}).get("value"),
                "expiry": row.get("expiry", {}).get("value"),
                "pack": row.get("pack", {}).get("value"),
                "barcode": row.get("barcode", {}).get("value"),
                "code": row.get("code", {}).get("value"),
                "quantity": row.get("quantity", {}).get("value"),
                "free_quantity": row.get("free_quantity", {}).get("value"),
                "rate": row.get("rate", {}).get("value"),
                "amount": row.get("amount", {}).get("value"),
                "subtotal": row.get("subtotal", {}).get("value"),
                "mrp": row.get("mrp", {}).get("value"),
                "gst_percent": row.get("gst_percent", {}).get("value"),
                "gst_amount": row.get("gst_amount", {}).get("value"),
                "cgst": row.get("cgst", {}).get("value"),
                "sgst": row.get("sgst", {}).get("value"),
                "igst": row.get("igst", {}).get("value"),
                "discount_percent": row.get("discount_percent", {}).get("value"),
                "row_total": row.get("row_total", {}).get("value"),
                "status": row.get("status"),
                "flags": row.get("flags", []),
            }
        )
    return db_rows
