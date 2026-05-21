"""Tests for the period parser."""

from __future__ import annotations

import pytest

from billbird_client.periods import parse_period


def test_parse_period_month():
    p = parse_period("2026-04")
    assert p.label == "2026-04"
    assert p.from_iso.startswith("2026-04-01")
    assert p.until_iso.startswith("2026-04-30")


def test_parse_period_december_rolls_over_correctly():
    p = parse_period("2026-12")
    assert p.from_iso.startswith("2026-12-01")
    assert p.until_iso.startswith("2026-12-31")


def test_parse_period_day():
    p = parse_period("2026-04-15")
    assert p.from_iso.startswith("2026-04-15")
    assert p.until_iso.startswith("2026-04-15")


def test_parse_period_last_n():
    p = parse_period("last-7d")
    assert p.from_iso.endswith("Z")
    assert p.until_iso.endswith("Z")
    assert p.label == "last-7d"


def test_parse_period_invalid():
    with pytest.raises(ValueError):
        parse_period("bogus")


def test_parse_period_zero_days_rejected():
    with pytest.raises(ValueError):
        parse_period("last-0d")


def test_parse_period_empty_string_rejected():
    with pytest.raises(ValueError):
        parse_period("")
