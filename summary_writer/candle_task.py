import threading
from queue import Queue

import dateutil
from bittrex import Bittrex, API_V2_0
from celery.task import task

from best_django import settings
from best_django.settings import CANDLE_TF_1H
from summary_writer.models import Market, Candle

latest_candle_queue = Queue()

bittrex_api = Bittrex(settings.BITTREX_API_KEY, settings.BITTREX_SECRET_KEY)
bittrex_api_v2 = Bittrex(settings.BITTREX_API_KEY, settings.BITTREX_SECRET_KEY, api_version=API_V2_0)


def _get_candle(market_name):
    market = Market.objects.filter(market_name=market_name)
    if market.exists():
        market = market.first()

        candle_count = Candle.objects.filter(market__market_name=market.market_name).count()
        if candle_count == 0:
            res_candles = bittrex_api_v2.get_candles(market=market.market_name, tick_interval=CANDLE_TF_1H)
            # print('request status ', res_candles['success'])
            if res_candles['success']:
                for c in res_candles['result']:
                    candle = Candle()
                    candle.market = market
                    candle.high = c['H']
                    candle.low = c['L']
                    candle.open = c['O']
                    candle.close = c['C']
                    candle.volume = c['V']
                    candle.base_volume = c['BV']
                    candle.timestamp = dateutil.parser.parse(c['T'])
                    candle.timeframe = CANDLE_TF_1H
                    candle.save()
        else:
            res_latest_candle = bittrex_api_v2.get_latest_candle(market=market.market_name, tick_interval=CANDLE_TF_1H)
            # print('request status ', res_latest_candle['success'])
            if res_latest_candle['success']:
                latest_candle = res_latest_candle['result'][0]
                if latest_candle is not None:
                    candle = Candle()
                    candle.market = market
                    candle.high = latest_candle['H']
                    candle.low = latest_candle['L']
                    candle.open = latest_candle['O']
                    candle.close = latest_candle['C']
                    candle.volume = latest_candle['V']
                    candle.base_volume = latest_candle['BV']
                    candle.timeframe = CANDLE_TF_1H
                    candle.timestamp = dateutil.parser.parse(latest_candle['T'])
                    if not Candle.objects.filter(timestamp=candle.timestamp).exists():
                        candle.save()


def process_latest_candle_queue():
    while True:
        market_name = latest_candle_queue.get()
        _get_candle(market_name)
        latest_candle_queue.task_done()


@task()
def get_latest_candle():
    print('Get latest tick...')
    markets = Market.objects.all()

    for i in range(3):
        t = threading.Thread(target=process_latest_candle_queue)
        t.daemon = True
        t.start()

    for market in markets:
        # get_tick(market.market_name)
        latest_candle_queue.put(market.market_name)

    return None