import math
from fractions import Fraction

import pytest

from counted_float._core.benchmarking.flops._sumprod_port import _dl_sum, tl_fma, tl_to_d
from counted_float._core.compatibility import is_numba_importable

# The TripleLength port only reproduces math.sumprod bit-for-bit when it can spell a genuine FMA
# (numba's llvm.fma intrinsic, or math.fma from Py3.13+) and a reference is available to compare
# against (math.sumprod, Py3.12+). Without a genuine FMA the fold degrades to the double-rounded
# x*y+z, which is documented as unusable; skip rather than assert against it.
_needs_reference_and_fma = pytest.mark.skipif(
    not (hasattr(math, "sumprod") and (is_numba_importable() or hasattr(math, "fma"))),
    reason="needs math.sumprod (Py3.12+) as reference and a genuine FMA (numba, or math.fma / Py3.13+)",
)


def _triplelength_sumprod(xs: list[float], ys: list[float]) -> float:
    """Reproduce math.sumprod(xs, ys) through the ported TripleLength fold and close-out."""
    hi, lo, tiny = 0.0, 0.0, 0.0
    for x, y in zip(xs, ys, strict=True):
        hi, lo, tiny = tl_fma(x, y, hi, lo, tiny)
    return tl_to_d(hi, lo, tiny)


@pytest.mark.parametrize(
    ("a", "b"),
    [
        (0.1, 0.2),  # sum is not exactly representable -> non-zero low term
        (1.0, 2.0**-53),  # the low bit falls off the top part
        (1e16, 1.0),  # widely separated magnitudes
        (-1e300, 1e-300),  # extreme magnitude gap
        (0.3, -0.7),  # cancellation
        (1.0, 3.0),  # exact sum -> low term is zero
        (2.0**53, 1.0),  # boundary of integer exactness
    ],
)
def test_dl_sum_is_an_exact_two_sum(a: float, b: float):
    """The high part is the rounded sum and (hi + lo) recovers a + b exactly (two-sum invariant)."""
    # --- act ---------------------------------------------
    hi, lo = _dl_sum(a, b)

    # --- assert ------------------------------------------
    assert hi == a + b  # hi is fl(a + b), the rounded sum
    assert Fraction(hi) + Fraction(lo) == Fraction(a) + Fraction(b)  # exact: lo captures every dropped bit


@_needs_reference_and_fma
@pytest.mark.parametrize(
    ("xs", "ys"),
    [
        ([1.0, 2.0, 3.0, 4.0], [5.0, 6.0, 7.0, 8.0]),  # well-conditioned, exact products
        ([0.1, 0.2, 0.3], [0.4, 0.5, 0.6]),  # rounded products, non-trivial compensation
        ([1e16, 1.0, -1e16, 1.0], [1.0, 1.0, 1.0, 1.0]),  # small terms a naive sum would drop
    ],
)
def test_triplelength_port_matches_sumprod(xs: list[float], ys: list[float]):
    """The fold + close-out reproduce CPython's math.sumprod bit-for-bit."""
    # --- act ---------------------------------------------
    result = _triplelength_sumprod(xs, ys)

    # --- assert ------------------------------------------
    assert result == math.sumprod(xs, ys)


@_needs_reference_and_fma
@pytest.mark.parametrize(
    ("xs", "ys"),
    [
        ([1e17, 1.0, -1e17], [1.0, 1.0, 1.0]),  # true sum 1.0; a naive sum collapses to 0.0
        ([1.0, 1e100, 1.0, -1e100], [1.0, 1.0, 1.0, 1.0]),  # true sum 2.0 under massive cancellation
    ],
)
def test_triplelength_port_matches_sumprod_under_cancellation(xs: list[float], ys: list[float]):
    """The low/tiny compensation terms are decisive here, so a sign/paren mutant would diverge."""
    # --- act ---------------------------------------------
    result = _triplelength_sumprod(xs, ys)

    # --- assert ------------------------------------------
    assert result == math.sumprod(xs, ys)
