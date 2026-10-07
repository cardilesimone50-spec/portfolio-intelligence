import pytest


def test_holiday_on_one_exchange_keeps_the_move():
    import numpy as np
    import pandas as pd

    from portfolio_intelligence.portfolio.returns import compute_daily_returns

    idx = pd.bdate_range("2024-01-01", periods=5)
    prices = pd.DataFrame({"MI": [100, 101, np.nan, 103, 104], "US": [10.0] * 5}, index=idx)
    returns = compute_daily_returns(prices)
    # 101 → 103 non si perde: 0 nel giorno di chiusura, il movimento il giorno dopo
    assert (1 + returns["MI"]).prod() == pytest.approx(1.04)
    assert returns["MI"].iloc[1] == 0.0


def test_unlisted_holding_weight_is_spread_not_cash():
    import numpy as np
    import pandas as pd

    from portfolio_intelligence.portfolio.returns import portfolio_daily_returns

    idx = pd.bdate_range("2024-01-01", periods=3)
    returns = pd.DataFrame({"OLD": [0.02, 0.02, 0.02], "NEW": [np.nan, np.nan, 0.0]}, index=idx)
    pf = [{"ticker": "OLD", "weight": 0.5}, {"ticker": "NEW", "weight": 0.5}]
    daily = portfolio_daily_returns(returns, pf)
    assert daily.iloc[0] == pytest.approx(0.02)  # prima della quotazione: tutto su OLD
    assert daily.iloc[2] == pytest.approx(0.01)
