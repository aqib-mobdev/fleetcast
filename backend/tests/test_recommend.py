from app.domain.exposure import Ledger
from app.domain.recommend import decide


def ledger(severe=0.0, warning=0.0, no_go=0.0, unrated=0.0, total=None, mean=None):
    if total is None:
        total = severe + warning + 100 + no_go + unrated
    if mean is None:
        mean = (severe * 3 + warning * 2 + no_go * 4) / (total - unrated) if total > unrated else None
    return Ledger(
        severe_mi=severe,
        warning_mi=warning,
        no_go_mi=no_go,
        unrated_mi=unrated,
        total_mi=total,
        mean_score=mean,
        worst=None,
    )


def test_fewest_severe_wins():
    verdict = decide({"A": ledger(severe=4), "B": ledger(severe=18)}, {"A": 300, "B": 300})
    assert verdict.route == "A"
    assert verdict.safe is True


def test_warning_breaks_severe_tie():
    verdict = decide({"A": ledger(severe=5, warning=30), "B": ledger(severe=5, warning=8)}, {"A": 300, "B": 300})
    assert verdict.route == "B"


def test_mean_breaks_high_and_severe_ties():
    verdict = decide(
        {"A": ledger(severe=5, warning=10, mean=2.2), "B": ledger(severe=5, warning=10, mean=1.4)},
        {"A": 300, "B": 300},
    )
    assert verdict.route == "B"


def test_duration_breaks_full_tie():
    verdict = decide(
        {"A": ledger(severe=5, warning=10, mean=1.5), "B": ledger(severe=5, warning=10, mean=1.5)},
        {"A": 360, "B": 280},
    )
    assert verdict.route == "B"
    assert "Travel time" in verdict.summary


def test_no_go_route_is_excluded():
    verdict = decide({"A": ledger(), "B": ledger(no_go=12)}, {"A": 400, "B": 360})
    assert verdict.route == "A"
    assert verdict.order[-1] == "B"


def test_all_no_go_returns_no_route():
    verdict = decide({"A": ledger(no_go=40), "B": ledger(no_go=10)}, {"A": 300, "B": 300})
    assert verdict.route is None
    assert verdict.safe is False
    assert verdict.fallback == "B"
    assert "No-Go" in verdict.summary


def test_all_unrated_is_not_called_safe():
    verdict = decide({"A": ledger(unrated=100, total=100), "B": ledger(unrated=120, total=120)}, {"A": 300, "B": 300})
    assert verdict.safe is False
    assert verdict.route is None
    assert "no route can be rated" in verdict.summary


def test_unrated_route_is_excluded_when_others_are_rated():
    verdict = decide({"A": ledger(unrated=100, total=100), "B": ledger(severe=1)}, {"A": 200, "B": 300})
    assert verdict.route == "B"
