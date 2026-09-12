# raffalib-python Miscellaneous functions
# Copyright (C) 2026 Raffaele Mancuso
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Write and read `Rnote <https://rnote.flxzt.net/>`_ save files (``.rnote``).

Rnote is a handwriting note-taking app. Its save file is a gzip-compressed JSON
document holding an *engine snapshot*: the page configuration, the camera and the
list of strokes. This module builds such files from raster images and text, which
is what a problem notebook needs: one file per exercise, showing the exercise
statement at the top of the page with the rest of the page free for handwritten work.

Items are placed one below the other from the top-left corner of the first page,
images as bitmap strokes and text as text strokes (the ones Rnote's typewriter tool
makes). Each stroke goes on the layer Rnote itself would put it on -- images on the
image layer (see `layer`), text on the first user layer -- so handwriting always sits
above them.
The page format and background default to A4 at 96 dpi, infinite layout and Rnote's
own light-blue pattern colour, drawn as a grid; build a different one with
:func:`document_config`. A plain string is text in Rnote's default style; a
:class:`Text` chooses font, size, weight, colour and alignment. Rnote lays text out
with the named font when it opens the file, so the height a text item takes is
estimated here (see :data:`LINE_HEIGHT`) only to place the next item below it.

Requires Pillow (``rnote`` extra); :func:`render_clip` also needs PyMuPDF.

Example::

    from PIL import Image
    from raffalib.rnote import Text, write_rnote

    write_rnote("ex_1.rnote", Image.open("exercise_1.png"))
    write_rnote("ex_2.rnote", ["Exercise 2", Image.open("exercise_2.png")])
    write_rnote("recap.rnote", Text("Percentiles", font_size=36, font_family="Calibri Light"))
"""

import base64
import gzip
import json
import textwrap
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageChops

#: A4 width in document units (pixels at 96 dpi), the page size of the reference notebooks.
A4_WIDTH = 793.701
#: A4 height in document units.
A4_HEIGHT = 1122.52
#: Distance of the images from the top and left page edges, in document units.
MARGIN = 40.0
#: Vertical space between stacked images, in document units.
GAP = 24.0
#: Minimum free space kept below the last image, in document units. Only has an effect
#: with ``layout="fixed_size"``: every other layout recomputes the document size when the
#: file is opened (the infinite ones grow it by two page sizes around the content).
TAIL = 200.0
#: Rnote version written in the file header. This is not cosmetic: it selects the schema
#: Rnote deserialises the snapshot with. ``0.14.2`` means the 0.13+ schema written here
#: (nested ``document.config``, 9-element ``transform`` matrices), which Rnote 0.15 still
#: reads by upgrading it on load. Raising it to ``0.15`` or above without rewriting the
#: matrices as 6-element ``affine`` arrays would make the file unreadable.
RNOTE_VERSION = "0.14.2"
#: Default text style, the one of Rnote's typewriter tool: font family, size (document units), weight.
FONT_FAMILY = "serif"
FONT_SIZE = 32.0
FONT_WEIGHT = 500
#: Height given to each line of text when estimating the space a text item takes, as a
#: multiple of the font size.
LINE_HEIGHT = 1.25
#: Named stroke layers, drawn in this order (a numbered user layer sits above them all).
#: Rnote puts pasted images on ``"image"`` and pages imported from a PDF on ``"document"``.
LAYERS = ("document", "image", "highlighter")


def _rgba(r: float, g: float, b: float, a: float = 1.0) -> dict:
    return {"r": r, "g": g, "b": b, "a": a}


def document_config(
    width: float = A4_WIDTH,
    height: float = A4_HEIGHT,
    dpi: float = 96.0,
    pattern: str = "grid",
    pattern_color: tuple[float, float, float] = (0.8, 0.9, 1.0),
    pattern_size: tuple[float, float] = (32.0, 32.0),
    background: tuple[float, float, float] = (1.0, 1.0, 1.0),
    layout: str = "infinite",
) -> dict:
    """Build the ``document.config`` block of an engine snapshot.

    :param width: page width in document units (pixels at 96 dpi)
    :type width: float
    :param height: page height in document units
    :type height: float
    :param dpi: document resolution
    :type dpi: float
    :param pattern: background pattern: ``"grid"``, ``"dots"``, ``"lines"`` or ``"none"``
    :type pattern: str
    :param pattern_color: pattern colour as RGB components in 0-1
    :type pattern_color: tuple[float, float, float]
    :param pattern_size: pattern spacing in document units
    :type pattern_size: tuple[float, float]
    :param background: page colour as RGB components in 0-1
    :type background: tuple[float, float, float]
    :param layout: page layout: ``"infinite"``, ``"continuous_vertical"``, ``"fixed_size"``
        or ``"semi_infinite"``
    :type layout: str
    :return: the config block, to be passed as ``config=`` to the writers
    :rtype: dict
    """
    return {
        "format": {
            "width": width,
            "height": height,
            "dpi": dpi,
            "orientation": "portrait" if height >= width else "landscape",
            "border_color": _rgba(0.871, 0.867, 0.855),
            "show_borders": True,
            "show_origin_indicator": True,
        },
        "background": {
            "color": _rgba(*background),
            "pattern": pattern,
            "pattern_size": list(pattern_size),
            "pattern_color": _rgba(*pattern_color),
        },
        "layout": layout,
    }


def _layer(layer: str | int) -> dict | str:
    """`layer` as Rnote's ``StrokeLayer``: a name from :data:`LAYERS`, or a user layer number."""
    if isinstance(layer, int) and not isinstance(layer, bool):
        return {"user_layer": layer}
    if layer in LAYERS:
        return layer
    raise ValueError(
        f"layer must be one of {', '.join(LAYERS)} or an int for a numbered user layer, "
        f"not {layer!r}"
    )


def _rect(w: float, h: float, cx: float, cy: float) -> dict:
    """Rnote rectangle: half extents plus an affine transform placing its centre at (cx, cy)."""
    return {
        "cuboid": {"half_extents": [w / 2, h / 2]},
        "transform": {"affine": [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, cx, cy, 1.0]},
    }


def _premultiplied_rgba(img: Image.Image) -> Image.Image:
    """`img` as RGBA with the colour channels multiplied by alpha, as Rnote stores bitmaps.

    Rnote tags every bitmap ``R8g8b8a8Premultiplied`` and its renderer expects exactly
    that, so the multiplication is done here even though Rnote's own image import skips
    it. Pillow truncates the division by 255, so a channel can come out one level low."""
    rgba = img.convert("RGBA")
    alpha = rgba.getchannel("A")
    if alpha.getextrema()[0] == 255:
        return rgba
    r, g, b = (ImageChops.multiply(ch, alpha) for ch in rgba.split()[:3])
    return Image.merge("RGBA", (r, g, b, alpha))


def bitmap_stroke(
    img: Image.Image, x: float, y: float, width: float
) -> tuple[dict, float]:
    """Bitmap stroke showing `img` with its top-left corner at (x, y), `width` document units wide.

    :param img: the image (any Pillow mode; converted to premultiplied RGBA)
    :type img: PIL.Image.Image
    :param x: left edge in document units
    :type x: float
    :param y: top edge in document units
    :type y: float
    :param width: displayed width in document units; the height follows the aspect ratio
    :type width: float
    :return: the stroke and its displayed height
    :rtype: tuple[dict, float]
    """
    rgba = _premultiplied_rgba(img)
    pw, ph = rgba.size
    height = width * ph / pw
    stroke = {
        "bitmapimage": {
            "image": {
                "data": base64.b64encode(rgba.tobytes()).decode("ascii"),
                "rectangle": _rect(pw, ph, pw / 2, ph / 2),
                "pixel_width": pw,
                "pixel_height": ph,
                "memory_format": "R8g8b8a8Premultiplied",
            },
            "rectangle": _rect(width, height, x + width / 2, y + height / 2),
        }
    }
    return stroke, height


@dataclass
class Text:
    """A text item for :func:`engine_snapshot`: the text and its style.

    :param text: the text; newlines start new lines
    :param font_size: font size in document units (Rnote's default is 32)
    :param font_family: font family name, resolved by Rnote on the machine that opens the file
    :param font_weight: CSS-style weight: 400 regular, 500 Rnote's default, 700 bold
    :param italic: italic face
    :param color: text colour as RGB components in 0-1
    :param width: width at which Rnote wraps the text, in document units; ``None`` wraps at
        the page width minus the margins
    :param alignment: ``"start"``, ``"center"``, ``"end"`` or ``"fill"``; Rnote 0.14 justifies
        ``"fill"`` text but draws ``"center"`` and ``"end"`` lines from the left edge
    """

    text: str
    font_size: float = FONT_SIZE
    font_family: str = FONT_FAMILY
    font_weight: int = FONT_WEIGHT
    italic: bool = False
    color: tuple[float, float, float] = (0.0, 0.0, 0.0)
    width: float | None = None
    alignment: str = "start"


def _text_height(text: str, font_size: float, max_width: float | None) -> float:
    """Estimated height of the laid-out text.

    Rnote measures the real font only when it loads the file, so the number of lines is
    guessed from an average glyph width of half the font size and each line is given
    :data:`LINE_HEIGHT` times the font size."""
    if max_width is None:
        lines = text.split("\n")
    else:
        per_line = max(1, int(max_width / (0.5 * font_size)))
        lines = [
            ln
            for para in text.split("\n")
            for ln in (textwrap.wrap(para, per_line) or [""])
        ]
    return len(lines) * font_size * LINE_HEIGHT


def text_stroke(
    text: str,
    x: float,
    y: float,
    *,
    font_size: float = FONT_SIZE,
    font_family: str = FONT_FAMILY,
    font_weight: int = FONT_WEIGHT,
    italic: bool = False,
    color: tuple[float, float, float] = (0.0, 0.0, 0.0),
    max_width: float | None = None,
    alignment: str = "start",
) -> tuple[dict, float]:
    """Text stroke (the text of Rnote's typewriter tool) with its top-left corner at (x, y).

    :param text: the text; newlines start new lines
    :type text: str
    :param x: left edge in document units
    :type x: float
    :param y: top edge in document units
    :type y: float
    :param font_size: font size in document units
    :type font_size: float
    :param font_family: font family name, resolved by Rnote when it opens the file
    :type font_family: str
    :param font_weight: CSS-style weight (400 regular, 700 bold)
    :type font_weight: int
    :param italic: italic face
    :type italic: bool
    :param color: text colour as RGB components in 0-1
    :type color: tuple[float, float, float]
    :param max_width: width at which Rnote wraps the text; ``None`` for no wrapping
    :type max_width: float | None
    :param alignment: ``"start"``, ``"center"``, ``"end"`` or ``"fill"``; Rnote 0.14 justifies
        ``"fill"`` text but draws ``"center"`` and ``"end"`` lines from the left edge
    :type alignment: str
    :return: the stroke and its estimated height (see :data:`LINE_HEIGHT`)
    :rtype: tuple[dict, float]
    """
    stroke = {
        "textstroke": {
            "text": text,
            "transform": {"affine": [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, x, y, 1.0]},
            "text_style": {
                "font_family": font_family,
                "font_size": font_size,
                "font_weight": font_weight,
                "font_style": "italic" if italic else "regular",
                "color": _rgba(*color),
                "max_width": max_width,
                "alignment": alignment,
                "ranged_text_attributes": [],
            },
        }
    }
    return stroke, _text_height(text, font_size, max_width)


def _is_pair(item) -> bool:
    """True for an ``(image, width)`` pair."""
    return (
        isinstance(item, (tuple, list))
        and len(item) == 2
        and isinstance(item[0], Image.Image)
    )


def _normalise(items, max_width: float) -> list:
    """`items` as a list of (image, width) pairs and :class:`Text` objects."""
    if isinstance(items, (Image.Image, str, Text)) or (
        isinstance(items, tuple) and _is_pair(items)
    ):
        items = [items]
    out = []
    for item in items:
        if isinstance(item, Image.Image):
            out.append((item, max_width))
        elif isinstance(item, str):
            out.append(Text(item))
        elif isinstance(item, Text):
            out.append(item)
        elif _is_pair(item):
            img, w = item
            out.append((img, min(float(w), max_width)))
        else:
            raise TypeError(
                "items must be images, (image, width) pairs, strings or Text objects, "
                f"not {type(item).__name__}"
            )
    return out


def engine_snapshot(
    items,
    *,
    margin: float = MARGIN,
    gap: float = GAP,
    tail: float = TAIL,
    layer: str | int = "image",
    config: dict | None = None,
) -> dict:
    """Engine snapshot holding `items` one below the other from the top-left of the first page.

    :param items: one item or a list of them: a Pillow image, an ``(image, width)`` pair, a
        string or a :class:`Text`. An image without a width is shown as wide as the page minus
        the margins, and wider widths are reduced to fit; a string is text in the default style,
        wrapped at that same width
    :type items: PIL.Image.Image | str | Text | list
    :param margin: distance of the items from the top and left page edges, document units
    :type margin: float
    :param gap: vertical space between consecutive items, document units
    :type gap: float
    :param tail: minimum free space left below the last item; only kept with
        ``layout="fixed_size"`` (see :data:`TAIL`)
    :type tail: float
    :param layer: layer the images go on: a name from :data:`LAYERS` or an int for a
        numbered user layer. The default is where Rnote puts a pasted image; its PDF import
        uses ``"document"`` instead, which draws below that. Text always goes on user layer 0
    :type layer: str | int
    :param config: page configuration from :func:`document_config`; default A4, infinite
        layout, light-blue grid
    :type config: dict | None
    :return: the snapshot (``document``, ``camera``, stroke and chrono components)
    :rtype: dict
    """
    config = config or document_config()
    _layer(layer)  # reject a bad layer before writing anything, even with no images
    page_w, page_h = config["format"]["width"], config["format"]["height"]
    full = page_w - 2 * margin
    strokes, y = [], margin  # strokes: (stroke, layer) pairs
    for item in _normalise(items, full):
        if isinstance(item, Text):
            stroke, height = text_stroke(
                item.text,
                margin,
                y,
                font_size=item.font_size,
                font_family=item.font_family,
                font_weight=item.font_weight,
                italic=item.italic,
                color=item.color,
                max_width=full if item.width is None else min(item.width, full),
                alignment=item.alignment,
            )
            stroke_layer = 0
        else:
            stroke, height = bitmap_stroke(item[0], margin, y, item[1])
            stroke_layer = layer
        strokes.append((stroke, stroke_layer))
        y += height + gap
    doc_h = max(page_h, y - gap + tail) if strokes else page_h
    return {
        "document": {
            "config": config,
            "x": 0.0,
            "y": 0.0,
            "width": page_w,
            "height": doc_h,
        },
        "camera": {"offset": [-margin, -margin], "size": [1200.0, 800.0], "zoom": 1.0},
        "stroke_components": [{"value": None, "version": 0}]
        + [{"value": s, "version": 1} for s, _ in strokes],
        "chrono_components": [{"value": None, "version": 0}]
        + [
            {"value": {"t": i + 1, "layer": _layer(lyr)}, "version": 1}
            for i, (_, lyr) in enumerate(strokes)
        ],
        "chrono_counter": len(strokes),
    }


def rnote_bytes(
    items, *, version: str = RNOTE_VERSION, compresslevel: int = 6, **kwargs
) -> bytes:
    """The bytes of an ``.rnote`` file holding `items`; see :func:`engine_snapshot` for the layout.

    :param items: images, ``(image, width)`` pairs, strings or :class:`Text` objects, one or a list
    :type items: PIL.Image.Image | str | Text | list
    :param version: Rnote version written in the file header
    :type version: str
    :param compresslevel: gzip level, 0-9
    :type compresslevel: int
    :param kwargs: layout options forwarded to :func:`engine_snapshot`
    :return: gzip-compressed JSON, ready to be written to disk
    :rtype: bytes
    """
    doc = {
        "version": version,
        "data": {"engine_snapshot": engine_snapshot(items, **kwargs)},
    }
    payload = json.dumps(doc, separators=(",", ":")).encode("utf-8")
    return gzip.compress(payload, compresslevel=compresslevel, mtime=0)


def write_rnote(fp, items, **kwargs) -> int:
    """Write an ``.rnote`` file holding `items` and return its size in bytes.

    :param fp: destination path (parent directories are created)
    :type fp: str | pathlib.Path
    :param items: images, ``(image, width)`` pairs, strings or :class:`Text` objects, one or a list
    :type items: PIL.Image.Image | str | Text | list
    :param kwargs: options forwarded to :func:`rnote_bytes`
    :return: number of bytes written
    :rtype: int
    """
    data = rnote_bytes(items, **kwargs)
    fp = Path(fp)
    fp.parent.mkdir(parents=True, exist_ok=True)
    fp.write_bytes(data)
    return len(data)


def read_rnote(fp) -> dict:
    """Parse an ``.rnote`` file written in the gzip-JSON format.

    The snapshot is returned as it is stored, so its shape follows the file's ``version``:
    files written before Rnote 0.13 keep ``format``, ``background`` and ``layout`` directly
    on ``document`` instead of under ``document.config``.

    :param fp: path of the file
    :type fp: str | pathlib.Path
    :return: the decoded document: ``{"version": ..., "data": {"engine_snapshot": ...}}``
    :rtype: dict
    """
    return json.loads(gzip.decompress(Path(fp).read_bytes()))


def stack(images: list[Image.Image], gaps: list[int] | None = None) -> Image.Image:
    """Stack images vertically, left-aligned on white, into one image.

    Transparent areas of an RGBA image keep the white background.

    :param images: the images, top to bottom
    :type images: list[PIL.Image.Image]
    :param gaps: white space in pixels put *before* each image (default none)
    :type gaps: list[int] | None
    :return: the composite RGB image
    :rtype: PIL.Image.Image
    """
    gaps = gaps or [0] * len(images)
    w = max(i.width for i in images)
    h = sum(i.height for i in images) + sum(gaps)
    out = Image.new("RGB", (w, h), "white")
    y = 0
    for img, gap in zip(images, gaps):
        y += gap
        out.paste(img, (0, y), img if img.mode in ("RGBA", "LA") else None)
        y += img.height
    return out


def render_clip(
    doc, pno: int, clip: tuple[float, float, float, float], zoom: float = 3.0
) -> Image.Image:
    """Render a rectangle of a PDF page to a Pillow image (needs PyMuPDF).

    :param doc: an open ``fitz.Document``
    :param pno: 1-based page number
    :type pno: int
    :param clip: ``(x0, y0, x1, y1)`` in PDF points
    :type clip: tuple[float, float, float, float]
    :param zoom: pixels per point
    :type zoom: float
    :return: the rendered clip, opaque RGB
    :rtype: PIL.Image.Image
    """
    import fitz

    pix = doc[pno - 1].get_pixmap(
        matrix=fitz.Matrix(zoom, zoom), clip=fitz.Rect(*clip), alpha=False
    )
    return Image.open(BytesIO(pix.tobytes("png")))
