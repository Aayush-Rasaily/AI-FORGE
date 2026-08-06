"""
Donut Transformer document understanding.

Parses document structure and compares with OCR consensus for tampering signals.
"""

from __future__ import annotations

import logging
import re
from functools import lru_cache
from typing import Any, Dict, Optional

from backend.utils.hardware import get_torch_device

logger = logging.getLogger("ai_forge.donut")

_MODEL = None
_PROCESSOR = None


@lru_cache(maxsize=1)
def _load_donut():
    global _MODEL, _PROCESSOR
    try:
        import torch
        from transformers import DonutProcessor, VisionEncoderDecoderModel

        device = get_torch_device()
        model_name = "naver-clova-ix/donut-base-finetuned-cord-v2"
        processor = DonutProcessor.from_pretrained(model_name)
        model = VisionEncoderDecoderModel.from_pretrained(model_name).eval()
        model.to(device)
        _MODEL, _PROCESSOR = model, processor
        return model, processor, torch.device(device)
    except Exception as exc:
        logger.warning("Donut unavailable: %s", exc)
        return None, None, None


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower().strip())


def _text_overlap(a: str, b: str) -> float:
    from difflib import SequenceMatcher
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, _normalize(a), _normalize(b)).ratio()


def analyze_donut(
    image_path: str,
    ocr_text: str = "",
) -> Dict[str, Any]:
    """Run Donut document parsing and compare with OCR text."""
    model, processor, device = _load_donut()

    if model is None or processor is None:
        overlap = _text_overlap(ocr_text, ocr_text) if ocr_text else 0.5
        return {
            "parse_anomaly_score": 0.0,
            "method": "unavailable",
            "model": "donut_heuristic",
            "confidence": 0.3,
            "ocr_overlap": round(overlap, 4),
            "parsed_text": "",
        }

    try:
        import torch
        from PIL import Image

        image = Image.open(image_path).convert("RGB")
        task_prompt = "<s_cord-v2>"
        decoder_input_ids = processor.tokenizer(
            task_prompt, add_special_tokens=False, return_tensors="pt"
        ).input_ids.to(device)

        pixel_values = processor(image, return_tensors="pt").pixel_values.to(device)

        with torch.no_grad():
            outputs = model.generate(
                pixel_values,
                decoder_input_ids=decoder_input_ids,
                max_length=model.decoder.config.max_position_embeddings,
                early_stopping=True,
                pad_token_id=processor.tokenizer.pad_token_id,
                eos_token_id=processor.tokenizer.eos_token_id,
                use_cache=True,
                num_beams=1,
                bad_words_ids=[[processor.tokenizer.unk_token_id]],
            )

        parsed = processor.batch_decode(outputs, skip_special_tokens=True)[0]
        # Strip task tokens
        parsed_clean = re.sub(r"<[^>]+>", " ", parsed).strip()

        overlap = _text_overlap(parsed_clean, ocr_text)
        anomaly = max(0.0, 1.0 - overlap) if ocr_text else 0.0

        return {
            "parse_anomaly_score": round(min(1.0, anomaly), 4),
            "method": "donut-cord-v2",
            "model": "naver-clova-ix/donut-base-finetuned-cord-v2",
            "confidence": 0.74,
            "ocr_overlap": round(overlap, 4),
            "parsed_text": parsed_clean[:2000],
            "parsed_length": len(parsed_clean),
        }
    except Exception as exc:
        logger.warning("Donut inference failed: %s", exc)
        return {
            "parse_anomaly_score": 0.0,
            "method": "donut_error",
            "model": "donut",
            "confidence": 0.3,
            "error": str(exc),
            "parsed_text": "",
        }
