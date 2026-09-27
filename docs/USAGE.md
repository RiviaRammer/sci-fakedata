# Usage

Install from the checkout with `python -m pip install -e .`; after publication use `python -m pip install sci-fakedata`. NumPy and all Excel input dependencies are installed automatically. For development, also install the tooling with `python -m pip install pytest build twine`.

## Generate NumPy arrays

```python
import sci_fakedata as sfd

data = sfd.gen.normal(n=(20, 3), seed=42, conclusion="A caller-supplied example conclusion.")
errors = sfd.gen.error(n=data.shape, systematic=0.2, std=0.05, seed=43)
measured = data + errors
white = sfd.gen.white_noise(n=1000, seed=42)
red = sfd.gen.red_noise(n=1000, alpha=0.9, seed=42)
uniform = sfd.gen.uniform(n=1000, low=0, high=1, seed=42)
```

Generators return an ndarray subclass labelled `synthetic=True`. `conclusion` is stored verbatim; it does not affect values, infer a confidence level or verify a scientific claim. Error is a constant systematic component plus independent Gaussian white noise. Red noise is stationary AR(1) along the last dimension. Shapes, parameters and seeds control generation.

## Analyze files or arrays

```python
import numpy as np
import sci_fakedata as sfd

values = sfd.load("measurements.csv")  # plain float ndarray
excel = sfd.load("source.xlsx", sheet="Fig.2b-1", skiprows=2, header=False, columns=[0, 1])
report = sfd.analyze.scan(values)
print(report.summary())
report.write("reports/result.txt")
report.write("reports/result.json")

# Passing a CSV path preserves lexical decimal places, including trailing zeros.
report = sfd.analyze.scan("measurements.csv")
report = sfd.analyze.scan({"CSV": values, "Excel": excel})
report = sfd.analyze.scan(np.random.default_rng(42).normal(size=(8, 8, 8)))

# Supply expected totals only when the data's meaning warrants it.
percentages = np.array([[0.3, 99.7], [0.4, 99.9]])
report = sfd.analyze.scan(percentages, expected_sum=100, sum_axis=1)
```

Supported files: CSV, TSV, delimited TXT, XLSX/XLSM, legacy XLS, and non-pickled numeric NPY. All supported input formats work with the default installation. `sfd.load_all("source.xlsx")` returns a mapping of numeric worksheet arrays.

Loading retains blanks/text as NaN and preserves relative positions. Automatic header handling removes the first row only if it has no numeric values and later rows do. For complex tables use `skiprows`, `header=False`, and `columns` to isolate measurements: P-values/sample sizes in other columns otherwise remain numeric inputs. Excel formulas require cached values; absent caches become NaN. An ndarray cannot recover original trailing zeros or instrument precision.

## Analysis behavior

- Decimal precision histograms, dominant terminal digits, repeated values and recurring tails within each axis line.
- Constant/arithmetic sequences based on genuinely adjacent finite positions.
- Duplicate series, consecutive matching blocks, fixed offsets, exact affine relationships, matching decimal tails and coarse difference grids between equal-length lines.
- Optional expected-sum checks on complete observations.

For shape `(a, b, c)`, lines vary along each dimension while fixing the others. Equal-length lines are compared both within and between axes/datasets. Coordinates are zero-based array indices after input selection. Pair comparisons use aligned finite intersections; missing values are never shifted away. Profiles include decimal/digit counts; findings record overlap counts, evidence indices and relationship parameters.

`min_samples=6` avoids two-point affine claims by default. `rtol`, `atol`, `max_decimals`, `tail_digits`, `match_fraction` control sensitivity. `grid_fraction=0.8` sets the minimum fraction of differences on the 0.1 grid; reported exceptions remain visible. Uniform precision and linear relationships may be legitimate. No heuristic assumes every measurement's final digits must be uniform, and there is no “fabrication probability.”

Text summaries are bilingual, with section dividers, readable metrics and paired-value tables. Displayed rows/columns/positions start at 1; JSON evidence indices remain zero-based. JSON preserves numeric evidence and adds Chinese/English rule titles. Default summaries expand up to 30 findings; saved text reports expand all findings.

Terminal output preserves Python's existing encoding, including `PYTHONIOENCODING`; saved text/JSON files always use UTF-8. If a terminal decodes output differently, match its charset explicitly: `sfd demo --encoding gb18030` for a GBK/GB18030 terminal, or `sfd demo --encoding utf-8` for a UTF-8 terminal. Version 0.1.2 forced UTF-8 even in GBK terminals; version 0.1.3 removes that override.

`max_series=2000` and `max_pairs=50000` bound work; the report explicitly states skipped profiling/pairs. Pair work is shared across length groups. For very large data choose meaningful blocks or raise the limits; default analysis is not guaranteed exhaustive.

## Demo and CLI

```bash
python examples/demo.py
sfd demo -o reports/demo.txt --json reports/demo.json
sfd analyze data/chit1_fig2b_1.csv --expected-sum 100 --sum-axis 1
sfd analyze data/raw/chit1_source_data_fig2.xlsx --sheet Fig.2b-1 --skiprows 2 --header no
python -m sci_fakedata analyze measurements.npy
```

The default demo compares six unmodified numeric blocks from Fig. 2b and Extended Data Fig. 3 of the Nature Source Data. It shows the 100.3% row total, eight identical Aged values, seven consecutive identical Young values, recurring decimal tails and coarse difference grids. URLs, cell ranges, hashes and correction details are in `data/provenance.json`. Full downloaded workbooks stay local and are excluded from builds; demo execution performs no download.

## Build and upload

```bash
python -m pytest
python -m build
python -m twine check --strict dist/*
python -m twine upload --username __token__ dist/*
```

Enter the complete `pypi-...` secret at the upload prompt. A token identifier is not a credential. Upload only the current version's archives and keep credentials outside the repository.

Version 0.1.3 implements no leaderboard, telemetry, IP lookup, language/timezone collection or steganography. Import, generation and analysis run locally.
