from rkitpy.list_replace import list_replace


def test_replaces_all_occurrences_in_place():
    lst = [1, 2, 3, 2, 4]
    list_replace(lst, 2, 5)
    assert lst == [1, 5, 3, 5, 4]


def test_returns_none():
    lst = [1]
    assert list_replace(lst, 1, 2) is None


def test_no_occurrence_leaves_list_unchanged():
    lst = [1, 2, 3]
    list_replace(lst, 9, 0)
    assert lst == [1, 2, 3]


def test_empty_list():
    lst = []
    list_replace(lst, 1, 2)
    assert lst == []


def test_all_elements_replaced():
    lst = [7, 7, 7]
    list_replace(lst, 7, 0)
    assert lst == [0, 0, 0]


def test_works_with_strings():
    lst = ["a", "b", "a"]
    list_replace(lst, "a", "z")
    assert lst == ["z", "b", "z"]
