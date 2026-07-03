from __future__ import annotations

import io
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont


def _get_font(size: int = 14) -> Any:
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "C:\\Windows\\Fonts\\arial.ttf",
    ]
    for fp in font_paths:
        if Path(fp).exists():
            return ImageFont.truetype(fp, size)
    return ImageFont.load_default()


def annotate_screenshot(
    image_bytes: bytes,
    annotations: list[dict[str, Any]] | None = None,
) -> bytes:
    """Annotate a screenshot with bounding boxes, labels, and arrows."""
    img = Image.open(io.BytesIO(image_bytes))
    draw = ImageDraw.Draw(img, "RGBA")
    font = _get_font()

    if annotations:
        for ann in annotations:
            _draw_annotation(draw, ann, font)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _draw_annotation(draw: Any, ann: dict[str, Any], font: Any) -> None:
    """Draw a single annotation on the image."""
    atype = ann.get("type", "box")

    if atype == "box":
        x, y, w, h = ann.get("x", 0), ann.get("y", 0), ann.get("width", 0), ann.get("height", 0)
        color = ann.get("color", "red")
        label = ann.get("label", "")
        outline_width = ann.get("outline_width", 2)

        for i in range(outline_width):
            draw.rectangle([x - i, y - i, x + w + i, y + h + i], outline=color)

        if label:
            bbox = draw.textbbox((x, y - 16), label, font=font)
            draw.rectangle(bbox, fill=color)
            draw.text((x, y - 16), label, fill="white", font=font)

    elif atype == "point":
        cx, cy = ann.get("x", 0), ann.get("y", 0)
        color = ann.get("color", "red")
        radius = ann.get("radius", 5)
        draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=color)

    elif atype == "arrow":
        sx, sy = ann.get("start_x", 0), ann.get("start_y", 0)
        ex, ey = ann.get("end_x", 0), ann.get("end_y", 0)
        color = ann.get("color", "red")
        draw.line([sx, sy, ex, ey], fill=color, width=2)

    elif atype == "label":
        x, y = ann.get("x", 0), ann.get("y", 0)
        text = ann.get("text", "")
        color = ann.get("color", "white")
        bg_color = ann.get("bg_color", "red")
        bbox = draw.textbbox((x, y), text, font=font)
        draw.rectangle(bbox, fill=bg_color)
        draw.text((x, y), text, fill=color, font=font)


def create_annotation(
    bbox: dict[str, float] | None = None,
    label: str = "",
    color: str = "red",
    atype: str = "box",
) -> dict[str, Any]:
    """Helper to create an annotation dict."""
    ann: dict[str, Any] = {"type": atype, "color": color}
    if bbox:
        ann.update(bbox)
    if label:
        ann["label"] = label
    return ann


__all__ = ["annotate_screenshot", "create_annotation"]
