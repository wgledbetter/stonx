import numpy as np
import datetime
import sys
import os

#-------------------------------------------------------------------------------
def normal(x, mu=0, sig=1):
    return np.exp(-(((x-mu)/sig)**2)/2)/(sig*np.sqrt(2*np.pi))


#-------------------------------------------------------------------------------
def stockPDF(s, t, s0, var, drift=0):
    # Probability of stock price 's' at time 't' given starting price 's0' and variance 'var'
    # Assumes variance 'var' occurs at t=1
    # So if it's weekly variance, t=1 is one week (5 days)
    return (2**(1/2)*np.exp(-np.log((s*np.exp(-t*(- var**2/2 + drift)))/s0)**2/(2*t*var**2)))/(2*np.pi**(1/2)*abs(t)**(1/2)*np.abs(var)*np.abs(s))
    # return np.exp(-np.log(s*np.exp(-t*(-var**2/2 + drift))/s0)**2/(2*t*var**2))/(np.sqrt(2*t*np.pi)*var*s)


#-------------------------------------------------------------------------------
def mktdays_between(start, end):
    ## Asumes 'end' is on a market day -- reasonable for this usage...
    delta = end - start
    current = start
    oneDay = datetime.timedelta(days=1)
    count = datetime.timedelta(days=0)
    while current + oneDay < end:
        if (current + oneDay).isoweekday() > 4:
            fake = 12
        else:
            count += oneDay

        current += oneDay

    oneHour = datetime.timedelta(hours=1)
    while current + oneHour < end:
        count += oneHour
        current += oneHour

    oneMinute = datetime.timedelta(minutes=1)
    while current + oneMinute < end:
        count += oneMinute
        current += oneMinute

    ## Return in decimal days
    return count.total_seconds()/oneDay.total_seconds()


#-------------------------------------------------------------------------------
def getThreads():
    """ Returns the number of available threads on a posix/win based system """
    if sys.platform == 'win32':
        return (int)(os.environ['NUMBER_OF_PROCESSORS'])
    else:
        return (int)(os.popen('grep -c cores /proc/cpuinfo').read())
