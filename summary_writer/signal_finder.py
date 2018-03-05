from bittrex import Bittrex, API_V2_0
from bs4 import BeautifulSoup
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
from summary_writer.models import Market, MarketSummary, Candle, Ticker
from rest.models import UserSubscription, SignalSendLog, Strategy
from best_django import settings
from utils import send_mail
from talib import MA_Type

bittrex_api = Bittrex(settings.BITTREX_API_KEY, settings.BITTREX_SECRET_KEY)
bittrex_api_v2 = Bittrex(settings.BITTREX_API_KEY, settings.BITTREX_SECRET_KEY, api_version=API_V2_0)


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
    strategy = Strategy.objects.filter(name='RSI').first()
    # replace variable in content
    content = strategy.message
    if '#MarketName#' in content:
        content = content.replace('#MarketName#', market_name)
    if '#OpenPrice#' in content:
        content = content.replace('#OpenPrice#', open_price)
    if '#HighPrice#' in content:
        content = content.replace('#HighPrice#', high_price)
    if '#LowPrice#' in content:
        content = content.replace('#LowPrice#', low_price)
    if '#ClosePrice#' in content:
        content = content.replace('#ClosePrice#', close_price)
    if '#Price#' in content:
        content = content.replace('#Price#', price)
    print('sending with content ', content)
    for us in UserSubscription.objects.filter(market=Market.objects.filter(market_name=market_name).first()):
        send_mail(title, us.profile.user.email, content)



def find_signal(market_name):
    print('market: ', market_name)
    candles = Candle.objects.filter(market__market_name=market_name).order_by('-timestamp')[:100]
    ticks = []
    for c in candles:
        # print('tick: {} \n'.format(c.timestamp))
        t = {
            'open': c.open,
            'high': c.high,
            'low': c.low,
            'close': c.close,
            'volume': c.volume
        }
        ticks.append(t)
    # pprint(ticks)
    df = pd.DataFrame(ticks)
    close = np.array([float(x) for x in df['close'].as_matrix()])
    upper, middle, lower = talib.BBANDS(close, matype=MA_Type.T3)
    real = talib.RSI(close, timeperiod=14)
    # fill nan
    upper = np.nan_to_num(upper)
    middle = np.nan_to_num(middle)
    lower = np.nan_to_num(lower)
    real = np.nan_to_num(real)
    
    tick = Ticker.objects.filter(market__market_name=market_name).order_by('-timestamp').first()
    if tick is not None:
        price = tick.bid + tick.ask / 2
        try:
            if price > upper[len(upper) - 1] and real[len(real) - 1] > 70:
                # print('sell')
                send_trading_alert_rsi(market_name, 'sell', open_price=df['open'].iloc[0], high_price=df['high'].iloc[0], low_price=df['low'].iloc[0], close_price=df['close'].iloc[0], price=price)
            elif price < lower[len(lower) - 1] and real[len(real) - 1] < 30:
                send_trading_alert_rsi(market_name, 'buy', open_price=df['open'].iloc[0], high_price=df['high'].iloc[0], low_price=df['low'].iloc[0], close_price=df['close'].iloc[0], price=price)
        except Exception as e:
            traceback.print_exc()


def rsi_process_queue():
    while True:
        market_name = rsi_queue.get()
        find_signal(market_name)
        rsi_queue.task_done()


@task()
def rsi():
    print('System analysing....')
    start_time = time.time()
    db.connections.close_all()
    
    markets = Market.objects.all()

    for i in range(3):
        t = threading.Thread(target=rsi_process_queue)
        t.daemon = True
        t.start()

    for market in markets:
        rsi_queue.put(market.market_name)
    
    rsi_queue.join()
    print("Execution time = {0:.5f}".format(time.time() - start_time))


"""
Close price strategy
"""
cp_queue = Queue()


def send_trading_alert_cp(market_name, action, open_price=0, high_price=0, low_price=0, close_price=0, price=0):
    title = 'Signal Alert ' + market_name
    strategy = Strategy.objects.filter(name="ClosePrice").first()
    # replace variable in content
    content = strategy.message
    if '#MarketName#' in content:
        content = content.replace('#MarketName#', market_name)
    if '#OpenPrice#' in content:
        content = content.replace('#OpenPrice#', open_price)
    if '#HighPrice#' in content:
        content = content.replace('#HighPrice#', high_price)
    if '#LowPrice#' in content:
        content = content.replace('#LowPrice#', low_price)
    if '#ClosePrice#' in content:
        content = content.replace('#ClosePrice#', close_price)
    if '#Price#' in content:
        content = content.replace('#Price#', price)
    print('sending with content ', content)
    for us in UserSubscription.objects.filter(market=Market.objects.filter(market_name=market_name).first()):
        send_mail(title, us.profile.user.email, content)


def find_signal_cp(market_name):
    print('market: ', market_name)
    candle = Candle.objects.filter(market__market_name=market_name).order_by('-timestamp').first()
    tick = Ticker.objects.filter(market__market_name=market_name).order_by('-timestamp').first()
    if candle is not None and tick is not None:
        pct = tick.bid - candle.close / candle.close
        if pct >= 0.1:
            send_trading_alert_cp(market_name, '', candle.open, candle.high, candle.low, candle.close, tick.bid)


def cp_process_queue():
    while True:
        market_name = cp_queue.get()
        find_signal_cp(market_name)
        cp_queue.task_done()


@task()
def close_price_strategy():
    print('System analysing....')
    db.connections.close_all()
    start_time = time.time()
    markets = Market.objects.all()

    for i in range(3):
        t = threading.Thread(target=cp_process_queue)
        t.daemon = True
        t.start()

    for market in markets:
        cp_queue.put(market.market_name)
    
    cp_queue.join()
    print("Execution time = {0:.5f}".format(time.time() - start_time))