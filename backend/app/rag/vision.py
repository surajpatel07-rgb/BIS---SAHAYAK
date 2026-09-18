"""Multimodal product identification (AI Product Identifier).

Pipeline stage 1 of the feature: image -> vision model -> structured product
identification. Stage 2 (BIS standard matching) reuses the existing RAG
retrieval stack in app/api/product_identification.py.

Honesty rules enforced here:
- The vision model must return JSON only; anything it cannot see in the image
  is reported as not detected ("" or empty list) rather than guessed.
- Multiple candidate products with confidences are returned so the UI can ask
  the user to disambiguate.
- Without GEMINI_API_KEY the service raises IdentificationUnavailable — the
  endpoint surfaces a clear message instead of fake results.
"""
from __future__ import annotations

import base64
import io
import json
import re
from dataclasses import dataclass, field

from app.config import settings
from app.logging_config import get_logger

logger = get_logger("app.rag.vision")

# ---- Limits (mirror the frontend's stated constraints) -----------------------
ALLOWED_TYPES = ("image/jpeg", "image/png", "image/webp", "image/jpg")
ALLOWED_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")


class VisionError(Exception):
    """Raised when the vision provider fails or returns unusable output."""


class IdentificationUnavailable(Exception):
    """Raised when no vision provider is configured (no GEMINI_API_KEY)."""


def validate_image(data: bytes, filename: str, content_type: str) -> str:
    """Validate type/size. Returns the normalized content type."""
    if not data:
        raise VisionError("The uploaded file is empty.")
    max_mb = settings.vision_max_image_mb
    if len(data) > max_mb * 1024 * 1024:
        raise VisionError(f"Image too large (max {max_mb} MB).")
    ctype = (content_type or "").lower().split(";")[0].strip()
    fname = (filename or "").lower()
    type_ok = ctype in ALLOWED_TYPES
    ext_ok = fname.endswith(ALLOWED_EXTENSIONS)
    if not type_ok and not ext_ok:
        raise VisionError(
            "Unsupported image format. Please upload a JPG, PNG or WEBP image."
        )
    if ctype == "image/jpg":
        ctype = "image/jpeg"
    return ctype or "image/jpeg"


def image_quality_flags(data: bytes) -> list[str]:
    """Cheap pixel heuristics: darkness, tiny dimensions, near-blank images.

    The Gemini call remains the judge of identification confidence; these flags
    only give the UI early, deterministic hints and are included in warnings.
    """
    flags: list[str] = []
    try:
        from PIL import Image  # Pillow

        img = Image.open(io.BytesIO(data))
        w, h = img.size
        if w < 64 or h < 64:
            flags.append("The image is very small; try a larger photo.")
        small = img.convert("L").resize((48, 48))
        pixels = list(small.getdata())
        mean = sum(pixels) / len(pixels)
        if mean < 18:
            flags.append("The image appears very dark; try better lighting.")
        lo, hi = min(pixels), max(pixels)
        if hi - lo < 8:
            flags.append("The image appears blank or featureless.")
    except VisionError:
        raise
    except Exception as exc:  # noqa: BLE001 — Pillow missing / corrupt image
        logger.debug("quality heuristics skipped: %s", exc)
    return flags


def preprocess_image(data: bytes) -> bytes:
    """Downscale oversized images to <=1024px on the long edge (JPEG).

    Keeps uploads fast and cheap for the vision call. Re-encodes PNG with
    alpha onto a white background since JPEG has no alpha channel.
    """
    try:
        from PIL import Image

        img = Image.open(io.BytesIO(data))
        img = img.convert("RGBA") if img.mode in ("RGBA", "LA", "P") else img
        if img.mode == "RGBA":
            bg = Image.new("RGB", img.size, (255, 255, 255))
            bg.paste(img, mask=img.split()[3])
            img = bg
        elif img.mode != "RGB":
            img = img.convert("RGB")
        w, h = img.size
        edge = max(w, h)
        target = max(256, settings.vision_target_edge)
        if edge > target:
            scale = target / edge
            img = img.resize((max(1, int(w * scale)), max(1, int(h * scale))))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=88)
        return buf.getvalue()
    except Exception:  # noqa: BLE001 — if Pillow can't process, send original
        logger.debug("preprocess failed; sending original bytes")
        return data


@dataclass
class Candidate:
    name: str
    confidence: float
    category: str = ""


@dataclass
class Identification:
    product_name: str = ""
    category: str = ""
    confidence: float = 0.0
    brand: str = ""
    model: str = ""
    product_type: str = ""
    specifications: list[str] = field(default_factory=list)
    markings: list[str] = field(default_factory=list)
    packaging_info: str = ""
    possible_matches: list[Candidate] = field(default_factory=list)
    raw_summary: str = ""

    @property
    def confident(self) -> bool:
        return self.confidence >= 0.45 and bool(self.product_name)


IDENTIFY_PROMPT = """You are a product-recognition assistant for an Indian Standards (BIS) \
helper application. Identify the product shown in the image.

Reply with ONLY a JSON object (no markdown fences, no commentary) using exactly these keys:
{
  "product_name": "specific product, e.g. 'stainless steel pressure cooker' (or empty string)",
  "category": "one of: kitchen appliance, electrical appliance, electronics, food product,
               jewellery, construction material, household item, packaging, other",
  "confidence": number 0.0-1.0 for the product_name identification,
  "brand": "visible brand text if confidently readable, else empty string",
  "model": "model/type number if readable, else empty string",
  "product_type": "the kind/variant of the product visible, else empty string",
  "specifications": ["visible specs, capacities, ratings, materials, sizes"],
  "markings": ["visible certification marks or labels e.g. ISI mark, hallmark, BIS label"],
  "packaging_info": "packaging details if the package is visible, else empty string",
  "possible_matches": [
    {"name": "alternative product this image could be", "confidence": 0.0}
  ]
}

RULES:
- Report ONLY what is actually visible or inferable from the image itself.
- If the image is blurry, dark, cropped, or does not clearly show a product, use a low
  confidence value (<=0.3) and put your best guesses in possible_matches.
- If you cannot identify any product at all, return empty strings for product_name and
  category, confidence 0, and explain briefly in "summary" (see below).
- Do NOT invent brands, model numbers, or standard numbers.
- List up to 3 alternative interpretations in possible_matches.
- Finally add a key "summary": one short sentence describing what the image shows."""

_MISMATCH_KEYS = {"summary", "raw_summary"}


def _parse_response(text: str) -> Identification:
    """Extract the JSON object from the model reply (tolerates fences/prose)."""
    cleaned = text.strip()
    m = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if not m:
        raise VisionError("Vision model returned an unparseable response.")
    raw = json.loads(m.group(0))

    def _s(key: str) -> str:
        v = raw.get(key, "")
        return str(v).strip() if v is not None else ""

    def _f(key: str) -> float:
        try:
            return max(0.0, min(1.0, float(raw.get(key, 0.0))))
        except (TypeError, ValueError):
            return 0.0

    matches: list[Candidate] = []
    for item in (raw.get("possible_matches") or [])[:5]:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        if not name:
            continue
        try:
            conf = max(0.0, min(1.0, float(item.get("confidence", 0.0))))
        except (TypeError, ValueError):
            conf = 0.0
        matches.append(Candidate(name=name, confidence=conf))

    specs = [str(s).strip() for s in (raw.get("specifications") or []) if str(s).strip()]
    marks = [str(s).strip() for s in (raw.get("markings") or []) if str(s).strip()]

    return Identification(
        product_name=_s("product_name"),
        category=_s("category"),
        confidence=_f("confidence"),
        brand=_s("brand"),
        model=_s("model"),
        product_type=_s("product_type"),
        specifications=specs[:8],
        markings=marks[:8],
        packaging_info=_s("packaging_info"),
        possible_matches=matches,
        raw_summary=_s("summary") or _s("raw_summary"),
    )


def identify_product(image_bytes: bytes, user_description: str = "") -> Identification:
    """One multimodal call: image (+ optional user note) -> structured identification."""
    if not settings.llm_available:
        raise IdentificationUnavailable(
            "Image identification requires a configured vision model "
            "(GEMINI_API_KEY). You can still use the product search below."
        )
    try:
        from google import genai
        from google.genai import types as gtypes

        client = genai.Client(api_key=settings.gemini_api_key)
        jpeg = preprocess_image(image_bytes)
        mime = "image/jpeg"
        prompt = IDENTIFY_PROMPT
        if user_description.strip():
            prompt += (
                f"\n\nUSER-PROVIDED HINT (may help identification, verify against the "
                f"image): {user_description.strip()[:500]}"
            )
        contents = gtypes.Content(
            role="user",
            parts=[
                gtypes.Part(inline_data=gtypes.Blob(mime_type=mime, data=jpeg)),
                gtypes.Part(text=prompt),
            ],
        )
        resp = client.models.generate_content(
            model=settings.gemini_model,
            contents=[contents],
            config={
                "temperature": 0.1,
                "max_output_tokens": 1200,
            },
        )
        text = getattr(resp, "text", None)
        if not text:
            raise VisionError("Vision model returned an empty response.")
        ident = _parse_response(text)
        logger.info(
            "vision identify: name=%r conf=%.2f matches=%d",
            ident.product_name, ident.confidence, len(ident.possible_matches),
        )
        return ident
    except (IdentificationUnavailable, VisionError):
        raise
    except Exception as exc:  # noqa: BLE001
        logger.error("Vision identification failed: %s", exc)
        raise VisionError(
            "The image analysis service is unavailable right now. Please try again."
        ) from exc


def identification_to_query(ident: Identification, user_description: str = "") -> str:
    """Stage-2 bridge: turn the identification into a natural BIS search query.

    The query goes through the *existing* understand_query + retrieval stack,
    so category detection and product matching stay consistent with chat.
    """
    parts: list[str] = []
    if ident.product_name:
        parts.append(f"BIS standard requirements for {ident.product_name}")
    elif user_description.strip():
        parts.append(f"BIS standard requirements for {user_description.strip()[:200]}")
    else:
        parts.append("BIS standard requirements")
    if ident.markings:
        parts.append("visible marks: " + ", ".join(ident.markings[:3]))
    if user_description.strip() and ident.product_name:
        parts.append(f"(user note: {user_description.strip()[:150]})")
    return "; ".join(parts)
