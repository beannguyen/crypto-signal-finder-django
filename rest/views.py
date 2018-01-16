import traceback
from decimal import *

import numpy as np
import pandas as pd
import talib
from bittrex import API_V2_0, Bittrex
from django.contrib.auth.models import User, Group
from django.core.paginator import Paginator
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from talib import MA_Type
import json

import constants
from best_django.settings import BITTREX_SECRET_KEY, BITTREX_API_KEY
from rest.models import MemberShipPlan, Profile
from rest.serializers import BaseResponse
from summary_writer.models import Market, MarketSummary, Candle

btx_v2 = Bittrex(BITTREX_API_KEY, BITTREX_SECRET_KEY, api_version=API_V2_0)


@api_view(['GET'])
@permission_classes((IsAuthenticated,))
def getmarkets(request):
    res = []
    try:
        markets = Market.objects.all()
        for m in markets:
            res.append({
                'market_currency': m.market_currency,
                'base_currency': m.base_currency,
                'market_currency_long': m.market_currency_long,
                'base_currency_long': m.base_currency_long,
                'min_trade_size': m.min_trade_size,
                'market_name': m.market_name,
                'is_active': m.is_active,
                'created_on': m.created_on
            })

        return Response({
            'success': True,
            'data': res
        })
    except Exception as e:
        print(e)
        return Response({
            'success': False,
            'data': res
        })


@api_view(['GET'])
@permission_classes((IsAuthenticated,))
def getmarketsummaries(request):
    """
    get all market with latest summary
    :return:
    """
    page = 1
    try:
        page = int(request.GET['p'])
    except:
        page = 1

    try:
        item_per_page = MarketSummary.objects.count()
        markets = MarketSummary.objects.all().order_by('market__market_name')
        paging = Paginator(markets, item_per_page)
        page = paging.page(page)
        m_res = []
        for m in page.object_list:
            m_res.append({
                'market_name': m.market.market_name,
                'volume': m.volume,
                'p_change': 100 * (Decimal(m.last) - Decimal(m.prev_day)) / Decimal(m.prev_day),
                'last_price': m.last,
                'high': m.high,
                'low': m.low,
                'spread': 0,
                # (Decimal(m.ask) - Decimal(m.bid)) * 100 / Decimal(m.bid),
                'predict_30m': 0,
                'market_currency_long': m.market.market_currency_long
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
    except Exception as e:
        print(e)
        return Response({
            'success': False,
            'data': []
        }, status=200)


@api_view(['GET'])
@permission_classes((IsAuthenticated,))
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
@permission_classes((IsAuthenticated,))
def get_latest_tick(request):
    market_name = request.GET['market']
    pass


@api_view(['POST'])
@permission_classes((AllowAny,))
def register(request, format=None):
    """
    Register new user
    ---
    # Request Json
    {
        "username": "bean",
        "email": "bean@gmail.com",
        "is_active": false,
        "password": "123456",
        "plan": 1,
        "group": 2
    }

    # Responses
    - Username exist:
    {
        "result": "ERR",
        "msg": "user_exist"
    }

    - Email exist:
    {
        "result": "ERR",
        "msg": "user_exist"
    }

    - Invalid group:
    {
        "result": "ERR",
        "msg": "group_not_found"
    }

    - Exception:
    {
        "result": "ERR",
        "msg": "throw Traceback"
    }

    - Create user successfully:
    {
        "result": "OK",
        "msg": "created"
    }

    """
    req = json.loads(request.body.decode('utf-8'))
    print(req)

    res = BaseResponse()

    try:
        username_count = User.objects.count(username=req['username'])
        if username_count > 0:
            res.result = constants.HTTP_ERR
            res.msg = 'user_exist'
            return Response(res)

        email_count = User.objects.count(email=req['email'])
        if email_count > 0:
            res.result = constants.HTTP_ERR
            res.msg = 'email_exist'
            return Response(res)

        group = Group.objects.get(pk=req['group'])
        if group is None:
            res.result = constants.HTTP_ERR
            res.msg = 'group_not_found'
            return Response(res)

        plan = None
        if req['plan'] is not None:
            plan = MemberShipPlan.objects.get(pk=req['plan'])

        # create user
        user = User.objects.create_user(username=req['username'],
                                        email=req['email'],
                                        password=req['password'])
        group.user_set.add(user)

        # add profile
        profile = Profile()
        profile.user = user
        profile.plan = plan
        profile.save()

        res.result = constants.HTTP_OK
        res.msg = 'created'
    except:
        err = traceback.print_exc()
        res.result = constants.HTTP_ERR
        res.msg = err

    return Response(res)


class CreateUserView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, format=None):
        """
        Register new user
        ---
        # Request Json
        {
            "username": "bean",
            "email": "bean@gmail.com",
            "is_active": false,
            "password": "123456",
            "plan": 1,
            "group": 2
        }

        # Responses
        - Username exist:
        {
            "result": "ERR",
            "msg": "user_exist"
        }

        - Email exist:
        {
            "result": "ERR",
            "msg": "user_exist"
        }

        - Invalid group:
        {
            "result": "ERR",
            "msg": "group_not_found"
        }

        - Invalid plan:
        {
            "result": "ERR",
            "msg": "plan_not_found"
        }

        - Exception:
        {
            "result": "ERR",
            "msg": "throw Traceback"
        }

        - Create user successfully:
        {
            "result": "OK",
            "msg": "created"
        }

        """
        req = json.loads(request.body.decode('utf-8'))
        print(req)

        res = BaseResponse()

        try:
            username_count = User.objects.count(username=req['username'])
            if username_count > 0:
                res.result = constants.HTTP_ERR
                res.msg = 'user_exist'
                return Response(res)

            email_count = User.objects.count(email=req['email'])
            if email_count > 0:
                res.result = constants.HTTP_ERR
                res.msg = 'email_exist'
                return Response(res)

            group = Group.objects.get(pk=req['group'])
            if group is None:
                res.result = constants.HTTP_ERR
                res.msg = 'group_not_found'
                return Response(res)

            plan = MemberShipPlan.objects.get(pk=req['plan'])
            if plan is None:
                res.result = constants.HTTP_ERR
                res.msg = 'plan_not_found'
                return Response(res)

            # create user
            user = User.objects.create_user(username=req['username'],
                                            email=req['email'],
                                            password=req['password'])
            group.user_set.add(user)

            # add profile
            profile = Profile()
            profile.user = user
            profile.plan = plan
            profile.save()

            res.result = constants.HTTP_OK
            res.msg = 'created'
        except:
            err = traceback.print_exc()
            res.result = constants.HTTP_ERR
            res.msg = err

        return Response(res)


def request_plan(request, format=None):
    pass