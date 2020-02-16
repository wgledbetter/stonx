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

irb = IronButterfly('AAPL', 320, 3.7, 325, 6, 6, 330, 3.8, '2020')
ep = irb.expectedProfit(330, 0.05)
breakpoint()
# irb.exerciseProfitChart('irb')

from opstrat import IronCondor

irc = IronCondor('TSLA', 725, 1.5, 750, 1.75, 775, 2.0, 800, 2.25, expr='2020', n=5)
irc.exerciseProfitChart('irc')

from opstrat import SkStPutButterfly

sspb = SkStPutButterfly('GOOG', 1250, 2.5, 1750, 3, 2000, 3.25, expr='dick')
sspb.exerciseProfitChart('sspb')

breakpoint()