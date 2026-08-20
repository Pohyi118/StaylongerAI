import easyocr
import re
import cv2
import numpy as np

# Initialize EasyOCR reader (downloads once, runs locally offline)
reader = easyocr.Reader(['en'], gpu=False)

def parse_handwritten_inventory(image_bytes: bytes) -> list[dict]:
    """
    1. Converts image bytes to OpenCV format.
    2. Runs local OCR to extract text lines.
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
        results = reader.readtext(img, detail=0)
    except Exception:
        return []

    inventory = []

    for line in results:
        match = re.search(r'([A-Za-z\s]+)\s*[-:]?\s*(\d+[\w]*)', line)
        if match:
            item_name = match.group(1).strip()
            quantity = match.group(2).strip()
            inventory.append({"item": item_name, "quantity": quantity})
        elif len(line.strip()) > 2:
            inventory.append({"item": line.strip(), "quantity": "1"})

    return inventory
