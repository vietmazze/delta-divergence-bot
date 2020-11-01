from binance.client import Client
from binance.websockets import BinanceSocketManager
from twisted.internet import reactor
import schedule
import time
import keyboard

class Chart:
    def __init__(self):
        self.time = []
        self.ohlc = []
        self.buy_volume = []
        self.sell_volume = []

    def append(self, time, ohlc, buy_volume, sell_volume):
        self.time.append(time)
        self.ohlc.append(ohlc)
        self.buy_volume.append(buy_volume)
        self.sell_volume.append(sell_volume)

class bcolors:
    HEADER = '\033[95m'
    RED = '\u001b[31m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def process_message(msg):
    global trades
    trade = dict()
    try:
        trade['price'] = float(msg['p'])
        trade['volume'] = float(msg['q']) * float(msg['p'])
        trade['side'] = 'None'
        if msg['m'] == False:
            trade['side'] = "Buy"
        if msg['m'] == True:
            trade['side'] = "Sell"
        
        trades.append(trade)
        #print(trade)

    except KeyError:
        print(msg)

def save_volume():
    global trades

    temp_trades = trades
    trades = []

    buy_volume = 0
    sell_volume = 0
    for trade in temp_trades:
        
        if trade['side'] == "Buy":
            buy_volume = buy_volume + trade['volume']
        if trade['side'] == "Sell":
            sell_volume = sell_volume + trade['volume']

    print("BUY VOLUME = %.2f" % buy_volume)
    print("SELL VOLUME = %.2f" % sell_volume)
    delta = buy_volume-sell_volume
    if delta >= 0:
        print("DELTA = %.2f" % delta)
    else:
        print("DELTA = %.2f" % delta)
    print("\n")

    


#----------------------------------------------#
#---------------FINE FUNZIONI------------------#
#----------------------------------------------#

try:
    
    trades = []

    print("input ticker: ")
    ticker = input().lower()

    print("input timeframe in minutes: ")
    timeframe = int(input())

    client = Client()
    bm = BinanceSocketManager(client)
    bm.start()
    conn_key = bm.start_aggtrade_socket(ticker, process_message)

    schedule.every(timeframe).minutes.at(":00").do(save_volume)
    while True:
        schedule.run_pending()
        time.sleep(1)

except KeyboardInterrupt:
    reactor.stop()