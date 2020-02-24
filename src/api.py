import numpy as np

class API:

    def __init__(self):
        self.dummy = 4


    #---------------------------------------------------------------------------
    def calcWeeklyVolatility(self, symbol, months=3):
        # Calculate Historical Weekly Volatility as a percentage
        # Standard deviation of daily high vs. low
        if months >= 1:
            df = self.history_DF(symbol, ptype='month', period=months, ftype='daily', freq=1)
            delta = []
            for i, c in df.iterrows():
                delta.append((c['high'] - c['low'])/c['open'])

            std_day = np.array(delta).std()
            std_wk = std_day*np.sqrt(5)  # Assume 5-day market week
            return std_wk
        else:
            fake = 69