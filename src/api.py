import os
import os.path
import sys
import requests
import time
from selenium import webdriver
from shutil import which
import urllib.parse as up
import pandas as pd
import numpy as np
import datetime

#-----
import config
import api_urls
import parameters as param
from option import Option


#-------------------------------------------------------------------------------
def td_authentication(client_id, redirect_uri, tdauser=None, tdapass=None):
    client_id = client_id + '@AMER.OAUTHAP'
    url = 'https://auth.tdameritrade.com/auth?response_type=code&redirect_uri=' + up.quote(redirect_uri) + '&client_id=' + up.quote(client_id)

    options = webdriver.ChromeOptions()

    if sys.platform == 'darwin':
        # MacOS
        if os.path.exists("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"):
            options.binary_location = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        elif os.path.exists("/Applications/Chrome.app/Contents/MacOS/Google Chrome"):
            options.binary_location = "/Applications/Chrome.app/Contents/MacOS/Google Chrome"
    elif 'linux' in sys.platform:
        # Linux
        options.binary_location = which('google-chrome') or which('chrome') or which('chromium')

    else:
        # Windows
        if os.path.exists('C:/Program Files (x86)/Google/Chrome/Application/chrome.exe'):
            options.binary_location = 'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe'
        elif os.path.exists('C:/Program Files/Google/Chrome/Application/chrome.exe'):
            options.binary_location = 'C:/Program Files/Google/Chrome/Application/chrome.exe'

    chrome_driver_binary = which('chromedriver') or "/usr/local/bin/chromedriver"
    driver = webdriver.Chrome(chrome_driver_binary, chrome_options=options)

    driver.get(url)

    # Set tdauser and tdapass from environemnt if TDAUSER and TDAPASS environment variables were defined
    tdauser = tdauser or os.environ.get('TDAUSER', '')
    tdapass = tdapass or os.environ.get('TDAPASS', '')

    # Fully automated oauth2 authentication (if tdauser and tdapass were intputed into the function, or found as environment variables)
    if tdauser and tdapass:
        ubox = driver.find_element_by_id('username')
        pbox = driver.find_element_by_id('password')
        ubox.send_keys(tdauser)
        pbox.send_keys(tdapass)
        driver.find_element_by_id('accept').click()

        driver.find_element_by_id('accept').click()
        while 1:
            try:
                code = up.unquote(driver.current_url.split('code=')[1])
                if code != '':
                    break
                else:
                    time.sleep(2)
            except (TypeError, IndexError):
                pass
    else:
        input('after giving access, hit enter to continue')
        code = up.unquote(driver.current_url.split('code=')[1])

    driver.close()

    resp = requests.post('https://api.tdameritrade.com/v1/oauth2/token',
                         headers={'Content-Type': 'application/x-www-form-urlencoded'},
                         data={'grant_type': 'authorization_code',
                               'refresh_token': '',
                               'access_type': 'offline',
                               'code': code,
                               'client_id': client_id,
                               'redirect_uri': redirect_uri})
    if resp.status_code != 200:
        raise Exception('Could not authenticate!')
    return resp.json()


#-------------------------------------------------------------------------------
def td_refresh_token(refresh_token, client_id):
    resp = requests.post('https://api.tdameritrade.com/v1/oauth2/token',
                         headers={'Content-Type': 'application/x-www-form-urlencoded'},
                         data={'grant_type': 'refresh_token',
                               'refresh_token': refresh_token,
                               'client_id': client_id})
    if resp.status_code != 200:
        raise Exception('Could not authenticate!')
    return resp.json()


#-------------------------------------------------------------------------------
class API:
    ## Initialization
    def __init__(self, broker='tdameritrade', token=None, rf_token=None):
        self.broker = broker
        self.token = token
        self.rf_token = rf_token
        self.apiStart()


    def apiStart(self):
        if self.broker == 'tdameritrade':
            if self.token == None:
                r = td_authentication(config.td_consumerkey, 'https://127.0.0.1')
                self.token = r['access_token']
                self.rf_token = r['refresh_token']

        elif self.broker == 'etrade':
            URL = 'https://sbapi.etrade.com/oauth/request_token'


    #---------------------------------------------------------------------------
    ## Http stuff
    def td_headers(self):
        return {'Authorization': 'Bearer ' + self.token}


    def refresh(self):
        if self.broker == 'tdameritrade':
            td_refresh_token(self.rf_token, config.td_consumerkey)


    #---------------------------------------------------------------------------
    ## Basic Methods
    def options(self, symbol, type='ALL', strikeCount=8, weeks=3.5):
        if self.broker == 'tdameritrade':
            enddate = (datetime.datetime.now() + datetime.timedelta(weeks=weeks)).strftime('%Y-%m-%d')
            PARAMS = {'symbol': symbol,
                      'contractType': 'ALL',
                      'strikeCount': strikeCount,
                      'toDate': enddate}
            rq = requests.get(api_urls.TD_OPTIONCHAIN, headers=self.td_headers(), params=PARAMS)
            calls = {}
            callDic = rq.json()['callExpDateMap']
            for d in callDic:
                calls[d] = {}
                for p in callDic[d]:
                    opDic = callDic[d][p][0]
                    calls[d][p] = Option.fromParams(symbol, param.CALL, opDic['last'], 0, float(p), d, ask=float(opDic['ask']), bid=float(opDic['bid']))

            puts = {}
            putDic = rq.json()['putExpDateMap']
            for d in putDic:
                puts[d] = {}
                for p in putDic[d]:
                    opDic = putDic[d][p][0]
                    puts[d][p] = Option.fromParams(symbol, param.PUT, opDic['last'], 0, float(p), d, ask=float(opDic['ask']), bid=float(opDic['bid']))

            return {'calls': calls, 'puts': puts}


    def history_DF(self, symbol, ptype='day', period=10, ftype='minute', freq=15):
        if self.broker == 'tdameritrade':
            PARAMS = {'periodType': ptype,
                      'period': period,
                      'frequencyType': ftype,
                      'frequency': freq,
                      }
            r = requests.get(api_urls.TD_HISTORY%symbol, headers=self.td_headers(), params=PARAMS)
            df = pd.DataFrame(r.json()['candles'])
            return df


    #---------------------------------------------------------------------------
    ## High-Order Methods
    def calcWeeklyVolatility(self, symbol, months=3):
        # Calculate Historical Weekly Volatility
        # Standard deviation of daily high vs. low
        if months >= 1:
            df = self.history_DF(symbol, ptype='month', period=months, ftype='daily', freq=1)
            delta = []
            for i, c in df.iterrows():
                delta.append((c['high'] - c['low'])/c['open'])

            std_day = np.array(delta).std()
            std_wk = std_day*np.sqrt(5)
            return std_wk
        else:
            fake = 69