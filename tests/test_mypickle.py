from rkitpy import mypickle


def test_write_then_read_roundtrip(tmp_path):
    data = {"a": 1, "b": [1, 2, 3], "c": "hello"}
    mypickle.write_pickle(data, tmp_path, "mydata")

    files = list(tmp_path.glob("mydata_*"))
    assert len(files) == 1

    loaded = mypickle.read_pickle(files[0])
    assert loaded == data


def test_roundtrip_preserves_non_string_keys(tmp_path):
    # keys=True keeps non-string dict keys intact across the roundtrip.
    data = {1: "one", (2, 3): "tuple-key"}
    mypickle.write_pickle(data, tmp_path, "keys")
    loaded = mypickle.read_pickle(next(tmp_path.glob("keys_*")))
    assert loaded == data


def test_write_pickle_filename_uses_stem(tmp_path):
    mypickle.write_pickle([1, 2], tmp_path, "stemname")
    files = list(tmp_path.glob("stemname_*"))
    assert len(files) == 1
    assert files[0].name.startswith("stemname_")
