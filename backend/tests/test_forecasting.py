"""Forecast maths and risk rules on tiny hand-built inputs (no database)."""
import math
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from app.services import forecasting as fc
from app.services.risk import classify_risk, classify_shortfall

NOW = datetime(2026, 3, 1)


def sess(days_ahead, capacity=10, booked=0):
    return SimpleNamespace(start_time=NOW + timedelta(days=days_ahead), capacity=capacity, booked=booked)


# --- Projection maths -------------------------------------------------------------------
def test_no_remaining_sessions_projection_is_attended():
    p = fc.project(attended=50, target=100, pool=80, terms=[])
    assert p.projected == 50 and p.sigma == 0 and p.low == 50 and p.high == 50
    assert p.p_hit == 0.0  # sigma 0 and target not reached: exactly 0, no division by zero


def test_no_remaining_sessions_but_target_reached_is_certain():
    assert fc.project(attended=100, target=100, pool=80, terms=[]).p_hit == 1.0


def test_zero_variance_p_hit_is_zero_or_one():
    certain = [fc.SessionTerm(NOW, n=10, q=1.0, in_window=True)]  # everyone surely turns up: variance 0
    assert fc.project(attended=90, target=100, pool=50, terms=certain).p_hit == 1.0
    assert fc.project(attended=91, target=105, pool=50, terms=certain).p_hit == 0.0


def test_mean_variance_and_p_hit_formula():
    terms = [fc.SessionTerm(NOW, n=20, q=0.8, in_window=True)]  # mu 16, var 3.2
    p = fc.project(attended=10, target=26, pool=100, terms=terms, inflation=1.0)
    assert p.mu == pytest.approx(16) and p.sigma == pytest.approx(math.sqrt(3.2))
    assert p.projected == pytest.approx(26)
    # need 16, mean 16: P(X >= 16) with continuity correction is a bit above one half
    assert p.p_hit == pytest.approx(1 - fc.normal_cdf(-0.5 / math.sqrt(3.2)))
    assert p.low == pytest.approx(26 - 1.645 * math.sqrt(3.2)) and p.high == pytest.approx(26 + 1.645 * math.sqrt(3.2))


def test_inflation_widens_only_the_range():
    terms = [fc.SessionTerm(NOW, n=20, q=0.8, in_window=True)]
    narrow = fc.project(10, 26, 100, terms, inflation=1.0)
    wide = fc.project(10, 26, 100, terms, inflation=4.0)
    assert wide.projected == narrow.projected
    assert wide.sigma == pytest.approx(2 * narrow.sigma)


def test_pool_caps_projection_range_and_p_hit():
    terms = [fc.SessionTerm(NOW, n=100, q=0.9, in_window=False)]  # would add ~90
    p = fc.project(attended=10, target=60, pool=30, terms=terms)
    assert p.projected == 40 and p.high <= 40 and p.low >= 10
    assert p.p_hit == 0.0  # needs 50 more completions but only 30 eligible drivers remain


def test_cone_ends_at_the_projection():
    terms = fc.session_terms([sess(5, booked=8), sess(40), sess(120)], NOW, p_show=0.8, p_fill=0.9)
    proj = fc.project(attended=5, target=100, pool=200, terms=terms)
    cone = fc.forecast_cone(5, 200, terms, NOW)
    assert cone[-1]["forecast_mean"] == pytest.approx(proj.projected)
    assert cone[-1]["forecast_low"] == pytest.approx(proj.low) and cone[-1]["forecast_high"] == pytest.approx(proj.high)
    means = [c["forecast_mean"] for c in cone]
    assert means == sorted(means)  # cumulative, so never goes down


# --- Booked vs unbooked sessions --------------------------------------------------------
def test_booked_and_unbooked_sessions_use_the_right_n_and_q():
    terms = fc.session_terms([sess(5, capacity=10, booked=7), sess(40, capacity=12, booked=0)], NOW, p_show=0.8, p_fill=0.5)
    inside, beyond = terms
    assert inside.in_window and inside.n == 7 and inside.q == pytest.approx(0.8)  # booked people, show rate
    assert not beyond.in_window and beyond.n == 12 and beyond.q == pytest.approx(0.4)  # capacity, fill x show


def test_window_boundary_is_21_days():
    inside, outside = fc.session_terms([sess(20, booked=3), sess(21, booked=3)], NOW, 0.8, 0.5)
    assert inside.in_window and not outside.in_window


# --- Smoothing and shrinkage ------------------------------------------------------------
def test_ewma_weights_recent_weeks_more():
    hits, trials = fc.ewma_counts([(1, 1), (0, 1)], alpha=0.3)
    assert (hits, trials) == (pytest.approx(0.7), pytest.approx(1.7))


def test_shrinkage_pulls_a_tiny_sample_toward_the_fleet_rate():
    assert fc.shrunk_rate(hits=1, trials=1, fleet_rate=0.5) == pytest.approx(11 / 21)  # 1/1 raw, but trusted little
    assert fc.shrunk_rate(hits=0, trials=0, fleet_rate=0.8) == pytest.approx(0.8)  # no data: the fleet rate


def test_shrinkage_fades_with_lots_of_data():
    assert fc.shrunk_rate(hits=900, trials=1000, fleet_rate=0.5) == pytest.approx(0.9, abs=0.01)


def test_one_session_course_is_pulled_toward_fleet():
    one_session = fc.smoothed_rate([(0, 0), (8, 8)], fallback=0.8)  # 8 of 8 showed up
    assert 0.8 < one_session < 0.93


def test_smoothed_rate_without_data_is_the_fallback():
    assert fc.smoothed_rate([], fallback=0.85) == 0.85
    assert fc.smoothed_rate([(0, 0), (0, 0)], fallback=0.85) == 0.85


def test_normal_cdf():
    assert fc.normal_cdf(0) == pytest.approx(0.5)
    assert fc.normal_cdf(1.645) == pytest.approx(0.95, abs=0.001)


# --- Risk thresholds at their boundaries ------------------------------------------------
def risk(attended=50, target=100, projected=100.0, p_hit=0.9, weeks=10, sessions=5):
    return classify_risk(attended, target, projected, p_hit, weeks, sessions)


def test_achieved_wins():
    assert risk(attended=100, p_hit=0.0, projected=100) == "achieved"


def test_high_boundaries():
    assert risk(p_hit=0.399) == "high"
    assert risk(p_hit=0.40) == "medium"  # exactly 0.40 is not "below"
    assert risk(projected=89.9, p_hit=0.9) == "high"
    assert risk(projected=90.0, p_hit=0.9) == "medium"  # exactly 90% of target is not "below"


def test_medium_boundaries():
    assert risk(p_hit=0.749) == "medium"
    assert risk(p_hit=0.75, projected=100) == "low"
    assert risk(p_hit=0.9, projected=99.9) == "medium"


def test_insufficient_data():
    assert risk(weeks=3) == "insufficient_data"
    assert risk(weeks=4) == "low"
    assert risk(sessions=0) == "insufficient_data"
    assert risk(attended=100, weeks=0, sessions=0) == "achieved"


# --- Shortfall types --------------------------------------------------------------------
def test_pool_gap():
    assert classify_shortfall("high", 0.8, attended=50, target=100, remaining_seats=500, pool=30)[0] == "pool_gap"


def test_capacity_gap():
    kind, seats_needed = classify_shortfall("high", 0.8, attended=50, target=100, remaining_seats=40, pool=200)
    assert kind == "capacity_gap" and seats_needed == pytest.approx(62.5)  # 50 / 0.8


def test_attendance_gap():
    assert classify_shortfall("medium", 0.8, attended=50, target=100, remaining_seats=80, pool=200)[0] == "attendance_gap"


def test_no_shortfall_when_not_at_risk():
    for level in ("low", "achieved", "insufficient_data"):
        assert classify_shortfall(level, 0.8, 50, 100, 0, 0)[0] == "none"
