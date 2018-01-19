import traceback
from decimal import *

import numpy as np
import pandas as pd
import talib
from bittrex import API_V2_0, Bittrex
from datetime import datetime
from django.contrib.auth.models import User, Group, Permission
from django.core.paginator import Paginator
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_jwt.serializers import JSONWebTokenSerializer
from rest_framework_jwt.settings import api_settings
from rest_framework_jwt.utils import jwt_response_payload_handler
from talib import MA_Type
import json

from best_django.settings import BITTREX_SECRET_KEY, BITTREX_API_KEY, HTTP_ERR, HTTP_OK, GROUP_LEADER
from rest.models import MemberShipPlan, Profile, WalletCurrency, MemberShipPlanPricing, AccountVerificationCode, Wallet
from summary_writer.models import Market, MarketSummary, Candle
from utils import generate_ref, send_mail, generate_email_verification_link

btx_v2 = Bittrex(BITTREX_API_KEY, BITTREX_SECRET_KEY, api_version=API_V2_0)


def has_permission(user, permission_name):
    return user.has_perm('rest.{}'.format(permission_name))


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
        "password": "123456",
        "ref": "Ma 6 ky tu, co the de null"
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

    res = {}

    try:
        username_count = User.objects.filter(username=req['username']).count()
        if username_count > 0:
            res['result'] = HTTP_ERR
            res['msg'] = 'user_exist'
            return Response(res)

        email_count = User.objects.filter(email=req['email']).count()
        if email_count > 0:
            res['result'] = HTTP_ERR
            res['msg'] = 'email_exist'
            return Response(res)

        # dang ky chua chon plan
        # plan = None
        # if req['plan'] is not None:
        #     plan = MemberShipPlan.objects.get(pk=req['plan'])

        ref_id = ''
        if 'ref' not in req or req['ref'] is None:
            ref_id = '1111'  # Admin ref
        else:
            ref_id = req['ref']

        refer = Profile.objects.filter(ref=ref_id).first()

        # create user
        user = User.objects.create_user(username=req['username'],
                                        email=req['email'],
                                        password=req['password'],
                                        is_active=False)

        group = Group.objects.filter(name='User').first()
        group.user_set.add(user)

        # add profile
        profile = Profile()
        profile.user = user
        profile.refer = refer
        # profile.plan = plan
        profile.save()

        try:
            v = AccountVerificationCode.objects.create(user=profile, verify_code=generate_ref(16))
            send_mail(subject='Account Activation',
                      to=user.email,
                      html_content='<p>Hi {}</p> '
                                   'Click following link to verify your email: '
                                   '{}'.format(user.username,
                                               generate_email_verification_link(
                                                   user.username,
                                                   v.verify_code)))
        except:
            traceback.print_exc()
            res['result'] = HTTP_ERR
            res['msg'] = 'cannot_send_mail'
            return Response(res)

        res['result'] = HTTP_OK
        res['msg'] = 'created'
    except:
        err = traceback.print_exc()
        res['result'] = HTTP_ERR
        res['msg'] = err

    return Response(res)


@api_view(['POST'])
@permission_classes((AllowAny,))
def verify_email(request, format=None):
    """
    Verify email
    ---
    # Request
    {
        "verify_code": "6517CE352F4F4688",
        "username": "thienbao0212"
    }
    """
    req = json.loads(request.body.decode('utf-8'))
    res = {}
    try:
        c = AccountVerificationCode.objects.filter(verify_code=req['verify_code'], user__user__username=req['username'])
        if c.exists():
            profile = Profile.objects.filter(user__username=req['username']).first()
            profile.is_email_verified = True
            profile.save()
            c.delete()
            res['result'] = HTTP_OK
            res['msg'] = 'verified'
        else:
            res['result'] = HTTP_ERR
            res['msg'] = 'invalid_verify_code'
    except:
        err = traceback.print_exc()
        res['result'] = HTTP_ERR
        res['msg'] = err

    return Response(res)


@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def get_leader_wallet(request, format=None):
    res = {}
    try:
        user = request.user
        req = json.loads(request.body.decode('utf-8'))

        wallet = Wallet.objects.filter(user=user, wallet_currency__symbol=req['type']).first()
        res['result'] = HTTP_OK
        res['wallet'] = {
            'address': wallet.address
        }
    except:
        traceback.print_exc()
        res['result'] = HTTP_ERR
        res['msg'] = 'exception'

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

        - Cannot send email:
        {
            "result": "ERR",
            "msg": "cannot_send_mail"
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

        res = {}

        try:
            if not has_permission(request.user, 'add_user'):
                return Response(status=550)

            username_count = User.objects.count(username=req['username'])
            if username_count > 0:
                res['result'] = HTTP_ERR
                res['msg'] = 'user_exist'
                return Response(res)

            email_count = User.objects.count(email=req['email'])
            if email_count > 0:
                res['result'] = HTTP_ERR
                res['msg'] = 'email_exist'
                return Response(res)

            group = Group.objects.get(pk=req['group'])
            if group is None:
                res['result'] = HTTP_ERR
                res['msg'] = 'group_not_found'
                return Response(res)

            plan = MemberShipPlan.objects.get(pk=req['plan'])
            if plan is None:
                res['result'] = HTTP_ERR
                res['msg'] = 'plan_not_found'
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

            # if user is added to Leader group
            if group.name == GROUP_LEADER:
                while True:
                    ref = generate_ref(16)
                    if ref is not None:
                        if not Profile.objects.filter(ref=ref).exists():
                            profile.ref = ref
                            break

            profile.save()

            res['result'] = HTTP_OK
            res['msg'] = 'created'
        except:
            err = traceback.print_exc()
            res['result'] = HTTP_ERR
            res['msg'] = err

        return Response(res)


def request_plan(request, format=None):
    pass


@api_view(['GET'])
@permission_classes((AllowAny,))
def get_pricing_plans(request, format=None):
    """
    Get all plan
    :param request:
    :param format:
    :return:
    """
    res = {}
    try:
        list = []
        plans = MemberShipPlan.objects.all()
        for p in plans:
            plan = {
                'name': p.name,
                'duration': p.duration,
                'market_subscription_limit': p.market_subscription_limit,
                'prices': []
            }
            for price in p.membershipplanpricing_set.all():
                p = {
                    'symbol': price.wallet_currency.symbol,
                    'price': price.price
                }
                plan['prices'].append(p)
            list.append(plan)

        res['result'] = HTTP_OK
        res['plans'] = list
    except:
        err = traceback.print_exc()
        res['result'] = HTTP_ERR
        res['msg'] = err

    return Response(res)


@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def create_wallet_type(request, format=None):
    """
    Create new wallet type.
    ---
    # Request
    {
        "name": "BTC Wallet",
        "symbol": "BTC"
    }
    """
    res = {}
    try:
        if not has_permission(request.user, 'add_walletcurrency'):
            return Response(status=550)

        req = json.loads(request.body.decode('utf-8'))
        w = WalletCurrency(name=req['name'], symbol=req['symbol'])
        w.save()
        res['result'] = HTTP_OK
        res['msg'] = 'success'
    except:
        err = traceback.print_exc()
        res['result'] = HTTP_ERR
        res['msg'] = err

    return Response(res)


@api_view(['GET'])
@permission_classes((AllowAny,))
def get_wallet_type_list(request, format=None):
    res = {}
    try:
        types = []
        objs = WalletCurrency.objects.all()
        for obj in objs:
            types.append({
                'name': obj.name,
                'symbol': obj.symbol
            })
        res['result'] = HTTP_OK
        res['data'] = types

    except:
        err = traceback.print_exc()
        res['result'] = HTTP_ERR
        res['msg'] = err

    return Response(res)


@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def create_plan(request, format=None):
    """
    Create new plan
    ---
    # Request example:
    { "name": "Sliver", "duration": 6 }
    """
    res = {}
    try:
        if not has_permission(request.user, 'add_membershipplan'):
            return Response(status=550)

        req = json.loads(request.body.decode('utf-8'))
        plan = MemberShipPlan(name=req['name'], duration=req['duration'])
        plan.save()

        res['result'] = HTTP_OK
        res['msg'] = 'success'
    except:
        err = traceback.print_exc()
        res['result'] = HTTP_ERR
        res['msg'] = err

    return Response(res)


@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def add_pricing_to_plan(request, format=None):
    """
    Add plan's pricing with specified currency

    ---
    #Request format:
    {
        "plan_id": 1,
        "wallet_type": 1,
        "price": 0.01
    }
    """
    res = {}
    try:
        req = json.loads(request.body.decode('utf-8'))
        if not has_permission(request.user, 'add_membershipplanpricing'):
            return Response(status=550)

        plan = MemberShipPlan.objects.get(pk=req['plan_id'])
        wallet_type = WalletCurrency.objects.get(pk=req['wallet_type'])
        pricing = MemberShipPlanPricing(plan=plan, wallet_currency=wallet_type, price=req['price'])
        pricing.save()
    except:
        err = traceback.print_exc()
        res['result'] = HTTP_ERR
        res['msg'] = err

    return Response(res)


@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def update_user_wallet(request, format=None):
    pass
