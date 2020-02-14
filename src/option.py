import parameters

MULT = 100

class Option:
    ## Init
    def __init__(self, symbol, CP, enter_price, BS, strike, expr, n=10, ask=0, bid=0):
        self.symbol = symbol
        self.CP = CP
        self.enter_price = enter_price
        self.BS = BS
        self.strike = strike
        self.expr = expr
        self.n = n
        self.ask = ask
        self.bid = bid


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
            option_price = self.enter_price
        return self.n*(MULT*self.BS*option_price + parameters.option_commission)


    def exerciseValue(self, stock_price):
        return -self.cost() + self.inTheMoney(stock_price)*self.n*MULT*self.CP*(stock_price - self.strike)


    def exitValue(self, option_price):
        return -self.BS*MULT*self.n*(self.enter_price - option_price) - 2*self.n*parameters.option_commission