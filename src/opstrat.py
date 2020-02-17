import plotly.offline as py
import plotly.graph_objs as go
import numpy as np
from scipy.special import erf

from option import Option
import parameters as p
from dopri import dopri

# Plotting setup
PLOT_EDGE = 0.02
PLOT_RES = 250


# Functions
def normal(x, mu=0, sig=1):
    return np.exp(-(((x-mu)/sig)**2)/2)/(sig*np.sqrt(2*np.pi))


class OpStrat:
    def __init__(self, oplist=[]):
        self.oplist = oplist


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
        im = True
        for op in self.oplist:
            im = im and op.inTheMoney(stock_price)

        return im


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


    def plotProb(self, price, vol, filename):
        pTrace = self.profitTrace()
        prob = []
        for p in pTrace.x:
            prob.append(normal(p, mu=price, sig=vol*price))

        prbTrace = go.Scatter(x=pTrace.x, y=prob, text=pTrace.y, mode='lines', line_width=3, name=self.name)
        layout = go.Layout(scene=dict(xaxis=dict(title_text='Stock Price ($)'),
                                      yaxis=dict(title_text='Probability')
                                      )
                           )
        fig = go.Figure(data=[prbTrace], layout=layout)
        py.plot(fig, './probability_{}_{}_{}.html'.format(filename, self.name, self.symbol))


    def expectedProfit(self, stock_price, vol):
        def fun(pr, dummy):
            prf = self.exerciseValue(pr)
            prb = normal(pr, stock_price, vol*stock_price)
            return np.array([prf*prb])

        pSpan = np.array([0, 3*stock_price])
        dp = stock_price/250
        e0 = np.array([0])
        ep = dopri(fun, pSpan, dp, e0)
        return ep[1][-1][0]


    def probOfProfit(self, stock_price, vol):
        def fun(pr, dummy):
            good = (self.exerciseValue(pr) >= 0)
            prb = normal(pr, stock_price, vol*stock_price)
            return np.array([good*prb])

        pSpan = np.array([0, 3*stock_price])
        dp = stock_price/250
        e0 = np.array([0])
        ep = dopri(fun, pSpan, dp, e0)
        return ep[1][-1][0]


    #---------------------------------------------------------------------------
    ## Generate
    @classmethod
    def gen(cls, stratname, opchain):
        # Returns list of all possible "stratnames" on the options "opchain"
        # opchain = {'calls': {'date1': {'strike1': Option(), 'strike2': Option()}, 'date2': {...}}, 'puts': {'date': {'strike': Option()}}}
        # First check overlap in put and call strikes
        callstrikes = []
        calldate0 = next(iter(opchain['calls']))
        for cs in opchain['calls'][calldate0]:
            callstrikes.append(cs)

        putstrikes = []
        putdate0 = next(iter(opchain['puts']))
        for ps in opchain['puts'][putdate0]:
            putstrikes.append(ps)



################################################################################
class IronCondor(OpStrat):
    # https://www.optionsplaybook.com/option-strategies/iron-condor/
    def __init__(self, symbol, A_st, A_pr, B_st, B_pr, C_st, C_pr, D_st, D_pr, expr, n=10):
        self.name = 'Iron Condor'
        self.symbol = symbol
        self.oplist = []
        self.oplist.append(Option(symbol, p.PUT, A_pr, p.BUY, A_st, expr=expr, n=n))
        self.oplist.append(Option(symbol, p.PUT, B_pr, p.SELL, B_st, expr=expr, n=n))
        self.oplist.append(Option(symbol, p.CALL, C_pr, p.SELL, C_st, expr=expr, n=n))
        self.oplist.append(Option(symbol, p.CALL, D_pr, p.BUY, D_st, expr=expr, n=n))


    @classmethod
    def structure(cls):
        return {'A': [{'BS': p.BUY, 'CP': p.PUT, 'M': 1}],
                'B': [{'BS': p.SELL, 'CP': p.PUT, 'M': 1}],
                'C': [{'BS': p.SELL, 'CP': p.CALL, 'M': 1}],
                'D': [{'BS': p.BUY, 'CP': p.CALL, 'M': 1}],
                'n': 4
                }


#_______________________________________________________________________________
class IronButterfly(OpStrat):
    # https://www.optionsplaybook.com/option-strategies/iron-butterfly/
    def __init__(self, symbol, A_st, A_pr, B_st, B_ppr, B_cpr, C_st, C_pr, expr, n=10):
        self.name = 'Iron Butterfly'
        self.symbol = symbol
        self.oplist = []
        self.oplist.append(Option(symbol, p.PUT, A_pr, p.BUY, A_st, expr=expr, n=n))
        self.oplist.append(Option(symbol, p.PUT, B_ppr, p.SELL, B_st, expr=expr, n=n))
        self.oplist.append(Option(symbol, p.CALL, B_cpr, p.SELL, B_st, expr=expr, n=n))
        self.oplist.append(Option(symbol, p.CALL, C_pr, p.BUY, C_st, expr=expr, n=n))


    @classmethod
    def structure(cls):
        return {'A': [{'BS': p.BUY, 'CP': p.PUT, 'M': 1}],
                'B': [{'BS': p.SELL, 'CP': p.PUT, 'M': 1},
                      {'BS': p.SELL, 'CP': p.CALL, 'M': 1}],
                'C': [{'BS': p.BUY, 'CP': p.CALL, 'M': 1}],
                'n': 4,
                }


#_______________________________________________________________________________
class LongStraddle(OpStrat):
    # https://www.optionsplaybook.com/option-strategies/long-straddle/
    def __init__(self, symbol, A_st, A_ppr, A_cpr, expr, n=10):
        self.name = 'Long Straddle'
        self.symbol = symbol
        self.oplist = []
        self.oplist.append(Option(symbol, p.CALL, A_cpr, p.BUY, A_st, expr=expr, n=n))
        self.oplist.append(Option(symbol, p.PUT, A_ppr, p.BUY, A_st, expr=expr, n=n))


    @classmethod
    def structure(cls):
        return {'A': [{'BS': p.BUY, 'CP': p.CALL, 'M': 1},
                      {'BS': p.BUY, 'CP': p.PUT, 'M': 1}],
                'n': 2,
                }


#_______________________________________________________________________________
class LongStrangle(OpStrat):
    # https://www.optionsplaybook.com/option-strategies/long-strangle/
    def __init__(self, symbol, A_st, A_pr, B_st, B_pr, expr, n=10):
        self.name = 'Long Strangle'
        self.symbol = symbol
        self.oplist = []
        self.oplist.append(Option(symbol, p.PUT, A_pr, p.BUY, A_st, expr=expr, n=n))
        self.oplist.append(Option(symbol, p.CALL, B_pr, p.BUY, B_st, expr=expr, n=n))


    @classmethod
    def structure(cls):
        return {'A': [{'BS': p.BUY, 'CP': p.PUT, 'M': 1}],
                'B': [{'BS': p.BUY, 'CP': p.CALL, 'M': 1}],
                'n': 2,
                }


#_______________________________________________________________________________
class SkStPutButterfly(OpStrat):
    # https://www.optionsplaybook.com/option-strategies/broken-wing-butterfly-put/
    def __init__(self, symbol, A_st, A_pr, C_st, C_pr, D_st, D_pr, expr, n=10):
        self.name = 'Broken Wing Put Butterfly'
        self.symbol = symbol
        self.oplist = []
        self.oplist.append(Option(symbol, p.PUT, A_pr, p.BUY, A_st, expr=expr, n=n))
        self.oplist.append(Option(symbol, p.PUT, C_pr, p.SELL, C_st, expr=expr, n=2*n))
        self.oplist.append(Option(symbol, p.PUT, D_pr, p.BUY, D_st, expr=expr, n=n))


    @classmethod
    def structure(cls):
        return {'A': [{'BS': p.BUY, 'CP': p.PUT, 'M': 1}],
                'B': [{'BS': p.SELL, 'CP': p.PUT, 'M': 2}],
                'C': [{'BS': p.BUY, 'CP': p.PUT, 'M': 1}],
                'n': 3,
                }