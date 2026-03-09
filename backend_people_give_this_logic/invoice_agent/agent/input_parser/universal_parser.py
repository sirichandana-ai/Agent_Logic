from invoice_agent.agent.input_parser.json_parser import parse_json_input
from invoice_agent.agent.input_parser.llm_cleaner import clean_llm_output
from invoice_agent.agent.input_parser.markdown_parser import parse_markdown_input


def parse_input(raw_text: str):
    cleaned = clean_llm_output(raw_text)
    try:
        return parse_json_input(cleaned)
    except Exception:
        return parse_markdown_input(cleaned)
