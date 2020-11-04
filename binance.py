"""
1)Testing BinanceWebSocketApiManager
https://github.com/oliver-zehentleitner/unicorn-binance-websocket-api
https://www.technopathy.club/2019/11/02/howto-unicorn-binance-websocket-api/
https://github.com/oliver-zehentleitner/unicorn-binance-websocket-api/blob/master/example_stream_buffer.py
https://github.com/oliver-zehentleitner/unicorn-binance-websocket-api/blob/master/example_process_streams.py
https://github.com/oliver-zehentleitner/unicorn-binance-websocket-api/blob/master/example_binance_futures.py
https://github.com/binance-exchange/binance-official-api-docs/blob/master/web-socket-streams.md#live-subscribingunsubscribing-to-streams

2) Cleaning data:
https://github.com/oliver-zehentleitner/unicorn_fy/blob/master/unicorn_fy/unicorn_fy.py

2) Identify the streams for grabbing volume
3) Save the stream data into a database for access?
"""
from unicorn_binance_websocket_api.unicorn_binance_websocket_api_manager import BinanceWebSocketApiManager
from unicorn_fy.unicorn_fy import UnicornFy
import logging
import time
import os
import threading
import json

logging.basicConfig(level=logging.INFO,
                    filename=os.path.basename(__file__) + '.log',
                    format="{asctime} [{levelname:8}] {process} {thread} {module}: {message}",
                    style="{")

"""
Connection Binance Futures
"""
binance_websocket_api_manager = BinanceWebSocketApiManager(
    exchange="binance.com-futures")

"""
Create channels and markets
"""

channels = {'aggTrade'}
markets = {'btcusdt'}

curr_stream = binance_websocket_api_manager.create_stream(
    channels, markets)


"""

data are stored in stream_buffer: 
remove oldest with pop_stream_data_from_stream_buffer()
"""


def print_stream_data_buffer(binance_websocket_api_manager):
    print("Initialize, wait 30secs for streams to come in")
    time.sleep(5)
    while True:
        if binance_websocket_api_manager.is_manager_stopping():
            exit(0)

        oldest_stream = UnicornFy.binance_com_futures_websocket(
            binance_websocket_api_manager.pop_stream_data_from_stream_buffer())
        if oldest_stream is False:
            time.sleep(0.01)
        else:
            try:
                print(oldest_stream)

            except KeyError:
                print("error printing data")
                # not able to process the data? write it back to the stream_buffer
                binance_websocket_api_manager.add_to_stream_buffer(
                    oldest_stream)


"""Process and save the correct data for buy/sell"""


def process_aggTrade(data):
    trades = []
    try:
        trade['volume'] = float(data['quantity']) * float(data['price'])
        trade['side'] = 'None'
        if data['is_market_maker'] == False:
            trade['side'] = "Buy"
        elif data['is_market_maker'] == True:
            trade['side'] = "Sell"
        trades.append(trade)
    #   trades = [{side:"buy",volume:2000},{..},{..}]
    except Exception as e:
        pass

# Every 1min, take total of all trades and combine to get netvolume?
# Every 1min, take the avg of price, or just get the last candle on the last min?
# if positive vol1 > vol2 > vol3 and price1 > price2 > price3 = Bull


worker_thread = threading.Thread(
    target=print_stream_data_buffer, args=(binance_websocket_api_manager,))
worker_thread.start()

time.sleep(5)
