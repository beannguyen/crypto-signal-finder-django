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
from datetime import datetime, date
from django import db
from django.db import connection

from best_django.celery import app
from summary_writer.models import Market, MarketSummary, Candle, Ticker
from rest.models import UserSubscription, SignalSendLog, Strategy, Profile
from best_django import settings
from utils import send_mail
from talib import MA_Type

bittrex_api = Bittrex(settings.BITTREX_API_KEY, settings.BITTREX_SECRET_KEY)
bittrex_api_v2 = Bittrex(settings.BITTREX_API_KEY, settings.BITTREX_SECRET_KEY, api_version=API_V2_0)

"""
The settings follow these tutorials
http://michal.karzynski.pl/blog/2014/05/18/setting-up-an-asynchronous-task-queue-for-django-using-celery-redis/
https://medium.com/@yehandjoe/celery-4-periodic-task-in-django-9f6b5a8c21c7
"""


@task()
def update_markets():
    print('Updating markets...')
    db.connections.close_all()
    res = bittrex_api.get_markets()
    # print(res)
    if res['success']:
        print('got {} markets'.format(len(res['result'])))
        for market in res['result']:
            m = Market.objects.filter(market_name=market['MarketName'])
            if not m.exists():
                new_market = Market()
            else:
                new_market = m.first()

            new_market.market_currency = market['MarketCurrency']
            new_market.base_currency = market['BaseCurrency']
            new_market.market_currency_long = market['MarketCurrencyLong']
            new_market.base_currency_long = market['BaseCurrencyLong']
            new_market.min_trade_size = market['MinTradeSize']
            new_market.market_name = market['MarketName']
            new_market.is_active = market['IsActive']
            new_market.save()
        print('Completed')
    return None


@task()
def update_market_summary():
    db.connections.close_all()
    update_markets()
    print('Updating market summary...')
    res = bittrex_api.get_market_summaries()
    if res['success']:
        for summ in res['result']:
            summary = MarketSummary.objects.filter(market__market_name=summ['MarketName'])
            if summary.exists():
                # print('existed')
                summary = summary.first()
                # update model
                summary.high = summ['High']
                summary.low = summ['Low']
                summary.volume = summ['Volume']
                summary.last = summ['Last']
                summary.base_volume = summ['BaseVolume']
                summary.updated_on = dateutil.parser.parse(summ['TimeStamp'])
                summary.bid = summ['Bid']
                summary.ask = summ['Ask']
                summary.prev_day = summ['PrevDay']
                summary.save()
            else:
                # print('not existed')
                market = Market.objects.filter(market_name=summ['MarketName']).first()
                # print('market: ', summ['MarketName'])
                summary = MarketSummary.objects.create(market=market,
                                                        high=summ['High'],
                                                        low=summ['Low'],
                                                        volume=summ['Volume'],
                                                        last=summ['Last'],
                                                        base_volume=summ['BaseVolume'],
                                                        updated_on=dateutil.parser.parse(summ['TimeStamp']),
                                                        bid=summ['Bid'],
                                                        ask=summ['Ask'],
                                                        prev_day=summ['PrevDay'])



@task()
def get_latest_tick():
    print('Get latest tick...')
    db.connections.close_all()
    markets = Market.objects.all()
    for market in markets:
        candle_count = Candle.objects.filter(market__market_name=market.market_name).count()
        if candle_count == 0:
            res_candles = bittrex_api_v2.get_candles(market=market.market_name, tick_interval='thirtyMin')
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
                    candle.save()
        else:
            res_latest_candle = bittrex_api_v2.get_latest_candle(market=market.market_name, tick_interval='thirtyMin')
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
                    candle.timestamp = dateutil.parser.parse(latest_candle['T'])
                    if not Candle.objects.filter(timestamp=candle.timestamp).exists():
                        candle.save()

@task()
def sendmail():
    send_mail('hell', 'bao.nlq94@gmail.com', '<p>Hello</p>')


queue = Queue()


def get_tick(market_name):
    res = bittrex_api.get_ticker(market_name)
    if res['success']:
        latest_tick = res['result']
        if latest_tick is not None:
            # print(latest_tick)
            Ticker.objects.create(market=Market.objects.get(market_name=market_name), 
                                  bid=latest_tick['Bid'] if latest_tick['Bid'] is not None else 0, 
                                  ask=latest_tick['Ask'] if latest_tick['Ask'] is not None else 0)


def process_queue():
    while True:
        market_name = queue.get()
        get_tick(market_name)
        queue.task_done()


@task()
def get_ticker():
    print('Get ticker....')

    start_time = time.time()
    
    db.connections.close_all()
    markets = Market.objects.all()

    for i in range(3):
        t = threading.Thread(target=process_queue)
        t.daemon = True
        t.start()
    
    for market in markets:
        # get_tick(market.market_name)
        queue.put(market.market_name)

    queue.join()
    print("Execution time = {0:.5f}".format(time.time() - start_time))


@task()
def check_overdue_action():
    start_time = time.time()
    
    db.connections.close_all()
    markets = Market.objects.all()

    accounts = Profile.objects.all()
    for acc in accounts:
        today = datetime.now().date()
        duration_date = acc.plan.duration * 30

        if today - acc.activated_date.date() > duration_date:
            if acc.status != settings.STT_ACCOUNT_OVERDUE:
                acc.status = settings.STT_ACCOUNT_OVERDUE
                acc.save()
                # send_mail(subject='Membership Alert!',
                #       to=u.email,
                #       html_content='<p>Hi {}</p> '
                #                    'our subscription has expired: '
                #                    '{}'.format(u.username,
                #                                generate_reset_pwd_link(
                #                                    u.username,
                #                                    vc.verify_code)))


@task()
def kill_all_idle_session():
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'Database_Name' AND pid <> pg_backend_pid() AND state in ('idle', 'idle in transaction', 'idle in transaction (aborted)', 'disabled') AND state_change < current_timestamp - INTERVAL '15' MINUTE;")