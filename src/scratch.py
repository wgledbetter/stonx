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

def gen(cls, opchain, n=10):
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
            print('Mixed call/put chain sizes for date {}'.format(date))
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

        # Generate strategy from dict
    strats = []
    for st in stratdefs:
        strats.append(cls(symb, st, n=n))

    return strats


################################################################################

# df = tdam.history_DF('TSLA')
# vol = tdam.calcWeeklyVolatility('TSLA', months=2)


# from option import Option
# from opstrat import IronButterfly

# data = {'A': [{'strike': 320, 'premium': 3.7}],
#         'B': [{'strike': 325, 'premium': 6},
#               {'strike': 325, 'premium': 2}],
#         'C': [{'strike': 330, 'premium': 3.8}],
#         'expr': '2020'
#         }
# irb = IronButterfly('AAPL',data)
# ep = irb.expectedProfit(330, 0.05)
# breakpoint()


# opchain = tdam.options('AAPL', weeks=3)
# strats = IronButterfly.gen(opchain)
# breakpoint()
