import polars as pl
import pytest

from rkitpy import gisco


def test_postcode_key():
    df = pl.DataFrame(
        {
            "pc": ["LV-1010", "3846 AG", "12-345", "d02 x285", "VLT 1171", None, "--"],
            "cntr": ["LV", "NL", "PL", "IE", "MT", "DE", "DE"],
        }
    )
    out = df.select(gisco.postcode_key(pl.col("pc"), pl.col("cntr")).alias("key"))[
        "key"
    ].to_list()
    assert out == ["1010", "3846AG", "12345", "D02", "VLT", None, None]


def test_fold_name():
    assert gisco.fold_name("Mainz, Stadt") == "MAINZ"
    assert gisco.fold_name("Alingsås  kommun") == "ALINGSAS KOMMUN"
    assert gisco.fold_name("L'Aquila") == "L AQUILA"
    assert gisco.fold_name("123") is None
    assert gisco.fold_name(None) is None


def test_gisco_country():
    assert gisco.gisco_country("GR") == "EL"
    assert gisco.gisco_country("gb") == "UK"
    assert gisco.gisco_country("DE") == "DE"
    assert gisco.gisco_country(None) is None


@pytest.fixture
def tables():
    # a toy GISCO extract: two German towns (5-digit codes) and a Dutch one (6-character codes)
    points = pl.DataFrame(
        {
            "cntr": ["DE", "DE", "DE", "DE", "NL", "NL"],
            "postcode": ["80331", "80333", "86153", "01067", "3846 AG", "3846 BB"],
            "lau": [
                "München",
                "München",
                "Augsburg",
                "Dresden",
                "Harderwijk",
                "Harderwijk",
            ],
            "nuts3_gisco": ["DE212", "DE212", "DE271", "DED21", "NL230", "NL230"],
            "lon": [11.57, 11.56, 10.89, 13.74, 5.62, 5.63],
            "lat": [48.14, 48.15, 48.37, 51.05, 52.35, 52.36],
        }
    ).with_columns(key=gisco.postcode_key(pl.col("postcode"), pl.col("cntr")))
    return gisco.PostcodeTables.from_gisco(points)


def test_locate(tables):
    df = pl.DataFrame(
        {
            "id": [1, 2, 3, 4, 5, 6, 7],
            "cntr": ["DE", "DE", "NL", "NL", "DE", "DE", "DE"],
            "postcode": ["80333", "1067", None, "3846", None, "99999", "9999"],
            "city": [None, None, "harderwijk", None, "Munchen", None, "Augsburg"],
        }
    )
    out = tables.locate(df, cntr="cntr", postcode="postcode", city="city").sort("id")
    # 1067 lost the leading zero of 01067; 3846 is the 4-character prefix of the Dutch codes
    assert out["nuts3_gisco"].to_list() == [
        "DE212",
        "DED21",
        "NL230",
        "NL230",
        "DE212",
        None,
        "DE271",
    ]
    assert out["source"].to_list() == [
        "postcode",
        "postcode",
        "city",
        "postcode",
        "city",
        None,
        "city",
    ]
    assert set(out.columns) == {
        "id",
        "cntr",
        "postcode",
        "city",
        "lon",
        "lat",
        "nuts3_gisco",
        "source",
    }


def test_locate_without_postcode_column(tables):
    df = pl.DataFrame({"cntr": ["DE"], "city": ["München"]})
    out = tables.locate(df, cntr="cntr", city="city")
    assert out["nuts3_gisco"].to_list() == ["DE212"]
