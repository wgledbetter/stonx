# This is a sample script for generating all possible Ir
# I think I know how I want it to work, but I don't exactly know where to implement it.
# This file's purpose is to establish the algorithm.
# Certain things, like how to generalize what each strategy needs to pull from the option stack, I don't really have any ideas for right now.
# I'd like the call signature to look something like
#     stratlist = genstrats(IronCondor, opchain)
# but I don't know if I can pass in enough data with the IronCondor typename for a generic algorithm genstrats() to operate.  --> @classmethod
# Really I need some kind of datatype or convention to define buy/sell call/put at each hierarchical strike price.
# opstrat.structure()
#     return {'A': [p.SELL, p.PUT, 1], 'B': [p.BUY, p.CALL, 2], 'C': [p.BUY, p.PUT, 1]}