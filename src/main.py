# Option Strategy Plots:
# Gets option quotes from TD Ameritrade and plots profit/loss as a function of underlying price for various strategies

from pathos.pools import ProcessPool

from tdam import TDAM
import config
import settings as s
from functions import getThreads
from instruments import test_instruments, dow30
from stratlist import stratlist

tdam = TDAM(token=config.td_token, rf_token=config.td_rf_token)

# Generate
instrument_list = dow30
allstratcombs = {}
failed = []
for symbol in instrument_list:
    print(symbol)
    allstratcombs[symbol] = []
    try:
        opchain = tdam.options(symbol, type='ALL', strikeCount=s.opchain_size, weeks=2)
    except:
        failed.append(symbol)
        print('OpChain Failed for {}'.format(symbol))
        continue

    for strat in stratlist:
        try:
            allstratcombs[symbol].append(strat.gen(opchain))
        except:
            print('StratGen Failed for {}: {}'.format(symbol, strat.name))


# Evaluate and Filter
def popOver(trio):
    return trio[1] > s.min_prob_profit

bigLongList = []
pool = ProcessPool(nodes=getThreads())
for symbol in allstratcombs:
    tdam.refresh()
    try:
        price = tdam.lastPrice(symbol)
        wk_vol = tdam.calcWeeklyVolatility(symbol, months=3)
        print('{}: Price = {}, Weekly Volatility = {}'.format(symbol, price, wk_vol))
        def evalPop(strat, price=price, wk_vol=wk_vol):
            pop = strat.probOfProfit(price, wk_vol)
            # early = strat.probOfEarlyExercise(price, wk_vol)
            return (strat, pop)

        def evalExp(strat, price=price, wk_vol=wk_vol):
            exp = strat.expectedProfit(price, wk_vol)
            return exp

        for stratlist in allstratcombs[symbol]:
            fullPop = pool.map(evalPop, stratlist)
            filt = list(filter(popOver, fullPop))
            filtExp = pool.map(evalExp, [st for st, pp in filt])
            flat = list(zip(*filt))
            flat.append(filtExp)
            bigLongList += list(zip(*flat))
            print('  Completed {}'.format(stratlist[0].name))

    except:
        print('{} Failed'.format(symbol))


# Sort
def scaledProfit(trio):
    return trio[1]*trio[2]

sortedList = list(sorted(bigLongList, key=scaledProfit))


breakpoint()
