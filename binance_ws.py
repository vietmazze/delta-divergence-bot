import collections
import logging
import time
import os
import threading
import json
import schedule
import numpy as np
import asyncio

from unicorn_binance_websocket_api.unicorn_binance_websocket_api_manager import BinanceWebSocketApiManager
from unicorn_fy.unicorn_fy import UnicornFy
from timer import Timer
from typing import Optional, Dict, Any, List
from colorprint import ColorPrint
from colorama import Fore, Back, Style, init

logging.basicConfig(level=logging.INFO, format=(
    Fore.BLUE + '[+] ' + Style.RESET_ALL + '%(message)s '))

"""
*self.prices = []  price from process_aggTrade(self, data)
*self.agg_trades = []trades from each individual trade in process_aggTrade(self, data) 
*self.total_volume = {}  Buy/Sell volume from each trade combined
*self.total_deltas = []  Each net_volume calculated from total_volume with the current timestamp price

"""


class BinanceWebSocket:
    def __init__(self,) -> None:
        self.prices = []
        self.agg_trades = []
        self.total_volume = {'sell_volume': 0, 'buy_volume': 0, 'timestamp': 0}
        self.total_deltas = []
        self.bearish_delta = []
        self.bullish_delta = []
        self.binance_websocket_manager = BinanceWebSocketApiManager(
            exchange="binance.com-futures")
        self.channels = {'aggTrade', 'kline_1m'}
        self.markets = {'btcusdt'}
        self.log = ColorPrint()
        self.timer = Timer()

    def create_streams(self):
        try:
            self.binance_websocket_manager.create_stream(
                self.channels, self.markets)

        except Exception as e:
            self.log.red(
                f'Unable to create streams with {self.channels} and {self.markets}')

    def get_stream_data_buffer(self):
        self.log.yellow("Initialize, wait 5secs for streams to come in")
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
                    if len(oldest_stream) > 4:
                        self.process_aggTrade(oldest_stream)
                    else:
                        pass
                except KeyError:
                    self.log.red(
                        f'Unable to call process_aggTrade() from get_stream_data_buffer()')
                    # not able to process the data? write it back to the stream_buffer
                    self.binance_websocket_manager.add_to_stream_buffer(
                        oldest_stream)

    def process_aggTrade(self, data):
        trade = {}
        price = {}
        try:
            if data['event_type'] == "aggTrade":
                trade['symbol'] = data['symbol']
                trade['curr_time'] = data['event_time']
                trade['volume'] = float(
                    data['quantity']) * float(data['price'])
                trade['side'] = 'None'
                if data['is_market_maker'] == False:
                    trade['side'] = "Buy"
                elif data['is_market_maker'] == True:
                    trade['side'] = "Sell"
                self.agg_trades.append(trade)
            # Continue to grab this grab this data, maybe once this is trigger we can THEN call delta_divergence()
            elif data['event_type'] == "kline":
                if data['kline']['is_closed']:
                    price['symbol'] = data['symbol']
                    price['timeframe'] = data['kline']['interval']
                    price['curr_time'] = data['event_time']
                    price['start_time'] = data['kline']['kline_start_time']
                    price['close_time'] = data['kline']['kline_close_time']
                    price['open'] = data['kline']['open_price']
                    price['close'] = data['kline']['close_price']
                    price['high'] = data['kline']['high_price']
                    price['low'] = data['kline']['low_price']
                    self.prices.append(price)
                    self.log.green(
                        "Closed price event found, init process_totalVolume")
                    self.process_totalVolume()
                    self.process_combineData()

        except Exception as e:
            self.log.red(
                f'Exception when processing buffer_stream in process_aggTrade(): \n {e}')

    def process_totalVolume(self) -> None:
        curr_agg_trades = self.agg_trades
        self.timer.start()
        try:
            for trade in curr_agg_trades:
                if trade['side'] == "Sell":
                    #self.sell_volume += trade['volume']
                    self.total_volume['sell_volume'] += float(trade['volume'])
                elif trade['side'] == "Buy":
                    #self.buy_volume += trade['volume']
                    self.total_volume['buy_volume'] += float(trade['volume'])
                self.total_volume['timestamp'] = trade['curr_time']
            self.agg_trades = []
        except Exception as e:
            self.log.red(
                f'Exception when processing in process_totalVolume():  \n {e}')
        self.timer.stop()

    def process_combineData(self) -> None:
        price = []
        delta = 0
        if len(self.total_volume) > 0:
            try:
                if len(self.total_volume) > 0 and len(self.prices) > 0:
                    delta = float(
                        self.total_volume['buy_volume'] - self.total_volume['sell_volume'])
                    price = self.prices.pop()

                total_delta = {
                    "timestamp": float(price['curr_time']) if price['curr_time'] else 0,
                    "delta": float(delta),
                    "price": float(price['close']) if price['close'] else 0,
                }
                try:
                    self.total_deltas.append(total_delta)
                except Exception as e:
                    self.log.red("Unable to append to total_deltas")
                self.print_data()
            except Exception as e:
                self.log.red(f'Exception error in process_combineData() {e}')

    def calc_volumeDivergence(self):
        deltas = self.vol_deltas
        bearish_delta = [False for __ in range(len(deltas))]
        bullish_delta = [False for __ in range(len(deltas))]

        try:
            for i in range(len(deltas)-1):
                # bearish
                if deltas[i] > deltas[i+1]:
                    # only accept positive entries:
                    if deltas[i] > 0 and deltas[i+1] > 0:
                        bearish_delta[i] = True
                        bearish_delta[i+1] = True

                elif deltas[i] < deltas[i+1]:
                    if deltas[i] < 0 and deltas[i+1] < 0:
                        bullish_delta[i] = True
                        bullish_delta[i+1] = True
                else:
                    self.log.blue(
                        f'Condition not met for deltas in calc_volumeDiv, {deltas[i]} vs {deltas[i+1]}')
            self.bearish_delta = bearish_delta
            self.bullish_delta = bullish_delta
        except Exception as e:
            self.log.red(
                f'Exception when processing in calc_deltaDivergence():  \n {e}')

    def print_data(self):
        self.log.green(f"""
                        Delta: {self.total_deltas}""")

    def load_thread(self):
        # start a worker process to move the received stream_data from the stream_buffer to a print function
        worker_thread = threading.Thread(
            target=self.get_stream_data_buffer, args=())
        worker_thread.start()


def main():
    cp.green(f'Starting Binance WebSocket Manager')
    try:

        # calling Binance manager.
        binance = BinanceWebSocket()
        binance.create_streams()
        binance.load_thread()
        time.sleep(5)
        schedule.every(1).minutes.do(binance.process_totalVolume)
        # schedule.every(1).minutes.do(binance.process_combineData)
        # schedule.every(1).minutes.do(binance.print_data)
        while True:
            schedule.run_pending()
            time.sleep(1)

    except Exception as ex:
        cp.red(f'Failed to start main() {ex}')


if __name__ == '__main__':
    try:
        cp = ColorPrint()
        main()
    except Exception as e:
        cp.red("Cannot start binance_ws.py, please check logs")
    finally:
        exit()
