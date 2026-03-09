# Backend Handoff Package

This folder contains the integrated OCR + rule-based correction logic.

## Files included
- `run_olmocr_with_rules.py`
  - Runs olmOCR (`allenai/olmOCR-2-7B-1025`) on image(s)
  - Saves raw OCR markdown
  - Applies local rule-based correction (`process_invoice`)
  - Saves corrected JSON (`rows` + `summary`)
- `invoice_agent/`
  - All parsing, normalization, validation, and aggregation logic.
- `main.py`
  - Existing CLI for processing markdown/json text input through rule engine.

## Typical usage (GPU machine)
```bash
python run_olmocr_with_rules.py 1.png 2.png -o ./results
```

Outputs per image:
- `results/<name>.md`   (raw OCR markdown)
- `results/<name>.json` (corrected structured JSON)

## If backend already has OCR text
Use only rule engine:
```bash
python main.py invoice.md
```
