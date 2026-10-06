import base64
import math

import pytest

pytest.importorskip("PIL")
from PIL import Image  # noqa: E402

from rkitpy import rnote  # noqa: E402


def img(w, h, color="black", mode="RGB"):
    return Image.new(mode, (w, h), color)


def strokes(doc):
    return [
        c["value"]
        for c in doc["data"]["engine_snapshot"]["stroke_components"]
        if c["value"] is not None
    ]


def placed(stroke):
    """(left, top, width, height) of a bitmap stroke on the page."""
    r = stroke["bitmapimage"]["rectangle"]
    hw, hh = r["cuboid"]["half_extents"]
    cx, cy = r["transform"]["affine"][6:8]
    return cx - hw, cy - hh, 2 * hw, 2 * hh


def test_write_then_read_single_image(tmp_path):
    fp = tmp_path / "sub" / "ex.rnote"
    n = rnote.write_rnote(fp, img(200, 100))
    assert fp.stat().st_size == n
    doc = rnote.read_rnote(fp)
    assert doc["version"] == rnote.RNOTE_VERSION
    snap = doc["data"]["engine_snapshot"]
    (s,) = strokes(doc)
    left, top, width, height = placed(s)
    assert (left, top) == (rnote.MARGIN, rnote.MARGIN)
    assert math.isclose(width, rnote.A4_WIDTH - 2 * rnote.MARGIN)
    assert math.isclose(height, width / 2)
    assert s["bitmapimage"]["image"]["pixel_width"] == 200
    assert s["bitmapimage"]["image"]["memory_format"] == "R8g8b8a8Premultiplied"
    assert len(base64.b64decode(s["bitmapimage"]["image"]["data"])) == 200 * 100 * 4
    assert snap["document"]["height"] == rnote.A4_HEIGHT
    assert snap["chrono_counter"] == 1
    assert snap["document"]["config"]["background"]["pattern"] == "grid"


def test_stacked_images_positions_and_document_growth():
    images = [(img(100, 100), 300.0), img(100, 50), (img(100, 400), 500.0)]
    snap = rnote.engine_snapshot(images, gap=10.0)
    boxes = [
        placed(c["value"]) for c in snap["stroke_components"] if c["value"] is not None
    ]
    full = rnote.A4_WIDTH - 2 * rnote.MARGIN
    assert [round(b[2]) for b in boxes] == [300, round(full), 500]
    assert boxes[0][1] == rnote.MARGIN
    assert math.isclose(boxes[1][1], rnote.MARGIN + 300 + 10)
    assert math.isclose(boxes[2][1], boxes[1][1] + full / 2 + 10)
    bottom = boxes[2][1] + 2000
    assert math.isclose(snap["document"]["height"], bottom + rnote.TAIL)
    assert snap["chrono_counter"] == 3
    assert [c["value"]["t"] for c in snap["chrono_components"] if c["value"]] == [
        1,
        2,
        3,
    ]


def test_width_is_capped_to_the_page():
    snap = rnote.engine_snapshot([(img(10, 10), 5000.0)])
    (s,) = [c["value"] for c in snap["stroke_components"] if c["value"]]
    assert math.isclose(placed(s)[2], rnote.A4_WIDTH - 2 * rnote.MARGIN)


def test_no_images_gives_an_empty_page():
    snap = rnote.engine_snapshot([])
    assert snap["chrono_counter"] == 0
    assert snap["document"]["height"] == rnote.A4_HEIGHT


def test_alpha_is_premultiplied():
    im = Image.new("RGBA", (1, 1), (200, 100, 50, 128))
    stroke, _ = rnote.bitmap_stroke(im, 0, 0, 10)
    r, g, b, a = base64.b64decode(stroke["bitmapimage"]["image"]["data"])
    assert a == 128
    assert (r, g, b) == (
        round(200 * 128 / 255),
        round(100 * 128 / 255),
        round(50 * 128 / 255),
    )


def test_opaque_image_is_untouched():
    stroke, _ = rnote.bitmap_stroke(Image.new("RGB", (1, 1), (200, 100, 50)), 0, 0, 10)
    assert base64.b64decode(stroke["bitmapimage"]["image"]["data"]) == bytes(
        [200, 100, 50, 255]
    )


def test_document_config():
    cfg = rnote.document_config(
        width=1122.52, height=793.701, pattern="dots", pattern_color=(0.5, 0.5, 0.5)
    )
    assert cfg["format"]["orientation"] == "landscape"
    assert cfg["background"]["pattern"] == "dots"
    assert cfg["background"]["pattern_color"] == {
        "r": 0.5,
        "g": 0.5,
        "b": 0.5,
        "a": 1.0,
    }
    snap = rnote.engine_snapshot(img(10, 10), config=cfg)
    assert snap["document"]["width"] == 1122.52


def test_bytes_are_deterministic():
    assert rnote.rnote_bytes(img(20, 20)) == rnote.rnote_bytes(img(20, 20))
    assert rnote.rnote_bytes(img(20, 20))[:2] == b"\x1f\x8b"


def test_stack():
    out = rnote.stack([img(30, 10, "red"), img(20, 5, "blue")], gaps=[0, 4])
    assert out.size == (30, 19)
    assert out.getpixel((0, 0)) == (255, 0, 0)
    assert out.getpixel((0, 12)) == (255, 255, 255)  # inside the gap
    assert out.getpixel((0, 14)) == (0, 0, 255)
    assert out.getpixel((25, 14)) == (255, 255, 255)  # right of the narrower image


def test_text_items_roundtrip(tmp_path):
    fp = tmp_path / "text.rnote"
    rnote.write_rnote(fp, ["Exercise 2", img(100, 50)], gap=10.0)
    doc = rnote.read_rnote(fp)
    title, picture = strokes(doc)
    ts = title["textstroke"]
    assert ts["text"] == "Exercise 2"
    assert ts["transform"]["affine"][6:8] == [rnote.MARGIN, rnote.MARGIN]
    style = ts["text_style"]
    assert style["font_family"] == rnote.FONT_FAMILY
    assert style["font_size"] == rnote.FONT_SIZE
    assert style["font_weight"] == rnote.FONT_WEIGHT
    assert style["font_style"] == "regular"
    assert style["color"] == {"r": 0.0, "g": 0.0, "b": 0.0, "a": 1.0}
    assert math.isclose(style["max_width"], rnote.A4_WIDTH - 2 * rnote.MARGIN)
    assert style["alignment"] == "start"
    assert style["ranged_text_attributes"] == []
    one_line = rnote.FONT_SIZE * rnote.LINE_HEIGHT
    assert math.isclose(placed(picture)[1], rnote.MARGIN + one_line + 10)
    assert doc["data"]["engine_snapshot"]["chrono_counter"] == 2


def test_text_style_and_wrapping_width():
    item = rnote.Text(
        "a b",
        font_size=20,
        font_family="Calibri Light",
        font_weight=700,
        italic=True,
        color=(1.0, 0.0, 0.0),
        width=300.0,
        alignment="center",
    )
    snap = rnote.engine_snapshot(item)
    (s,) = [c["value"] for c in snap["stroke_components"] if c["value"]]
    style = s["textstroke"]["text_style"]
    assert style["font_family"] == "Calibri Light"
    assert style["font_size"] == 20
    assert style["font_weight"] == 700
    assert style["font_style"] == "italic"
    assert style["color"]["r"] == 1.0
    assert style["max_width"] == 300.0
    assert style["alignment"] == "center"
    wide = rnote.engine_snapshot(rnote.Text("a", width=5000.0))
    (s,) = [c["value"] for c in wide["stroke_components"] if c["value"]]
    assert math.isclose(
        s["textstroke"]["text_style"]["max_width"], rnote.A4_WIDTH - 2 * rnote.MARGIN
    )


def test_text_height_estimate():
    _, one = rnote.text_stroke("short", 0, 0)
    _, three = rnote.text_stroke("a\nb\nc", 0, 0)
    assert math.isclose(three, 3 * one)
    _, unwrapped = rnote.text_stroke("word " * 40, 0, 0)
    _, wrapped = rnote.text_stroke("word " * 40, 0, 0, max_width=200.0)
    assert unwrapped == one and wrapped > 3 * one
    stroke, _ = rnote.text_stroke("x", 0, 0)
    assert stroke["textstroke"]["text_style"]["max_width"] is None


def test_render_clip():
    fitz = pytest.importorskip("fitz")
    doc = fitz.open()
    page = doc.new_page(width=200, height=100)
    page.insert_text((20, 50), "hello", fontsize=20)
    out = rnote.render_clip(doc, 1, (10, 30, 110, 70), zoom=2.0)
    assert out.size == (200, 80)
    assert out.mode == "RGB"
    assert out.getextrema()[0][0] < 255  # some ink in the clip


def layers(snap):
    return [c["value"]["layer"] for c in snap["chrono_components"] if c["value"]]


def test_strokes_go_on_rnotes_own_layers():
    snap = rnote.engine_snapshot(["Exercise 1", img(100, 50)])
    assert layers(snap) == [{"user_layer": 0}, "image"]


def test_a_bare_image_width_pair_is_one_item():
    snap = rnote.engine_snapshot((img(100, 100), 300.0))
    (s,) = [c["value"] for c in snap["stroke_components"] if c["value"]]
    assert math.isclose(placed(s)[2], 300.0)


def test_unsupported_item_is_rejected():
    with pytest.raises(TypeError, match="items must be images"):
        rnote.engine_snapshot([img(10, 10), 300.0])


def test_stack_keeps_the_background_behind_transparency():
    out = rnote.stack([Image.new("RGBA", (10, 10), (255, 0, 0, 0))])
    assert out.getpixel((5, 5)) == (255, 255, 255)


def test_layer_can_be_chosen():
    snap = rnote.engine_snapshot(["title", img(10, 10)], layer="document")
    assert layers(snap) == [{"user_layer": 0}, "document"]
    snap = rnote.engine_snapshot(img(10, 10), layer=2)
    assert layers(snap) == [{"user_layer": 2}]


def test_unknown_layer_is_rejected():
    with pytest.raises(ValueError, match="layer must be one of"):
        rnote.engine_snapshot([], layer="background")
