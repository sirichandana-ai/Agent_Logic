import argparse
import json
import sys
from pathlib import Path

from invoice_agent.agent.agent_core import process_invoice


def main():
    parser = argparse.ArgumentParser(description="Process invoice markdown/json into validated rows.")
    parser.add_argument("input_file", help="Path to OCR markdown (.md/.txt) or json file")
    parser.add_argument("-o", "--output", help="Optional output json path")
    args = parser.parse_args()

    raw_text = Path(args.input_file).read_text(encoding="utf-8")
    result = process_invoice(raw_text)

    output = json.dumps(result["rows"], indent=2, ensure_ascii=False)
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
    sys.stdout.buffer.write(output.encode("utf-8"))
    sys.stdout.buffer.write(b"\n")


if __name__ == "__main__":
    main()
