import re


def clean_llm_output(text: str) -> str:
    """Strip common LLM wrappers while preserving JSON/markdown body."""
    if not text:
        return ""

    # Remove fenced code block wrappers but keep inner content.
    text = re.sub(r"```(?:json|markdown|md)?", "", text, flags=re.IGNORECASE)
    text = text.replace("```", "")

    # Trim any junk before first plausible content.
    first_json = text.find("{")
    first_table = text.find("|")
    starts = [i for i in (first_json, first_table) if i >= 0]
    if starts:
        text = text[min(starts):]

    return text.strip()
