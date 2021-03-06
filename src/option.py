from datetime import datetime, timedelta
import pytz
from tzlocal import get_localzone

import parameters as p
from functions import mktdays_between
import settings as s

MULT = 100

class Option:
    ## Init
    def __init__(self, symbol, optype, prices, expr, n=s.nContracts, ask=0, bid=0):
        self.symbol = symbol
        self.CP = optype['CP']
        self.premium = prices['premium']
        self.BS = optype['BS']
        self.strike = prices['strike']
        try:
            self.expr = datetime.strptime(expr[0:10], '%Y-%m-%d').replace(hour=17, minute=30, tzinfo=pytz.timezone(zone='America/New_York'))
        except:
            self.expr = expr
        self.n = n
        self.ask = ask
        self.bid = bid


    def __str__(self):
        return '{}: BS = {}, CP = {}, Strike = {}, Premium = {}, n = {}'.format(self.symbol, self.BS, self.CP, self.strike, self.premium, self.n)


    def __repr__(self):
        return '{}: BS = {}, CP = {}, Strike = {}, Premium = {}, n = {}'.format(self.symbol, self.BS, self.CP, self.strike, self.premium, self.n)


    @classmethod
    def fromParams(cls, symbol, CP, premium, BS, strike, expr, n=s.nContracts, ask=0, bid=0):
        prices = {'premium': premium, 'strike': strike}
        optype = {'CP': CP, 'BS': BS}
        return cls(symbol, optype, prices, expr, n=n, ask=ask, bid=bid)


    #---------------------------------------------------------------------------
    ## Measures
    def inTheMoney(self, stock_price):
        if stock_price > self.strike:
            return self.CP == 1  # Evals true when option is a call and stock is above strike
        elif stock_price == self.strike:
            return False
        else:
            return self.CP == -1  # Evals true when option is a put and stock is below strike


    def cost(self, option_price=None):
        if option_price == None:
            option_price = self.premium
        return self.n*(MULT*self.BS*option_price + p.option_commission)


    def exerciseValue(self, stock_price):
        return -self.cost() + self.inTheMoney(stock_price)*self.n*MULT*self.CP*self.BS*(stock_price - self.strike)


    def exitValue(self, option_price):
        return -self.BS*MULT*self.n*(self.premium - option_price) - 2*self.n*p.option_commission


    def remainingTime(self):
        now = datetime.now().replace(tzinfo=get_localzone())
        return self.expr - now

    def remainingDays(self):
        dt = self.remainingTime()
        return dt.total_seconds()/timedelta(days=1).total_seconds()

    def remainingMarketDays(self):
        now = datetime.now().replace(tzinfo=get_localzone())
        return mktdays_between(now, self.expr)


    #---------------------------------------------------------------------------
    ## API Commands
    def update(self, api):
        self.premium = api.optionPrice(self.symbol, self.CP, self.strike, self.expr.strftime('%Y-%m-%d'))


    def execute(self, api):
        return 69