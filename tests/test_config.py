from portfolio_intelligence.analytics.performance import TRADING_DAYS as performance_trading_days
from portfolio_intelligence.analytics.pipeline import TRADING_DAYS as pipeline_trading_days
from portfolio_intelligence.config import (
    BETA_HIGH,
    BETA_LOW,
    HEALTH_SCORE_FAIR,
    HEALTH_SCORE_GOOD,
    MIN_PERIODS_CEIL,
    MIN_PERIODS_FLOOR,
    TRADING_DAYS,
    rolling_min_periods,
)
from portfolio_intelligence.portfolio.optimization import TRADING_DAYS as optimization_trading_days
from portfolio_intelligence.portfolio.risk import correlation_matrix
from portfolio_intelligence.ui.components import AMBER, _status_color
from portfolio_intelligence.views.common import TRADING_DAYS as common_trading_days
from portfolio_intelligence.visualization.charts import GAIN, LOSS


def test_trading_days_is_a_single_source_of_truth():
    assert TRADING_DAYS == 252
    # ogni modulo che lo re-importa deve puntare alla stessa costante,
    # non a una copia locale (portfolio_intelligence.config.TRADING_DAYS in 6 moduli era il bug)
    assert performance_trading_days is TRADING_DAYS
    assert pipeline_trading_days is TRADING_DAYS
    assert optimization_trading_days is TRADING_DAYS
    assert common_trading_days is TRADING_DAYS


def test_rolling_min_periods_matches_the_old_hand_rolled_formula():
    # la vecchia euristica duplicata in 3 moduli: max(15, min(60, n // 2))
    assert rolling_min_periods(10) == max(15, min(60, 10 // 2))
    assert rolling_min_periods(100) == max(15, min(60, 100 // 2))
    assert rolling_min_periods(1000) == max(15, min(60, 1000 // 2))


def test_rolling_min_periods_respects_floor_and_ceiling():
    assert rolling_min_periods(0) == MIN_PERIODS_FLOOR
    assert rolling_min_periods(1_000_000) == MIN_PERIODS_CEIL


def test_correlation_matrix_default_min_periods_is_centralized():
    # il default della firma deve restare 40 (comportamento invariato)
    import inspect

    assert inspect.signature(correlation_matrix).parameters["min_periods"].default == 40


def test_health_score_color_bands_are_centralized():
    assert HEALTH_SCORE_GOOD == 67
    assert HEALTH_SCORE_FAIR == 34
    assert _status_color(HEALTH_SCORE_GOOD) == GAIN
    assert _status_color(HEALTH_SCORE_FAIR) == AMBER
    assert _status_color(HEALTH_SCORE_FAIR - 1) == LOSS


def test_beta_bands_are_consistent():
    assert BETA_LOW < BETA_HIGH
