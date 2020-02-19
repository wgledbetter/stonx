# Option Strategy Plots:
# Gets option quotes from TD Ameritrade and plots profit/loss as a function of underlying price for various strategies

import requests
import numpy as np
import pandas as pd

from api import API
import config

tdam = API(token=config.td_token, rf_token=config.td_rf_token)
# df = tdam.history_DF('TSLA')
# vol = tdam.calcWeeklyVolatility('TSLA', months=2)


from option import Option
from opstrat import IronButterfly

data = {'A': [{'strike': 320, 'premium': 3.7}],
        'B': [{'strike': 325, 'premium': 6},
              {'strike': 325, 'premium': 2}],
        'C': [{'strike': 330, 'premium': 3.8}],
        'expr': '2020'
        }
irb = IronButterfly('AAPL',data)
ep = irb.expectedProfit(330, 0.05)
breakpoint()


opchain = tdam.options('AAPL', weeks=3)
strats = IronButterfly.gen(opchain)

from instruments import test_instruments
from opstrat import stratlist

allstratcombs = {}
failed = []
for symbol in instruments:
    allstratcombs[symbol] = []
    try:
        opchain = tdam.options(symbol, type='ALL', strikeCount=12, weeks=1)
    except:
        failed.append(symbol)
        continue

    for strat in stratlist:
        try:
            allstratcombs[symbol].append(strat.gen(opchain))
        except:
            breakpoint()
            print('StratGen Failed for {}: {}'.format(symbol, strat.name))


breakpoint()