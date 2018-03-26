from datetime import datetime

from bittrex import Bittrex, API_V2_0
from celery import shared_task, task
import dateutil.parser
import requests
import traceback
import numpy as np
import pandas as pd
import talib
import threading
import time
from queue import Queue
from django import db

from best_django.celery import app
from best_django.settings import CANDLE_TF_1H, MAX_THREAD, STT_ACCOUNT_ACTIVATED
from summary_writer.candle_task import _repair_candles, _update_latest_candle
from summary_writer.tasks import get_tick
from summary_writer.logger import write_log
from summary_writer.models import Market, MarketSummary, Candle, Ticker, ErrorLog
from rest.models import UserSubscription, SignalSendLog, Strategy, Profile
from best_django import settings
from utils import send_mail
from talib import MA_Type

bittrex_api = Bittrex(settings.BITTREX_API_KEY, settings.BITTREX_SECRET_KEY)
bittrex_api_v2 = Bittrex(settings.BITTREX_API_KEY, settings.BITTREX_SECRET_KEY, api_version=API_V2_0)

selected_tf = CANDLE_TF_1H
DEBUG = False


def send_trading_alert(market, action):
    title = 'Signal Alert ' + market.market_name
    content = 'Market: <string>' + market.market_name + '</strong><br /> You can ' + action + ' rightnow.'
    for us in UserSubscription.objects.filter(market=market):
        if SignalSendLog.objects.filter(profile=us.profile, market=market).exists():
            log = SignalSendLog.objects.filter(profile=us.profile, market=market).order_by('-timestamp').first()
            if action == 'sell' and log.action == 'buy' or action == 'buy' and log.action == 'sell':
                send_mail(title, us.profile.user.email, content)
        else:
            if action == 'buy':
                send_mail(title, us.profile.user.email, content)


rsi_queue = Queue()


def send_trading_alert_rsi(market_name, action, open_price=0, high_price=0, low_price=0, close_price=0, price=0):
    title = 'Signal Alert ' + market_name
    strategy = Strategy.objects.filter(name='BB&RSI').first()
    # replace variable in content
    content = strategy.message
    if '#MarketName#' in content:
        content = content.replace('#MarketName#', '{}'.format(market_name))
    if '#OpenPrice#' in content:
        content = content.replace('#OpenPrice#', '{}'.format(open_price))
    if '#HighPrice#' in content:
        content = content.replace('#HighPrice#', '{}'.format(high_price))
    if '#LowPrice#' in content:
        content = content.replace('#LowPrice#', '{}'.format(low_price))
    if '#ClosePrice#' in content:
        content = content.replace('#ClosePrice#', '{}'.format(close_price))
    if '#Price#' in content:
        content = content.replace('#Price#', '{}'.format(price))
    # write_log('sending with content ', content)
    send_mail(title, 'beanchanel@gmail.com', content)
    if not DEBUG:
        for us in UserSubscription.objects.filter(market=Market.objects.filter(market_name=market_name).first()):
            # if SignalSendLog.objects.filter(profile=us.profile, market__market_name=market_name).exists():
            #     log = SignalSendLog.objects.filter(profile=us.profile, market=market_name).order_by(
            #         '-timestamp').first()
            #     if action == 'sell' and log.action == 'buy' or action == 'buy' and log.action == 'sell':
            #         send_mail(title, us.profile.user.email, content)
            # else:
            #     if action == 'buy':
            #         send_mail(title, us.profile.user.email, content)
            if us.profile.status == STT_ACCOUNT_ACTIVATED:
                send_mail(title, us.profile.user.email, content)
    else:
        send_mail(title, 'beanchanel@gmail.com', content)


def check_signal_log(market_name):
    log = SignalSendLog.objects.filter(market__market_name=market_name).order_by(
        '-timestamp').first()
    # write_log('sending log %s' % log)
    if log is not None:
        d = datetime.utcnow()
        diff = d - log.timestamp
        if 1 * 60 * 60 <= diff.seconds:
            return True
        else:
            return False
    else:
        return True


def _get_ticks(market_name):
    """
    get latest 100 candles
    :param market_name:
    :return:
    """
    candles = reversed(
        Candle.objects.filter(market__market_name=market_name, timeframe=selected_tf).order_by('-timestamp')[:100])
    ticks = []
    indexes = []
    prev_ts = None
    err_count = 0
    for c in candles:
        indexes.append(c.timestamp)
        t = {
            'open': c.open,
            'high': c.high,
            'low': c.low,
            'close': c.close,
            'volume': c.volume,
            'timestamp': c.timestamp
        }
        ticks.append(t)
    return ticks, indexes


def find_signal(market_name):
    if check_signal_log(market_name):
        write_log('market: %s' % market_name)
        ticks, indexes = _get_ticks(market_name)
        # pwrite_log(ticks)
        # write_log(datetime.utcnow())

        if len(ticks) > 0:
            write_log('latest candle timestamp {}'.format(ticks[len(ticks) - 1]['timestamp']))
            diffn = datetime.utcnow() - ticks[len(ticks) - 1]['timestamp']
            # write_log(diffn)
            if diffn.seconds >= (1 * 60 * 60):
                write_log('{} Latest candle is out of date.'.format(market_name))
            else:
                df = pd.DataFrame(ticks, index=indexes)
                ohlc_dict = {'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'}
                df = df.resample('1H').apply(ohlc_dict).dropna(how='any')
                # write_log(df)
                close = np.array([float(x) for x in df['close'].as_matrix()])
                upper, middle, lower = talib.BBANDS(close, matype=MA_Type.T3)
                real = talib.RSI(close, timeperiod=14)
                # fill nan
                upper = np.nan_to_num(upper)
                middle = np.nan_to_num(middle)
                lower = np.nan_to_num(lower)
                real = np.nan_to_num(real)

                # get latest bid/ask
                tick = Ticker.objects.filter(market__market_name=market_name).order_by('-timestamp').first()
                if tick is not None:
                    dn = datetime.utcnow()
                    diff = dn - tick.timestamp
                    if diff.seconds > 0.5 * 60:
                        write_log('old tick')
                        ErrorLog.objects.create(error="{}: got old tick, cannot calculate signal".format(market_name))
                        tick = get_tick(market_name)
                    if tick is not None:
                        price = (tick.bid + tick.ask) / 2
                        try:
                            # if price > (upper[len(upper) - 1] + (0.05 * upper[len(upper) - 1])) \
                            # and real[len(real) - 1] > 70:
                            #     # write_log('sell')
                            #     send_trading_alert_rsi(market_name, 'sell', open_price=df['open'].iloc[0],
                            #                            high_price=df['high'].iloc[0], low_price=df['low'].iloc[0],
                            #                            close_price=df['close'].iloc[0], price=price)
                            # - (0.05 * lower[len(lower) - 1])
                            write_log('lower bb {}'.format(lower[len(lower) - 1]))
                            write_log('rsi {}'.format(real[len(real) - 1]))
                            if price < (lower[len(lower) - 1]) \
                                    and real[len(real) - 1] < 30:
                                write_log('sending signal...')
                                SignalSendLog.objects.create(
                                    market=Market.objects.filter(market_name=market_name).first(), action='log',
                                    timestamp=datetime.utcnow())
                                send_trading_alert_rsi(market_name, 'buy', open_price=df['open'].iloc[0],
                                                       high_price=df['high'].iloc[0],
                                                       low_price=df['low'].iloc[0], close_price=df['close'].iloc[0],
                                                       price=price)
                        except Exception as e:
                            traceback.print_exc()
                else:
                    ErrorLog.objects.create(error="{}: tick is None".format(market_name))


def rsi_process_queue():
    while True:
        market_name = rsi_queue.get()
        find_signal(market_name)
        rsi_queue.task_done()


@task()
def rsi():
    write_log('System analysing....')
    start_time = time.time()
    # db.connections.close_all()

    markets = Market.objects.all()

    for i in range(MAX_THREAD):
        t = threading.Thread(target=rsi_process_queue)
        t.daemon = True
        t.start()

    for market in markets:
        rsi_queue.put(market.market_name)

    rsi_queue.join()
    write_log("Execution time = {0:.5f}".format(time.time() - start_time))


def seq_rsi():
    markets = Market.objects.filter(market_name__contains='USDT')
    for market in markets:
        write_log('market %s' % market.market_name)
        find_signal(market.market_name)


"""
Close price strategy
"""
cp_queue = Queue()


def send_trading_alert_cp(market_name, action, open_price=0, high_price=0, low_price=0, close_price=0, bid_price=0,
                          ask_price=0):
    title = 'Signal Alert ' + market_name
    strategy = Strategy.objects.filter(name="ClosePrice").first()
    # replace variable in content
    content = strategy.message
    if '#MarketName#' in content:
        content = content.replace('#MarketName#', '{}'.format(market_name))
    if '#OpenPrice#' in content:
        content = content.replace('#OpenPrice#', '{}'.format(open_price))
    if '#HighPrice#' in content:
        content = content.replace('#HighPrice#', '{}'.format(high_price))
    if '#LowPrice#' in content:
        content = content.replace('#LowPrice#', '{}'.format(low_price))
    if '#ClosePrice#' in content:
        content = content.replace('#ClosePrice#', '{}'.format(close_price))
    if '#Bid#' in content:
        content = content.replace('#Bid#', '{}'.format(bid_price))
    if '#Ask#' in content:
        content = content.replace('#Ask#', '{}'.format(ask_price))
    if '#Price#' in content:
        content = content.replace('#Price#', '{}'.format((ask_price + bid_price) / 2))
    # write_log('sending with content ', content)
    send_mail(title, 'beanchanel@gmail.com', content)
    for us in UserSubscription.objects.filter(market=Market.objects.filter(market_name=market_name).first()):
        if us.profile.status == STT_ACCOUNT_ACTIVATED:
            send_mail(title, us.profile.user.email, content)


def find_signal_cp(market_name):
    # write_log('market: ', market_name)
    candle = Candle.objects.filter(market__market_name=market_name, timeframe=selected_tf).order_by(
        '-timestamp').first()
    tick = Ticker.objects.filter(market__market_name=market_name).order_by('-timestamp').first()
    if candle is not None and tick is not None:
        bid_pct = (tick.bid - candle.close) / candle.close
        write_log('bid {}'.format(bid_pct))
        ask_pct = (tick.ask - candle.close) / candle.close
        write_log('ask {}'.format(ask_pct))
        if bid_pct >= 0.1 or bid_pct <= 0.1 or ask_pct >= 0.1 or ask_pct <= 0.1:
            send_trading_alert_cp(market_name, '', candle.open, candle.high, candle.low, candle.close, tick.bid,
                                  tick.ask)


@task()
def close_price_strategy():
    write_log('System analysing....')
    # db.connections.close_all()
    start_time = time.time()
    market = Market.objects.filter(market_name="USDT-BTC").first()
    find_signal_cp(market.market_name)
    write_log("Execution time = {0:.5f}".format(time.time() - start_time))
