"""
Integrated pipeline:
1) Run olmOCR (Transformers direct inference) on one or many images.
2) Save raw OCR markdown.
3) Run local rule-based invoice correction logic.
4) Save corrected JSON for backend/API consumption.
"""

import argparse
import base64
import json
import os
from io import BytesIO
from pathlib import Path
from typing import List

import torch
from PIL import Image
from transformers import AutoProcessor, Qwen2_5_VLForConditionalGeneration
from olmocr.prompts import build_no_anchoring_v4_yaml_prompt

from invoice_agent.agent.agent_core import process_invoice

MODEL_ID = "allenai/olmOCR-2-7B-1025"
PROCESSOR_ID = "Qwen/Qwen2.5-VL-7B-Instruct"
TARGET_DIM = 1288


def image_to_base64png(image: Image.Image) -> str:
    w, h = image.size
    scale = TARGET_DIM / max(w, h)
    image = image.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    buf = BytesIO()
    image.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def load_model():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Loading model on {device} ...")
    model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
        MODEL_ID,
        torch_dtype=torch.bfloat16 if device == "cuda" else torch.float32,
    ).eval().to(device)
    processor = AutoProcessor.from_pretrained(PROCESSOR_ID)
    return model, processor, device


def run_ocr(image_path: str, model, processor, device: str) -> str:
    image = Image.open(image_path).convert("RGB")
    image_base64 = image_to_base64png(image)

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": build_no_anchoring_v4_yaml_prompt()},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_base64}"}},
            ],
        }
    ]

    text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    main_image = Image.open(BytesIO(base64.b64decode(image_base64)))

    inputs = processor(text=[text], images=[main_image], padding=True, return_tensors="pt")
    inputs = {k: v.to(device) for k, v in inputs.items()}

    with torch.no_grad():
        output = model.generate(
            **inputs,
            temperature=0.1,
            max_new_tokens=4096,
            num_return_sequences=1,
            do_sample=True,
        )

    new_tokens = output[:, inputs["input_ids"].shape[1] :]
    return processor.tokenizer.batch_decode(new_tokens, skip_special_tokens=True)[0]


def process_images(images: List[str], output_dir: str):
    os.makedirs(output_dir, exist_ok=True)
    model, processor, device = load_model()

    for image_path in images:
        p = Path(image_path).resolve()
        if not p.exists():
            print(f"[SKIP] Not found: {p}")
            continue

        print(f"\n{'=' * 60}\nProcessing: {p.name}\n{'=' * 60}")
        try:
            markdown_text = run_ocr(str(p), model, processor, device)

            md_out = Path(output_dir) / f"{p.stem}.md"
            md_out.write_text(markdown_text, encoding="utf-8")

            corrected = process_invoice(markdown_text)
            json_out = Path(output_dir) / f"{p.stem}.json"
            json_out.write_text(json.dumps(corrected, indent=2, ensure_ascii=False), encoding="utf-8")

            print(f"[OK] markdown -> {md_out}")
            print(f"[OK] corrected json -> {json_out}")
            print(f"Preview:\n{markdown_text[:400]}{'...' if len(markdown_text) > 400 else ''}")
        except Exception as exc:
            print(f"[FAIL] {p.name}: {exc}")

    print(f"\nAll done. Results in: {output_dir}")


def main():
    parser = argparse.ArgumentParser(description="Run olmOCR and apply local rule-based invoice correction.")
    parser.add_argument("images", nargs="+", help="Image paths to process")
    parser.add_argument("-o", "--output-dir", default="./results", help="Output directory")
    args = parser.parse_args()
    process_images(args.images, args.output_dir)


if __name__ == "__main__":
    main()
