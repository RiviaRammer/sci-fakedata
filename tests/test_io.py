from pathlib import Path

import numpy as np
import pytest

import sci_fakedata as sfd
from sci_fakedata.io import sheet_names


def test_csv_text_precision_and_missing_values(tmp_path):
    path = tmp_path / "data.csv"
    path.write_text("A,B\n1.2300,2.5300\n,3.6000\n4.5600,4.8600\n7.8900,8.1900\n2.3400,2.6400\n5.6700,5.9700\n8.9100,9.2100\n", encoding="utf-8")
    values = sfd.load(path)
    assert isinstance(values, np.ndarray) and values.shape == (7, 2)
    assert np.isnan(values[1, 0])
    report = sfd.analyze.scan(path)
    assert report.profiles[0]["decimal_places"] == {4: 6}
    assert report.profiles[1]["decimal_places"] == {4: 7}


def test_no_header_semicolon_and_ragged_rows(tmp_path):
    path = tmp_path / "data.csv"
    path.write_text("1;2;3\n4;5\n6;7;8\n", encoding="utf-8")
    values = sfd.load(path)
    assert values.shape == (3, 3) and values[0, 0] == 1
    assert np.isnan(values[1, 2])


def test_tsv_skiprows_columns(tmp_path):
    path = tmp_path / "data.tsv"
    path.write_text("Title\nA\tB\tC\n1\t2\t3\n4\t5\t6\n", encoding="utf-8")
    np.testing.assert_array_equal(sfd.load(path, skiprows=1, columns=[0, 2]), [[1, 3], [4, 6]])


def test_excel_sheets_formulas(tmp_path):
    openpyxl = pytest.importorskip("openpyxl")
    book = openpyxl.Workbook()
    first = book.active
    first.title = "Measured"
    first.append(["A", "B"])
    for i in range(8):
        first.append([i + 0.25, i + 0.55])
    second = book.create_sheet("Other")
    second.append([1, "=1+1", 3])
    second.append([4, 5, 6])
    book.create_sheet("Blank")
    path = tmp_path / "source.xlsx"
    book.save(path)
    assert sheet_names(path) == ["Measured", "Other", "Blank"]
    np.testing.assert_allclose(sfd.load(path, sheet="Measured")[:, 1] - sfd.load(path, sheet=0)[:, 0], 0.3)
    tables = sfd.load_all(path)
    assert set(tables) == {"Measured", "Other"}
    assert np.isnan(tables["Other"][0, 1])
    assert any(f.code == "constant_offset" for f in sfd.analyze.scan(path).findings)


def test_numpy_disallows_pickle(tmp_path):
    path = tmp_path / "data.npy"
    values = np.arange(60).reshape(3, 4, 5)
    np.save(path, values)
    np.testing.assert_array_equal(sfd.load(path), values)
    np.save(path, np.array([{"not": "numeric"}], dtype=object))
    with pytest.raises(ValueError):
        sfd.load(path)


@pytest.mark.parametrize("body", ["", "A,B\nhello,world\n", "\n"])
def test_empty_input(body, tmp_path):
    path = tmp_path / "empty.csv"
    path.write_text(body, encoding="utf-8")
    with pytest.raises(ValueError):
        sfd.load(path)


def test_scientific_notation_precision(tmp_path):
    path = tmp_path / "scientific.csv"
    path.write_text("A\n-1.2300e-2\n-2.3400e-2\n-3.4500e-2\n-4.5600e-2\n-5.6700e-2\n-6.7800e-2\n", encoding="utf-8")
    assert sfd.analyze.scan(path).profiles[0]["decimal_places"] == {6: 6}


def test_packaged_data_matches_repo():
    root = Path(__file__).resolve().parents[1]
    for name in ("chit1_fig2b_1.csv", "chit1_fig2b_2.csv", "provenance.json"):
        assert (root / "data" / name).read_bytes() == (root / "src/sci_fakedata/datasets" / name).read_bytes()
