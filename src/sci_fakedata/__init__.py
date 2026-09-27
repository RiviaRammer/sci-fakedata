"""Synthetic data generation and local numerical-pattern analysis."""

from . import analyze, gen
from .io import load, load_all
from .report import Finding, Report

__version__ = "0.1.3"
__all__ = ["analyze", "gen", "load", "load_all", "Finding", "Report"]
