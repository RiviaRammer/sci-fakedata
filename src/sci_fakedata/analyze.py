"""Explainable comparisons of axis-aligned NumPy series, including equal lengths across axes."""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from itertools import combinations
import operator
from pathlib import Path

import numpy as np

from .io import Table, read
from .report import Finding, Report


@dataclass
class _Series:
    name: str
    values: np.ndarray
    text: np.ndarray | None
    axis: int
    dataset: str


def _represent(value, token, max_decimals):
    """Decimal digit evidence, avoiding long binary-float formatting tails."""
    if token is not None:
        try:
            decimal = Decimal(str(token))
            places = max(0, -decimal.as_tuple().exponent)
        except (InvalidOperation, TypeError, ValueError):
            places = 0
            decimal = None
        if decimal is not None and decimal.is_finite() and places <= max_decimals:
            rendered = format(abs(decimal), "f")
            fraction = rendered.partition(".")[2]
            return places, fraction
    rendered = format(abs(float(value)), f".{max_decimals}f").rstrip("0").rstrip(".")
    fraction = rendered.partition(".")[2]
    return len(fraction), fraction


def _lines(name, table):
    values = table.values
    for axis in range(values.ndim):
        moved = np.moveaxis(values, axis, -1)
        text = np.moveaxis(table.text, axis, -1) if table.text is not None else None
        for index in np.ndindex(moved.shape[:-1]):
            axes = [dimension for dimension in range(values.ndim) if dimension != axis]
            coordinates = ",".join(f"{dimension}={value}" for dimension, value in zip(axes, index))
            label = f"{name}:axis={axis}[{coordinates}]"
            yield _Series(label, moved[index], None if text is None else text[index], axis, name)


def _digits(series, mask, max_decimals):
    indices = np.flatnonzero(mask)
    return [_represent(series.values[i], None if series.text is None else series.text[i], max_decimals) for i in indices]


def _profile(series, *, min_samples, max_decimals, rtol, atol):
    mask = np.isfinite(series.values)
    values = series.values[mask]
    digits = _digits(series, mask, max_decimals)
    precision = Counter(places for places, _ in digits)
    endings = Counter(fraction[-1] for _, fraction in digits if fraction)
    profile = {
        "series": series.name,
        "axis": series.axis,
        "length": len(series.values),
        "finite_count": len(values),
        "missing_or_infinite": int((~mask).sum()),
        "decimal_places": dict(sorted(precision.items())),
        "terminal_digits": dict(sorted(endings.items())),
        "min": float(values.min()),
        "max": float(values.max()),
    }
    findings = []

    def add(code, message, metrics, severity="review"):
        findings.append(Finding(code, message, (series.name,), metrics, severity))

    if len(precision) == 1:
        places = next(iter(precision))
        add("uniform_precision", "All finite values have the same represented decimal precision; this can be ordinary rounding.",
            {"decimal_places": places, "samples": len(values)}, "info")
    if endings and sum(endings.values()) >= 20:
        digit, count = endings.most_common(1)[0]
        fraction = count / sum(endings.values())
        if fraction >= 0.65:
            add("terminal_digit_concentration", "One final decimal digit dominates. Check quantization/rounding before interpreting this pattern.",
                {"digit": digit, "count": count, "decimal_samples": sum(endings.values()), "fraction": fraction})
    unique, counts = np.unique(values, return_counts=True)
    if len(values) >= max(8, min_samples) and counts.max() / len(values) >= 0.5:
        position = int(np.argmax(counts))
        add("repeated_value", "One value occurs in at least half the finite samples; discrete or constant measurements may explain it.",
            {"value": float(unique[position]), "count": int(counts[position]), "samples": len(values)})
    adjacent = mask[:-1] & mask[1:]
    differences = np.diff(series.values)[adjacent]
    if len(differences):
        profile["adjacent_differences"] = {
            "count": len(differences),
            "mean": float(differences.mean()),
            "std": float(differences.std()),
        }
    if len(differences) >= min_samples - 1 and np.allclose(differences, differences[0], rtol=rtol, atol=atol):
        constant = np.isclose(differences[0], 0.0, rtol=0.0, atol=atol)
        add("constant_series" if constant else "arithmetic_sequence",
            "Consecutive finite positions have a constant difference; missing positions were not joined.",
            {"step": float(differences[0]), "adjacent_pairs": len(differences)}, "info" if constant else "review")
    fractions = [fraction for places, fraction in digits if places >= 3]
    if len(fractions) >= max(8, min_samples):
        tail, count = Counter(fraction[-3:] for fraction in fractions).most_common(1)[0]
        if count / len(fractions) >= 0.8:
            add("repeated_tail_within_series", "The same three decimal tail digits recur in at least 80% of eligible values.",
                {"tail": tail, "count": count, "eligible_samples": len(fractions)})
    return profile, findings


def _pair(left, right, *, min_samples, max_decimals, tail_digits, match_fraction, grid_fraction, rtol, atol):
    mask = np.isfinite(left.values) & np.isfinite(right.values)
    count = int(mask.sum())
    if count < min_samples:
        return []
    a, b = left.values[mask], right.values[mask]
    difference = b - a
    if not np.isfinite(difference).all():
        return []
    locations = np.flatnonzero(mask)
    base = {
        "finite_overlap": count,
        "length": len(left.values),
        "cross_axis": left.axis != right.axis,
        "cross_dataset": left.dataset != right.dataset,
        "difference_mean": float(difference.mean()),
        "difference_std": float(difference.std()),
        "example_indices": locations[:5].tolist(),
        "samples": [{"index": int(index), "left": float(av), "right": float(bv), "difference": float(delta)}
                    for index, av, bv, delta in zip(locations[:6], a[:6], b[:6], difference[:6])],
    }
    result = []

    def add(code, message, **metrics):
        result.append(Finding(code, message, (left.name, right.name), {**base, **metrics}))

    varying_a = np.ptp(a) > atol
    varying_b = np.ptp(b) > atol
    if not (varying_a or varying_b):
        # Constant lines are already described once in their own profiles.
        return result
    constant_offset = np.allclose(difference, difference[0], rtol=rtol, atol=atol)
    if constant_offset:
        duplicate = np.isclose(difference[0], 0.0, rtol=0.0, atol=atol)
        add("duplicate_series" if duplicate else "constant_offset",
            "Values coincide at the aligned finite positions." if duplicate else "right - left is constant at the aligned finite positions.",
            offset=float(difference[0]))
    elif varying_a and varying_b:
        centered_a, centered_b = a - a.mean(), b - b.mean()
        denominator = float(centered_a @ centered_a)
        if np.isfinite(denominator) and denominator > 0:
            slope = float((centered_a @ centered_b) / denominator)
            residual = centered_b - slope * centered_a
            tolerance = atol + rtol * float(np.ptp(b))
            if np.isfinite(slope) and np.max(np.abs(residual)) <= tolerance:
                add("affine_relation", "An exact affine relation fits the finite overlap; units and derived quantities may explain it.",
                    slope=slope, intercept=float(b.mean() - slope * a.mean()), max_residual=float(np.max(np.abs(residual))))
    if not constant_offset:
        same = np.isclose(left.values, right.values, rtol=0.0, atol=atol) & mask
        # Keep original positions: gaps must terminate a matching block.
        padded = np.r_[False, same, False].astype(int)
        starts = np.flatnonzero(np.diff(padded) == 1)
        stops = np.flatnonzero(np.diff(padded) == -1)
        if len(starts):
            longest = int(np.argmax(stops - starts))
            start, stop = int(starts[longest]), int(stops[longest])
            if stop - start >= min_samples:
                add("repeated_block", "A consecutive aligned block matches exactly although the complete series differ.",
                    block_start=start, block_stop=stop, block_length=stop - start,
                    matching_values=int(same.sum()), match_fraction=float(same.sum() / count))
    if not constant_offset:
        difference_steps = np.diff(difference)
        # Do not join difference positions separated by missing observations.
        consecutive = np.diff(locations) == 1
        difference_steps = difference_steps[consecutive]
        if len(difference_steps) >= min_samples - 1 and np.allclose(difference_steps, difference_steps[0], rtol=rtol, atol=atol):
            add("arithmetic_difference", "The aligned difference itself changes by a constant step.",
                difference_step=float(difference_steps[0]))
    digits_a = _digits(left, mask, max_decimals)
    digits_b = _digits(right, mask, max_decimals)
    eligible_tail = [(index, da, db) for index, da, db in zip(locations, digits_a, digits_b)
                     if da[0] == db[0] and da[0] >= tail_digits]
    if eligible_tail and not np.allclose(a, b, rtol=0.0, atol=atol):
        hits = [int(index) for index, da, db in eligible_tail if da[1][-tail_digits:] == db[1][-tail_digits:]]
        if len(eligible_tail) >= min_samples and len(hits) / len(eligible_tail) >= match_fraction:
            add("repeated_decimal_tail", "Decimal tails match at the same represented precision despite different overall values.",
                tail_digits=tail_digits, matches=len(hits), eligible_samples=len(eligible_tail), matched_indices=hits[:10])
    high_precision = sum(max(da[0], db[0]) >= 3 for da, db in zip(digits_a, digits_b))
    if high_precision >= min_samples and not constant_offset:
        on_grid = np.isclose(difference * 10, np.rint(difference * 10), rtol=0.0, atol=atol * 10 + rtol)
        fraction = float(on_grid.mean())
        if fraction >= grid_fraction:
            add("coarse_difference_grid", "High-precision source values yield differences on a 0.1 grid at or above the configured fraction; check how the values were derived.",
                grid_step=0.1, matches=int(on_grid.sum()), fraction=fraction, threshold=grid_fraction,
                off_grid_indices=locations[~on_grid].tolist())
    return result


def _positive_integer(name, value, *, minimum=1):
    try:
        integer = operator.index(value)
    except TypeError as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if isinstance(value, (bool, np.bool_)) or integer < minimum:
        raise ValueError(f"{name} must be at least {minimum}")
    return integer


def scan(data, *, min_samples=6, max_decimals=12, tail_digits=3, match_fraction=0.95,
         rtol=1e-9, atol=1e-10, max_series=2000, max_pairs=50000, axes=None,
         expected_sum=None, sum_axis=-1, sum_atol=1e-4, grid_fraction=0.8, **load_options) -> Report:
    """Analyze an ndarray, file path, or mapping of named arrays/files.

    Extract every axis-aligned 1-D line; compare equal-length lines both
    within and between axes/datasets. NaNs stay in position and comparisons
    use the finite intersection. max_series/max_pairs bound work explicitly;
    skipped work is reported. These are pattern heuristics, not p-values.
    """
    min_samples = _positive_integer("min_samples", min_samples, minimum=3)
    max_decimals = _positive_integer("max_decimals", max_decimals)
    tail_digits = _positive_integer("tail_digits", tail_digits)
    max_series = _positive_integer("max_series", max_series)
    max_pairs = _positive_integer("max_pairs", max_pairs)
    if max_decimals > 18 or tail_digits > max_decimals:
        raise ValueError("require tail_digits <= max_decimals <= 18")
    if not np.isfinite([rtol, atol, match_fraction]).all() or rtol < 0 or atol < 0 or not 0 < match_fraction <= 1:
        raise ValueError("tolerances must be finite/non-negative and match_fraction must be in (0, 1]")
    if not np.isfinite(grid_fraction) or not 0 < grid_fraction <= 1:
        raise ValueError("grid_fraction must be in (0, 1]")
    if not np.isfinite(sum_atol) or sum_atol < 0:
        raise ValueError("sum_atol must be finite and non-negative")
    selected_axes = None if axes is None else set(axes)
    if selected_axes is not None and (not selected_axes or any(not isinstance(axis, int) or axis < 0 for axis in selected_axes)):
        raise ValueError("axes must contain non-negative integer axis indices")
    inputs = data if isinstance(data, Mapping) else {"data": data}
    if not inputs:
        raise ValueError("no datasets provided")
    tables, conclusions, notes = {}, {}, []
    for name, source in inputs.items():
        if not isinstance(name, str):
            raise ValueError("dataset names must be strings")
        if isinstance(source, (str, Path)):
            table = read(source, **load_options)
            notes.extend(table.notes)
            if table.source:
                notes.append(f"{name} input: {table.source}")
        else:
            if load_options:
                raise ValueError("file loading options apply only to file inputs")
            raw = np.asarray(source)
            if raw.dtype.kind not in "iuf":
                raise ValueError("arrays must contain real numeric values, not strings, booleans or complex numbers")
            table = Table(np.asarray(raw, dtype=float))
            notes.append("NumPy/Excel numeric representations cannot recover original trailing zeros or instrument precision.")
        if table.values.ndim == 0 or not table.values.size:
            raise ValueError("data must be a non-empty array with at least one dimension")
        if not np.isfinite(table.values).any():
            raise ValueError("data has no finite numeric values")
        if selected_axes is not None and max(selected_axes) >= table.values.ndim:
            raise ValueError(f"axes out of range for {name}")
        tables[name] = table
        conclusion = getattr(source, "conclusion", None)
        if conclusion is not None:
            conclusions[name] = str(conclusion)
    series, profiles, findings = [], [], []
    if expected_sum is not None:
        totals = expected_sum if isinstance(expected_sum, Mapping) else {name: expected_sum for name in tables}
        if any(name not in tables for name in totals):
            raise ValueError("expected_sum refers to an unknown dataset")
        for name, target in totals.items():
            if not np.isfinite(target):
                raise ValueError("expected_sum must be finite")
            values = tables[name].values
            if not isinstance(sum_axis, int) or not -values.ndim <= sum_axis < values.ndim:
                raise ValueError("sum_axis is out of range")
            complete = np.isfinite(values).all(axis=sum_axis)
            sums = values.sum(axis=sum_axis)
            mismatches = complete & ~np.isclose(sums, target, rtol=0.0, atol=sum_atol)
            for index in np.argwhere(mismatches):
                coordinate = tuple(int(i) for i in index)
                actual = float(sums[coordinate])
                findings.append(Finding("sum_mismatch", "Complete values do not sum to the explicitly supplied expected total.",
                                        (f"{name}:sum_axis={sum_axis}[{coordinate}]",),
                                        {"expected": float(target), "actual": actual, "difference": actual - float(target), "atol": sum_atol,
                                         "components": np.asarray(np.take(values, coordinate[0], axis=0) if values.ndim == 2 and sum_axis in (1, -1) else []).tolist()}))
    eligible_count = 0
    for name, table in tables.items():
        for line in _lines(name, table):
            if selected_axes is not None and line.axis not in selected_axes:
                continue
            if np.isfinite(line.values).sum() < min_samples:
                continue
            eligible_count += 1
            if len(series) >= max_series:
                continue
            series.append(line)
            profile, found = _profile(line, min_samples=min_samples, max_decimals=max_decimals, rtol=rtol, atol=atol)
            profiles.append(profile)
            findings.extend(found)
    groups = defaultdict(list)
    for line in series:
        groups[len(line.values)].append(line)
    eligible_pairs = sum(len(lines) * (len(lines) - 1) // 2 for lines in groups.values())
    checked, within_axes, cross_axes, cross_datasets = 0, 0, 0, 0
    # Round-robin across length groups avoids spending the entire budget on
    # just the first (e.g. row) dimension of a large table.
    iterators = [iter(combinations(lines, 2)) for _, lines in sorted(groups.items()) if len(lines) > 1]
    while iterators and checked < max_pairs:
        active = []
        for iterator in iterators:
            if checked >= max_pairs:
                break
            try:
                left, right = next(iterator)
            except StopIteration:
                continue
            active.append(iterator)
            checked += 1
            cross_axes += int(left.axis != right.axis)
            within_axes += int(left.axis == right.axis)
            cross_datasets += int(left.dataset != right.dataset)
            findings.extend(_pair(left, right, min_samples=min_samples, max_decimals=max_decimals,
                                  tail_digits=tail_digits, match_fraction=match_fraction,
                                  grid_fraction=grid_fraction, rtol=rtol, atol=atol))
        iterators = active
    if eligible_count > len(series):
        notes.append(f"Series budget reached: {eligible_count - len(series)} eligible lines not profiled.")
    if checked < eligible_pairs:
        notes.append(f"Pair budget reached: {eligible_pairs - checked} equal-length pairs not compared.")
    if not profiles:
        notes.append(f"No axis line has at least {min_samples} finite samples; reduce min_samples or select a larger numeric block.")
    notes.extend([
        f"Digit inspection uses at most {max_decimals} decimal places; CSV lexical zeros are retained up to this limit.",
        "Equal length does not imply scientific comparability; inspect the recorded axis/dataset coordinates and panel labels.",
        "Rounding, repeated measurements, units, and derived quantities may explain reported relationships.",
    ])
    # Put review leads before routine precision information in short summaries.
    findings.sort(key=lambda finding: finding.severity == "info")
    return Report({name: table.values.shape for name, table in tables.items()}, profiles, findings,
                  {"eligible_series": eligible_count, "profiled_series": len(series),
                   "eligible_pairs": eligible_pairs, "checked_pairs": checked,
                   "within_axis_pairs": within_axes, "cross_axis_pairs": cross_axes,
                   "cross_dataset_pairs": cross_datasets}, list(dict.fromkeys(notes)), conclusions)
