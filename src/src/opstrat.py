import plotly.offline as py
import plotly.graph_objs as go
import numpy as np

from option import Option

PLOT_EDGE = 0.05
PLOT_RES = 200

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


    #---------------------------------------------------------------------------
    ## Analysis
    def exerciseProfitChart(self, filename):
        self.oplist.sort(key=lambda x: x.strike)
        spread = self.oplist[-1].strike - self.oplist[0].strike
        pMin = self.oplist[0].strike*(1-PLOT_EDGE)
        pMax = self.oplist[-1].strike*(1+PLOT_EDGE)
        prices = np.linspace(pMin, pMax, PLOT_RES)
        profit = []
        for p in prices:
            profit.append(self.exerciseValue(p))

        trace = go.Scatter(x=prices, y=profit, mode='lines', line_width=3, name=self.name)

        layout = go.Layout(scene=dict(xaxis=dict(title_text='Stock Price ($)'),
                                      yaxis=dict(title_text='Net Outcome ($)')
                                      )
                           )
        fig = go.Figure(data=[trace], layout=layout)
        py.plot(fig, './{}_{}_{}.html'.format(filename, self.name, self.symbol))



################################################################################
# Need to rethink constructors bc put and call prices are different
class IronCondor(OpStrat):
    # https://www.optionsplaybook.com/option-strategies/iron-condor/
    def __init__(self, symbol, A_st, A_pr, B_st, B_pr, C_st, C_pr, D_st, D_pr, expr, n=10):
        self.name = 'Iron Condor'
        self.symbol = symbol
        self.oplist = []
        self.oplist.append(Option(symbol, -1, A_pr, 1, A_st, expr=expr, n=n))
        self.oplist.append(Option(symbol, -1, B_pr, -1, B_st, expr=expr, n=n))
        self.oplist.append(Option(symbol, 1, C_pr, -1, C_st, expr=expr, n=n))
        self.oplist.append(Option(symbol, 1, D_pr, 1, D_st, expr=expr, n=n))


#_______________________________________________________________________________
class IronButterfly(OpStrat):
    # https://www.optionsplaybook.com/option-strategies/iron-butterfly/
    def __init__(self, symbol, A_st, A_pr, B_st, B_pr, C_st, C_pr, expr, n=10):
        self.name = 'Iron Butterfly'
        self.symbol = symbol
        self.oplist = []
        self.oplist.append(Option(symbol, -1, A_pr, 1, A_st, expr=expr, n=n))
        self.oplist.append(Option(symbol, -1, B_pr, -1, B_st, expr=expr, n=n))
        self.oplist.append(Option(symbol, 1, B_pr, -1, B_st, expr=expr, n=n))
        self.oplist.append(Option(symbol, 1, C_pr, 1, C_st, expr=expr, n=n))


#_______________________________________________________________________________
class LongStraddle(OpStrat):
    # https://www.optionsplaybook.com/option-strategies/long-straddle/
    def __init__(self, symbol, A_st, A_pr, expr, n=10):
        self.name = 'Long Straddle'
        self.symbol = symbol
        self.oplist = []
        self.oplist.append(Option(symbol, 1, A_pr, 1, A_st, expr=expr, n=n))
        self.oplist.append(Option(symbol, -1, A_pr, 1, A_st, expr=expr, n=n))


#_______________________________________________________________________________
class LongStrangle(OpStrat):
    # https://www.optionsplaybook.com/option-strategies/long-strangle/
    def __init__(self, symbol, A_st, A_pr, B_st, B_pr, expr, n=10):
        self.name = 'Long Strangle'
        self.symbol = symbol
        self.oplist = []
        self.oplist.append(Option(symbol, -1, A_pr, 1, A_st, expr=expr, n=n))
        self.oplist.append(Option(symbol, 1, B_pr, 1, B_st, expr=expr, n=n))


#_______________________________________________________________________________
class SkStPutButterfly(OpStrat):
    # https://www.optionsplaybook.com/option-strategies/broken-wing-butterfly-put/
    def __init__(self, symbol, A_st, A_pr, C_st, C_pr, D_st, D_pr, expr, n=10):
        self.name = 'Broken Wing Put Butterfly'
        self.symbol = symbol
        self.oplist = []
        self.oplist.append(Option(symbol, -1, A_pr, 1, A_st, expr=expr, n=n))
        self.oplist.append(Option(symbol, -1, C_pr, -1, C_st, expr=expr, n=2*n))
        self.oplist.append(Option(symbol, -1, D_pr, 1, D_st, expr=expr, n=n))