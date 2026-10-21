from dataclasses import dataclass

from app.domain.exposure import Ledger


@dataclass
class Verdict:
    route: str | None
    safe: bool
    summary: str
    order: list[str]
    fallback: str | None

    def payload(self) -> dict:
        return {
            "route": self.route,
            "safe": self.safe,
            "summary": self.summary,
            "order": self.order,
            "fallback": self.fallback,
        }


def _mean(ledger: Ledger) -> float:
    return ledger.mean_score if ledger.mean_score is not None else float("inf")


def decide(ledgers: dict[str, Ledger], minutes: dict[str, float]) -> Verdict:
    eligible = {
        k: v
        for k, v in ledgers.items()
        if v.no_go_mi <= 0.001 and v.unrated_mi < v.total_mi - 0.001
    }

    if eligible:
        order = sorted(
            eligible,
            key=lambda k: (
                round(eligible[k].severe_mi, 2),
                round(eligible[k].warning_mi, 2),
                _mean(eligible[k]),
                minutes.get(k, float("inf")),
            ),
        )
        winner = order[0]
        best = eligible[winner]
        runner = eligible[order[1]] if len(order) > 1 else None
        summary = _summary(winner, best, runner, minutes)
        return Verdict(
            route=winner,
            safe=True,
            summary=summary,
            order=order + [k for k in ledgers if k not in eligible],
            fallback=None,
        )

    order = sorted(
        ledgers,
        key=lambda k: (
            round(ledgers[k].no_go_mi, 2),
            round(ledgers[k].severe_mi, 2),
            round(ledgers[k].warning_mi, 2),
            round(ledgers[k].unrated_mi, 2),
            _mean(ledgers[k]),
            minutes.get(k, float("inf")),
        ),
    )
    least = order[0]
    everything_unrated = all(v.unrated_mi >= v.total_mi - 0.001 for v in ledgers.values())
    if everything_unrated:
        summary = (
            "Weather data is unavailable for this corridor, so no route can be rated. "
            f"Route {least} is shown for reference only; do not dispatch on this assessment."
        )
    else:
        summary = (
            "Every alternative includes No-Go conditions. "
            f"Route {least} has the least exposure ({ledgers[least].no_go_mi:.1f} mi). "
            "Delay departure or re-check the corridor before dispatching."
        )
    return Verdict(route=None, safe=False, summary=summary, order=order, fallback=least)


def _summary(winner: str, best: Ledger, runner: Ledger | None, minutes: dict[str, float]) -> str:
    if best.severe_mi > 0.05:
        text = f"Route {winner} has the least Severe exposure ({best.severe_mi:.1f} mi)."
    else:
        text = f"Route {winner} avoids Severe conditions."

    if runner is not None:
        if abs(runner.severe_mi - best.severe_mi) < 0.05 and runner.warning_mi > best.warning_mi + 0.05:
            text += f" It also has fewer Warning miles ({best.warning_mi:.1f} vs {runner.warning_mi:.1f})."
        elif abs(runner.warning_mi - best.warning_mi) < 0.05 and _mean(runner) > _mean(best) + 0.01:
            text += f" Lower mean risk ({_mean(best):.2f} vs {_mean(runner):.2f})."
        elif abs(_mean(runner) - _mean(best)) < 0.01:
            text += (
                f" Travel time decided it: {minutes.get(winner, 0):.0f} min."
            )

    if best.unrated_mi > 0:
        share = best.unrated_mi / best.total_mi if best.total_mi else 0
        text += f" {share:.0%} of the route is unrated because forecast data is missing."
    return text
