import requests
import json
import time
import csv

milliTime = lambda: int(round(time.time() * 1000))
endpoint = "https://api.binance.com"
general_info = "/api/v3/ticker/24hr"
aggr_orders = "/api/v3/aggTrades"
btc_price = 10000

class Pair:
    def __init__(self, ticker, volume, price):
        self.ticker = ticker
        self.volume = volume
        self.price = price
    
    def print(self):
        return self.ticker, self.volume, self.price

def getBtcList():
    pair_list_btc = []

    try:
        r = requests.get(endpoint+general_info, timeout = 5)
    except (
        requests.ConnectionError,
        requests.exceptions.ReadTimeout,
        requests.exceptions.Timeout,
        requests.exceptions.ConnectTimeout,
    ) as e:
        print(e)

    if r is not None:
        data = r.json()
        for line in data:
            if line["symbol"].endswith("BTC"):
                pair_list_btc.append(Pair(line["symbol"],float(line["quoteVolume"]),float(line["lastPrice"])))

    if pair_list_btc is not [] and len(pair_list_btc) <= 1024:
        return pair_list_btc
    elif len(pair_list_btc) <= 1024:
        print("BTC LIST TOO LONG")

    print("Error in getBtcList")

def getTop100List(collateral):
    global btc_price
    pair_list_btc = []
    pair_list_usdt = []

    try:
        r = requests.get(endpoint+general_info, timeout = 5)
    except (
        requests.ConnectionError,
        requests.exceptions.ReadTimeout,
        requests.exceptions.Timeout,
        requests.exceptions.ConnectTimeout,
    ) as e:
        print(e)

    if r is not None:
        data = r.json()
        for line in data:
            if line["symbol"].endswith("BTC"):
                pair_list_btc.append(Pair(line["symbol"],float(line["quoteVolume"]),float(line["lastPrice"])))
            if line["symbol"].endswith("USDT"):
                pair_list_usdt.append(Pair(line["symbol"],float(line["quoteVolume"]),float(line["lastPrice"])))
            if line["symbol"] == "BTCUSDT":
                btc_price = float(line["lastPrice"])

    if collateral == "BTC":
        if pair_list_btc is not []:
            sorted_btc_list = sorted(pair_list_btc, key = lambda x: x.volume)
            unified_list = sorted_btc_list[100:]
            return unified_list
    if collateral == "USDT":
        if pair_list_usdt is not []:
            sorted_usdt_list = sorted(pair_list_usdt, key = lambda x: x.volume)
            unified_list = sorted_usdt_list[100:]
            return unified_list
    print("Error in getTop100List")

def checkOrderbook(pair, last_id):
    buy_volume = 0.0
    sell_volume = 0.0
    r = None

    if last_id == 0:
        parameters = "?symbol=" + pair.ticker + "&limit=10"
    else:
        parameters = "?symbol=" + pair.ticker + "&fromId=" + str(last_id) + "&limit=1000"

    try:
        print(parameters)
        r = requests.get(endpoint + aggr_orders + parameters, timeout = 5)
    except (
        requests.ConnectionError,
        requests.exceptions.ReadTimeout,
        requests.exceptions.Timeout,
        requests.exceptions.ConnectTimeout,
    ) as e:
        print(e)
    
    if r is not None:
        data = r.json()
        for line in data:
            try:
                if line["m"] == "false":
                    buy_volume = buy_volume + (float(line["q"]) * float(line["p"]))
                if line["m"] == "true":
                    sell_volume = sell_volume + (float(line["q"]) * float(line["p"]))
            except TypeError:
                print(data)
        try:
            temp_id = data[-1]["T"]
            last_id = temp_id
        except IndexError:
            last_id = last_id
    
    if last_id is not None:
        return buy_volume, sell_volume, last_id
    else:
        print("Error in checkOrderbook")
