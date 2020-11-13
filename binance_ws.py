from unicorn_binance_websocket_api.unicorn_binance_websocket_api_manager import BinanceWebSocketApiManager
from unicorn_fy.unicorn_fy import UnicornFy
import logging
import time
import os
import threading
import json
import schedule
import numpy as np
from typing import Optional, Dict, Any, List
from colorprint import ColorPrint
from colorama import Fore, Back, Style, init

logging.basicConfig(level=logging.INFO, format=(
    Fore.BLUE + '[+] ' + Style.RESET_ALL + '%(message)s '))


class BinanceWebSocket:
    def __init__(self,) -> None:
        self.prices = []
        self.trades = []
        self.vol_deltas = []
        self.price_deltas = []
        self.bearish_delta = []
        self.bullish_delta = []
        self.buy_volume = 0
        self.sell_volume = 0
        self.binance_websocket_manager = BinanceWebSocketApiManager(
            exchange="binance.com-futures")
        self.channels = {'aggTrade', 'kline_1m'}
        self.markets = {'btcusdt'}
        self.log = ColorPrint()

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

                trade['volume'] = float(
                    data['quantity']) * float(data['price'])
                trade['side'] = 'None'
                if data['is_market_maker'] == False:
                    trade['side'] = "Buy"
                elif data['is_market_maker'] == True:
                    trade['side'] = "Sell"
                self.trades.append(trade)
            elif data['event_type'] == "kline":
                if data['kline']['is_closed']:
                    price['symbol'] = data['symbol']
                    price['interval'] = data['kline']['interval']
                    price['curr_time'] = data['event_time']
                    price['close_time'] = data['kline']['kline_close_time']
                    price['close_price'] = data['kline']['close_price']
                    self.prices.append(price)

        except Exception as e:
            self.log.red(
                f'Exception when processing buffer_stream in process_aggTrade(): \n {e}')

    def process_totalPrice(self) -> None:
        temp_prices = self.prices
        price_tag = []
        try:
            for price in temp_prices:
                price_tag.append(price['close_price'])
            # self.calc_priceDivergence(price_tag)
        except Exception as e:
            pass

    def process_totalVolume(self) -> None:
        temp_trades = self.trades
        try:
            for trade in temp_trades:
                if trade['side'] == "Sell":
                    self.sell_volume += trade['volume']
                elif trade['side'] == "Buy":
                    self.buy_volume += trade['volume']
            currDelta = self.buy_volume - self.sell_volume
            self.vol_deltas.append(float(currDelta))
            self.trades = []
        except Exception as e:
            self.log.red(
                f'Exception when processing in process_totalVolume():  \n {e}')

    def calc_volumeDivergence(self):
        deltas = self.vol_deltas
        bearish_delta = [False for __ in range(len(deltas))]
        bullish_delta = [False for __ in range(len(deltas))]
        # [positive,negative,negative]
        # [negative,negative,positive]

        # check for negative vol Bearish:
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

    # def calc_priceDivergence(self, price_tag):
    #     #price_tag = []
    #     price_decrease = [False for __ in range(len(price_tag))]
    #     price_increase =[False for __ in range(len(price_tag))]
    #     for i in range(len(price_tag)):
    #         if price_tag[i] > price_tag[i+1]:
    #             price_decrease[i] = True
    #         else:
    #             price_decrease[i] = False
    #     for i in range(len(price_tag)):
    #         if price_tag[i] < price_tag[i+1]:
    #             price_increase[i] = True
    #         else:
    #             price_increase[i] = False
    def print_data(self):
        self.log.green(f"""

                        Volume Delta : {self.vol_deltas} \n
                        Bearish Delta: {self.bearish_delta} \n
                        Bullish Delta: {self.bullish_delta}""")

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
        schedule.every(1).minutes.do(binance.calc_volumeDivergence)
        schedule.every(1).minutes.do(binance.print_data)
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
