"""Regression tests for the generated top-of-site download decision table (no network)."""

import importlib.util
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_build_site():
    spec = importlib.util.spec_from_file_location("build_site", ROOT / "scripts" / "build_site.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_decision_board_marks_every_generated_tiff_not_ok():
    bs = _load_build_site()
    html_block, md = bs.decision_board()
    assert "NOT OK TO SUBMIT" in md
    assert "NOT OK TO SUBMIT" in html_block
    # Every new-TIFF row must say NOT OK; nothing may be marked as a submit-ready file.
    assert "Gates pass" not in md
    assert "H28-6 gravity persistence" in md
    assert "H33-1 buried-step complement" in md


def test_decision_board_lists_all_nine_historical_sites_as_not_new():
    bs = _load_build_site()
    _, md = bs.decision_board()
    for site in ("GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30",
                 "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36"):
        assert re.search(rf"\| {site} historical best \|", md), site
    assert md.count("do not resubmit") == 9


def test_decision_board_table_rows_have_five_cells():
    bs = _load_build_site()
    _, md = bs.decision_board()
    rows = [line for line in md.splitlines() if line.startswith("| ") and "historical" in line
            or line.startswith("| GEMSDOE27 H")]
    assert rows
    for line in rows:
        # A raw "|" inside a cell would split it; the rendered table must keep exactly 5 cells.
        assert line.count(" | ") == 4, line[:120]
