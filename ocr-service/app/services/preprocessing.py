"""Image decoding and preprocessing utilities for OCR."""

from __future__ import annotations

import io

import cv2
import numpy as np
from PIL import Image, UnidentifiedImageError

MIN_HEIGHT_PIXELS = 700
MIN_WIDTH_PIXELS = 700
GAUSSIAN_BLUR_KERNEL_SIZE = (5, 5)
ADAPTIVE_THRESHOLD_BLOCK_SIZE = 31
ADAPTIVE_THRESHOLD_C_VALUE = 15
SHARPENING_KERNEL = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]], dtype=np.float32)


class ImageProcessingError(ValueError):
    """Raised when an uploaded file cannot be converted into a valid image."""


def decode_image(file_bytes: bytes) -> np.ndarray:
    """
    Decode raw uploaded file bytes into a BGR OpenCV image.

    Uses OpenCV first for speed and falls back to Pillow for unsupported encodings.
    """
    if not file_bytes:
        raise ImageProcessingError("Uploaded file is empty.")

    byte_array = np.frombuffer(file_bytes, dtype=np.uint8)
    image = cv2.imdecode(byte_array, cv2.IMREAD_COLOR)
    if image is not None:
        return image

    try:
        pil_image = Image.open(io.BytesIO(file_bytes)).convert("RGB")
        rgb_array = np.array(pil_image)
        return cv2.cvtColor(rgb_array, cv2.COLOR_RGB2BGR)
    except (UnidentifiedImageError, OSError) as exc:
        raise ImageProcessingError("Invalid or corrupted image file.") from exc


def prepare_image_for_paddle_ocr(image: np.ndarray) -> np.ndarray:
    """
    Light preparation for PaddleOCR: keep color/BGR and only upscale small images.

    Heavy binarization (see preprocess_image) hurts phone screenshots and colored UI.
    """
    if image is None or image.size == 0:
        raise ImageProcessingError("Image preprocessing failed due to empty input.")

    if image.ndim == 2:
        image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)

    height, width = image.shape[:2]
    if height >= MIN_HEIGHT_PIXELS and width >= MIN_WIDTH_PIXELS:
        return image

    height_scale = MIN_HEIGHT_PIXELS / max(height, 1)
    width_scale = MIN_WIDTH_PIXELS / max(width, 1)
    scale_factor = max(height_scale, width_scale)
    resized_width = max(int(width * scale_factor), 1)
    resized_height = max(int(height * scale_factor), 1)
    return cv2.resize(
        image,
        (resized_width, resized_height),
        interpolation=cv2.INTER_CUBIC,
    )


def preprocess_image(image: np.ndarray) -> np.ndarray:
    """
    Prepare an image for OCR using denoise + contrast normalization pipeline.

    Steps:
    1) Grayscale conversion
    2) Upscale when image is smaller than minimum OCR-friendly size
    3) Gaussian denoising
    4) Adaptive thresholding
    5) Optional sharpening to recover stroke edges
    """
    if image is None or image.size == 0:
        raise ImageProcessingError("Image preprocessing failed due to empty input.")

    grayscale = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    resized = _resize_if_small(grayscale)
    blurred = cv2.GaussianBlur(resized, GAUSSIAN_BLUR_KERNEL_SIZE, sigmaX=0)
    thresholded = cv2.adaptiveThreshold(
        blurred,
        maxValue=255,
        adaptiveMethod=cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        thresholdType=cv2.THRESH_BINARY,
        blockSize=ADAPTIVE_THRESHOLD_BLOCK_SIZE,
        C=ADAPTIVE_THRESHOLD_C_VALUE,
    )
    sharpened = cv2.filter2D(thresholded, ddepth=-1, kernel=SHARPENING_KERNEL)
    return sharpened


def _resize_if_small(image: np.ndarray) -> np.ndarray:
    """Scale up small images while preserving aspect ratio."""
    height, width = image.shape[:2]
    if height >= MIN_HEIGHT_PIXELS and width >= MIN_WIDTH_PIXELS:
        return image

    height_scale = MIN_HEIGHT_PIXELS / max(height, 1)
    width_scale = MIN_WIDTH_PIXELS / max(width, 1)
    scale_factor = max(height_scale, width_scale)

    resized_width = max(int(width * scale_factor), 1)
    resized_height = max(int(height * scale_factor), 1)
    return cv2.resize(
        image,
        (resized_width, resized_height),
        interpolation=cv2.INTER_CUBIC,
    )
