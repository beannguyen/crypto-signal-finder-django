import threading
from queue import Queue

import dateutil.parser
from bittrex import Bittrex, API_V2_0
from celery.task import task

from best_django import settings
from best_django.settings import CANDLE_TF_1H, MAX_THREAD
from summary_writer.logger import write_log
from summary_writer.models import Market, Candle

latest_candle_queue = Queue()

bittrex_api = Bittrex(settings.BITTREX_API_KEY, settings.BITTREX_SECRET_KEY)
bittrex_api_v2 = Bittrex(settings.BITTREX_API_KEY, settings.BITTREX_SECRET_KEY, api_version=API_V2_0)


def _repair_candles(market, interval, max_length=None):
    res_candles = bittrex_api_v2.get_candles(market=market.market_name, tick_interval=interval)
    # write_log(res_candles)
    if res_candles['success']:
        if res_candles['result'] is not None:
            latest_candles = sorted(res_candles['result'], key=lambda cd: cd['T'], reverse=True)[
                             :int(max_length)] if max_length is not None else res_candles['result']
            # print(latest_candles)
        else:
            write_log('result is none')
            latest_candles = []

        for c in latest_candles:
            candle = Candle()
            candle.market = market
            candle.high = c['H']
            candle.low = c['L']
            candle.open = c['O']
            candle.close = c['C']
            candle.volume = c['V']
            candle.base_volume = c['BV']
            candle.timestamp = dateutil.parser.parse(c['T'])
            write_log('ts %s' % candle.timestamp)
            candle.timeframe = interval
            if not Candle.objects.filter(market__market_name=market.market_name,
                                         timeframe=interval,
                                         timestamp=candle.timestamp).exists():
                write_log('{}: inserting ...'.format(candle.timestamp))
                candle.save()


def _update_latest_candle(market, interval):
    res_latest_candle = bittrex_api_v2.get_latest_candle(market=market.market_name, tick_interval=CANDLE_TF_1H)
    # write_log('insert new candle ', res_latest_candle['success'])
    # pwrite_log(res_latest_candle['result'])
    if res_latest_candle['success']:
        latest_candle = res_latest_candle['result'][0]
        if latest_candle is not None:
            ts = dateutil.parser.parse(latest_candle['T'])
            if not Candle.objects.filter(market__market_name=market.market_name,
                                         timeframe=interval,
                                         timestamp=ts).exists():
                write_log('Inserting new candle...')
                candle = Candle()
                candle.market = market
                candle.high = latest_candle['H']
                candle.low = latest_candle['L']
                candle.open = latest_candle['O']
                candle.close = latest_candle['C']
                candle.volume = latest_candle['V']
                candle.base_volume = latest_candle['BV']
                candle.timeframe = CANDLE_TF_1H
                candle.timestamp = ts
                candle.save()
            else:
                write_log('Updating candle\'s close price...')
                lc = Candle.objects.filter(market__market_name=market.market_name,
                                           timeframe=interval,
                                           timestamp=ts).first()
                lc.close = latest_candle['C']
                lc.save()


def _get_candle(market_name):
    market = Market.objects.filter(market_name=market_name)
    if market.exists():
        market = market.first()

        candles = Candle.objects.filter(market__market_name=market.market_name, timeframe=CANDLE_TF_1H).order_by(
            '-timestamp')[:100]

        # prev_ts = None
        # err_count = 0
        # if candles.count() > 0:
        #     # write_log('candle in db ', candle_count)
        #     for c in reversed(candles):
        #         if prev_ts is None:
        #             prev_ts = c.timestamp
        #         else:
        #             diff = c.timestamp - prev_ts
        #             if diff.seconds > (1 * 60 * 60):
        #                 # write_log('tick: {} - {}'.format(prev_ts, c.timestamp))
        #                 err_count += 1
        #             prev_ts = c.timestamp

        # if candles.count() > 0 and err_count == 0:
        #     write_log('update latest')
        #     _update_latest_candle(market=market, interval=CANDLE_TF_1H)
        # elif candles.count() > 0 and err_count > 0:
        #     write_log('repairing..')
        #     _repair_candles(market=market, interval=CANDLE_TF_1H, max_length=150)
        # else:
        #     write_log('get candles')
        #     _repair_candles(market=market, interval=CANDLE_TF_1H)
        if candles.count() > 0:
            _update_latest_candle(market=market, interval=CANDLE_TF_1H)
        else:
            _repair_candles(market=market, interval=CANDLE_TF_1H)


def process_latest_candle_queue():
    while True:
        market_name = latest_candle_queue.get()
        _get_candle(market_name)
        latest_candle_queue.task_done()


@task()
def get_latest_candle():
    write_log('Get latest tick...')
    markets = Market.objects.all()
    # write_log('get ', markets.count())

    for i in range(MAX_THREAD):
        t = threading.Thread(target=process_latest_candle_queue)
        t.daemon = True
        t.start()

    for market in markets:
        # get_tick(market.market_name)
        latest_candle_queue.put(market.market_name)

    latest_candle_queue.join()


def seq_get_latest_candle():
    markets = Market.objects.all()
    for market in markets:
        write_log('market %s' % market.market_name)
        _get_candle(market.market_name)


def get_market_c():
    market = Market.objects.filter(market_name='ETH-VIB').first()
    _get_candle(market.market_name)


def test():
    market = Market.objects.get(pk=88)
    write_log('get candle %s' % market.market_name)
    # _update_latest_candle(market=market, interval=CANDLE_TF_1H)
    _repair_candles(market=market, interval=CANDLE_TF_1H, max_length=150)
    # _get_candle(market)
