import pytest

from app.domain.exposure import Ledger, ledger_for
from app.domain.severity import Level as L


def test_interval_attribution_and_mean():
    ledger = ledger_for([0, 20, 40, 60, 100], [L.CLEAR, L.WARNING, L.SEVERE, L.CLEAR, L.CLEAR], 100)
    assert ledger.warning_mi == pytest.approx(20)
    assert ledger.severe_mi == pytest.approx(40)
    assert ledger.clear_mi == pytest.approx(40)
    assert ledger.mean_score == pytest.approx((20 * 2 + 40 * 3) / 100)
    assert ledger.worst is L.SEVERE


def test_miles_conserved_across_intervals():
    for interval, levels in [
        (10, [L.CAUTION if i % 3 == 0 else L.CLEAR for i in range(11)]),
        (25, [L.CAUTION if i % 3 == 0 else L.CLEAR for i in range(5)]),
        (50, [L.CAUTION if i % 3 == 0 else L.CLEAR for i in range(3)]),
    ]:
        marks = list(range(0, 101, interval))
        if marks[-1] != 100:
            marks.append(100)
        levels = levels[: len(marks)]
        ledger = ledger_for(marks, levels, 100)
        total = (
            ledger.clear_mi
            + ledger.caution_mi
            + ledger.warning_mi
            + ledger.severe_mi
            + ledger.no_go_mi
            + ledger.unrated_mi
        )
        assert total == pytest.approx(100)


def test_unrated_endpoints_are_not_clear():
    ledger = ledger_for([0, 40, 70, 100], [None, L.CLEAR, None, L.WARNING], 100)
    assert ledger.unrated_mi == pytest.approx(100)
    assert ledger.clear_mi == 0
    assert ledger.mean_score is None
    assert ledger.worst is None


def test_partial_unrated_excluded_from_mean():
    ledger = ledger_for([0, 30, 100], [L.CLEAR, L.CLEAR, None], 100)
    assert ledger.clear_mi == pytest.approx(30)
    assert ledger.unrated_mi == pytest.approx(70)
    assert ledger.mean_score == pytest.approx(0)


def test_no_go_tracked_separately():
    ledger = ledger_for([0, 20, 50], [L.SEVERE, L.NO_GO, L.CLEAR], 50)
    assert ledger.no_go_mi == pytest.approx(50)
    assert ledger.worst is L.NO_GO
    assert ledger.payload()["no_go_mi"] == 50.0


def test_payload_fields():
    ledger = Ledger(total_mi=10, clear_mi=10)
    row = ledger.payload()
    for field in ("clear_mi", "caution_mi", "warning_mi", "severe_mi", "no_go_mi", "unrated_mi", "total_mi"):
        assert field in row
