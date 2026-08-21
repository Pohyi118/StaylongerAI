import asyncio
import re

import cv2
import numpy as np

# Lazy-load EasyOCR reader to avoid blocking startup
_reader = None


def _get_reader():
    """Lazy initialization of EasyOCR reader to avoid startup delay."""
    global _reader
    if _reader is None:
        import easyocr
        _reader = easyocr.Reader(["en"], gpu=False)
    return _reader


def _sanitize_name(raw: str) -> str:
    # Collapse whitespace, cap length, keep alphanumerics/hyphens/slashes.
    name = " ".join(str(raw).split()).strip()
    name = re.sub(r"[^A-Za-z0-9\s\-\/\.]", "", name).strip()
    return name[:80]


def _sanitize_quantity(raw: str) -> str:
    # Extract a leading numeric quantity; drop letters/garbage ("2x", "5pcs" -> "2", "5").
    m = re.match(r"(\d+(?:\.\d+)?)", str(raw).strip())
    return m.group(1) if m else "1"


async def parse_handwritten_inventory(image_bytes: bytes) -> list[dict]:
    """
    1. Converts image bytes to OpenCV format.
    2. Runs local OCR to extract text lines (async, non-blocking).
    3. Parses items and quantities into structured data.
    """
    if not image_bytes or len(image_bytes) < 10:
        return []

    try:
        np_arr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if img is None or img.size == 0:
            return []
    except Exception:
        return []

    try:
        # Run OCR in thread pool to avoid blocking event loop
        reader = _get_reader()
        results = await asyncio.to_thread(reader.readtext, img, 0)
    except Exception:
        return []

    inventory = []
    seen = set()

    for bbox, text, confidence in results:
        line = str(text).strip()
        if not line:
            continue

        # Drop pure numeric-only lines (likely prices/phone number fragments).
        if re.fullmatch(r"[\d\s\.\,\-\/]+", line):
            continue

        match = re.search(r"([A-Za-z][A-Za-z\s\-\/]*?)\s*[-:]?\s*(\d+[\w]*)", line)
        if match:
            item_name = _sanitize_name(match.group(1))
            quantity = _sanitize_quantity(match.group(2))
        elif len(line) > 2:
            item_name = _sanitize_name(line)
            quantity = "1"
        else:
            continue

        if not item_name:
            continue

        # OCR returns multiple overlapping boxes for one line; dedupe.
        key = (item_name.lower(), quantity)
        if key in seen:
            continue
        seen.add(key)
        inventory.append({"item": item_name, "quantity": quantity})

    return inventory