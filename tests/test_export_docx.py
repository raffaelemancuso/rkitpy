import pytest

pytest.importorskip("docx")

from docx import Document  # noqa: E402

from rkitpy.export_docx import DocxFile  # noqa: E402


def test_create_table_and_save(tmp_path):
    doc = DocxFile()
    doc.add_table(3, 2)
    doc.table.cell(0, 0).text = "header"
    doc.table.cell(1, 1).text = "value"
    out = tmp_path / "out.docx"
    doc.save(out)

    assert out.exists()
    reopened = Document(str(out))
    assert len(reopened.tables) == 1
    table = reopened.tables[0]
    assert len(table.rows) == 3
    assert len(table.columns) == 2
    assert table.cell(0, 0).text == "header"
    assert table.cell(1, 1).text == "value"


def test_portrait_is_default():
    doc = DocxFile()
    assert doc.page_width < doc.page_height


def test_landscape_orientation():
    doc = DocxFile(landscape=True)
    assert doc.page_width > doc.page_height


def test_heading_written_to_document(tmp_path):
    doc = DocxFile(heading_text="My Heading")
    out = tmp_path / "heading.docx"
    doc.save(out)

    reopened = Document(str(out))
    texts = [p.text for p in reopened.paragraphs]
    assert "My Heading" in texts


def test_save_without_table(tmp_path):
    doc = DocxFile()
    out = tmp_path / "empty.docx"
    doc.save(out)
    assert out.exists()


def test_footnote_written_after_table(tmp_path):
    doc = DocxFile(footnote_text="Note: * p < 0.05.")
    doc.add_table(2, 2)
    out = tmp_path / "footnote.docx"
    doc.save(out)

    reopened = Document(str(out))
    # the footnote must be the last block-level element, i.e. after the table
    body_elements = list(reopened.element.body)
    tbl_pos = next(i for i, el in enumerate(body_elements) if el.tag.endswith("}tbl"))
    footnote_paras = [p for p in reopened.paragraphs if p.text == "Note: * p < 0.05."]
    assert len(footnote_paras) == 1
    para_pos = body_elements.index(footnote_paras[0]._p)
    assert para_pos > tbl_pos


def test_init_and_add_table_options_apply(tmp_path):
    doc = DocxFile(heading_text="My Heading")
    doc.add_table(2, 2, table_style="Light Grid")
    out = tmp_path / "styled.docx"
    doc.save(out)

    reopened = Document(str(out))
    assert "My Heading" in [p.text for p in reopened.paragraphs]
    assert len(reopened.tables) == 1
    assert reopened.tables[0].style.name == "Light Grid"
