"""Offline regression tests for Text-to-SQL evaluation."""

from evals.evaluate_agent import rows_equal, values_equal


def test_numeric_values_allow_small_floating_point_differences():
    assert values_equal(5.65, 5.6500001)


def test_numeric_values_reject_meaningful_differences():
    assert not values_equal(5.65, 5.66)


def test_non_numeric_values_must_match_exactly():
    assert values_equal("Metallica", "Metallica")
    assert not values_equal("Metallica", "metallica")


def test_rows_must_match_in_the_same_order():
    expected = [["Album A", "Artist A"], ["Album B", "Artist B"]]
    actual = [["Album B", "Artist B"], ["Album A", "Artist A"]]

    assert not rows_equal(expected, actual)


def test_rows_must_have_the_same_number_of_rows():
    assert not rows_equal([[1], [2]], [[1]])


def test_rows_must_have_the_same_number_of_columns():
    assert not rows_equal([[1, "Name"]], [[1, "Name", "Email"]])


def test_matching_rows_with_rounded_numeric_values_pass():
    expected = [[5.65]]
    actual = [[5.6500001]]

    assert rows_equal(expected, actual)