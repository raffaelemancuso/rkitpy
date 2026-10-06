from rkitpy.tqdm import tqdm_batch


def test_batches_cover_all_items():
    data = list(range(10))
    batches = [tuple(b) for b in tqdm_batch(data, 3)(disable=True)]
    assert batches == [(0, 1, 2), (3, 4, 5), (6, 7, 8), (9,)]


def test_exact_division():
    data = list(range(9))
    batches = [tuple(b) for b in tqdm_batch(data, 3)(disable=True)]
    assert batches == [(0, 1, 2), (3, 4, 5), (6, 7, 8)]


def test_total_is_ceiling_division():
    bar = tqdm_batch(list(range(10)), 3)
    assert bar.keywords["total"] == 4


def test_total_exact_division():
    bar = tqdm_batch(list(range(9)), 3)
    assert bar.keywords["total"] == 3
