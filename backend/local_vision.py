"""Local inventory OCR helpers.

EasyOCR is intentionally initialized lazily. Importing the FastAPI app should
not download model files or fail just because the optional local OCR stack is
not available; callers can then fall back to Gemini.
"""

from __future__ import annotations

import logging
import importlib
import importlib.util
import os
import re
import threading

logger = logging.getLogger(__name__)
cv2 = None
np = None
easyocr = None
_dependency_load_attempted = False
_reader = None
_reader_initialization_failed = False
_dependency_lock = threading.Lock()
_reader_lock = threading.Lock()
_read_lock = threading.Lock()


def local_ocr_available() -> bool:
    """Return whether the local OCR packages are installed, without importing them."""
    return all(
        importlib.util.find_spec(package_name) is not None
        for package_name in ("easyocr", "cv2", "numpy")
    )


def _load_dependencies() -> bool:
    global cv2, np, easyocr, _dependency_load_attempted

    if _dependency_load_attempted:
        return cv2 is not None and np is not None and easyocr is not None

    with _dependency_lock:
        if _dependency_load_attempted:
            return cv2 is not None and np is not None and easyocr is not None
        _dependency_load_attempted = True
        try:
            cv2 = importlib.import_module("cv2")
            np = importlib.import_module("numpy")
            easyocr = importlib.import_module("easyocr")
        except (ImportError, OSError):
            cv2 = None
            np = None
            easyocr = None
            logger.warning("EasyOCR dependencies are unavailable; Gemini fallback will be used.")
            return False
    return True


def _get_reader():
    global _reader, _reader_initialization_failed

    if _reader is not None or _reader_initialization_failed:
        return _reader

    if not _load_dependencies():
        _reader_initialization_failed = True
        return None

    with _reader_lock:
        if _reader is not None or _reader_initialization_failed:
            return _reader

        try:
            use_gpu = os.getenv("EASYOCR_GPU", "false").lower() in {"1", "true", "yes"}
            allow_download = os.getenv("EASYOCR_DOWNLOAD_ENABLED", "true").lower() not in {
                "0",
                "false",
                "no",
            }
            _reader = easyocr.Reader(
                ["en"],
                gpu=use_gpu,
                download_enabled=allow_download,
            )
        except Exception:
            _reader_initialization_failed = True
            logger.warning(
                "EasyOCR could not initialize; Gemini fallback will be used for inventory images."
            )

    return _reader


def _parse_inventory_line(line: str) -> dict[str, str] | None:
    cleaned = re.sub(r"^[\s\u2022*\-]+", "", line).strip()
    if len(cleaned) < 2:
        return None

    # Common handwritten formats: "Rice - 10kg", "Soap: 4", or "3 x Cans".
    item_first = re.match(
        r"^(.+?)(?:\s*[-:]\s*|\s+[xX]\s+|\s+)(\d+(?:\.\d+)?\s*[A-Za-z]*)$",
        cleaned,
        flags=re.IGNORECASE,
    )
    if item_first:
        return {
            "item": item_first.group(1).strip(" -:"),
            "quantity": re.sub(r"\s+", "", item_first.group(2)),
        }

    quantity_first = re.match(
        r"^(\d+(?:\.\d+)?\s*[A-Za-z]*)\s*(?:x|[-:])?\s+(.+)$",
        cleaned,
        flags=re.IGNORECASE,
    )
    if quantity_first:
        return {
            "item": quantity_first.group(2).strip(" -:"),
            "quantity": re.sub(r"\s+", "", quantity_first.group(1)),
        }

    return {"item": cleaned, "quantity": "1"}


def parse_handwritten_inventory(image_bytes: bytes) -> list[dict[str, str]]:
    """Extract normalized ``item``/``quantity`` records from image bytes."""
    if not image_bytes or len(image_bytes) < 10 or not _load_dependencies():
        return []

    try:
        np_arr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if image is None or image.size == 0:
            return []
    except Exception:
        return []

    reader = _get_reader()
    if reader is None:
        return []

    try:
        with _read_lock:
            results = reader.readtext(image, detail=1)
    except Exception:
        logger.warning("EasyOCR failed while reading an inventory image; using Gemini fallback.")
        return []

    try:
        confidence_floor = float(os.getenv("EASYOCR_MIN_CONFIDENCE", "0.15"))
    except ValueError:
        confidence_floor = 0.15

    inventory: list[dict[str, str]] = []
    for result in results:
        if not isinstance(result, (list, tuple)) or len(result) < 2:
            continue

        text = str(result[1]).strip()
        confidence = float(result[2]) if len(result) > 2 else 1.0
        if confidence < confidence_floor:
            continue

        parsed = _parse_inventory_line(text)
        if parsed and parsed["item"]:
            inventory.append(parsed)

    return inventory
