"""Small, reproducible generators; conclusions are user-supplied metadata."""

from __future__ import annotations

import operator
from typing import Any

import numpy as np


class SyntheticArray(np.ndarray):
    """A NumPy array labelled as synthetic, with optional declared conclusion.

    A conclusion is stored verbatim. It is not inferred or statistically
    verified, and does not influence the random samples.
    """

    def __new__(cls, values: Any, *, conclusion: str | None = None):
        obj = np.asarray(values, dtype=float).view(cls)
        obj.synthetic = True
        obj.conclusion = conclusion
        return obj

    def __array_finalize__(self, parent):
        if parent is not None:
            self.synthetic = getattr(parent, "synthetic", True)
            self.conclusion = getattr(parent, "conclusion", None)


def _shape(n: int | tuple[int, ...]) -> tuple[int, ...]:
    sizes = n if isinstance(n, tuple) else (n,)
    if not sizes:
        raise ValueError("n must specify at least one dimension")
    try:
        shape = tuple(operator.index(value) for value in sizes)
    except TypeError as exc:
        raise ValueError("n must be an integer or tuple of integers") from exc
    if any(isinstance(value, (bool, np.bool_)) for value in sizes):
        raise ValueError("n must not contain booleans")
    if any(value < 0 for value in shape):
        raise ValueError("dimensions must be non-negative")
    return shape


def _finite(**values: float) -> None:
    if not all(np.isfinite(value) for value in values.values()):
        raise ValueError("parameters must be finite")


def normal(n=1000, mean=0.0, std=1.0, seed=None, *, conclusion=None):
    """Generate independent normal samples; n may be a multidimensional shape."""
    _finite(mean=mean, std=std)
    if std < 0:
        raise ValueError("std must be non-negative")
    values = np.random.default_rng(seed).normal(mean, std, size=_shape(n))
    return SyntheticArray(values, conclusion=conclusion)


def uniform(n=1000, low=0.0, high=1.0, seed=None, *, conclusion=None):
    """Generate independent uniform samples."""
    _finite(low=low, high=high)
    if high <= low:
        raise ValueError("high must be greater than low")
    values = np.random.default_rng(seed).uniform(low, high, size=_shape(n))
    return SyntheticArray(values, conclusion=conclusion)


def error(n=1000, systematic=0.0, std=1.0, seed=None):
    """Return systematic bias + independent Gaussian white noise.

    std is the standard deviation of the random component. White describes
    independence of that component, not an exactly flat finite-sample FFT.
    """
    return normal(n=n, mean=systematic, std=std, seed=seed)


def white_noise(n=1000, std=1.0, seed=None):
    """Zero-mean independent Gaussian noise."""
    return error(n=n, std=std, seed=seed)


def red_noise(n=1000, alpha=0.9, std=1.0, seed=None, *, conclusion=None):
    """Stationary AR(1) noise along the last axis (positive autocorrelation)."""
    _finite(alpha=alpha, std=std)
    if not 0 < alpha < 1:
        raise ValueError("alpha must be between 0 and 1")
    if std < 0:
        raise ValueError("std must be non-negative")
    shape = _shape(n)
    samples = np.random.default_rng(seed).normal(size=shape)
    result = np.empty(shape, dtype=float)
    if shape[-1]:
        result[..., 0] = samples[..., 0] * std
        innovation = std * np.sqrt(1 - alpha**2)
        for index in range(1, shape[-1]):
            result[..., index] = alpha * result[..., index - 1] + innovation * samples[..., index]
    return SyntheticArray(result, conclusion=conclusion)

