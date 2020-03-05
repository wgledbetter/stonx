# Option Strategy Plots:
# Gets option quotes from TD Ameritrade and plots profit/loss as a function of underlying price for various strategies

from pathos.pools import ProcessPool
import pickle

from tdam import TDAM
import config
import settings as s
from functions import getThreads
from instruments import test_instruments, dow30, sp100, sp500, index, everything
from stratlist import allstrats, test_list

tdam = TDAM(token=config.td_token, rf_token=config.td_rf_token)

#-------------------------------------------------------------------------------
# Choose domain
instrument_list = sp500
stratlist = allstrats

#-------------------------------------------------------------------------------
# Generate
allstratcombs = {}
failed = []
for symbol in instrument_list:
    print(symbol)
    allstratcombs[symbol] = []
    tdam.refresh()
    try:
        opchain = tdam.options(symbol, type='ALL', strikeCount=s.opchain_size, weeks=4)
    except:
        failed.append(symbol)
        print('OpChain Failed for {}'.format(symbol))
        continue

    for strat in stratlist:
        try:
            allstratcombs[symbol].append(strat.gen(opchain))
        except:
            print('StratGen Failed for {}: {}'.format(symbol, strat.name))


savename = 'save_allstratcombs.pkl'
savefile = open(savename, 'wb')
pickle.dump(allstratcombs, savefile)
savefile.close()


#-------------------------------------------------------------------------------
# Evaluate and Filter
def popOver(pair):
    return pair[1] > s.min_prob_profit

def goodBuy(pair):
    return pair[1]

def profRatio(pair):
    return pair[1] > s.min_profit_ratio

def noFreePremiums(pair):
    return not pair[1]

def expOver(trio):
    return trio[2] > s.min_expected_profit

bigLongList = []
pool = ProcessPool(nodes=20)
for symbol in allstratcombs:
    tdam.refresh()
    try:
        price = tdam.lastPrice(symbol)
        wk_drift = tdam.calcWeeklyDrift(symbol, months=3)
        wk_vol = tdam.calcWeeklyVolatility(symbol, months=3)
        print('{}: Price = {}, Weekly Volatility = {}, Weekly Drift = {}'.format(symbol, price, wk_vol, wk_drift))
        def evalGoodBuy(strat, price=price):
            # strat.update(api)
            return (strat, strat.safeSell(price))

        def evalPop(strat, price=price, wk_vol=wk_vol, wk_drift=wk_drift):
            # strat.update(api)
            pop = strat.probOfProfit(price, wk_vol, wk_drift)
            # early = strat.probOfEarlyExercise(price, wk_vol)
            return (strat, pop)

        def evalRatio(strat, price=price, wk_vol=wk_vol, wk_drift=wk_drift):
            # strat.update(api)
            rat = strat.ratioMaxToExpected(price, wk_vol, wk_drift)
            return (strat, rat)

        def evalExp(strat, price=price, wk_vol=wk_vol, wk_drift=wk_drift):
            # strat.update(api)
            exp = strat.expectedProfit(price, wk_vol, wk_drift)
            return exp

        def freePremium(strat):
            # Returns true if any returns are zero
            ret = 0
            for op in strat.oplist:
                ret += (op.premium == 0)

            return (strat, ret > 0)


        for stratlist in allstratcombs[symbol]:
            # Remove strategies if any option premiums are zero
            goodStrats = pool.map(freePremium, stratlist)
            filt = list(filter(noFreePremiums, goodStrats))
            # Remove strategies that sell ITM options
            goodStrats = pool.map(evalGoodBuy, [st for st, _ in filt])
            filt = list(filter(goodBuy, goodStrats))
            # Evaluate profit ratio and filter above threshold
            profStrats = pool.map(evalRatio, [st for st, _ in filt])
            filt = list(filter(profRatio, profStrats))
            # Evaluate probability of profit and filter above threshold
            popList = pool.map(evalPop, [st for st, _ in filt])
            filt = list(filter(popOver, popList))
            # Calculate expected profit for remaining strats
            filtExp = pool.map(evalExp, [st for st, _ in filt])
            flat = list(zip(*filt))
            flat.append(filtExp)
            popAndExp = list(zip(*flat))
            bigLongList += list(filter(expOver, popAndExp))
            print('  Completed {}'.format(stratlist[0].name))

    except:
        print('{} Failed'.format(symbol))


#-------------------------------------------------------------------------------
# Sort
def scaledProfit(trio):
    return trio[1]*trio[2]

def maxProfit(trio):
    return trio[0].maxProfit()

sortedList = list(sorted(bigLongList, key=maxProfit))
sortedList.reverse()


savename = 'save_sortedList.pkl'
savefile = open(savename, 'wb')
pickle.dump(sortedList, savefile)
savefile.close()
breakpoint()
