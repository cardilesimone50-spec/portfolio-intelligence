from src.analytics.performance import TRADING_DAYS as performance_trading_days
from src.analytics.pipeline import TRADING_DAYS as pipeline_trading_days
from src.config import TRADING_DAYS
from src.portfolio.optimization import TRADING_DAYS as optimization_trading_days
from src.views.common import TRADING_DAYS as common_trading_days


def test_trading_days_is_a_single_source_of_truth():
    assert TRADING_DAYS == 252
    # ogni modulo che lo re-importa deve puntare alla stessa costante,
    # non a una copia locale (src.config.TRADING_DAYS in 6 moduli era il bug)
    assert performance_trading_days is TRADING_DAYS
    assert pipeline_trading_days is TRADING_DAYS
    assert optimization_trading_days is TRADING_DAYS
    assert common_trading_days is TRADING_DAYS
