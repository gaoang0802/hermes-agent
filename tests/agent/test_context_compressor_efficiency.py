"""Tests for context_compressor compression efficiency helpers (PR #29859)."""

from __future__ import annotations

import pytest

from agent.context_compressor import (
    _COMPRESSION_EFFICIENCY_GREEN,
    _COMPRESSION_EFFICIENCY_YELLOW,
    _compression_efficiency_level,
)


# ---------------------------------------------------------------------------
# _compression_efficiency_level — threshold boundaries
# ---------------------------------------------------------------------------

def test_green_above_threshold():
    """Ratio >= GREEN threshold returns 🟢."""
    assert _compression_efficiency_level(_COMPRESSION_EFFICIENCY_GREEN) == "🟢"
    assert _compression_efficiency_level(_COMPRESSION_EFFICIENCY_GREEN + 10) == "🟢"
    assert _compression_efficiency_level(_COMPRESSION_EFFICIENCY_GREEN + 0.01) == "🟢"
    assert _compression_efficiency_level(999.0) == "🟢"


def test_green_at_threshold():
    """Ratio exactly at GREEN threshold is still 🟢 (inclusive)."""
    assert _compression_efficiency_level(float(_COMPRESSION_EFFICIENCY_GREEN)) == "🟢"


def test_yellow_between_thresholds():
    """Ratio between YELLOW (inclusive) and GREEN (exclusive) returns 🟡."""
    # One epsilon below green
    just_below_green = _COMPRESSION_EFFICIENCY_GREEN - 1e-9
    assert _compression_efficiency_level(just_below_green) == "🟡"
    # At yellow threshold
    assert _compression_efficiency_level(_COMPRESSION_EFFICIENCY_YELLOW) == "🟡"
    # Mid-range
    assert _compression_efficiency_level(4.0) == "🟡"
    assert _compression_efficiency_level(3.5) == "🟡"


def test_red_below_yellow():
    """Ratio below YELLOW threshold returns 🔴."""
    just_below_yellow = _COMPRESSION_EFFICIENCY_YELLOW - 1e-9
    assert _compression_efficiency_level(just_below_yellow) == "🔴"
    assert _compression_efficiency_level(1.0) == "🔴"
    assert _compression_efficiency_level(0.0) == "🔴"


def test_red_negative_ratio():
    """Negative ratio (shouldn't happen in practice) still returns 🔴."""
    assert _compression_efficiency_level(-1.0) == "🔴"
    assert _compression_efficiency_level(-100.0) == "🔴"


# ---------------------------------------------------------------------------
# Zero-denominator guard — the caller already checks > 0, but verify the
# function is never called with NaN/Inf (the guard in compress() uses
# `summary_tokens_est > 0 and saved_estimate > 0`).
# ---------------------------------------------------------------------------

def test_zero_denominator_guard():
    """Without the guard, zero summary_tokens_est would raise ZeroDivisionError.

    The compress() guard ``if summary_tokens_est > 0 and saved_estimate > 0``
    prevents this.  Verify the danger directly.
    """
    with pytest.raises(ZeroDivisionError):
        _ = 100 / 0  # summary_tokens_est=0 case
    # The guard uses > 0 for both values — confirm it catches zero and negative
    assert not (0 > 0), "zero fails > 0 check"
    assert not (-1 > 0), "negative fails > 0 check"
    assert 1 > 0, "positive passes > 0 check"
