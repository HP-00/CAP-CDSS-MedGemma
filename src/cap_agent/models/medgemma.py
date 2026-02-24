"""MedGemma 1.5 4B model loading and inference.

Uses a lazy singleton pattern — the model only loads when first called,
allowing the package to be imported on CPU-only machines for testing.
"""

import json
import logging
import os
import re
import threading
from typing import Callable, List, Optional

from json_repair import repair_json

from cap_agent.utils.config import MODEL_ID, MODEL_KWARGS
from cap_agent.models.prompts import (
    CAP_SYSTEM_INSTRUCTION,
    CAP_SYSTEM_INSTRUCTION_NO_THINKING,
    CAP_EXTRACTION_INSTRUCTION,
)

try:
    from langsmith.run_helpers import traceable as _traceable_decorator
    _HAS_LANGSMITH = True
except ImportError:
    _HAS_LANGSMITH = False

logger = logging.getLogger(__name__)

_model = None
_processor = None


def _is_json_complete(text: str) -> bool:
    """Check if text contains a structurally complete JSON object.

    Tracks brace depth with string-escape awareness. Returns True when
    the first top-level ``{`` reaches depth 0 again (i.e., all braces matched).
    Handles: nested objects, braces inside quoted strings, escaped quotes.
    Returns False if no ``{`` found or braces remain unmatched.
    """
    start = text.find("{")
    if start == -1:
        return False

    depth = 0
    in_string = False
    escape_next = False
    for ch in text[start:]:
        if escape_next:
            escape_next = False
            continue
        if ch == "\\":
            if in_string:
                escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return True
    return False


def get_model_and_processor():
    """Load MedGemma model and processor on first call (lazy singleton).

    Requires:
        - CUDA-capable GPU
        - HF_TOKEN environment variable set
    """
    global _model, _processor
    if _model is None:
        import torch
        from transformers import AutoModelForImageTextToText, AutoProcessor

        if not torch.cuda.is_available():
            raise RuntimeError(
                "MedGemma requires a CUDA GPU. "
                "Run on Colab with A100 runtime or similar."
            )

        hf_token = os.environ.get("HF_TOKEN")
        if not hf_token:
            raise RuntimeError(
                "HF_TOKEN environment variable not set. "
                "Required for gated model access."
            )

        # Resolve dtype from string to torch dtype object
        kwargs = dict(MODEL_KWARGS)
        dtype_str = kwargs.pop("dtype")
        kwargs["dtype"] = getattr(torch, dtype_str)

        _model = AutoModelForImageTextToText.from_pretrained(MODEL_ID, **kwargs)
        _processor = AutoProcessor.from_pretrained(MODEL_ID)

        # --- Warm-up: pre-compile CUDA kernels ---
        logger.info("Warm-up: text-only forward pass...")
        from PIL import Image as _WarmupImage

        warmup_msgs = [{"role": "user", "content": [{"type": "text", "text": "Hello"}]}]
        warmup_inputs = _processor.apply_chat_template(
            warmup_msgs, add_generation_prompt=True,
            tokenize=True, return_dict=True, return_tensors="pt",
        ).to(_model.device)
        with torch.inference_mode():
            _model.generate(**warmup_inputs, max_new_tokens=1, do_sample=False)

        logger.info("Warm-up: image+text forward pass...")
        dummy_img = _WarmupImage.new("RGB", (224, 224), color=(128, 128, 128))
        warmup_img_msgs = [{"role": "user", "content": [
            {"type": "image", "image": dummy_img},
            {"type": "text", "text": "Describe"},
        ]}]
        warmup_img_inputs = _processor.apply_chat_template(
            warmup_img_msgs, add_generation_prompt=True,
            tokenize=True, return_dict=True, return_tensors="pt",
        ).to(_model.device)
        with torch.inference_mode():
            _model.generate(**warmup_img_inputs, max_new_tokens=1, do_sample=False)

        torch.cuda.synchronize()
        logger.info("Warm-up complete.")

    return _model, _processor


def pad_image_to_square(pil_image):
    """Pad PIL image to square, matching MedGemma training preprocessing.

    Converts grayscale to RGB, strips alpha channel, pads shorter dimension
    symmetrically with zeros. From Google's MedGemma reference notebooks.
    """
    import numpy as np
    import skimage.util
    import skimage.color
    from PIL import Image

    arr = np.array(pil_image)
    arr = skimage.util.img_as_ubyte(arr)
    if len(arr.shape) < 3:
        arr = skimage.color.gray2rgb(arr)
    if arr.shape[2] == 4:
        arr = skimage.color.rgba2rgb(arr)
        arr = skimage.util.img_as_ubyte(arr)
    h, w = arr.shape[:2]
    if h < w:
        dh = w - h
        arr = np.pad(arr, ((dh // 2, dh - dh // 2), (0, 0), (0, 0)))
    elif w < h:
        dw = h - w
        arr = np.pad(arr, ((0, 0), (dw // 2, dw - dw // 2), (0, 0)))
    return Image.fromarray(arr)


def call_medgemma(
    prompt: str,
    max_new_tokens: int = 1500,
    images: Optional[List] = None,
    enable_thinking: bool = True,
    system_instruction: Optional[str] = None,
) -> str:
    """Call MedGemma 1.5 4B with optional thinking mode.

    Args:
        prompt: Text prompt for the model.
        max_new_tokens: Maximum tokens to generate.
        images: Optional list of PIL Images. Images appear before text in the
                user message, matching Google's reference notebook format.
        enable_thinking: If True (default), use system instruction with thinking
                        prefix. Set False for extraction/synthesis calls where
                        structured output is all we need.
        system_instruction: Override the default system instruction. If None,
                           auto-selects based on enable_thinking. Use
                           CAP_EXTRACTION_INSTRUCTION for extraction calls.
    """
    import torch

    model, processor = get_model_and_processor()

    # 3-tier system instruction selection:
    #   1. Explicit override (system_instruction=CAP_EXTRACTION_INSTRUCTION)
    #   2. Thinking enabled → CAP_SYSTEM_INSTRUCTION (with thinking prefix)
    #   3. Thinking disabled → CAP_SYSTEM_INSTRUCTION_NO_THINKING
    if system_instruction is not None:
        sys_instruction = system_instruction
    elif enable_thinking:
        sys_instruction = CAP_SYSTEM_INSTRUCTION
    else:
        sys_instruction = CAP_SYSTEM_INSTRUCTION_NO_THINKING

    # Build user content: system instruction first, then images, then prompt.
    # Gemma 3 has no native system role — apply_chat_template silently prepends
    # system to user anyway. We embed explicitly for clarity and robustness.
    user_content = [{"type": "text", "text": sys_instruction + "\n\n"}]
    if images:
        for img in images:
            user_content.append({"type": "image", "image": img})
    user_content.append({"type": "text", "text": prompt})

    messages = [{"role": "user", "content": user_content}]

    inputs = processor.apply_chat_template(
        messages,
        add_generation_prompt=True,
        tokenize=True,
        return_dict=True,
        return_tensors="pt",
    ).to(model.device)

    input_len = inputs["input_ids"].shape[-1]

    # JSON-complete StoppingCriteria: for non-thinking calls, halt generation
    # as soon as a structurally complete JSON object is detected. Saves 18-72s
    # per run by eliminating post-JSON token waste.
    generate_kwargs = dict(max_new_tokens=max_new_tokens, do_sample=False)
    if not enable_thinking and system_instruction is CAP_EXTRACTION_INSTRUCTION:
        from transformers import StoppingCriteria, StoppingCriteriaList

        class _JSONStopCriteria(StoppingCriteria):
            def __call__(self, input_ids, scores, **kwargs):
                decoded = processor.tokenizer.decode(
                    input_ids[0, input_len:], skip_special_tokens=True,
                )
                return _is_json_complete(decoded)

        generate_kwargs["stopping_criteria"] = StoppingCriteriaList([_JSONStopCriteria()])

    with torch.inference_mode():
        generation = model.generate(**inputs, **generate_kwargs)
        generation = generation[0][input_len:]

    return processor.decode(generation, skip_special_tokens=True)


def call_medgemma_streaming(
    prompt: str,
    max_new_tokens: int = 1500,
    images: Optional[List] = None,
    enable_thinking: bool = True,
    system_instruction: Optional[str] = None,
    token_callback: Optional[Callable[[str, bool], None]] = None,
) -> str:
    """Call MedGemma with token-level streaming via callback.

    Same contract as call_medgemma() — returns the full generated text string.
    Additionally calls token_callback(token_text, is_thinking) for each token
    as it is generated, enabling real-time SSE streaming.

    Uses TextIteratorStreamer in a background thread so the main thread can
    process tokens as they arrive.
    """
    import torch
    from transformers import TextIteratorStreamer

    model, processor = get_model_and_processor()

    if system_instruction is not None:
        sys_instruction = system_instruction
    elif enable_thinking:
        sys_instruction = CAP_SYSTEM_INSTRUCTION
    else:
        sys_instruction = CAP_SYSTEM_INSTRUCTION_NO_THINKING

    user_content = [{"type": "text", "text": sys_instruction + "\n\n"}]
    if images:
        for img in images:
            user_content.append({"type": "image", "image": img})
    user_content.append({"type": "text", "text": prompt})

    messages = [{"role": "user", "content": user_content}]

    inputs = processor.apply_chat_template(
        messages,
        add_generation_prompt=True,
        tokenize=True,
        return_dict=True,
        return_tensors="pt",
    ).to(model.device)

    input_len = inputs["input_ids"].shape[-1]

    streamer = TextIteratorStreamer(
        processor.tokenizer,
        skip_prompt=True,
        skip_special_tokens=True,
        timeout=60.0,
    )

    generate_kwargs = dict(
        **inputs,
        max_new_tokens=max_new_tokens,
        do_sample=False,
        streamer=streamer,
    )

    # JSON StoppingCriteria — same logic as call_medgemma()
    if not enable_thinking and system_instruction is CAP_EXTRACTION_INSTRUCTION:
        from transformers import StoppingCriteria, StoppingCriteriaList

        class _JSONStopCriteria(StoppingCriteria):
            def __call__(self, input_ids, scores, **kwargs):
                decoded = processor.tokenizer.decode(
                    input_ids[0, input_len:], skip_special_tokens=True,
                )
                return _is_json_complete(decoded)

        generate_kwargs["stopping_criteria"] = StoppingCriteriaList([_JSONStopCriteria()])

    # Run generation in a background thread
    def _generate():
        with torch.inference_mode():
            model.generate(**generate_kwargs)

    gen_thread = threading.Thread(target=_generate, daemon=True)
    gen_thread.start()

    # Iterate tokens from streamer, track thinking state, invoke callback
    full_text = []
    in_thinking = False
    thinking_buffer = ""

    for token_text in streamer:
        # Detect thinking token boundaries
        if "<unused94>" in token_text:
            in_thinking = True
            token_text = token_text.replace("<unused94>thought\n", "").replace("<unused94>", "")
        if "<unused95>" in token_text:
            in_thinking = False
            token_text = token_text.replace("<unused95>", "")

        full_text.append(token_text)

        if token_callback and token_text:
            token_callback(token_text, in_thinking)

    gen_thread.join(timeout=5.0)
    return "".join(full_text)


# Conditionally wrap with LangSmith tracing when available.
# Non-breaking: when langsmith isn't installed, call_medgemma is unchanged.
if _HAS_LANGSMITH:
    call_medgemma = _traceable_decorator(
        run_type="llm",
        name="MedGemma",
        metadata={"model": "medgemma-1.5-4b-it"},
    )(call_medgemma)
    call_medgemma_streaming = _traceable_decorator(
        run_type="llm",
        name="MedGemma-streaming",
        metadata={"model": "medgemma-1.5-4b-it"},
    )(call_medgemma_streaming)


def extract_thinking(text: str) -> tuple:
    """Extract thinking trace and final response from MedGemma output.

    MedGemma 1.5 uses <unused94> and <unused95> tokens to delimit thinking.
    These tokens survive skip_special_tokens=True in the tokenizer.
    """
    if "<unused95>" in text:
        thought, response = text.split("<unused95>", 1)
        thought = thought.replace("<unused94>thought\n", "").replace("<unused94>", "").strip()
        return thought, response.strip()
    return "", text.strip()


def parse_json_response(text: str, expect_list: bool = False):
    """Extract JSON from model output, handling markdown code blocks.

    Tier 0: json_repair (handles truncation, trailing commas, missing braces)
    Tier 1: Regex for markdown code blocks
    Tier 2: Bare JSON regex extraction

    Args:
        text: Raw model output potentially containing JSON.
        expect_list: If True, also match JSON arrays and return [] on failure
                     instead of {}. Used for localization bounding box results.
    """
    # --- Tier 0: json_repair (handles truncation, trailing commas) ---
    try:
        repaired = repair_json(text, return_objects=True)
        if isinstance(repaired, dict) and repaired:
            return repaired
        if isinstance(repaired, list) and repaired and expect_list:
            return repaired
    except Exception:
        pass

    # --- Tier 1: Regex for code blocks ---
    # Pattern for objects or arrays in code blocks
    if expect_list:
        code_block = re.search(r'```(?:json)?\s*(\[.*?\]|\{.*?\})\s*```', text, re.DOTALL)
    else:
        code_block = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if code_block:
        try:
            return json.loads(code_block.group(1))
        except json.JSONDecodeError:
            pass

    if expect_list:
        # Try array first, then object
        list_match = re.search(r'\[.*\]', text, re.DOTALL)
        if list_match:
            try:
                return json.loads(list_match.group())
            except json.JSONDecodeError:
                pass

    json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
    return [] if expect_list else {}
