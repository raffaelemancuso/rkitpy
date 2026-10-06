"""Offline geocoding of European addresses to NUTS-3 regions with the GISCO
postcode point dataset (one point per postcode area, each carrying its NUTS-3
region), as used by orbis-name-scraper (src/eu_all/3_geocode.py) and the
PATSTAT notebook of paper 6.

The lookup goes: full postcode -> 4-character postcode prefix (countries whose
codes are longer, such as NL "3846 AG" and PT "2500-277") -> municipality (LAU)
name, usable when at least `city_min_share` of its postcodes lie in one NUTS-3
region. Country ids follow GISCO (EL for Greece, UK for the United Kingdom).

    tables = PostcodeTables.from_gisco(load_postcode_points(fp))
    located = tables.locate(df, cntr="cntr", postcode="postcode", city="city")

Licence of the data: CC-BY-SA 4.0, (c) European Union - GISCO, 2024.
"""

from __future__ import annotations

import re
import unicodedata
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import polars as pl

GISCO_PCODE_URL = "https://gisco-services.ec.europa.eu/distribution/v2/pcode/parquet/PCODE_PT_2024_4326.parquet"
ISO_TO_GISCO = {"GR": "EL", "GB": "UK"}


def download(url: str, fp: Path) -> Path:
    """Download `url` to `fp` unless the file exists; returns `fp`."""
    fp = Path(fp)
    if not fp.is_file():
        fp.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=600) as r, open(fp, "wb") as f:
            f.write(r.read())
    return fp


def gisco_country(iso2: str | None) -> str | None:
    """ISO 3166-1 alpha-2 code to the GISCO country id (EL, UK)."""
    if iso2 is None:
        return None
    return ISO_TO_GISCO.get(iso2.upper(), iso2.upper())


def fold_name(s: str | None) -> str | None:
    """Municipality/city name key: text before the first comma ("Mainz, Stadt"),
    accents stripped, upper case, letters and single spaces only."""
    if s is None:
        return None
    s = s.split(",")[0]
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = " ".join(re.sub(r"[^A-Za-z ]+", " ", s).upper().split())
    return s or None


def fold_column(df: pl.DataFrame, col: str, key: str) -> pl.DataFrame:
    """Add `key` = fold_name(`col`), computed once per distinct value."""
    uniq = df.select(pl.col(col).unique()).to_series()
    mapping = {v: fold_name(v) for v in uniq if v is not None}
    return df.with_columns(
        pl.col(col)
        .replace_strict(mapping, default=None, return_dtype=pl.String)
        .alias(key)
    )


def postcode_key(col: pl.Expr, cntr: pl.Expr) -> pl.Expr:
    """Postcode key shared by GISCO and the sources: upper-case alphanumerics, a
    leading country prefix dropped ("LV-1010", "HU-1138"), and only the
    3-character routing key / locality code for Ireland and Malta."""
    key = col.cast(pl.String).str.to_uppercase().str.replace_all(r"[^A-Z0-9]", "")
    key = (
        pl.when(key.str.contains(r"^[A-Z]{2}\d")).then(key.str.slice(2)).otherwise(key)
    )
    key = pl.when(cntr.is_in(["IE", "MT"])).then(key.str.slice(0, 3)).otherwise(key)
    return pl.when(key == "").then(None).otherwise(key)


def load_postcode_points(fp: Path | str) -> pl.DataFrame:
    """The GISCO postcode points as cntr, postcode, lau, nuts3_gisco, lon, lat, key."""
    gisco = pl.read_parquet(
        fp, columns=["POSTCODE", "CNTR_ID", "LAU_NAME", "NUTS3_2024", "Shape_bbox"]
    ).select(
        cntr=pl.col("CNTR_ID"),
        postcode=pl.col("POSTCODE"),
        lau=pl.col("LAU_NAME"),
        nuts3_gisco=pl.col("NUTS3_2024").str.strip_chars("'"),
        # point geometries: the bounding box is the point itself
        lon=pl.col("Shape_bbox").struct.field("xmin").cast(pl.Float64),
        lat=pl.col("Shape_bbox").struct.field("ymin").cast(pl.Float64),
    )
    return gisco.with_columns(key=postcode_key(pl.col("postcode"), pl.col("cntr")))


@dataclass
class PostcodeTables:
    """Lookup tables built from the GISCO postcode points."""

    postcodes: (
        pl.DataFrame
    )  # cntr, key, lon, lat, nuts3_gisco: one point per postcode key
    prefixes: (
        pl.DataFrame
    )  # cntr, key4, lon, lat, nuts3_gisco: 4-character prefixes of long codes
    key_length: pl.DataFrame  # cntr, klen: the usual key length of the country
    cities: (
        pl.DataFrame
    )  # cntr, city_key, lon, lat, nuts3_gisco: usable municipality names
    n_city_names: int  # municipality names in the dataset, usable or not

    @classmethod
    def from_gisco(
        cls, gisco: pl.DataFrame, city_min_share: float = 0.9
    ) -> "PostcodeTables":
        pc_tbl = (
            gisco.drop_nulls("key")
            .group_by("cntr", "key")
            .agg(
                pl.col("lon").mean(),
                pl.col("lat").mean(),
                pl.col("nuts3_gisco").mode().first(),
            )
        )
        klen_tbl = pc_tbl.group_by("cntr").agg(
            pl.col("key").str.len_chars().mode().first().alias("klen")
        )
        pc4_tbl = (
            pc_tbl.join(klen_tbl, on="cntr")
            .filter(pl.col("klen") >= 6)
            .with_columns(key4=pl.col("key").str.slice(0, 4))
            .group_by("cntr", "key4")
            .agg(
                pl.col("lon").mean(),
                pl.col("lat").mean(),
                pl.col("nuts3_gisco").mode().first(),
            )
        )
        city_tbl = (
            fold_column(gisco.drop_nulls("lau"), "lau", "city_key")
            .drop_nulls("city_key")
            .with_columns(
                nuts3_mode=pl.col("nuts3_gisco")
                .mode()
                .first()
                .over("cntr", "city_key"),
                share=(pl.col("nuts3_gisco") == pl.col("nuts3_gisco").mode().first())
                .mean()
                .over("cntr", "city_key"),
            )
            .filter(
                (pl.col("share") >= city_min_share)
                & (pl.col("nuts3_gisco") == pl.col("nuts3_mode"))
            )
            .with_columns(
                d2=(pl.col("lon") - pl.col("lon").mean().over("cntr", "city_key")) ** 2
                + (pl.col("lat") - pl.col("lat").mean().over("cntr", "city_key")) ** 2
            )
            .group_by("cntr", "city_key")
            .agg(
                pl.col("lon").sort_by("d2").first(),
                pl.col("lat").sort_by("d2").first(),
                pl.col("nuts3_mode").first().alias("nuts3_gisco"),
            )
        )
        n_city_names = gisco.select("cntr", "lau").drop_nulls().unique().height
        return cls(pc_tbl, pc4_tbl, klen_tbl, city_tbl, n_city_names)

    def locate(
        self,
        df: pl.DataFrame,
        cntr: str,
        postcode: str | None = None,
        city: str | None = None,
    ) -> pl.DataFrame:
        """Append lon, lat, nuts3_gisco and source ("postcode", "city" or null) to
        `df` from its GISCO country id column `cntr`, its postcode column and its
        municipality-name column (either may be omitted)."""
        out = df.with_columns(
            key=postcode_key(pl.col(postcode), pl.col(cntr))
            if postcode
            else pl.lit(None, dtype=pl.String),
        ).join(self.key_length, on=cntr, how="left")
        out = out.with_columns(
            # a numeric postcode one digit short of the country's usual length lost a leading zero
            key=pl.when(
                pl.col("key").str.contains(r"^\d+$")
                & (pl.col("key").str.len_chars() == pl.col("klen") - 1)
            )
            .then(pl.col("key").str.zfill(pl.col("klen")))
            .otherwise(pl.col("key"))
        ).with_columns(
            key4=pl.when(
                (pl.col("klen") >= 6) & (pl.col("key").str.len_chars() == 4)
            ).then(pl.col("key"))
        )
        out = (
            fold_column(out, city, "city_key")
            if city
            else out.with_columns(city_key=pl.lit(None, dtype=pl.String))
        )
        out = (
            out.join(
                self.postcodes.rename(
                    {
                        "cntr": cntr,
                        "lon": "lon_pc",
                        "lat": "lat_pc",
                        "nuts3_gisco": "nuts3_pc",
                    }
                ),
                on=[cntr, "key"],
                how="left",
            )
            .join(
                self.prefixes.rename(
                    {
                        "cntr": cntr,
                        "lon": "lon_p4",
                        "lat": "lat_p4",
                        "nuts3_gisco": "nuts3_p4",
                    }
                ),
                on=[cntr, "key4"],
                how="left",
            )
            .join(
                self.cities.rename(
                    {
                        "cntr": cntr,
                        "lon": "lon_ct",
                        "lat": "lat_ct",
                        "nuts3_gisco": "nuts3_ct",
                    }
                ),
                on=[cntr, "city_key"],
                how="left",
            )
            .with_columns(
                lon=pl.coalesce("lon_pc", "lon_p4", "lon_ct"),
                lat=pl.coalesce("lat_pc", "lat_p4", "lat_ct"),
                nuts3_gisco=pl.coalesce("nuts3_pc", "nuts3_p4", "nuts3_ct"),
                source=pl.when(
                    pl.col("nuts3_pc").is_not_null() | pl.col("nuts3_p4").is_not_null()
                )
                .then(pl.lit("postcode"))
                .when(pl.col("nuts3_ct").is_not_null())
                .then(pl.lit("city"))
                .otherwise(None),
            )
        )
        return out.drop(
            "key",
            "klen",
            "key4",
            "city_key",
            "lon_pc",
            "lat_pc",
            "nuts3_pc",
            "lon_p4",
            "lat_p4",
            "nuts3_p4",
            "lon_ct",
            "lat_ct",
            "nuts3_ct",
        )
