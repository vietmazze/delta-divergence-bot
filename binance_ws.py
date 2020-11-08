from unicorn_binance_websocket_api.unicorn_binance_websocket_api_manager import BinanceWebSocketApiManager
from unicorn_fy.unicorn_fy import UnicornFy
import logging
import time
import os
import threading
import json
import numpy as np
from typing import Optional, Dict, Any, List
from colorprint import ColorPrint
from colorama import Fore, Back, Style, init

logging.basicConfig(level=logging.INFO, format=(
    Fore.BLUE + '[+] ' + Style.RESET_ALL + '%(message)s '))


class BinanceWebSocket:
    def __init__(self) -> None:
        self.prices = []
        self.delta = []
        self.trades = []
        self.binance_websocket_manager = BinanceWebSocketApiManager(
            exchange="binance.com-futures")
        self.channels = {}
        self.markets = {}
        self.log = ColorPrint()

    def create_streams(self):
        self.streams= self.binance_websocket_manager.create_stream(self.channels,self.markets)
        
    def get_stream_data_buffer(self):
        print("Initialize, wait 30secs for streams to come in")
        time.sleep(5)
        while True:
            if self.binance_websocket_manager.is_manager_stopping():
                exit(0)

            oldest_stream = UnicornFy.binance_com_futures_websocket(
                self.binance_websocket_manager.pop_stream_data_from_stream_buffer())
            if oldest_stream is False:
                time.sleep(0.01)
            else:
                try:
                    process_aggTrade(oldest_stream)

                except KeyError:
                    print("error printing data")
                    # not able to process the data? write it back to the stream_buffer
                    self.binance_websocket_manager.add_to_stream_buffer(
                        oldest_stream)

    def process_aggTrade(data):
        trade = {}
        price = {}
        try:
            if data['event_type'] == "aggTrade":

                trade['volume'] = float(
                    data['quantity']) * float(data['price'])
                trade['side'] = 'None'
                if data['is_market_maker'] == False:
                    trade['side'] = "Buy"
                elif data['is_market_maker'] == True:
                    trade['side'] = "Sell"
                self.trades.append(trade)
            if data['event_type'] == "kline":
                if data['kline']['isClosed']:
                    price['symbol'] = data['symbol']
                    price['interval'] = data['kline']['interval']
                    price['curr_time'] = data['event_time']
                    price['close_time'] = data['kline']['kline_close_time']
                    price['close_price'] = data['kline']['close_price']                   
                    self.prices.append(price)
    #   trades = [{side:"buy",volume:2000},{..},{..}]
        except Exception as e:
            self.log.red(
                f'Exception when processing buffer_stream in process_aggTrade(): \n {e}')
    def process_totalPrice(self) -> None:
        temp_prices= self.prices
        price_tag = []
        try:
            for price in temp_prices:
                price_tag.append(price['close_price'])
            self.calc_priceDivergence(price_tag)
        except Exception as e:
            pass
    def process_totalVolume(self) -> None:
        temp_trades = self.trades
        buy_volume = 0
        sell_volume = 0
        try:
            for trade in temp_trades:
                if trade['side'] == "Sell":
                    sell_volume += trade['volume']
                elif trade['side'] == "Buy":
                    buy_volume += trade['volume']
            currDelta = buy_volume - sell_volume
            self.delta.append(currDelta)
        except Exception as e:
            self.log.red(
                f'Exception when processing in process_totalVolume():  \n {e}')

    def calc_volumeDivergence():
        delta = self.delta
        neg_deltaDiv = [False] for __ in range(len(delta))
        pos_deltaDiv = [False] for __ in range(len(delta))
        # [positive,negative,negative]
        # [negative,negative,positive]

        # check for negative vol Bearish:
        try:
            if max(delta) < 0:
                # [-100,-200,-300]
                for i in range(len(delta)):
                    if delta[i] > delta[i+1]:
                        neg_deltaDiv[i] = True
                    else:
                        neg_deltaDiv[i] = False
        # check for positive vol Bullish:
            elif min(delta) > 0:
                # [300,200,100]
                for i in range(0, len(delta)):
                    if delta[i] > delta[i+1]:
                        pos_deltaDiv[i] = True
                    else:
                        pos_deltaDiv[i] = False
        except Exception as e:
            self.log.red(
                f'Exception when processing in calc_deltaDivergence():  \n {e}')

    def calc_priceDivergence(price_tag):
        #price_tag = []
        price_decrease = [False] for __ in range(len(price_tag))
        price_increase = [False] for __ in range(len(price_tag))
        for i in range(len(price_tag)):
            if price_tag[i] > price_tag[i+1]:
                price_decrease[i] = True
            else:
                price_decrease[i] = False
        for i in range(len(price_tag)):
            if price_tag[i] < price_tag[i+1]:
                price_increase[i] = True
            else:
                price_increase[i] = False

def main():
    input("Starting Binance Websocket")
    try:
        # calling Binance manager.
    except expression as identifier:
        pass


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print("Cannot start binance_ws.py, please check logs")
    finally:
        exit()
