"""Risk level, shortfall type and reasons for each course. Deterministic: same numbers in, same answer out.

The Phase 5 agent reads ``shortfall_type`` and ``reasons`` to decide which kind of fix to propose,
so they are structured data first and text second.
"""
from datetime import timedelta

from app.services.forecasting import CourseForecast
from app.services.tracking import TrackingFacts, breakdown_from_facts

# --- Thresholds -------------------------------------------------------------------------
P_HIGH = 0.40  # P(hit target) below this is high risk
PROJECTED_HIGH = 0.90  # projected below this share of target is high risk
P_MEDIUM = 0.75  # P(hit target) below this is medium risk
MIN_WEEKS_FOR_FLAG = 4  # closed weeks needed before we trust a flag
GROUP_GAP_POINTS = 15.0  # a group this many completion-% points behind the best group is a "group gap"
MIN_GROUP_SIZE = 15  # ignore groups with fewer active drivers than this (too small to read)
SHOW_GAP = 0.05  # show rate this far below the fleet is worth a reason
RECENT_CANCEL_WEEKS = 6
BEHIND_PACE_SHARE = 0.05  # behind pace by more than this share of target is worth a reason
MAX_REASONS = 4

RISK_ORDER = {"high": 0, "medium": 1, "low": 2, "achieved": 3, "insufficient_data": 4}
AT_RISK = ("medium", "high")


def classify_risk(
    attended: int, target: int, projected: float, p_hit: float, weeks_observed: int, completed_sessions: int,
) -> str:
    """'achieved', 'high', 'medium', 'low' or 'insufficient_data'.

    - achieved: already at or above target (always wins);
    - insufficient_data: fewer than MIN_WEEKS_FOR_FLAG closed weeks this year, or the course has not run a
      single session yet (the forecast is still shown, but no alert is opened);
    - high: P(hit) < 0.40 or projected < 90% of target;
    - medium: P(hit) < 0.75 or projected < target;
    - low: otherwise.
    """
    if attended >= target:
        return "achieved"
    if weeks_observed < MIN_WEEKS_FOR_FLAG or completed_sessions == 0:
        return "insufficient_data"
    if p_hit < P_HIGH or projected < PROJECTED_HIGH * target:
        return "high"
    if p_hit < P_MEDIUM or projected < target:
        return "medium"
    return "low"


def classify_shortfall(risk: str, p_show: float, attended: int, target: int, remaining_seats: int, pool: int) -> tuple[str, float]:
    """(shortfall type, seats needed). Tells the agent which tool to reach for.

    seats_needed = (target − attended) ÷ p_show: seats we must fill to get enough people through the door.
    - pool_gap: fewer eligible drivers are left than completions still needed. Fix = review the target.
    - capacity_gap: even if every remaining seat is filled there are too few. Fix = add sessions.
    - attendance_gap: enough seats exist but low fill or show-up means they will not convert.
      Fix = fill empty seats / move drivers to better slots.
    - none: risk is low, achieved or unknown.
    """
    need = max(0, target - attended)
    seats_needed = need / p_show if p_show > 0 else float("inf")
    if risk not in AT_RISK:
        return "none", seats_needed
    if pool < need:
        return "pool_gap", seats_needed
    if remaining_seats < seats_needed:
        return "capacity_gap", seats_needed
    return "attendance_gap", seats_needed


def _reason(code: str, message: str, value: float, benchmark: float, impact: float, **extra) -> dict:
    return {"code": code, "message": message, "value": round(value, 3), "benchmark": round(benchmark, 3),
            "impact": round(impact, 1), **extra}


def build_reasons(facts: TrackingFacts, fc: CourseForecast) -> list[dict]:
    """Facts that explain the risk, biggest impact (in completions) first, at most MAX_REASONS.

    Each reason is ``{code, message, value, benchmark, impact}``. Codes: low_show_rate, group_gap,
    recent_cancellations, capacity_short, pool_short, behind_pace and the fallback projected_shortfall.
    """
    reasons: list[dict] = []
    need = max(0, fc.target - fc.attended)

    if fc.fleet_show - fc.p_show >= SHOW_GAP:
        impact = fc.expected_attempts * (fc.fleet_show - fc.p_show)
        reasons.append(_reason(
            "low_show_rate", f"Show-up rate {fc.p_show:.0%} vs fleet {fc.fleet_show:.0%}", fc.p_show, fc.fleet_show, impact,
        ))

    groups = [g for g in breakdown_from_facts(facts, fc.course_id, "shift") if g["active_drivers"] >= MIN_GROUP_SIZE]
    if len(groups) >= 2:
        best, worst = groups[0], groups[-1]  # sorted by completion %, best first
        if best["completion_pct"] - worst["completion_pct"] > GROUP_GAP_POINTS:
            gap = best["completion_pct"] - worst["completion_pct"]
            reasons.append(_reason(
                "group_gap",
                f"{worst['group'].capitalize()} shift completion {worst['completion_pct']:.0f}% "
                f"vs {best['group']} {best['completion_pct']:.0f}%",
                worst["completion_pct"], best["completion_pct"], gap / 100 * worst["active_drivers"],
                group=worst["group"], by="shift",
            ))

    cutoff = facts.now - timedelta(weeks=RECENT_CANCEL_WEEKS)
    cancelled = [s for s in facts.sessions_of(fc.course_id) if s.status == "cancelled" and s.start_time >= cutoff]
    if cancelled:
        seats = sum(s.capacity for s in cancelled)
        reasons.append(_reason(
            "recent_cancellations",
            f"{len(cancelled)} session{'s' if len(cancelled) != 1 else ''} ({seats} seats) cancelled in the last "
            f"{RECENT_CANCEL_WEEKS} weeks",
            len(cancelled), 0, seats * fc.p_fill * fc.p_show,
        ))

    seats_needed = need / fc.p_show if fc.p_show > 0 else float("inf")
    if fc.remaining_seats < seats_needed and fc.eligible_pool >= need:
        reasons.append(_reason(
            "capacity_short",
            f"Only {fc.remaining_seats} seats left but ~{seats_needed:.0f} needed at current show-up rate",
            fc.remaining_seats, seats_needed, (seats_needed - fc.remaining_seats) * fc.p_show,
        ))

    if fc.eligible_pool < need:
        reasons.append(_reason(
            "pool_short",
            f"Only {fc.eligible_pool} eligible drivers left but {need} more completions needed",
            fc.eligible_pool, need, need - fc.eligible_pool,
        ))

    if fc.pace_gap < -BEHIND_PACE_SHARE * fc.target:
        reasons.append(_reason(
            "behind_pace", f"{-fc.pace_gap:.0f} completions behind target pace", fc.pace_gap, 0, -fc.pace_gap,
        ))

    reasons.sort(key=lambda r: -r["impact"])
    reasons = reasons[:MAX_REASONS]
    if not reasons:  # always say something for an at-risk course
        reasons.append(_reason(
            "projected_shortfall", f"Projected {fc.projected:.0f} vs target {fc.target}", fc.projected, fc.target,
            max(0.0, fc.target - fc.projected),
        ))
    return reasons


def assess(facts: TrackingFacts, fc: CourseForecast) -> CourseForecast:
    """Fill in risk_level, shortfall_type, seats_needed and reasons on a forecast."""
    fc.risk_level = classify_risk(fc.attended, fc.target, fc.projected, fc.p_hit, fc.weeks_observed, fc.completed_sessions)
    fc.shortfall_type, fc.seats_needed = classify_shortfall(
        fc.risk_level, fc.p_show, fc.attended, fc.target, fc.remaining_seats, fc.eligible_pool,
    )
    fc.reasons = build_reasons(facts, fc) if fc.risk_level in AT_RISK else []
    return fc
