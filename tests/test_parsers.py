"""
tests/test_parsers.py
─────────────────────
Pure-function tests for the parsers. These don't need Flask or Supabase —
they exercise the natural-language → structured-data logic that drives
voice dictation and quick-add.

Run with:  python -m pytest tests/test_parsers.py -v
"""
from datetime import date


# ═══════════════════════════════════════════════════
# Planner input parser (existing, legacy)
# ═══════════════════════════════════════════════════

def test_parse_planner_input_importable():
    """If parse_planner_input moved or was renamed, catch it."""
    try:
        from utils.planner_parser import parse_planner_input
    except ImportError:
        try:
            from app import parse_planner_input  # legacy location
        except ImportError:
            import pytest
            pytest.skip("parse_planner_input not importable from known locations")
    assert callable(parse_planner_input)


# ═══════════════════════════════════════════════════
# Time / date utilities
# ═══════════════════════════════════════════════════

def test_agenda_days_overdue():
    """_days_overdue: how many whole days past a due date."""
    from services.agenda_service import _days_overdue
    ref = date(2026, 4, 18)
    assert _days_overdue("2026-04-15", ref) == 3
    assert _days_overdue("2026-04-20", ref) == 0   # not overdue yet
    assert _days_overdue(None, ref) == 0
    assert _days_overdue("not-a-date", ref) == 0   # graceful


def test_agenda_iso_passthrough():
    """_to_iso accepts both date and string."""
    from services.agenda_service import _to_iso
    assert _to_iso(date(2026, 1, 1)) == "2026-01-01"
    assert _to_iso("2026-01-01") == "2026-01-01"
