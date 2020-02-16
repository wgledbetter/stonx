import numpy as np
np.set_printoptions(edgeitems=30, linewidth=100000, 
    formatter=dict(float=lambda x: "%.3g" % x))

def rk(bTab, func, tSpan, dt, y0):
    ## Preliminary
    rows, cols = bTab.shape
    try:
        dim = max(y0.shape)
    except:
        dim = 1
        
    stages = cols - 1
    
    a = bTab[0:cols, 1:cols]
    b = bTab[cols-1, 1:cols+1]
    c = bTab[0:cols, 0]
    
    
    ## Setup
    t0 = tSpan[0]
    tf = tSpan[1]
    tLen = tf - t0
    steps = int(round(tLen/dt))
    h = tLen/steps
    
    t = np.linspace(t0, tf, num=steps)
    y = np.zeros((steps+1,dim))
    y[0,:] = y0
    
    
    ## Integrate
    for i in range(steps):
        sum_bk = 0
        k = np.zeros((stages, dim))
        for s in range(stages):
            yTerm = 0
            for j in range(s-1):
                yTerm += a[s,j]*k[j,:]
                
            ys = y[i,:] + h*yTerm
            ts = t[i] + c[s]*h
            k[s,:] = func(ts, ys)
            sum_bk += b[s]*k[s,:]
            
        y[i+1,:] = y[i,:] + h*sum_bk
        
    
    return t, y