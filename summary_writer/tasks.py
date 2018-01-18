from bittrex import Bittrex, API_V2_0
from celery import shared_task, task
import dateutil.parser
import requests

from best_django.celery import app
from summary_writer.models import Market, MarketSummary, Candle
from best_django import settings

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
    res = bittrex_api.get_markets()
    # print(res)
    if res['success']:
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
    print('Updating market summary...')
    res = bittrex_api.get_market_summaries()
    if res['success']:
        for summ in res['result']:
            summary = MarketSummary.objects.filter(market__market_name=summ['MarketName'])
            if summary.exists():
                print('existed')
                summary = summary.first()
            else:
                summary = MarketSummary()
                summary.market = Market.objects.filter(market_name=summ['MarketName']).first()

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


@task()
def get_latest_tick():
    print('Get latest tick...')
    markets = Market.objects.all()
    for market in markets:
        candle_count = Candle.objects.filter(market__market_name=market.market_name).count()
        if candle_count == 0:
            res_candles = bittrex_api_v2.get_candles(market=market.market_name, tick_interval='thirtyMin')
            print('request status ', res_candles['success'])
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
            print('request status ', res_latest_candle['success'])
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
def crawl_cnn_news():
    url = "https://www.ccn.com/wp-admin/admin-ajax.php"

    payload = "action=loadmore&query=a%3A5%3A%7Bs%3A13%3A%22category_name%22%3Bs%3A23%3A%22cryptocurrency-analysis%22%3Bs%3A3%3A%22cat%22%3Bi%3A3%3Bs%3A5%3A%22paged%22%3Bi%3A1%3Bs%3A14%3A%22posts_per_page%22%3Bi%3A16%3Bs%3A5%3A%22order%22%3Bs%3A4%3A%22DESC%22%3B%7D&page=1"
    headers = {
        'Content-Type': "application/x-www-form-urlencoded"
    }
    response = requests.request("POST", url, data=payload, headers=headers)

    print(response.text)
