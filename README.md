# Invoice Agentic Logic (Markdown → Validated Rows)

This project takes **OLMOCR markdown output** as input and returns robust, rule-based, corrected invoice rows.

## Goal

Given noisy OCR markdown (wrong aliases, missing values, wrong totals), this pipeline:

1. Parses rows from markdown (pipe-table and OCR space-table styles).
2. Normalizes field names to a canonical schema.
3. Recalculates row math (`subtotal`, `gst_amount`, `cgst`, `sgst`, `row_total`).
4. Applies domain validations (expiry format, GST sanity, MRP sanity, negative values).
5. Flags suspicious corrections instead of silently failing.
6. Returns clean database-ready rows.

---

## Architecture

```text
main.py
  -> agent_core.process_invoice(raw_text)
      -> input_parser.universal_parser.parse_input
          -> llm_cleaner.clean_llm_output
          -> try json_parser.parse_json_input
          -> else markdown_parser.parse_markdown_input
      -> resolver.item_normalizer.normalize_item_row
      -> reasoning.row_calculator.calculate_row
      -> reasoning.invoice_aggregator.aggregate_invoice
      -> mapper.database_mapper.map_to_database_rows
```

### Module overview

- `invoice_agent/agent/input_parser/markdown_parser.py`
  - Reads OCR markdown and extracts:
    - `items`
    - `gst_summary`
    - `totals`
  - Handles:
    - pipe tables (`| col |`)
    - OCR space-separated tables (`MFG Hsn Product ...`)
    - compact fallback rows for uneven OCR layouts

- `invoice_agent/agent/resolver/item_normalizer.py`
  - Maps noisy keys (`Descrption`, `quantty`, `tax`) to canonical fields.
  - Adds confidence values to each mapped field.

- `invoice_agent/agent/reasoning/row_calculator.py`
  - Deterministically computes invoice row values.
  - Infers missing values (qty/rate/gst%) when possible.
  - Auto-corrects major mismatches and records flags.
  - Runs domain checks (expiry format, MRP-vs-rate sanity, GST range sanity).

- `invoice_agent/agent/reasoning/invoice_aggregator.py`
  - Rebuilds invoice-level subtotal + GST from computed rows.
  - Flags mismatch against provided invoice totals.

- `invoice_agent/agent/mapper/database_mapper.py`
  - Returns flattened, DB-ready row dictionaries.

---

## Canonical output row schema

Each row in output `rows` contains:

- `hsn`, `product_name`, `company`, `batch`, `expiry`, `pack`
- `quantity`, `free_quantity`, `rate`, `amount`, `subtotal`
- `mrp`, `gst_percent`, `gst_amount`, `cgst`, `sgst`, `igst`
- `discount_percent`, `row_total`
- `status`, `flags`

---

## How to run (your actual workflow)

### 1) Put your OLMOCR markdown file anywhere
Example: `my_invoice.md`

### 2) Run parser + rule engine

```bash
python main.py my_invoice.md
```

### 3) Optional: save output JSON

```bash
python main.py my_invoice.md -o result.json
```

Output contains:
- `rows`: final corrected rows (1 row input => 1 row output, 2 rows => 2 rows, etc.)
- `summary`: invoice-level recomputed totals and discrepancy flags

---

## Robustness strategy

- Uses alias + fuzzy matching to survive OCR spelling issues.
- Uses deterministic math over OCR totals (trust math, not OCR blindly).
- Applies tolerance thresholds for small rounding noise.
- Runs domain sanity checks for practical invoice errors.
- Handles split OCR rows where HSN/product continuation appears on the next line.
- Emits row-level and invoice-level flags for auditability.

---

## Already done for your requested extension points

1. **Added aliases** in `resolver/column_aliases.py` (expanded business variants like `particulars`, `sku`, `schemeqty`, etc.).
2. **Added custom row parser fallback** in `input_parser/markdown_parser.py` for compact OCR row patterns.
3. **Added domain checks** in `reasoning/row_calculator.py`:
   - expiry format check
   - suspicious GST% range check
   - rate-vs-MRP sanity
   - negative quantity/discount correction flags

