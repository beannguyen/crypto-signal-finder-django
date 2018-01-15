from pprint import pprint

from bittrex import API_V2_0, Bittrex
from decimal import Decimal
from django.core.paginator import Paginator
from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.response import Response
import pandas as pd
import numpy as np
import talib
from talib import MA_Type

from best_django.settings import BITTREX_SECRET_KEY, BITTREX_API_KEY
from summary_writer.models import Market, MarketSummary, Candle

btx_v2 = Bittrex(BITTREX_API_KEY, BITTREX_SECRET_KEY, api_version=API_V2_0)


@api_view(['GET'])
def get_markets(request):
    """
    get all market with latest summary
    :return:
    """
    page = 1
    try:
        page = int(request.GET['p'])
    except:
        page = 1
    item_per_page = 15
    markets = MarketSummary.objects.filter(market__base_currency=request.GET['base-market']).order_by(
        'market__market_name')
    paging = Paginator(markets, item_per_page)
    page = paging.page(page)
    m_res = []
    for m in page.object_list:
        m_res.append({
            'market_name': m.market.market_name,
            'volume': m.volume,
            'p_change': 100 * (m.last - m.prev_day) / m.prev_day,
            'last_price': m.last,
            '24h_high': m.high,
            '24h_low': m.low,
            'spread': (Decimal(m.ask) - m.bid) * 100 / m.bid,
            'predict_30m': 0
        })

    return Response({
        'success': True,
        'data': m_res,
        'paging': {
            'total': paging.count,
            'num_pages': paging.num_pages,
            'has_next': page.has_next(),
            'has_prev': page.has_previous()
        }
    }, status=200)


@api_view(['GET'])
def get_tick(request):
    """
    get ticks
    :param request:
    :return:
    """
    market_name = ''
    try:
        market_name = request.GET['market']
    except Exception as e:
        print(e)
        return Response({
            'success': False,
            'data': []
        }, status=200)

    print(market_name)
    candles = Candle.objects.filter(market__market_name=market_name)
    if candles.count() == 0:
        return Response({
            'success': True,
            'data': []
        }, status=200)

    ticks = []
    for c in candles:
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

    return Response({
        'success': True,
        'data': {
            'open': [float(x) for x in df['open'].as_matrix()],
            'high': [float(x) for x in df['high'].as_matrix()],
            'low': [float(x) for x in df['low'].as_matrix()],
            'close': [float(x) for x in df['close'].as_matrix()],
            'volume': [float(x) for x in df['volume'].as_matrix()],
        },
        'bb': {
            'upper': [float(x) for x in upper.tolist()],
            'middle': [float(x) for x in middle.tolist()],
            'lower': [float(x) for x in lower.tolist()]
        },
        'rsi': [float(x) for x in real.tolist()]
    }, status=200)


@api_view(['GET'])
def get_latest_tick(request):
    market_name = request.GET['market']
    pass
