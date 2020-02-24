from opstrat import *

allstrats = [IronCondor,
             IronButterfly,
             #--------
             LongStraddle,
             ShortStraddle,
             LongStrangle,
             ShortStrangle,
             #--------
             LongCall,
             LongPut,
             ShortCall,
             ShortPut,
             #--------
             LongCallSpread,
             LongPutSpread,
             ShortCallSpread,
             ShortPutSpread,
             #--------
             BackCallSpread,
             BackPutSpread,
             #--------
             LongCallButterflySpread,
             LongPutButterflySpread,
             InverseCallButterfly,
             InversePutButterfly,
             #--------
             ChristmasTreeCallButterfly,
             FlipChristmasTreeCallButterfly,
             InvChristmasTreeCallButterfly,
             InvFlipChristmasTreeCallButterfly,
             #--------
             ChristmasTreePutButterfly,
             FlipChristmasTreePutButterfly,
             InvChristmasTreePutButterfly,
             InvFlipChristmasTreePutButterfly,
             #--------
             LongCallCondor,
             ShortCallCondor,
             LongPutCondor,
             ShortPutCondor             
]

test_list = [IronCondor,
             LongStraddle,
             ShortStrangle,
             FlipChristmasTreeCallButterfly,
             InvChristmasTreeCallButterfly
            ]
