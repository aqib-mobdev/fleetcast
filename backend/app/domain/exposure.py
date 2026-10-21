from dataclasses import dataclass, field

from app.domain.severity import Level


@dataclass
class Ledger:
    clear_mi: float = 0.0
    caution_mi: float = 0.0
    warning_mi: float = 0.0
    severe_mi: float = 0.0
    no_go_mi: float = 0.0
    unrated_mi: float = 0.0
    total_mi: float = 0.0
    mean_score: float | None = None
    worst: Level | None = None
    by_level: dict = field(default_factory=dict)

    def payload(self) -> dict:
        return {
            "clear_mi": round(self.clear_mi, 1),
            "caution_mi": round(self.caution_mi, 1),
            "warning_mi": round(self.warning_mi, 1),
            "severe_mi": round(self.severe_mi, 1),
            "no_go_mi": round(self.no_go_mi, 1),
            "unrated_mi": round(self.unrated_mi, 1),
            "total_mi": round(self.total_mi, 1),
            "mean_score": None if self.mean_score is None else round(self.mean_score, 3),
            "worst": None if self.worst is None else self.worst.code,
            "worst_label": None if self.worst is None else self.worst.label,
            "unrated_ratio": round(self.unrated_mi / self.total_mi, 4) if self.total_mi else 0.0,
        }


def ledger_for(miles: list[float], levels: list[Level | None], total_mi: float) -> Ledger:
    buckets = dict.fromkeys(Level, 0.0)
    ledger = Ledger(total_mi=total_mi)

    for left, right, a, b in zip(miles, miles[1:], levels, levels[1:], strict=False):
        span = max(0.0, right - left)
        if a is None or b is None:
            ledger.unrated_mi += span
        else:
            buckets[max(a, b)] += span

    ledger.clear_mi = buckets[Level.CLEAR]
    ledger.caution_mi = buckets[Level.CAUTION]
    ledger.warning_mi = buckets[Level.WARNING]
    ledger.severe_mi = buckets[Level.SEVERE]
    ledger.no_go_mi = buckets[Level.NO_GO]
    ledger.by_level = {level.code: round(value, 1) for level, value in buckets.items() if value > 0}

    rated_mi = total_mi - ledger.unrated_mi
    if rated_mi > 0.0001:
        score = sum(float(level) * mi for level, mi in buckets.items()) / rated_mi
        ledger.mean_score = score
        if any(mi > 0 for mi in buckets.values()):
            ledger.worst = max(level for level, mi in buckets.items() if mi > 0)
    return ledger
