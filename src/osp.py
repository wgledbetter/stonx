# Option Strategy Plots:
# Gets option quotes from TD Ameritrade and plots profit/loss as a function of underlying price for various strategies

import requests
import numpy as np
import pandas as pd

from api import API
import config

# tdam = API(token=config.td_token, rf_token=config.td_rf_token)
# df = tdam.history_DF('TSLA')
# vol = tdam.calcWeeklyVolatility('TSLA', months=2)


from option import Option
from opstrat import IronButterfly

irb = IronButterfly('AAPL', 320, 3.7, 325, 6, 330, 3.8, '2020')

breakpoint()