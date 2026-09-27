import json

import numpy as np
import pytest

import sci_fakedata as sfd


def codes(report):
    return {finding.code for finding in report.findings}


def test_offset_duplicate_and_affine():
    base = np.array([1.234, 4.689, 3.417, 8.256, 2.741, 7.312, 5.913, 9.438])
    report = sfd.analyze.scan(np.column_stack((base, base + 0.3, base.copy(), base * 2.0 + 5)))
    assert {"constant_offset", "duplicate_series", "affine_relation"} <= codes(report)
    finding = next(f for f in report.findings if f.code == "constant_offset")
    assert finding.metrics["offset"] == pytest.approx(0.3)
    assert finding.metrics["finite_overlap"] == len(base)


def test_repeated_tails_and_coarse_differences():
    base = np.array([1.12345, 3.23456, 5.34567, 8.45678, 2.56789, 6.67891, 4.78912, 7.89123])
    delta = np.array([0.2, 0.7, 0.1, 0.6, 0.4, 0.3, 0.8, 0.5])
    report = sfd.analyze.scan(np.column_stack((base, base + delta)))
    assert {"coarse_difference_grid", "repeated_decimal_tail"} <= codes(report)
    assert "constant_offset" not in codes(report)


def test_three_dimensions_and_cross_axes():
    matrix = np.random.default_rng(11).normal(size=(6, 6, 6))
    matrix[0, :, 0] = matrix[:, 1, 1] + 0.3
    report = sfd.analyze.scan(matrix)
    assert len(report.profiles) == 108
    assert report.comparisons["cross_axis_pairs"] > 0
    assert any(f.code == "constant_offset" and f.metrics["cross_axis"] for f in report.findings)


def test_missing_alignment():
    left = np.array([1, np.nan, 3, 5, 7, 9, 2, 6], dtype=float)
    right = left + 0.3
    right[3] = np.nan
    report = sfd.analyze.scan(np.column_stack((left, right)))
    finding = next(f for f in report.findings if f.code == "constant_offset")
    assert finding.metrics["finite_overlap"] == 6
    assert finding.metrics["example_indices"] == [0, 2, 4, 5, 6]


def test_nan_gap_not_joined():
    report = sfd.analyze.scan(np.array([0, 1, np.nan, 100, 101, np.nan, 300, 301]))
    assert "arithmetic_sequence" not in codes(report)


def test_decimal_bias():
    report = sfd.analyze.scan(np.arange(30, dtype=float) + 0.25)
    assert {"terminal_digit_concentration", "uniform_precision", "arithmetic_sequence"} <= codes(report)
    assert next(f for f in report.findings if f.code == "terminal_digit_concentration").metrics["digit"] == "5"


def test_independent_control():
    report = sfd.analyze.scan(np.random.default_rng(41).normal(size=(100, 3)))
    assert not ({"constant_offset", "duplicate_series", "affine_relation", "coarse_difference_grid"} & codes(report))


def test_named_arrays_compared():
    base = np.random.default_rng(31).normal(size=12)
    report = sfd.analyze.scan({"first": base, "second": base + 0.3})
    assert report.comparisons["cross_dataset_pairs"] == 1
    assert "constant_offset" in codes(report)


def test_budgets_visible():
    report = sfd.analyze.scan(np.random.default_rng(4).normal(size=(10, 10)), max_series=5, max_pairs=3)
    assert report.comparisons["eligible_series"] == 20
    assert report.comparisons["profiled_series"] == 5
    assert report.comparisons["checked_pairs"] == 3
    assert any("Series budget" in n for n in report.notes)
    assert any("Pair budget" in n for n in report.notes)


def test_expected_sum_opt_in():
    values = np.array([[0.3, 99.7], [0.4, 99.9], [np.nan, 100]])
    assert "sum_mismatch" not in codes(sfd.analyze.scan(values))
    report = sfd.analyze.scan(values, expected_sum=100, sum_axis=1)
    findings = [f for f in report.findings if f.code == "sum_mismatch"]
    assert len(findings) == 1
    assert findings[0].metrics["actual"] == pytest.approx(100.3)


def test_axis_selection():
    report = sfd.analyze.scan(np.random.default_rng(0).normal(size=(8, 9)), axes=[0])
    assert len(report.profiles) == 9
    assert report.comparisons["cross_axis_pairs"] == 0


def test_insufficient_samples():
    report = sfd.analyze.scan(np.array([[1., 2.], [3., 4.]]))
    assert not report.findings
    assert any("No axis line" in n for n in report.notes)


@pytest.mark.parametrize("values", [[], np.array(1.0), [np.nan, np.inf], ["1", "2"], [True, False], [1 + 1j]])
def test_invalid_arrays(values):
    with pytest.raises(ValueError):
        sfd.analyze.scan(values)


@pytest.mark.parametrize("options", [{"min_samples": 2}, {"max_pairs": 0}, {"max_series": False},
                                    {"max_decimals": 19}, {"match_fraction": 2}, {"atol": -1},
                                    {"axes": [2]}, {"expected_sum": float("nan")}, {"sum_axis": 2, "expected_sum": 1}])
def test_invalid_options(options):
    with pytest.raises(ValueError):
        sfd.analyze.scan(np.arange(10.), **options)


def test_reports_and_declared_conclusion(tmp_path):
    report = sfd.analyze.scan(sfd.gen.normal(seed=5, conclusion="Declared example conclusion"))
    assert report.declared_conclusions == {"data": "Declared example conclusion"}
    assert "not verified" in report.summary()
    report.write(tmp_path / "report.json")
    assert json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))["shapes"]["data"] == [1000]
    report.write(tmp_path / "report.txt")
    assert "numerical pattern report" in (tmp_path / "report.txt").read_text(encoding="utf-8")
