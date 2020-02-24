import plotly.offline as py
import plotly.graph_objs as go
import numpy as np
# from scipy.special import erf
from itertools import combinations

from option import Option
import parameters as p
from dopri import dopri
from functions import normal, stockPDF
import settings as s

# Plotting setup
PLOT_EDGE = 0.02
PLOT_RES = 250

# Probability Integration Upper Bound
INT_MIN = 0.001
MULT = 5
INT_DENOM = 100


class OpStrat:
    def __init__(self, oplist=[]):
        self.oplist = oplist


    def __str__(self):
        string = self.name + ':\n'
        for op in self.oplist:
            string += '  {}\n'.format(op.__str__())

        return string


    def __repr__(self):
        return '{}: {}'.format(self.name, self.symbol)


    #---------------------------------------------------------------------------
    ## Measures
    def cost(self):
        c = 0
        for op in self.oplist:
            c += op.cost()

        return c


    def exerciseValue(self, stock_price):
        ev = 0
        for op in self.oplist:
            ev += op.exerciseValue(stock_price)

        return ev


    def exitValue(self, option_price):
        ev = 0
        for op in self.oplist:
            ev += op.exitValue(option_price)

        return ev


    def anyInMoney(self, stock_price):
        im = False
        for op in self.oplist:
            if not im and op.inTheMoney(stock_price):
                im = True

        return im


    def remainingTime(self):
        return self.oplist[0].remainingTime()


    def remainingDays(self):
        return self.oplist[0].remainingDays()


    def remainingMarketDays(self):
        return self.oplist[0].remainingMarketDays()


    def safeSell(self, stock_price):
        # Returns false if you're selling ITM
        # Use this before executing by passing in the current stock price.
        # If you're selling something ITM, it could be exercised immediately, which is bad for you.
        safe = True
        for op in self.oplist:
            if safe and op.BS == p.SELL:
                safe = safe and not op.inTheMoney(stock_price)

        return safe


    #---------------------------------------------------------------------------
    ## Analysis
    def profitTrace(self):
        self.oplist.sort(key=lambda x: x.strike)
        spread = self.oplist[-1].strike - self.oplist[0].strike
        pMin = self.oplist[0].strike*(1-PLOT_EDGE)
        pMax = self.oplist[-1].strike*(1+PLOT_EDGE)
        prices = np.linspace(pMin, pMax, PLOT_RES)
        profit = []
        for p in prices:
            profit.append(self.exerciseValue(p))

        trace = go.Scatter(x=prices, y=profit, mode='lines', line_width=3, name=self.name)
        return trace


    def exerciseProfitChart(self, filename):
        trace = self.profitTrace()
        layout = go.Layout(scene=dict(xaxis=dict(title_text='Stock Price ($)'),
                                      yaxis=dict(title_text='Net Outcome ($)')
                                      )
                           )
        fig = go.Figure(data=[trace], layout=layout)
        py.plot(fig, './profit_{}_{}_{}.html'.format(filename, self.name, self.symbol))


    def plotProb(self, price, wk_vol, wk_drift=0, filename='temp'):
        timeToExpInWeeks = self.remainingMarketDays()/5
        pTrace = self.profitTrace()
        prob = []
        for p in pTrace.x:
            # prob.append(normal(p, mu=price, sig=wk_vol*price))
            prob.append(stockPDF(p, timeToExpInWeeks, price, wk_vol, drift=wk_drift))

        prbTrace = go.Scatter(x=pTrace.x, y=prob, text=pTrace.y, mode='lines', line_width=3, name=self.name)
        layout = go.Layout(scene=dict(xaxis=dict(title_text='Stock Price ($)'),
                                      yaxis=dict(title_text='Probability')
                                      )
                           )
        fig = go.Figure(data=[prbTrace], layout=layout)
        py.plot(fig, './probability_{}_{}_{}.html'.format(filename, self.name, self.symbol))


    def expectedProfit(self, stock_price, wk_vol, wk_drift=0):
        timeToExpInWeeks = self.remainingMarketDays()/5
        def fun(pr, dummy):
            prf = self.exerciseValue(pr)
            # prb = normal(pr, stock_price, wk_vol*stock_price)
            prb = stockPDF(pr, timeToExpInWeeks, stock_price, wk_vol, drift=wk_drift)
            return np.array([prf*prb])

        pSpan = np.array([INT_MIN, MULT*stock_price])
        dp = stock_price/INT_DENOM
        e0 = np.array([0])
        ep = dopri(fun, pSpan, dp, e0)
        return ep[1][-1][0]


    def probOfProfit(self, stock_price, wk_vol, wk_drift=0):
        timeToExpInWeeks = self.remainingMarketDays()/5
        def fun(pr, dummy):
            good = (self.exerciseValue(pr) >= 0)
            # prb = normal(pr, stock_price, wk_vol*stock_price)
            prb = stockPDF(pr, timeToExpInWeeks, stock_price, wk_vol, drift=wk_drift)
            return np.array([good*prb])

        pSpan = np.array([INT_MIN, MULT*stock_price])
        dp = stock_price/INT_DENOM
        e0 = np.array([0])
        ep = dopri(fun, pSpan, dp, e0)
        return ep[1][-1][0]


    def probOfEarlyExercise(self, stock_price, wk_vol, wk_drift=0):
        timeToExpInWeeks = self.remainingMarketDays()/5
        def exprobAtTime(time, dummy):
            def probExNow(pr, dummy):
                aim = self.anyInMoney(pr)
                prb = stockPDF(pr, time, stock_price, wk_vol, drift=wk_drift)
                return np.array([aim*prb])

            pSpan = np.array([INT_MIN, MULT*stock_price])
            dp = stock_price/INT_DENOM
            e0 = np.array([0])
            ep = dopri(probExNow, pSpan, dp, e0)
            return ep[1][-1][0]

        tSpan = np.array([0.001, timeToExpInWeeks])
        dt = timeToExpInWeeks/INT_DENOM
        pb0 = np.array([0])
        pb = dopri(exprobAtTime, tSpan, dt, pb0)
        return pb[1][-1][0]


    #---------------------------------------------------------------------------
    ## Generate
    @classmethod
    def gen(cls, opchain, n=s.nContracts):
        # Returns list of all possible "stratnames" on the options "opchain"
        # opchain = {'calls': {'date1': {'strike1': Option(), 'strike2': Option()}, 'date2': {...}}, 'puts': {'date': {'strike': Option()}}}
        # First check overlap in put and call strikes
        calldate0 = next(iter(opchain['calls']))
        callstrike0 = next(iter(opchain['calls'][calldate0]))
        symb = opchain['calls'][calldate0][callstrike0].symbol
        struct = cls.structure

        stratdefs = []
        for date in opchain['calls']:
            callstrikes = []
            for cs in opchain['calls'][date]:
                callstrikes.append(cs)

            putstrikes = []
            for ps in opchain['puts'][date]:
                putstrikes.append(ps)

            if not callstrikes == putstrikes:
                print('Mixed call/put chains for date {}'.format(date))
                continue

            combs = list(combinations(callstrikes, struct['n']))

            # Write definitions dicts into stratdefs
            for c in combs:
                opstruct = {}
                opstruct['expr'] = date
                k = 0
                for I in struct:
                    if I == 'n':
                        continue

                    opstruct[I] = []
                    for j, J in enumerate(struct[I]):
                        opstruct[I].append({})
                        opstruct[I][j]['strike'] = float(c[k])
                        if struct[I][j]['CP'] == 1:
                            # Call
                            opstruct[I][j]['premium'] = float(opchain['calls'][date][c[k]].premium)
                        else:
                            # Put
                            opstruct[I][j]['premium'] = float(opchain['puts'][date][c[k]].premium)

                        k += 1

                stratdefs.append(opstruct)

        # Generate strategy from dicts
        strats = []
        for st in stratdefs:
            strats.append(cls(symb, st, n=n))

        return strats



################################################################################
class IronCondor(OpStrat):
    # https://www.optionsplaybook.com/option-strategies/iron-condor/
    # def __init__(self, symbol, A_st, A_pr, B_st, B_pr, C_st, C_pr, D_st, D_pr, expr, n=s.nContracts):
    #     self.name = 'Iron Condor'
    #     self.symbol = symbol
    #     self.oplist = []
    #     self.oplist.append(Option(symbol, p.PUT, A_pr, p.BUY, A_st, expr=expr, n=n))
    #     self.oplist.append(Option(symbol, p.PUT, B_pr, p.SELL, B_st, expr=expr, n=n))
    #     self.oplist.append(Option(symbol, p.CALL, C_pr, p.SELL, C_st, expr=expr, n=n))
    #     self.oplist.append(Option(symbol, p.CALL, D_pr, p.BUY, D_st, expr=expr, n=n))

    name = 'IronCondor'
    structure = {'A': [{'BS': p.BUY, 'CP': p.PUT, 'M': 1}],
                 'B': [{'BS': p.SELL, 'CP': p.PUT, 'M': 1}],
                 'C': [{'BS': p.SELL, 'CP': p.CALL, 'M': 1}],
                 'D': [{'BS': p.BUY, 'CP': p.CALL, 'M': 1}],
                 'n': 4
                 }

    def __init__(self, symbol, struct, n=s.nContracts):
        self.symbol = symbol
        self.oplist = []
        optype = self.structure
        self.oplist.append(Option(symbol, optype['A'][0], struct['A'][0], struct['expr'], n=n*optype['A'][0]['M']))
        self.oplist.append(Option(symbol, optype['B'][0], struct['B'][0], struct['expr'], n=n*optype['B'][0]['M']))
        self.oplist.append(Option(symbol, optype['C'][0], struct['C'][0], struct['expr'], n=n*optype['C'][0]['M']))
        self.oplist.append(Option(symbol, optype['D'][0], struct['D'][0], struct['expr'], n=n*optype['D'][0]['M']))
        self.expr = self.oplist[0].expr


#_______________________________________________________________________________
class IronButterfly(OpStrat):
    # https://www.optionsplaybook.com/option-strategies/iron-butterfly/
    # def __init__(self, symbol, A_st, A_pr, B_st, B_ppr, B_cpr, C_st, C_pr, expr, n=s.nContracts):
    #     self.name = 'Iron Butterfly'
    #     self.symbol = symbol
    #     self.oplist = []
    #     self.oplist.append(Option(symbol, p.PUT, A_pr, p.BUY, A_st, expr=expr, n=n))
    #     self.oplist.append(Option(symbol, p.PUT, B_ppr, p.SELL, B_st, expr=expr, n=n))
    #     self.oplist.append(Option(symbol, p.CALL, B_cpr, p.SELL, B_st, expr=expr, n=n))
    #     self.oplist.append(Option(symbol, p.CALL, C_pr, p.BUY, C_st, expr=expr, n=n))

    name = 'Iron Butterfly'
    structure = {'A': [{'BS': p.BUY, 'CP': p.PUT, 'M': 1}],
                 'B': [{'BS': p.SELL, 'CP': p.PUT, 'M': 1},
                       {'BS': p.SELL, 'CP': p.CALL, 'M': 1}],
                 'C': [{'BS': p.BUY, 'CP': p.CALL, 'M': 1}],
                 'n': 4,
                 }

    def __init__(self, symbol, struct, n=s.nContracts):
        self.symbol = symbol
        self.oplist = []
        optype = self.structure
        self.oplist.append(Option(symbol, optype['A'][0], struct['A'][0], struct['expr'], n=n*optype['A'][0]['M']))
        self.oplist.append(Option(symbol, optype['B'][0], struct['B'][0], struct['expr'], n=n*optype['B'][0]['M']))
        self.oplist.append(Option(symbol, optype['B'][1], struct['B'][1], struct['expr'], n=n*optype['B'][1]['M']))
        self.oplist.append(Option(symbol, optype['C'][0], struct['C'][0], struct['expr'], n=n*optype['C'][0]['M']))
        self.expr = self.oplist[0].expr


#_______________________________________________________________________________
class LongStraddle(OpStrat):
    # https://www.optionsplaybook.com/option-strategies/long-straddle/
    # def __init__(self, symbol, A_st, A_ppr, A_cpr, expr, n=s.nContracts):
    #     self.name = 'Long Straddle'
    #     self.symbol = symbol
    #     self.oplist = []
    #     self.oplist.append(Option(symbol, p.CALL, A_cpr, p.BUY, A_st, expr=expr, n=n))
    #     self.oplist.append(Option(symbol, p.PUT, A_ppr, p.BUY, A_st, expr=expr, n=n))

    name = 'Long Straddle'
    structure = {'A': [{'BS': p.BUY, 'CP': p.CALL, 'M': 1},
                       {'BS': p.BUY, 'CP': p.PUT, 'M': 1}],
                 'n': 2,
                 }

    def __init__(self, symbol, struct, n=s.nContracts):
        self.symbol = symbol
        self.oplist = []
        optype = self.structure
        self.oplist.append(Option(symbol, optype['A'][0], struct['A'][0], struct['expr'], n=n*optype['A'][0]['M']))
        self.oplist.append(Option(symbol, optype['A'][1], struct['A'][1], struct['expr'], n=n*optype['A'][1]['M']))
        self.expr = self.oplist[0].expr


#_______________________________________________________________________________
class ShortStraddle(OpStrat):
    name = 'Short Straddle'
    structure = {'A': [{'BS': p.SELL, 'CP': p.CALL, 'M': 1},
                       {'BS': p.SELL, 'CP': p.PUT, 'M': 1}],
                 'n': 2,
                 }

    def __init__(self, symbol, struct, n=s.nContracts):
        self.symbol = symbol
        self.oplist = []
        optype = self.structure
        self.oplist.append(Option(symbol, optype['A'][0], struct['A'][0], struct['expr'], n=n*optype['A'][0]['M']))
        self.oplist.append(Option(symbol, optype['A'][1], struct['A'][1], struct['expr'], n=n*optype['A'][1]['M']))
        self.expr = self.oplist[0].expr


#_______________________________________________________________________________
class LongStrangle(OpStrat):
    # https://www.optionsplaybook.com/option-strategies/long-strangle/
    # def __init__(self, symbol, A_st, A_pr, B_st, B_pr, expr, n=s.nContracts):
    #     self.name = 'Long Strangle'
    #     self.symbol = symbol
    #     self.oplist = []
    #     self.oplist.append(Option(symbol, p.PUT, A_pr, p.BUY, A_st, expr=expr, n=n))
    #     self.oplist.append(Option(symbol, p.CALL, B_pr, p.BUY, B_st, expr=expr, n=n))

    name = 'Long Strangle'
    structure = {'A': [{'BS': p.BUY, 'CP': p.PUT, 'M': 1}],
                 'B': [{'BS': p.BUY, 'CP': p.CALL, 'M': 1}],
                 'n': 2,
                 }

    def __init__(self, symbol, struct, n=s.nContracts):
        self.symbol = symbol
        self.oplist = []
        optype = self.structure
        self.oplist.append(Option(symbol, optype['A'][0], struct['A'][0], struct['expr'], n=n*optype['A'][0]['M']))
        self.oplist.append(Option(symbol, optype['B'][0], struct['B'][0], struct['expr'], n=n*optype['B'][0]['M']))
        self.expr = self.oplist[0].expr


#_______________________________________________________________________________
class ShortStrangle(OpStrat):
    name = 'Short Strangle'
    structure = {'A': [{'BS': p.SELL, 'CP': p.PUT, 'M': 1}],
                 'B': [{'BS': p.SELL, 'CP': p.CALL, 'M': 1}],
                 'n': 2,
                 }

    def __init__(self, symbol, struct, n=s.nContracts):
        self.symbol = symbol
        self.oplist = []
        optype = self.structure
        self.oplist.append(Option(symbol, optype['A'][0], struct['A'][0], struct['expr'], n=n*optype['A'][0]['M']))
        self.oplist.append(Option(symbol, optype['B'][0], struct['B'][0], struct['expr'], n=n*optype['B'][0]['M']))
        self.expr = self.oplist[0].expr


#_______________________________________________________________________________
class SkStPutButterfly(OpStrat):
    # https://www.optionsplaybook.com/option-strategies/broken-wing-butterfly-put/
    # def __init__(self, symbol, A_st, A_pr, C_st, C_pr, D_st, D_pr, expr, n=s.nContracts):
    #     self.name = 'Broken Wing Put Butterfly'
    #     self.symbol = symbol
    #     self.oplist = []
    #     self.oplist.append(Option(symbol, p.PUT, A_pr, p.BUY, A_st, expr=expr, n=n))
    #     self.oplist.append(Option(symbol, p.PUT, C_pr, p.SELL, C_st, expr=expr, n=2*n))
    #     self.oplist.append(Option(symbol, p.PUT, D_pr, p.BUY, D_st, expr=expr, n=n))

    name = 'Broken Wing Put Butterfly'
    structure = {'A': [{'BS': p.BUY, 'CP': p.PUT, 'M': 1}],
                 'B': [{'BS': p.SELL, 'CP': p.PUT, 'M': 2}],
                 'C': [{'BS': p.BUY, 'CP': p.PUT, 'M': 1}],
                 'n': 3,
                 }

    def __init__(self, symbol, struct, n=s.nContracts):
        self.symbol = symbol
        self.oplist = []
        optype = self.structure
        self.oplist.append(Option(symbol, optype['A'][0], struct['A'][0], struct['expr'], n=n*optype['A'][0]['M']))
        self.oplist.append(Option(symbol, optype['B'][0], struct['B'][0], struct['expr'], n=n*optype['B'][0]['M']))
        self.oplist.append(Option(symbol, optype['C'][0], struct['C'][0], struct['expr'], n=n*optype['C'][0]['M']))
        self.expr = self.oplist[0].expr


#_______________________________________________________________________________
class SkStCallButterfly(OpStrat):
    # https://www.optionsplaybook.com/option-strategies/broken-wing-butterfly-call/
    name = 'Broken Wing Call Butterfly'
    structure = {'A': [{'BS': p.BUY, 'CP': p.CALL, 'M': 1}],
                 'B': [{'BS': p.SELL, 'CP': p.CALL, 'M': 2}],
                 'C': [{'BS': p.BUY, 'CP': p.CALL, 'M': 1}],
                 'n': 3,
                 }
    def __init__(self, symbol, struct, n=s.nContracts):
        self.symbol = symbol
        self.oplist = []
        optype = self.structure
        self.oplist.append(Option(symbol, optype['A'][0], struct['A'][0], struct['expr'], n=n*optype['A'][0]['M']))
        self.oplist.append(Option(symbol, optype['B'][0], struct['B'][0], struct['expr'], n=n*optype['B'][0]['M']))
        self.oplist.append(Option(symbol, optype['C'][0], struct['C'][0], struct['expr'], n=n*optype['C'][0]['M']))
        self.expr = self.oplist[0].expr


#_______________________________________________________________________________
class LongCall(OpStrat):
    # https://www.optionsplaybook.com/option-strategies/long-call/
    name = 'Long Call'
    structure = {'A': [{'BS': p.BUY, 'CP': p.CALL, 'M': 1}],
                 'n': 1
                 }
    def __init__(self, symbol, struct, n=s.nContracts):
        self.symbol = symbol
        self.oplist = []
        optype = self.structure
        self.oplist.append(Option(symbol, optype['A'][0], struct['A'][0], struct['expr'], n=n*optype['A'][0]['M']))
        self.expr = self.oplist[0].expr


#_______________________________________________________________________________
class LongPut(OpStrat):
    # https://www.optionsplaybook.com/option-strategies/long-put/
    name = 'Long Put'
    structure = {'A': [{'BS': p.BUY, 'CP': p.PUT, 'M': 1}],
                 'n': 1
                 }
    def __init__(self, symbol, struct, n=s.nContracts):
        self.symbol = symbol
        self.oplist = []
        optype = self.structure
        self.oplist.append(Option(symbol, optype['A'][0], struct['A'][0], struct['expr'], n=n*optype['A'][0]['M']))
        self.expr = self.oplist[0].expr


#_______________________________________________________________________________
class ShortCall(OpStrat):
    name = 'Short Call'
    structure = {'A': [{'BS': p.SELL, 'CP': p.CALL, 'M': 1}],
                 'n': 1
                 }
    def __init__(self, symbol, struct, n=s.nContracts):
        self.symbol = symbol
        self.oplist = []
        optype = self.structure
        self.oplist.append(Option(symbol, optype['A'][0], struct['A'][0], struct['expr'], n=n*optype['A'][0]['M']))
        self.expr = self.oplist[0].expr


#_______________________________________________________________________________
class ShortPut(OpStrat):
    name = 'Short Put'
    structure = {'A': [{'BS': p.SELL, 'CP': p.PUT, 'M': 1}],
                 'n': 1
                 }
    def __init__(self, symbol, struct, n=s.nContracts):
        self.symbol = symbol
        self.oplist = []
        optype = self.structure
        self.oplist.append(Option(symbol, optype['A'][0], struct['A'][0], struct['expr'], n=n*optype['A'][0]['M']))
        self.expr = self.oplist[0].expr


#_______________________________________________________________________________
class LongCallSpread(OpStrat):
    # https://www.optionsplaybook.com/option-strategies/long-call-spread/
    name = 'Long Call Spread'
    structure = {'A': [{'BS': p.BUY, 'CP': p.CALL, 'M': 1}],
                 'B': [{'BS': p.SELL, 'CP': p.CALL, 'M': 1}],
                 'n': 2
                 }
    def __init__(self, symbol, struct, n=s.nContracts):
        self.symbol = symbol
        self.oplist = []
        optype = self.structure
        self.oplist.append(Option(symbol, optype['A'][0], struct['A'][0], struct['expr'], n=n*optype['A'][0]['M']))
        self.oplist.append(Option(symbol, optype['B'][0], struct['B'][0], struct['expr'], n=n*optype['B'][0]['M']))
        self.expr = self.oplist[0].expr


#_______________________________________________________________________________
class LongPutSpread(OpStrat):
    # https://www.optionsplaybook.com/option-strategies/long-put-spread/
    name = 'Long Put Spread'
    structure = {'A': [{'BS': p.SELL, 'CP': p.PUT, 'M': 1}],
                 'B': [{'BS': p.BUY, 'CP': p.PUT, 'M': 1}],
                 'n': 2
                 }
    def __init__(self, symbol, struct, n=s.nContracts):
        self.symbol = symbol
        self.oplist = []
        optype = self.structure
        self.oplist.append(Option(symbol, optype['A'][0], struct['A'][0], struct['expr'], n=n*optype['A'][0]['M']))
        self.oplist.append(Option(symbol, optype['B'][0], struct['B'][0], struct['expr'], n=n*optype['B'][0]['M']))
        self.expr = self.oplist[0].expr


#_______________________________________________________________________________
class ShortCallSpread(OpStrat):
    # https://www.optionsplaybook.com/option-strategies/short-call-spread/
    name = 'Short Call Spread'
    structure = {'A': [{'BS': p.SELL, 'CP': p.CALL, 'M': 1}],
                 'B': [{'BS': p.BUY, 'CP': p.CALL, 'M': 1}],
                 'n': 2
                 }
    def __init__(self, symbol, struct, n=s.nContracts):
        self.symbol = symbol
        self.oplist = []
        optype = self.structure
        self.oplist.append(Option(symbol, optype['A'][0], struct['A'][0], struct['expr'], n=n*optype['A'][0]['M']))
        self.oplist.append(Option(symbol, optype['B'][0], struct['B'][0], struct['expr'], n=n*optype['B'][0]['M']))
        self.expr = self.oplist[0].expr


#_______________________________________________________________________________
class ShortPutSpread(OpStrat):
    # https://www.optionsplaybook.com/option-strategies/short-put-spread/
    name = 'Short Put Spread'
    structure = {'A': [{'BS': p.BUY, 'CP': p.PUT, 'M': 1}],
                 'B': [{'BS': p.SELL, 'CP': p.PUT, 'M': 1}],
                 'n': 2
                 }
    def __init__(self, symbol, struct, n=s.nContracts):
        self.symbol = symbol
        self.oplist = []
        optype = self.structure
        self.oplist.append(Option(symbol, optype['A'][0], struct['A'][0], struct['expr'], n=n*optype['A'][0]['M']))
        self.oplist.append(Option(symbol, optype['B'][0], struct['B'][0], struct['expr'], n=n*optype['B'][0]['M']))
        self.expr = self.oplist[0].expr


#_______________________________________________________________________________
class BackCallSpread(OpStrat):
    # https://www.optionsplaybook.com/option-strategies/call-backspread/
    name = 'Back Call Spread'
    structure = {'A': [{'BS': p.SELL, 'CP': p.CALL, 'M': 1}],
                 'B': [{'BS': p.BUY, 'CP': p.CALL, 'M': 2}],
                 'n': 2
                 }
    def __init__(self, symbol, struct, n=s.nContracts):
        self.symbol = symbol
        self.oplist = []
        optype = self.structure
        self.oplist.append(Option(symbol, optype['A'][0], struct['A'][0], struct['expr'], n=n*optype['A'][0]['M']))
        self.oplist.append(Option(symbol, optype['B'][0], struct['B'][0], struct['expr'], n=n*optype['B'][0]['M']))
        self.expr = self.oplist[0].expr


#_______________________________________________________________________________
class BackPutSpread(OpStrat):
    # https://www.optionsplaybook.com/option-strategies/put-backspread/
    name = 'Back Put Spread'
    structure = {'A': [{'BS': p.BUY, 'CP': p.PUT, 'M': 2}],
                 'B': [{'BS': p.SELL, 'CP': p.PUT, 'M': 1}],
                 'n': 2
                 }
    def __init__(self, symbol, struct, n=s.nContracts):
        self.symbol = symbol
        self.oplist = []
        optype = self.structure
        self.oplist.append(Option(symbol, optype['A'][0], struct['A'][0], struct['expr'], n=n*optype['A'][0]['M']))
        self.oplist.append(Option(symbol, optype['B'][0], struct['B'][0], struct['expr'], n=n*optype['B'][0]['M']))
        self.expr = self.oplist[0].expr


#_______________________________________________________________________________
class LongCallButterflySpread(OpStrat):
    # https://www.optionsplaybook.com/option-strategies/long-call-butterfly-spread/
    # Note: For my implementation, this is identical to Skip-Strike Call Butterfly
    name = 'Long Call Butterfly Spread'
    structure = {'A': [{'BS': p.BUY, 'CP': p.CALL, 'M': 1}],
                 'B': [{'BS': p.SELL, 'CP': p.CALL, 'M': 2}],
                 'C': [{'BS': p.BUY, 'CP': p.CALL, 'M': 1}],
                 'n': 3,
                 }

    def __init__(self, symbol, struct, n=s.nContracts):
        self.symbol = symbol
        self.oplist = []
        optype = self.structure
        self.oplist.append(Option(symbol, optype['A'][0], struct['A'][0], struct['expr'], n=n*optype['A'][0]['M']))
        self.oplist.append(Option(symbol, optype['B'][0], struct['B'][0], struct['expr'], n=n*optype['B'][0]['M']))
        self.oplist.append(Option(symbol, optype['C'][0], struct['C'][0], struct['expr'], n=n*optype['C'][0]['M']))
        self.expr = self.oplist[0].expr


#_______________________________________________________________________________
class LongPutButterflySpread(OpStrat):
    # https://www.optionsplaybook.com/option-strategies/long-put-butterfly-spread/
    # Note: For my implementation, this is identical to Skip-Strike Put Butterfly
    name = 'Long Put Butterfly Spread'
    structure = {'A': [{'BS': p.BUY, 'CP': p.PUT, 'M': 1}],
                 'B': [{'BS': p.SELL, 'CP': p.PUT, 'M': 2}],
                 'C': [{'BS': p.BUY, 'CP': p.PUT, 'M': 1}],
                 'n': 3,
                 }

    def __init__(self, symbol, struct, n=s.nContracts):
        self.symbol = symbol
        self.oplist = []
        optype = self.structure
        self.oplist.append(Option(symbol, optype['A'][0], struct['A'][0], struct['expr'], n=n*optype['A'][0]['M']))
        self.oplist.append(Option(symbol, optype['B'][0], struct['B'][0], struct['expr'], n=n*optype['B'][0]['M']))
        self.oplist.append(Option(symbol, optype['C'][0], struct['C'][0], struct['expr'], n=n*optype['C'][0]['M']))
        self.expr = self.oplist[0].expr


#_______________________________________________________________________________
class InverseCallButterfly(OpStrat):
    # https://www.optionsplaybook.com/option-strategies/inverse-broken-wing-butterfly-call/
    name = 'Inverse Call Butterfly'
    structure = {'A': [{'BS': p.SELL, 'CP': p.CALL, 'M': 1}],
                 'B': [{'BS': p.BUY, 'CP': p.CALL, 'M': 2}],
                 'C': [{'BS': p.SELL, 'CP': p.CALL, 'M': 1}],
                 'n': 3,
                 }

    def __init__(self, symbol, struct, n=s.nContracts):
        self.symbol = symbol
        self.oplist = []
        optype = self.structure
        self.oplist.append(Option(symbol, optype['A'][0], struct['A'][0], struct['expr'], n=n*optype['A'][0]['M']))
        self.oplist.append(Option(symbol, optype['B'][0], struct['B'][0], struct['expr'], n=n*optype['B'][0]['M']))
        self.oplist.append(Option(symbol, optype['C'][0], struct['C'][0], struct['expr'], n=n*optype['C'][0]['M']))
        self.expr = self.oplist[0].expr


#_______________________________________________________________________________
class InversePutButterfly(OpStrat):
    # https://www.optionsplaybook.com/option-strategies/inverse-broken-wing-butterfly-put/
    name = 'Inverse Put Butterfly'
    structure = {'A': [{'BS': p.SELL, 'CP': p.PUT, 'M': 1}],
                 'B': [{'BS': p.BUY, 'CP': p.PUT, 'M': 2}],
                 'C': [{'BS': p.SELL, 'CP': p.PUT, 'M': 1}],
                 'n': 3,
                 }

    def __init__(self, symbol, struct, n=s.nContracts):
        self.symbol = symbol
        self.oplist = []
        optype = self.structure
        self.oplist.append(Option(symbol, optype['A'][0], struct['A'][0], struct['expr'], n=n*optype['A'][0]['M']))
        self.oplist.append(Option(symbol, optype['B'][0], struct['B'][0], struct['expr'], n=n*optype['B'][0]['M']))
        self.oplist.append(Option(symbol, optype['C'][0], struct['C'][0], struct['expr'], n=n*optype['C'][0]['M']))
        self.expr = self.oplist[0].expr


#_______________________________________________________________________________
class ChristmasTreeCallButterfly(OpStrat):
    # https://www.optionsplaybook.com/option-strategies/christmas-tree-butterfly-call/
    name = 'Christmas Tree Call Butterfly'
    structure = {'A': [{'BS': p.BUY, 'CP': p.CALL, 'M': 1}],
                 'B': [{'BS': p.SELL, 'CP': p.CALL, 'M': 3}],
                 'C': [{'BS': p.BUY, 'CP': p.CALL, 'M': 2}],
                 'n': 3,
                 }

    def __init__(self, symbol, struct, n=s.nContracts):
        self.symbol = symbol
        self.oplist = []
        optype = self.structure
        self.oplist.append(Option(symbol, optype['A'][0], struct['A'][0], struct['expr'], n=n*optype['A'][0]['M']))
        self.oplist.append(Option(symbol, optype['B'][0], struct['B'][0], struct['expr'], n=n*optype['B'][0]['M']))
        self.oplist.append(Option(symbol, optype['C'][0], struct['C'][0], struct['expr'], n=n*optype['C'][0]['M']))
        self.expr = self.oplist[0].expr


#_______________________________________________________________________________
class FlipChristmasTreeCallButterfly(OpStrat):
    name = 'Flipped Christmas Tree Call Butterfly'
    structure = {'A': [{'BS': p.BUY, 'CP': p.CALL, 'M': 2}],
                 'B': [{'BS': p.SELL, 'CP': p.CALL, 'M': 3}],
                 'C': [{'BS': p.BUY, 'CP': p.CALL, 'M': 1}],
                 'n': 3,
                 }

    def __init__(self, symbol, struct, n=s.nContracts):
        self.symbol = symbol
        self.oplist = []
        optype = self.structure
        self.oplist.append(Option(symbol, optype['A'][0], struct['A'][0], struct['expr'], n=n*optype['A'][0]['M']))
        self.oplist.append(Option(symbol, optype['B'][0], struct['B'][0], struct['expr'], n=n*optype['B'][0]['M']))
        self.oplist.append(Option(symbol, optype['C'][0], struct['C'][0], struct['expr'], n=n*optype['C'][0]['M']))
        self.expr = self.oplist[0].expr


#_______________________________________________________________________________
class InvChristmasTreeCallButterfly(OpStrat):
    name = 'Inverse Christmas Tree Call Butterfly'
    structure = {'A': [{'BS': p.SELL, 'CP': p.CALL, 'M': 1}],
                 'B': [{'BS': p.BUY, 'CP': p.CALL, 'M': 3}],
                 'C': [{'BS': p.SELL, 'CP': p.CALL, 'M': 2}],
                 'n': 3,
                 }

    def __init__(self, symbol, struct, n=s.nContracts):
        self.symbol = symbol
        self.oplist = []
        optype = self.structure
        self.oplist.append(Option(symbol, optype['A'][0], struct['A'][0], struct['expr'], n=n*optype['A'][0]['M']))
        self.oplist.append(Option(symbol, optype['B'][0], struct['B'][0], struct['expr'], n=n*optype['B'][0]['M']))
        self.oplist.append(Option(symbol, optype['C'][0], struct['C'][0], struct['expr'], n=n*optype['C'][0]['M']))
        self.expr = self.oplist[0].expr


#_______________________________________________________________________________
class InvFlipChristmasTreeCallButterfly(OpStrat):
    name = 'Inverse Flipped Christmas Tree Call Butterfly'
    structure = {'A': [{'BS': p.SELL, 'CP': p.CALL, 'M': 2}],
                 'B': [{'BS': p.BUY, 'CP': p.CALL, 'M': 3}],
                 'C': [{'BS': p.SELL, 'CP': p.CALL, 'M': 1}],
                 'n': 3,
                 }

    def __init__(self, symbol, struct, n=s.nContracts):
        self.symbol = symbol
        self.oplist = []
        optype = self.structure
        self.oplist.append(Option(symbol, optype['A'][0], struct['A'][0], struct['expr'], n=n*optype['A'][0]['M']))
        self.oplist.append(Option(symbol, optype['B'][0], struct['B'][0], struct['expr'], n=n*optype['B'][0]['M']))
        self.oplist.append(Option(symbol, optype['C'][0], struct['C'][0], struct['expr'], n=n*optype['C'][0]['M']))
        self.expr = self.oplist[0].expr


#_______________________________________________________________________________
class ChristmasTreePutButterfly(OpStrat):
    # https://www.optionsplaybook.com/option-strategies/christmas-tree-butterfly-put/
    name = 'Christmas Tree Put Butterfly'
    structure = {'A': [{'BS': p.BUY, 'CP': p.PUT, 'M': 2}],
                 'B': [{'BS': p.SELL, 'CP': p.PUT, 'M': 3}],
                 'C': [{'BS': p.BUY, 'CP': p.PUT, 'M': 1}],
                 'n': 3,
                 }

    def __init__(self, symbol, struct, n=s.nContracts):
        self.symbol = symbol
        self.oplist = []
        optype = self.structure
        self.oplist.append(Option(symbol, optype['A'][0], struct['A'][0], struct['expr'], n=n*optype['A'][0]['M']))
        self.oplist.append(Option(symbol, optype['B'][0], struct['B'][0], struct['expr'], n=n*optype['B'][0]['M']))
        self.oplist.append(Option(symbol, optype['C'][0], struct['C'][0], struct['expr'], n=n*optype['C'][0]['M']))
        self.expr = self.oplist[0].expr


#_______________________________________________________________________________
class FlipChristmasTreePutButterfly(OpStrat):
    name = 'Flipped Christmas Tree Put Butterfly'
    structure = {'A': [{'BS': p.BUY, 'CP': p.PUT, 'M': 1}],
                 'B': [{'BS': p.SELL, 'CP': p.PUT, 'M': 3}],
                 'C': [{'BS': p.BUY, 'CP': p.PUT, 'M': 2}],
                 'n': 3,
                 }

    def __init__(self, symbol, struct, n=s.nContracts):
        self.symbol = symbol
        self.oplist = []
        optype = self.structure
        self.oplist.append(Option(symbol, optype['A'][0], struct['A'][0], struct['expr'], n=n*optype['A'][0]['M']))
        self.oplist.append(Option(symbol, optype['B'][0], struct['B'][0], struct['expr'], n=n*optype['B'][0]['M']))
        self.oplist.append(Option(symbol, optype['C'][0], struct['C'][0], struct['expr'], n=n*optype['C'][0]['M']))
        self.expr = self.oplist[0].expr


#_______________________________________________________________________________
class InvChristmasTreePutButterfly(OpStrat):
    name = 'Inverse Christmas Tree Put Butterfly'
    structure = {'A': [{'BS': p.SELL, 'CP': p.PUT, 'M': 2}],
                 'B': [{'BS': p.BUY, 'CP': p.PUT, 'M': 3}],
                 'C': [{'BS': p.SELL, 'CP': p.PUT, 'M': 1}],
                 'n': 3,
                 }

    def __init__(self, symbol, struct, n=s.nContracts):
        self.symbol = symbol
        self.oplist = []
        optype = self.structure
        self.oplist.append(Option(symbol, optype['A'][0], struct['A'][0], struct['expr'], n=n*optype['A'][0]['M']))
        self.oplist.append(Option(symbol, optype['B'][0], struct['B'][0], struct['expr'], n=n*optype['B'][0]['M']))
        self.oplist.append(Option(symbol, optype['C'][0], struct['C'][0], struct['expr'], n=n*optype['C'][0]['M']))
        self.expr = self.oplist[0].expr


#_______________________________________________________________________________
class InvFlipChristmasTreePutButterfly(OpStrat):
    name = 'Inverse Flipped Christmas Tree Put Butterfly'
    structure = {'A': [{'BS': p.SELL, 'CP': p.PUT, 'M': 1}],
                 'B': [{'BS': p.BUY, 'CP': p.PUT, 'M': 3}],
                 'C': [{'BS': p.SELL, 'CP': p.PUT, 'M': 2}],
                 'n': 3,
                 }

    def __init__(self, symbol, struct, n=s.nContracts):
        self.symbol = symbol
        self.oplist = []
        optype = self.structure
        self.oplist.append(Option(symbol, optype['A'][0], struct['A'][0], struct['expr'], n=n*optype['A'][0]['M']))
        self.oplist.append(Option(symbol, optype['B'][0], struct['B'][0], struct['expr'], n=n*optype['B'][0]['M']))
        self.oplist.append(Option(symbol, optype['C'][0], struct['C'][0], struct['expr'], n=n*optype['C'][0]['M']))
        self.expr = self.oplist[0].expr


#_______________________________________________________________________________
class LongCallCondor(OpStrat):
    # https://www.optionsplaybook.com/option-strategies/long-call-condor-spread/
    name = 'Long Call Condor'
    structure = {'A': [{'BS': p.BUY, 'CP': p.CALL, 'M': 1}],
                 'B': [{'BS': p.SELL, 'CP': p.CALL, 'M': 1}],
                 'C': [{'BS': p.SELL, 'CP': p.CALL, 'M': 1}],
                 'D': [{'BS': p.BUY, 'CP': p.CALL, 'M': 1}],
                 'n': 4
                 }

    def __init__(self, symbol, struct, n=s.nContracts):
        self.symbol = symbol
        self.oplist = []
        optype = self.structure
        self.oplist.append(Option(symbol, optype['A'][0], struct['A'][0], struct['expr'], n=n*optype['A'][0]['M']))
        self.oplist.append(Option(symbol, optype['B'][0], struct['B'][0], struct['expr'], n=n*optype['B'][0]['M']))
        self.oplist.append(Option(symbol, optype['C'][0], struct['C'][0], struct['expr'], n=n*optype['C'][0]['M']))
        self.oplist.append(Option(symbol, optype['D'][0], struct['D'][0], struct['expr'], n=n*optype['D'][0]['M']))
        self.expr = self.oplist[0].expr


#_______________________________________________________________________________
class ShortCallCondor(OpStrat):
    name = 'Short Call Condor'
    structure = {'A': [{'BS': p.SELL, 'CP': p.CALL, 'M': 1}],
                 'B': [{'BS': p.BUY, 'CP': p.CALL, 'M': 1}],
                 'C': [{'BS': p.BUY, 'CP': p.CALL, 'M': 1}],
                 'D': [{'BS': p.SELL, 'CP': p.CALL, 'M': 1}],
                 'n': 4
                 }

    def __init__(self, symbol, struct, n=s.nContracts):
        self.symbol = symbol
        self.oplist = []
        optype = self.structure
        self.oplist.append(Option(symbol, optype['A'][0], struct['A'][0], struct['expr'], n=n*optype['A'][0]['M']))
        self.oplist.append(Option(symbol, optype['B'][0], struct['B'][0], struct['expr'], n=n*optype['B'][0]['M']))
        self.oplist.append(Option(symbol, optype['C'][0], struct['C'][0], struct['expr'], n=n*optype['C'][0]['M']))
        self.oplist.append(Option(symbol, optype['D'][0], struct['D'][0], struct['expr'], n=n*optype['D'][0]['M']))
        self.expr = self.oplist[0].expr


#_______________________________________________________________________________
class LongPutCondor(OpStrat):
    # https://www.optionsplaybook.com/option-strategies/long-put-condor-spread/
    name = 'Long Put Condor'
    structure = {'A': [{'BS': p.BUY, 'CP': p.PUT, 'M': 1}],
                 'B': [{'BS': p.SELL, 'CP': p.PUT, 'M': 1}],
                 'C': [{'BS': p.SELL, 'CP': p.PUT, 'M': 1}],
                 'D': [{'BS': p.BUY, 'CP': p.PUT, 'M': 1}],
                 'n': 4
                 }

    def __init__(self, symbol, struct, n=s.nContracts):
        self.symbol = symbol
        self.oplist = []
        optype = self.structure
        self.oplist.append(Option(symbol, optype['A'][0], struct['A'][0], struct['expr'], n=n*optype['A'][0]['M']))
        self.oplist.append(Option(symbol, optype['B'][0], struct['B'][0], struct['expr'], n=n*optype['B'][0]['M']))
        self.oplist.append(Option(symbol, optype['C'][0], struct['C'][0], struct['expr'], n=n*optype['C'][0]['M']))
        self.oplist.append(Option(symbol, optype['D'][0], struct['D'][0], struct['expr'], n=n*optype['D'][0]['M']))
        self.expr = self.oplist[0].expr


#_______________________________________________________________________________
class ShortPutCondor(OpStrat):
    name = 'Short Put Condor'
    structure = {'A': [{'BS': p.SELL, 'CP': p.PUT, 'M': 1}],
                 'B': [{'BS': p.BUY, 'CP': p.PUT, 'M': 1}],
                 'C': [{'BS': p.BUY, 'CP': p.PUT, 'M': 1}],
                 'D': [{'BS': p.SELL, 'CP': p.PUT, 'M': 1}],
                 'n': 4
                 }

    def __init__(self, symbol, struct, n=s.nContracts):
        self.symbol = symbol
        self.oplist = []
        optype = self.structure
        self.oplist.append(Option(symbol, optype['A'][0], struct['A'][0], struct['expr'], n=n*optype['A'][0]['M']))
        self.oplist.append(Option(symbol, optype['B'][0], struct['B'][0], struct['expr'], n=n*optype['B'][0]['M']))
        self.oplist.append(Option(symbol, optype['C'][0], struct['C'][0], struct['expr'], n=n*optype['C'][0]['M']))
        self.oplist.append(Option(symbol, optype['D'][0], struct['D'][0], struct['expr'], n=n*optype['D'][0]['M']))
        self.expr = self.oplist[0].expr


#_______________________________________________________________________________
class Template(OpStrat):
    # https://www.optionsplaybook.com/option-strategies/TEMPLATE/
    name = 'Template Name'
    structure = {'A': [{'BS': 0, 'CP': 0, 'M': 0}],
                 'B': [{'BS': 0, 'CP': 0, 'M': 0}],
                 'n': 2
                }

    def __init__(self, symbol, struct, n=s.nContracts):
        self.symbol = symbol
        self.oplist = []
        optype = self.structure
        self.oplist.append(Option(symbol, optype['A'][0], struct['A'][0], struct['expr'], n=n*optype['A'][0]['M']))
        self.oplist.append(Option(symbol, optype['B'][0], struct['B'][0], struct['expr'], n=n*optype['B'][0]['M']))
        self.expr = self.oplist[0].expr
