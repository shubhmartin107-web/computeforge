import io
from unittest.mock import patch

import pytest
from PIL import Image, UnidentifiedImageError

from computeforge.observability.screenshots import annotate_screenshot, create_annotation


def _make_image(width: int = 100, height: int = 100, fmt: str = "PNG") -> bytes:
    img = Image.new("RGB", (width, height), color="blue")
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


def test_annotate_screenshot_box():
    img_bytes = _make_image()
    annotations = [
        create_annotation(bbox={"x": 10, "y": 10, "width": 50, "height": 30}, label="button", color="red")
    ]
    result = annotate_screenshot(img_bytes, annotations)
    assert isinstance(result, bytes)
    assert len(result) > 0
    img = Image.open(io.BytesIO(result))
    assert img.size == (100, 100)


def test_annotate_screenshot_point():
    img_bytes = _make_image()
    annotations = [{"type": "point", "x": 50, "y": 50, "color": "red", "radius": 5}]
    result = annotate_screenshot(img_bytes, annotations)
    assert isinstance(result, bytes)
    img = Image.open(io.BytesIO(result))
    assert img.size == (100, 100)


def test_annotate_screenshot_arrow():
    img_bytes = _make_image()
    annotations = [{"type": "arrow", "start_x": 10, "start_y": 10, "end_x": 90, "end_y": 90, "color": "green"}]
    result = annotate_screenshot(img_bytes, annotations)
    assert isinstance(result, bytes)
    img = Image.open(io.BytesIO(result))
    assert img.size == (100, 100)


def test_annotate_screenshot_label():
    img_bytes = _make_image()
    annotations = [{"type": "label", "x": 20, "y": 20, "text": "Hello", "color": "white", "bg_color": "blue"}]
    result = annotate_screenshot(img_bytes, annotations)
    assert isinstance(result, bytes)
    img = Image.open(io.BytesIO(result))
    assert img.size == (100, 100)


def test_annotate_screenshot_no_annotations():
    img_bytes = _make_image()
    result = annotate_screenshot(img_bytes)
    assert isinstance(result, bytes)
    img = Image.open(io.BytesIO(result))
    assert img.size == (100, 100)


def test_annotate_screenshot_multiple():
    img_bytes = _make_image()
    annotations = [
        create_annotation(bbox={"x": 10, "y": 10, "width": 30, "height": 30}, label="A"),
        {"type": "point", "x": 80, "y": 80, "color": "blue"},
        {"type": "arrow", "start_x": 10, "start_y": 10, "end_x": 80, "end_y": 80},
    ]
    result = annotate_screenshot(img_bytes, annotations)
    assert isinstance(result, bytes)
    img = Image.open(io.BytesIO(result))
    assert img.size == (100, 100)


def test_annotate_screenshot_various_sizes():
    for size in [(50, 50), (200, 100)]:
        img_bytes = _make_image(*size)
        result = annotate_screenshot(img_bytes, [{"type": "box", "x": 5, "y": 5, "width": 10, "height": 10}])
        img = Image.open(io.BytesIO(result))
        assert img.size == size


def test_annotate_screenshot_invalid_bytes():
    with pytest.raises(UnidentifiedImageError):
        annotate_screenshot(b"not an image")


def test_create_annotation_helper():
    ann = create_annotation(bbox={"x": 1, "y": 2, "width": 10, "height": 20}, label="test", color="blue")
    assert ann["type"] == "box"
    assert ann["color"] == "blue"
    assert ann["label"] == "test"
    assert ann["x"] == 1
    assert ann["y"] == 2


def test_create_annotation_without_bbox():
    ann = create_annotation(atype="point", label="dot")
    assert ann["type"] == "point"
    assert ann["label"] == "dot"


def test_font_fallback():
    with patch("computeforge.observability.screenshots.Path") as mock_path:
        mock_path.return_value.exists.return_value = False
        img_bytes = _make_image()
        annotations = [{"type": "label", "x": 10, "y": 10, "text": "Fallback", "color": "white", "bg_color": "black"}]
        result = annotate_screenshot(img_bytes, annotations)
        assert isinstance(result, bytes)


def test_unknown_annotation_type():
    img_bytes = _make_image()
    annotations = [{"type": "unknown_type", "x": 10, "y": 10}]
    result = annotate_screenshot(img_bytes, annotations)
    assert isinstance(result, bytes)
    img = Image.open(io.BytesIO(result))
    assert img.size == (100, 100)
