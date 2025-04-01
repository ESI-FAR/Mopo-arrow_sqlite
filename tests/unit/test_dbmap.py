import numpy as np
import pandas as pd

from ...spine.dbmap import \
    filter_frequencies, \
    low_res_datetime

def test_filter_frequencies():
    assert filter_frequencies("5 years") == "5 Y"
    assert filter_frequencies("5 year") == "5 Y"
    assert filter_frequencies("3s") == "3s"
    assert filter_frequencies("60") == "60m"

def test_low_res_datetime():
    target = pd.date_range(start="2001-01-01", freq="7D", periods=5)
    low_res = low_res_datetime(start="2001-01-01", freq="1W", periods=5)

    assert low_res.dtype == "datetime64[s]"
    assert target.freq == low_res.freq
    for date_target, date_low_res in zip(target, low_res):
        assert date_target == date_low_res

    assert low_res_datetime(start="0001-01-01", freq="1s", periods=1)[0] == pd.Timestamp('0001-01-01')
