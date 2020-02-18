import parameters as p

MULT = 100

class Option:
    ## Init
    def __init__(self, symbol, optype, prices, expr, n=10, ask=0, bid=0):
        self.symbol = symbol
        self.CP = optype['CP']
        self.premium = prices['premium']
        self.BS = optype['BS']
        self.strike = prices['strike']
        self.expr = expr
        self.n = n
        self.ask = ask
        self.bid = bid


    @classmethod
    def fromParams(cls, symbol, CP, premium, BS, strike, expr, n=10, ask=0, bid=0):
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