import traceback
from decimal import *

import numpy as np
import pandas as pd
import talib
from bittrex import API_V2_0, Bittrex
from datetime import datetime, timedelta
from django.contrib.auth.models import User, Group, Permission
from django.core.paginator import Paginator
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_jwt.serializers import JSONWebTokenSerializer
from rest_framework_jwt.settings import api_settings
from rest_framework_jwt.utils import jwt_response_payload_handler
from talib import MA_Type
import json

from best_django.settings import BITTREX_SECRET_KEY, BITTREX_API_KEY, HTTP_ERR, HTTP_OK, GROUP_LEADER, \
    STT_PAYMENT_PENDING, STT_ACCOUNT_PENDING, GROUP_ADMIN, STT_PAYMENT_APPROVED, STT_ACCOUNT_ACTIVATED, \
    GROUP_USER, STT_ACCOUNT_OVERDUE, STT_ACCOUNT_BANNED, ADMIN_REF_UID, ACCOUNT_VERIFICATION_EMAIL, \
    ACCOUNT_VERIFICATION_FORGOTPWD, UNLIMITED, STT_PAYMENT_PREPARING
from rest.models import MemberShipPlan, Profile, WalletCurrency, MemberShipPlanPricing, AccountVerificationCode, Wallet, \
    Payment, SalePackageAssignment, UserSubscription, NewsItem, Strategy, NewsCategory, BankAccount
from summary_writer.models import Market, MarketSummary, Candle, Ticker
from utils import generate_ref, send_mail, generate_email_verification_link, get_user_status_name, \
    generate_reset_pwd_link

btx_v2 = Bittrex(BITTREX_API_KEY, BITTREX_SECRET_KEY, api_version=API_V2_0)


class JSONWebTokenAPIView(APIView):
    """
    Base API View that various JWT interactions inherit from.
    """
    permission_classes = ()
    authentication_classes = ()

    def get_serializer_context(self):
        """
        Extra context provided to the serializer class.
        """
        return {
            'request': self.request,
            'view': self,
        }

    def get_serializer_class(self):
        """
        Return the class to use for the serializer.
        Defaults to using `self.serializer_class`.
        You may want to override this if you need to provide different
        serializations depending on the incoming request.
        (Eg. admins get full serialization, others get basic serialization)
        """
        assert self.serializer_class is not None, (
                "'%s' should either include a `serializer_class` attribute, "
                "or override the `get_serializer_class()` method."
                % self.__class__.__name__)
        return self.serializer_class

    def get_serializer(self, *args, **kwargs):
        """
        Return the serializer instance that should be used for validating and
        deserializing input, and for serializing output.
        """
        serializer_class = self.get_serializer_class()
        kwargs['context'] = self.get_serializer_context()
        return serializer_class(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            user = serializer.object.get('user') or request.user
            token = serializer.object.get('token')
            response_data = jwt_response_payload_handler(token, user, request)
            profile = Profile.objects.get(user=user)
            groups = user.groups.all()
            response_data['result'] = HTTP_OK
            response_data['profile'] = {
                'plan': {
                    'id': profile.plan.pk,
                    'name': profile.plan.name
                } if profile.plan is not None else None,
                'ref': profile.ref if profile.ref is not None else '',
                'refer': profile.refer.user_id if profile.refer is not None else None,
                'is_email_verified': profile.is_email_verified,
                'status': profile.status,
                'email': profile.user.email
            }

            for group in groups:
                response_data['profile']['group'] = {
                    'id': group.pk,
                    'name': group.name
                }
            response = Response(response_data)
            if api_settings.JWT_AUTH_COOKIE:
                expiration = (datetime.utcnow() +
                              api_settings.JWT_EXPIRATION_DELTA)
                response.set_cookie(api_settings.JWT_AUTH_COOKIE,
                                    token,
                                    expires=expiration,
                                    httponly=True)
            return response

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ObtainJSONWebToken(JSONWebTokenAPIView):
    """
    API View that receives a POST with a user's username and password.

    Returns a JSON Web Token that can be used for authenticated requests.
    """
    serializer_class = JSONWebTokenSerializer


obtain_jwt_token = ObtainJSONWebToken.as_view()


def has_permission(user, permission_name, label='rest'):
    return user.has_perm('{}.{}'.format(label, permission_name))


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
    try:
        pages = MarketSummary.objects.all().order_by('market__market_name')
        m_res = []
        for m in pages:
            p_change = 100 * (Decimal(m.last) - Decimal(m.prev_day)) / Decimal(m.prev_day) if Decimal(m.prev_day) != 0 else 0
            # print('p_change: ', p_change)
            m_res.append({
                'market_name': m.market.market_name,
                'volume': m.volume,
                'p_change': p_change,
                'last_price': m.last,
                'high': m.high,
                'low': m.low,
                'spread': 0,
                # (Decimal(m.ask) - Decimal(m.bid)) * 100 / Decimal(m.bid),
                'predict_30m': 0,
                'market_currency_long': m.market.market_currency_long,
                'is_subscribed': UserSubscription.objects.filter(profile=Profile.objects.get(user=request.user),
                                                                market=m.market).count() > 0
            })

        return Response({
            'success': True,
            'data': m_res
            # 'paging': {
            #     'total': paging.count,
            #     'num_pages': paging.num_pages,
            #     'has_next': page.has_next(),
            #     'has_prev': page.has_previous()
            # }
        }, status=200)
    except Exception as e:
        traceback.print_exc()
        return Response({
            'success': False,
            'msg': e,
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
                                        is_active=True)

        group = Group.objects.filter(name='User').first()
        group.user_set.add(user)

        # add profile
        profile = Profile()
        profile.user = user
        profile.refer = refer
        # profile.plan = plan
        profile.save()

        try:
            v = AccountVerificationCode.objects.create(user=profile, verify_code=generate_ref(16), expire_on=datetime.now() + timedelta(days=1))
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
        traceback.print_exc()
        res['result'] = HTTP_ERR
        res['msg'] = 'exception'

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
    except Exception as e:
        traceback.print_exc()
        res['result'] = HTTP_ERR
        res['msg'] = 'exception'

    return Response(res)


@api_view(['POST'])
@permission_classes((AllowAny,))
def forgot_password(request, format=None):
    req = json.loads(request.body.decode('utf-8'))
    res = {}
    try:
        u = User.objects.filter(email=req['email'])
        if u.exists():
            u = u.first()
            profile = Profile.objects.get(user=u)
            # delete all previous tokens
            AccountVerificationCode.objects.filter(user=profile, type=ACCOUNT_VERIFICATION_FORGOTPWD).delete()

            vc = AccountVerificationCode.objects.create(user=profile, verify_code=generate_ref(16), expire_on=datetime.now() + timedelta(days=1), type=ACCOUNT_VERIFICATION_FORGOTPWD)
            send_mail(subject='Reset Your Password',
                      to=u.email,
                      html_content='<p>Hi {}</p> '
                                   'Click following link to reset your password: '
                                   '{}'.format(u.username,
                                               generate_reset_pwd_link(
                                                   u.username,
                                                   vc.verify_code)))
            res['result'] = HTTP_OK
            res['msg'] = 'sent'
        else:
            res['result'] = HTTP_ERR
            res['msg'] = 'email_not_found'
    except Exception as e:
        traceback.print_exc()
        res['result'] = HTTP_ERR
        res['msg'] = 'exception'

    return Response(res)


@api_view(['POST'])
@permission_classes((AllowAny,))
def reset_password(request, format=None):
    req = json.loads(request.body.decode('utf-8'))
    res = {}
    try:
        user = User.objects.filter(username=req['username'])
        if user.exists():
            user = user.first()
            vc = AccountVerificationCode.objects.filter(user=Profile.objects.get(user=user), verify_code=req['token'])
            if vc.exists():
                if req['password'] == req['confirmPassword']:
                    user.set_password(req['password'])
                    user.save()
                    vc.delete()
                    res['result'] = HTTP_OK
                else:
                    res['result'] = HTTP_ERR
                    res['msg'] = 'password_field_mismatch'
            else:
                res['result'] = HTTP_ERR
                res['msg'] = 'invalid_token'
        else:
            res['result'] = HTTP_ERR
            res['msg'] = 'user_not_exists'
    except Exception as e:
        traceback.print_exc()
        res['result'] = HTTP_ERR
        res['msg'] = 'exception'

    return Response(res)


@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def get_leader_wallet(request, format=None):
    """
    Get Leader Wallet address
    ---
    #Request
    {"type": "BTC"}
    """
    res = {}
    try:
        profile = Profile.objects.get(user=request.user)
        req = json.loads(request.body.decode('utf-8'))
        type = WalletCurrency.objects.get(symbol=req['type'])
        # get wallet of refer user.
        wallet = Wallet.objects.filter(user=profile.refer, wallet_currency=type).first()
        # print(wallet)
        res['result'] = HTTP_OK
        res['wallet'] = {
            'address': wallet.address if wallet is not None else ''
        }
    except Exception as e:
        traceback.print_exc()
        res['result'] = HTTP_ERR
        res['msg'] = 'exception'

    return Response(res)


@api_view(['GET'])
@permission_classes((IsAuthenticated,))
def get_my_wallet(request, format=None):
    """
    Get my Wallet address
    ---
    #Request
    # Response
    {
        "result": "OK",
        "wallets": [
            {
                "address": "3CMCRgEm8HVz3DrWaCCid3vAANE42jcEv9",
                "symbol": "BTC"
            },
            {
                "address": "LTdsVS8VDw6syvfQADdhf2PHAm3rMGJvPX",
                "symbol": "ETH"
            }
        ]
    }
    """
    res = {}
    try:
        profile = Profile.objects.get(user=request.user)
        # req = json.loads(request.body.decode('utf-8'))
        types = WalletCurrency.objects.all()
        # get wallet of refer user.
        ws = []
        for t in types:
            wallet = Wallet.objects.filter(user=profile, wallet_currency=t).first()
            ws.append({
                'symbol': t.symbol,
                'address': wallet.address if wallet is not None else ""
            })
        res['result'] = HTTP_OK
        res['wallets'] = ws
    except Exception as e:
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

        - Package is unavailable:
        {
            "result": "ERR",
            "msg": "not_enough_availble_package"
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
        # print(req)

        res = {}

        try:
            if not has_permission(request.user, 'add_user', 'auth'):
                return Response(status=550)

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
            
            if is_leader_user(request.user):
                pkg = SalePackageAssignment.objects.filter(profile=Profile.objects.get(user=request.user), plan=plan).first()
                if pkg is not None:
                    # print('pkg', pkg)
                    refer = Profile.objects.get(user=request.user)
                    sold_pkg = Profile.objects.filter(refer=refer, plan=plan).count()
                    # print('sold ', sold_pkg)
                    if pkg.package_count <= sold_pkg:
                        res['result'] = HTTP_ERR
                        res['msg'] = 'not_enough_availble_package'
                        return Response(res)
                else:
                    res['result'] = HTTP_ERR
                    res['msg'] = 'not_enough_availble_package'
                    return Response(res)

            # create user
            user = User.objects.create_user(username=req['username'],
                                            email=req['email'],
                                            password=req['password'],
                                            is_active=True)
            group.user_set.add(user)

            # add profile
            profile = Profile()
            profile.user = user
            profile.plan = plan

            # if user is added to Leader group
            if group.name == GROUP_LEADER:
                profile.status = STT_ACCOUNT_ACTIVATED
                profile.activated_date = datetime.now()
                while True:
                    ref = generate_ref(4)
                    if ref is not None:
                        if not Profile.objects.filter(ref=ref).exists():
                            profile.ref = ref
                            break
            
            # insert ref
            profile.refer = Profile.objects.get(user=request.user)

            profile.save()

            res['result'] = HTTP_OK
            res['msg'] = 'created'
        except Exception as e:
            traceback.print_exc()
            res['result'] = HTTP_ERR
            res['msg'] = 'exception'

        return Response(res)


def request_plan(request, format=None):
    pass


@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def get_pricing_plans(request, format=None):
    """
    Get all plan
    ---
    # Request:
    {"type": "all"} or {"type": "available_only"}
    """
    res = {}
    try:
        req = json.loads(request.body.decode('utf-8'))
        list = []
        plans = MemberShipPlan.objects.all()
        
        base_currency = WalletCurrency.objects.filter(is_base=True).first()

        for p in plans:
            if req['type'] != 'all':
                user_profile = Profile.objects.get(user=request.user)
                if is_leader_user(user_profile.refer.user):
                    pkg = SalePackageAssignment.objects.filter(profile__user_id=user_profile.refer.user.pk, plan=p).first()
                    # get current user's profile
                    sold_pkg = Profile.objects.filter(refer=user_profile.refer, plan=p).count()
                    if pkg.package_count <= sold_pkg:
                        continue
            
            pricing = MemberShipPlanPricing.objects.filter(plan=p, wallet_currency=base_currency).first()
            plan = {
                'id': p.pk,
                'name': p.name,
                'duration': p.duration,
                'market_subscription_limit': p.market_subscription_limit,
                'price': Decimal(pricing.price) if pricing is not None else 0
            }
            list.append(plan)

        res['result'] = HTTP_OK
        res['plans'] = list
    except Exception as e:
        traceback.print_exc()
        res['result'] = HTTP_ERR
        res['msg'] = 'exception'

    return Response(res)


@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def get_pricing_plans_by_wallet(request, format=None):
    res = {}
    try:
        req = json.loads(request.body.decode('utf-8'))
        plan = MemberShipPlan.objects.filter(pk=req['plan_id']).first()

        profile = Profile.objects.filter(user=request.user).first()
        wallets = Wallet.objects.filter(user=profile.refer)
        # print(wallets.count())
        prices = []
        for p in MemberShipPlanPricing.objects.filter(plan=plan):
            leader_wallet = wallets.filter(wallet_currency=p.wallet_currency).first()
            if leader_wallet is not None:
                prices.append({
                    'id': p.id,
                    'symbol': p.wallet_currency.symbol,
                    'price': p.price,
                    'address': leader_wallet.address
                })

        res['result'] = HTTP_OK
        res['prices'] = prices
    except Exception as e:
        traceback.print_exc()
        res['result'] = HTTP_ERR
        res['msg'] = 'exception'

    return Response(res)


@api_view(['GET'])
@permission_classes((IsAuthenticated,))
def get_my_pricing_plans(request, format=None):
    """
    Get my all plan
    ---
    # Request:
    {"type": "all"} or {"type": "available_only"}
    """
    res = {}
    try:
        # req = json.loads(request.body.decode('utf-8'))
        list = []
        plans = MemberShipPlan.objects.all()
        
        for p in plans:
            if is_leader_user(request.user):
                pkg = SalePackageAssignment.objects.filter(profile__user_id=request.user.pk, plan=p).first()
                if pkg is not None:
                    # get current user's profile
                    refer = Profile.objects.get(user=request.user)
                    sold_pkg = Profile.objects.filter(refer=refer, plan=p).count()
                    if pkg.package_count <= sold_pkg:
                        continue
            plan = {
                'id': p.pk,
                'name': p.name,
                'duration': p.duration,
                'market_subscription_limit': p.market_subscription_limit,
                'prices': []
            }
            for price in MemberShipPlanPricing.objects.filter(plan=p):
                p = {
                    'id': price.wallet_currency.pk,
                    'symbol': price.wallet_currency.symbol,
                    'price': price.price
                }
                plan['prices'].append(p)
            list.append(plan)

        res['result'] = HTTP_OK
        res['plans'] = list
    except Exception as e:
        traceback.print_exc()
        res['result'] = HTTP_ERR
        res['msg'] = 'exception'

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
    except Exception as e:
        traceback.print_exc()
        res['result'] = HTTP_ERR
        res['msg'] = 'exception'

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
                'symbol': obj.symbol,
                'isDisabled': obj.is_disabled,
                'isBase': obj.is_base
            })
        res['result'] = HTTP_OK
        res['data'] = types

    except Exception as e:
        traceback.print_exc()
        res['result'] = HTTP_ERR
        res['msg'] = 'exception'

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
        MemberShipPlan.objects.create(name=req['name'], duration=req['duration'])

        base_pricing = req['pricing']
        base_currency = WalletCurrency.objects.filter(is_base=True).first()
        MemberShipPlanPricing.objects.create(plan=plan, wallet_currency=base_currency, price=base_pricing)

        for currency in WalletCurrency.objects.filter(is_base=False):
            market = Market.objects.filter(base_currency=base_currency.symbol, market_currency=currency.symbol).first()
            tick = Ticker.objects.filter(market=market).order_by('-timestamp').first()
            price = (tick.bid + tick.ask) / 2
            plan_price = Decimal(base_pricing) / price
            MemberShipPlanPricing.objects.create(plan=plan, wallet_currency=currency, price=plan_price)

        res['result'] = HTTP_OK
        res['msg'] = 'success'
    except Exception as e:
        traceback.print_exc()
        res['result'] = HTTP_ERR
        res['msg'] = 'exception'

    return Response(res)


@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def update_plan(request, format=None):
    """
    Update plan
    ---
    # Request example:
    { "id": 1, "name": "Sliver", "duration": 6 }
    """
    res = {}
    try:
        if not has_permission(request.user, 'change_membershipplan'):
            return Response(status=550)

        req = json.loads(request.body.decode('utf-8'))
        plan = MemberShipPlan.objects.filter(pk=req['id']).first()
        if plan is not None:
            plan.name = req['name']
            plan.duration = req['duration']
            plan.save()

            base_pricing = req['pricing']
            base_currency = WalletCurrency.objects.filter(is_base=True).first()
            pricing_obj = MemberShipPlanPricing.objects.filter(plan=plan, wallet_currency=base_currency).first()
            if pricing_obj is not None:
                pricing_obj.price = Decimal(base_pricing)
                pricing_obj.save()
            else:
                MemberShipPlanPricing.objects.create(plan=plan, wallet_currency=base_currency, price=base_pricing)

            for currency in WalletCurrency.objects.filter(is_base=False):
                # calculating new price
                market = Market.objects.filter(base_currency=base_currency.symbol, market_currency=currency.symbol).first()
                tick = Ticker.objects.filter(market=market).order_by('-timestamp').first()
                price = (tick.bid + tick.ask) / 2
                plan_price = Decimal(base_pricing) / price
                # update plan pricing
                p = MemberShipPlanPricing.objects.filter(plan=plan, wallet_currency=currency).first()
                if p is not None:
                    p.price = plan_price
                    p.save()
                else:
                    MemberShipPlanPricing.objects.create(plan=plan, wallet_currency=currency, price=plan_price)

        res['result'] = HTTP_OK
        res['msg'] = 'success'
    except Exception as e:
        traceback.print_exc()
        res['result'] = HTTP_ERR
        res['msg'] = 'exception'

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
    except Exception as e:
        traceback.print_exc()
        res['result'] = HTTP_ERR
        res['msg'] = 'exception'

    return Response(res)


@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def update_user_wallet(request, format=None):
    """
    #request
    {
        "wallet_type": "ETH",
        "address": "LTdsVS8VDw6syvfQADdhf2PHAm3rMGJvPX"
    }
    """
    res = {}
    try:
        req = json.loads(request.body.decode('utf-8'))
        if not has_permission(request.user, 'change_wallet'):
            return Response(status=550)

        profile = Profile.objects.filter(user=request.user).first()
        wallet = Wallet.objects.filter(user=profile, wallet_currency__symbol=req['wallet_type'])
        if wallet.exists():
            wallet = wallet.first()
            wallet.address = req['address']
            wallet.save()
        else:
            type = WalletCurrency.objects.filter(symbol=req['wallet_type']).first()
            Wallet.objects.create(user=profile, wallet_currency=type, address=req['address'])

        res['result'] = HTTP_OK
    except Exception as e:
        traceback.print_exc()
        res['result'] = HTTP_ERR
        res['msg'] = 'exception'

    return Response(res)


@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def confirm_payment(request, format=None):
    """
    Confirm payment is valid
    ---
    # Request
    - {
        "payment_id": 1
    }

    # Response
    - Payment ID could not be found
    {
        "result": "ERR",
        "msg": "payment_not_found"
    }
    - Success
    {"result": "OK"}
    """
    res = {}
    try:
        req = json.loads(request.body.decode('utf-8'))
        if not has_permission(request.user, 'can_confirm_payment'):
            return Response(status=550)

        if Payment.objects.filter(pk=req['payment_id']).exists():
            bill = Payment.objects.get(pk=req['payment_id'])
            bill.status = STT_PAYMENT_APPROVED
            bill.save()

            bill.profile.status = STT_ACCOUNT_ACTIVATED
            bill.profile.save()

            try:
                send_mail(subject='Account Activation',
                        to=bill.profile.user.email,
                        html_content='<p>Hi {}</p><br /> Your account is now activated. Visit and enjoy our platform.'.format(bill.profile.user.username))
            except:
                traceback.print_exc()

            res['result'] = HTTP_OK
        else:
            res['result'] = HTTP_ERR
            res['msg'] = 'payment_not_found'
    except Exception as e:
        traceback.print_exc()
        res['result'] = HTTP_ERR
        res['msg'] = 'exception'

    return Response(res)


@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def prepare_payment(request, format=None):
    res = {}
    try:
        profile = Profile.objects.get(user=request.user)

        # create bill
        bill = Payment.objects.filter(profile=profile, status=STT_PAYMENT_PREPARING)
        if bill.exists():
            bill = bill.first()
            bill.hash = generate_ref(4)
            bill.save()
        else:
            bill = Payment.objects.create(profile=profile,
                               hash=generate_ref(4),
                               status=STT_PAYMENT_PREPARING)
        res = {
            'result': HTTP_OK,
            'hash': bill.hash
        }
    except Exception as e:
        traceback.print_exc()
        res['result'] = HTTP_ERR
        res['msg'] = 'exception'

    return Response(res)


@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def submit_payment(request, format=None):
    """
    Submit payment
    ---
    # Request
    {
        "wallet_type": 1,
        "hash": "sdfsdfsdfdsfwerew",
        "plan": 2
    }
    """
    res = {}
    try:
        req = json.loads(request.body.decode('utf-8'))
        profile = Profile.objects.get(user=request.user)

        bill = Payment.objects.filter(hash=req['hash']).first()
        if bill is not None:
            bill.status = STT_PAYMENT_PENDING
            bill.save()
            try:
                send_mail(subject='New Subscription',
                        to=profile.refer.user.email,
                        html_content='<p>Hi {}</p><br /> New account register. Go to Dashboard to review.'.format(profile.refer.user.username))
            except:
                traceback.print_exc()
            
            # update profile info
            profile.plan = MemberShipPlan.objects.get(pk=req['plan'])
            profile.status = STT_ACCOUNT_PENDING
            profile.save()
            res['result'] = HTTP_OK
        else:
            res['result'] = HTTP_ERR
            res['msg'] = 'exception'    
    except Exception as e:
        traceback.print_exc()
        res['result'] = HTTP_ERR
        res['msg'] = 'exception'

    return Response(res)


@api_view(['GET'])
@permission_classes((IsAuthenticated,))
def get_user_list(request, format=None):
    res = {}
    try:
        # req = json.loads(request.body.decode('utf-8'))
        users = []
        group = None
        for g in request.user.groups.all():
            group = g
            break
        if group.name == GROUP_ADMIN:
            users = Profile.objects.all()
        elif group.name == GROUP_LEADER:
            refer_profile = Profile.objects.get(user=request.user)
            users = Profile.objects.filter(refer=refer_profile)

        res['users'] = []
        for user in users:
            if user.user.username == 'bean':
                continue
            group = {}
            groups = user.user.groups.all()
            for g in groups:
                group = {
                    'id': g.pk,
                    'name': g.name
                }
                break

            res['users'].append({
                'id': user.user.pk,
                'username': user.user.username,
                'email': user.user.email,
                'group': group,
                'plan': {
                    'id': user.plan.pk,
                    'name': user.plan.name
                } if user.plan is not None else None,
                'refer_by': {
                    'id': user.refer.user.pk,
                    'name': user.refer.user.username
                } if user.refer is not None else None,
                'is_email_verified': user.is_email_verified,
                'status': get_user_status_name(user.status)
            })

        res['result'] = HTTP_OK
        
    except Exception as e:
        traceback.print_exc()
        res['result'] = HTTP_ERR
        res['msg'] = 'exception'

    return Response(res)


@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def search_user_by_invoice(request, format=None):
    res = {}
    try:
        req = json.loads(request.body.decode('utf-8'))
        profile=Profile.objects.get(user=request.user)

        users = []
        inv = Payment.objects.filter(hash=req['hash'])
        if inv.exists():
            inv = inv.first()
            if inv.profile.refer.pk == profile.user.pk:
                user = inv.profile

                group = {}
                groups = user.user.groups.all()
                for g in groups:
                    group = {
                        'id': g.pk,
                        'name': g.name
                    }
                    break

                users.append({
                    'id': user.user.pk,
                    'username': user.user.username,
                    'email': user.user.email,
                    'group': group,
                    'plan': {
                        'id': user.plan.pk,
                        'name': user.plan.name
                    } if user.plan is not None else None,
                    'refer_by': {
                        'id': user.refer.user.pk,
                        'name': user.refer.user.username
                    } if user.refer is not None else None,
                    'is_email_verified': user.is_email_verified,
                    'status': get_user_status_name(user.status)
                })
        res['result'] = HTTP_OK
        res['users'] = users
    except Exception as e:
        traceback.print_exc()
        res['result'] = HTTP_ERR
        res['msg'] = 'exception'

    return Response(res)


@api_view(['GET'])
@permission_classes((AllowAny,))
def get_groups(request, format=None):
    """
    Get groups list.
    ---
    # Request: 
    - khong gui gi :D
    """
    res = {}
    try:
        # req = json.loads(request.body.decode('utf-8'))
        groups = Group.objects.all()
        res['groups'] = []
        for g in groups:
            res['groups'].append({
                'id': g.pk,
                'name': g.name
            })
        res['result'] = HTTP_OK
    except Exception as e:
        traceback.print_exc()
        res['result'] = HTTP_ERR
        res['msg'] = 'exception'

    return Response(res)


@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def get_user_payment_history(request, format=None):
    """
    Get list payment history
    ---
    # Request
    - {
        "user_id": 18
    }
    """
    res = {}
    try:
        if not has_permission(request.user, 'can_view_payment_history'):
            return Response(status=550)

        req = json.loads(request.body.decode('utf-8'))
        profile = Profile.objects.get(user_id=req['user_id'])
        payments = Payment.objects.filter(profile=profile).order_by('-updated_on')
        res['list'] = []
        for p in payments:
            res['list'].append({
                'id': p.pk,
                'hash': p.hash,
                'updated_on': p.updated_on,
                'status': p.status,
                'wallet_type': {
                    'id': p.wallet_type.pk,
                    'name': p.wallet_type.symbol
                } if p.wallet_type is not None else None
            })
        res['result'] = HTTP_OK
    except Exception as e:
        traceback.print_exc()
        res['result'] = HTTP_ERR
        res['msg'] = 'exception'

    return Response(res)


def is_leader_user(user):
    groups = user.groups.all()
    for g in groups:
        if g.name == GROUP_LEADER:
            return True
    return False


@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def assign_sale_package(request, format=None):
    """
    Assign package for leader
    ---
    # Request
    {
        "assigned_to": 9,
        "packages": [
            {
                "plan_id": 1,
                "count": 3
            }
        ]
    }
    # Response
    - User is not in Leader group
    {"msg":"user_not_leader","result":"ERR"}
    - User not exists
    {"msg":"user_not_exists","result":"ERR"}
    - Update success
    {"result":"OK"}
    """
    res = {}
    try:
        if not has_permission(request.user, 'change_salepackageassignment'):
            return Response(status=550)

        req = json.loads(request.body.decode('utf-8'))
        user = User.objects.filter(pk=req['assigned_to'])
        if not user.exists():
            res['result'] = HTTP_ERR
            res['msg'] = 'user_not_exists'
            return Response(res)
        else:
            user = user.first()
        
        profile = Profile.objects.get(user=user)
        
        if not is_leader_user(user):
            res['result'] = HTTP_ERR
            res['msg'] = 'user_not_leader'
            return Response(res)

        for p in req['packages']:
            pkg = SalePackageAssignment.objects.filter(profile__user_id=profile.user.pk, plan=MemberShipPlan.objects.get(pk=p['plan_id'])).first()
            if pkg is None:
                SalePackageAssignment.objects.create(profile=profile, plan=MemberShipPlan.objects.get(pk=p['plan_id']), package_count=p['count'])
            else:
                pkg.package_count = p['count']
                pkg.save()
        res['result'] = HTTP_OK
    except Exception as e:
        traceback.print_exc()
        res['result'] = HTTP_ERR
        res['msg'] = 'exception'

    return Response(res)


@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def get_sale_package(request, format=None):
    """
    Get sale package
    ---
    # Request
    {
        "user_id": 2
    }
    # Response
    - User is not in Leader group
    {"msg":"user_not_leader","result":"ERR"}
    - User not exists
    {"msg":"user_not_exists","result":"ERR"}
    - Update success
    {
        "result": "OK",
        "packages": [
            {
                "plan_id": 1,
                "plan_name": "Plan A",
                "count": 4
            }
        ]
    }
    """
    res = {}
    try:
        req = json.loads(request.body.decode('utf-8'))
        user = User.objects.filter(pk=req['user_id'])
        if not user.exists():
            res['result'] = HTTP_ERR
            res['msg'] = 'user_not_exists'
            return Response(res)
        else:
            user = user.first()
        
        profile = Profile.objects.get(user=user)
        
        if not is_leader_user(user):
            res['result'] = HTTP_ERR
            res['msg'] = 'user_not_leader'
            return Response(res)

        plans = MemberShipPlan.objects.all()
        res['packages'] = []
        for plan in plans:
            pkg = SalePackageAssignment.objects.filter(profile__user_id=profile.user.pk, plan=plan).first()
            sold_pkg = Profile.objects.filter(refer=profile, plan=plan).count()
            d = {
                'plan_id': plan.pk,
                'plan_name': plan.name,
                'count': 0,
                'sold_count': sold_pkg
            }
            if pkg is not None:
                d['count'] = pkg.package_count
            res['packages'].append(d)
        res['result'] = HTTP_OK
    except Exception as e:
        traceback.print_exc()
        res['result'] = HTTP_ERR
        res['msg'] = 'exception'

    return Response(res)


@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def user_subscribe(request, format=None):
    """
    # Request
    {"market_name": "BTC-LTC"}

    # Response
    - Chua chon plan nao
    { "result": "ERR", "msg": "unpaid_user" }
    - Chua thanh toan, hoac tai khoan bi khoa
    { "result": "ERR", "msg": "user_not_activated" }
    - Da subscribe hon so luong quy dinh (20 markets)
    { "result": "ERR", "msg": "reached_limit" }

    - Thanh cong
    {"result": "OK"}
    """
    res = {}
    try:
        req = json.loads(request.body.decode('utf-8'))
        profile = Profile.objects.get(user=request.user)
        market = Market.objects.get(market_name=req['market_name'])
        subscription_count = UserSubscription.objects.filter(profile=profile).count()
        if profile.ref != ADMIN_REF_UID:
            if profile.plan is None:
                res['result'] = HTTP_ERR
                res['msg'] = 'unpaid_user'
                return Response(res)

            if profile.status != STT_ACCOUNT_ACTIVATED:
                res['result'] = HTTP_ERR
                res['msg'] = 'user_not_activated'
                return Response(res)

            if profile.plan.market_subscription_limit != UNLIMITED:
                if subscription_count >= profile.plan.market_subscription_limit:
                    res['result'] = HTTP_ERR
                    res['msg'] = 'reached_limit'
                    return Response(res)

        if not UserSubscription.objects.filter(profile=profile, market=market).exists():
            UserSubscription.objects.create(profile=profile, market=market)

        res['result'] = HTTP_OK
    except Exception as e:
        traceback.print_exc()
        res['result'] = HTTP_ERR
        res['msg'] = 'exception'

    return Response(res)


@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def unsubscribe_market(request, format=None):
    """
    # Request
    {"market_name": "BTC-LTC"}

    # Response
    - Chua chon plan nao
    { "result": "ERR", "msg": "unpaid_user" }
    - Chua thanh toan, hoac tai khoan bi khoa
    { "result": "ERR", "msg": "user_not_activated" }

    - Thanh cong
    {"result": "OK"}
    """
    res = {}
    try:
        req = json.loads(request.body.decode('utf-8'))
        profile = Profile.objects.get(user=request.user)
        market = Market.objects.get(market_name=req['market_name'])
        subscription_count = UserSubscription.objects.filter(profile=profile).count()
        if profile.plan is None:
            res['result'] = HTTP_ERR
            res['msg'] = 'unpaid_user'
            return Response(res)

        if profile.status != STT_ACCOUNT_ACTIVATED:
            res['result'] = HTTP_ERR
            res['msg'] = 'user_not_activated'
            return Response(res)

        if UserSubscription.objects.filter(profile=profile, market=market).exists():
            UserSubscription.objects.filter(profile=profile, market=market).delete()

        res['result'] = HTTP_OK
    except Exception as e:
        traceback.print_exc()
        res['result'] = HTTP_ERR
        res['msg'] = 'exception'

    return Response(res)


@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def activate_user(request, format=None):
    """
    # Request:
    {
        "user_id": 24
    }

    # Response
    - Refer user đó không phải là thằng request
    { "result": "ERR", "msg": "refer_user_invalid" }

    - Chưa chọn plan nào mà đòi active
    { "result": "ERR", "msg": "invalid_plan" }

    - Thành công
    {
        "result": "OK"
    }
    """
    res = {}
    try:
        req = json.loads(request.body.decode('utf-8'))
        user_profile = Profile.objects.get(user=User.objects.get(pk=req['user_id']))
        leader_profile = Profile.objects.get(user=request.user)

        if not has_permission(request.user, 'can_activate_user', label='auth'):
            return Response(status=550)

        if user_profile.refer.pk != leader_profile.pk:
            res['result'] = HTTP_ERR
            res['msg'] = 'refer_user_invalid'
            return Response(res)
        
        if user_profile.plan is None:
            res['result'] = HTTP_ERR
            res['msg'] = 'invalid_plan'
            return Response(res)

        if user_profile.status == STT_ACCOUNT_ACTIVATED:
            res['result'] = HTTP_ERR
            res['msg'] = 'aleady_activated'
            return Response(res)

        user_profile.status = STT_ACCOUNT_ACTIVATED
        user_profile.activated_date = datetime.now()
        user_profile.save()

        inv = Payment.objects.filter(profile=user_profile, status=STT_PAYMENT_PENDING)
        if inv.exists():
            inv = inv.first()
            inv.status = STT_PAYMENT_APPROVED
            inv.save()

        res['result'] = HTTP_OK
    except Exception as e:
        traceback.print_exc()
        res['result'] = HTTP_ERR
        res['msg'] = 'exception'

    return Response(res)


@api_view(['GET'])
@permission_classes((AllowAny,))
def get_news(request, format=None):
    res = {}
    try:
        newslist = NewsItem.objects.all()[:50]
        nlist = []
        for news in newslist:
            nlist.append({
                'title': news.title,
                'url': news.url,
                'img': news.img,
                'short_desc': news.short_desc,
                'category': {
                    'title': news.category_title,
                    'url': news.category_url
                },
                'date': news.date
            })
        res['result'] = HTTP_OK
        res['list'] = nlist
    except Exception as e:
        traceback.print_exc()
        res['result'] = HTTP_ERR
        res['msg'] = 'exception'

    return Response(res)


@api_view(['GET'])
@permission_classes((AllowAny,))
def get_news_categories(request, format=None):
    res = {}
    try:
        newslist = NewsCategory.objects.all()[:10]
        nlist = []
        for cat in newslist:
            nlist.append({
                'title': cat.title,
                'url': cat.url
            })
        res['result'] = HTTP_OK
        res['list'] = nlist
    except Exception as e:
        traceback.print_exc()
        res['result'] = HTTP_ERR
        res['msg'] = 'exception'

    return Response(res)


@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def update_user_plan(request, format=None):
    """
    # Request
    {
        "user_id": 23, // user can change plan
        "plan_id": 3 // plan id
    }
    """
    res = {}
    try:
        if not has_permission(request.user, 'change_membershipplan', 'rest'):
            return Response(status=550)

        req = json.loads(request.body.decode('utf-8'))
        profile = Profile.objects.filter(user__pk=req['user_id']).first()
        if profile is not None:
            plan = MemberShipPlan.objects.get(pk=req['plan_id'])
            profile.plan = plan
            profile.save()
            res['result'] = HTTP_OK
        else:
            res['result'] = HTTP_ERR
    except Exception as e:
        traceback.print_exc()
        res['result'] = HTTP_ERR
        res['msg'] = 'exception'

    return Response(res)


@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def renew_user(request, format=None):
    """
    # Request
    {
        "user_id": 23, // user can change plan
    }
    """
    res = {}
    try:
        if not has_permission(request.user, 'can_activate_user', label='auth'):
            return Response(status=550)

        req = json.loads(request.body.decode('utf-8'))
        profile = Profile.objects.filter(user__pk=req['user_id']).first()
        if profile is not None:
            if profile.status == STT_ACCOUNT_OVERDUE:
                profile.activated_date = datetime.now()
                profile.status = STT_ACCOUNT_ACTIVATED
                profile.save()
                res['result'] = HTTP_OK
            else:
                res['result'] = HTTP_ERR
                res['msg'] = 'user_cannot_renew'
        else:
            res['result'] = HTTP_ERR
    except Exception as e:
        traceback.print_exc()
        res['result'] = HTTP_ERR
        res['msg'] = 'exception'

    return Response(res)


@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def ban_user(request, format=None):
    """
    # Request
    {
        "user_id": 23, // user can change plan
    }
    """
    res = {}
    try:
        if not has_permission(request.user, 'can_activate_user', label='auth'):
            return Response(status=550)

        req = json.loads(request.body.decode('utf-8'))
        profile = Profile.objects.filter(user__pk=req['user_id']).first()
        if profile is not None:
            profile.status = STT_ACCOUNT_BANNED
            profile.save()
            res['result'] = HTTP_OK
        else:
            res['result'] = HTTP_ERR
    except Exception as e:
        traceback.print_exc()
        res['result'] = HTTP_ERR
        res['msg'] = 'exception'

    return Response(res)


@api_view(['GET'])
@permission_classes((IsAuthenticated,))
def get_user_profile(request, format=None):
    res = {}
    try:
        profile = Profile.objects.filter(user=request.user).first()
        if profile is not None:
            res['result'] = HTTP_OK

            group = profile.user.groups.first()
            plan_duration_days = profile.plan.duration * 30 if profile.plan is not None else 0

            res['profile'] = {
                'id': profile.user.pk,
                'username': profile.user.username,
                'email': profile.user.email,
                'first_name': profile.user.first_name,
                'last_name': profile.user.last_name,
                'phone_number': profile.phone_number,
                'status': profile.status,
                'avatar': profile.avatar,
                'ref': profile.ref,
                'team_member': Profile.objects.filter(refer=profile).count(),
                'plan': {
                    'id': profile.plan.pk,
                    'name': profile.plan.name,
                    'duration': profile.plan.duration,
                    'market_subscription_limit': profile.plan.market_subscription_limit
                } if profile.plan is not None else {},
                'group': {
                    'id': group.pk,
                    'name': group.name
                } if group is not None else {},
                'market_subscribe': UserSubscription.objects.filter(profile=profile).count(),
                'wallets': [],
                'activated_date': profile.activated_date,
                'expire_date': profile.activated_date + timedelta(days=plan_duration_days) if profile.activated_date is not None else None
            }

            for wc in WalletCurrency.objects.filter(is_base=False, is_disabled=False):
                w = Wallet.objects.filter(user=profile, wallet_currency=wc).first()
                res['profile']['wallets'].append({
                    'id': w.pk if w is not None else None,
                    'currency': {
                        'id': wc.pk,
                        'name': wc.name,
                        'symbol': wc.symbol
                    },
                    'address': w.address if w is not None else ''
                })
        else:
            res['result'] = HTTP_ERR
            res['msg'] = 'user_not_found'
    except Exception as e:
        traceback.print_exc()
        res['result'] = HTTP_ERR
        res['msg'] = 'exception'

    return Response(res)


@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def update_profile(request, format=None):
    res = {}
    try:
        req = json.loads(request.body.decode('utf-8'))
        user = request.user
        user.first_name = req['first_name']
        user.last_name = req['last_name']
        user.save()

        profile = Profile.objects.get(user=request.user)
        profile.phone_number = req['phone_number']
        profile.save()

        res['result'] = HTTP_OK
    except Exception as e:
        traceback.print_exc()
        res['result'] = HTTP_ERR
        res['msg'] = 'exception'

    return Response(res)


@api_view(['GET'])
@permission_classes((IsAuthenticated,))
def get_leader_info(request, format=None):
    res = {}
    try:
        profile = Profile.objects.get(user=request.user)
        refer = profile.refer
        bank_account = BankAccount.objects.filter(user=refer).first()
        info = {
            'email': refer.user.email,
            'phone_number': refer.phone_number,
            'avatar': refer.avatar,
            'fullname': '{} {}'.format(refer.user.last_name, refer.user.first_name),
            'bank_account': {
                'name': bank_account.bank_name if bank_account is not None else '',
                'account': bank_account.bank_account if bank_account is not None else '',
                'branch': bank_account.bank_branch if bank_account is not None else ''
            }
        }
        res['result'] = HTTP_OK
        res['info'] = info
    except Exception as e:
        traceback.print_exc()
        res['result'] = HTTP_ERR
        res['msg'] = 'exception'

    return Response(res)


@api_view(['GET'])
@permission_classes((IsAuthenticated,))
def get_bank_account(request, format=None):
    res = {}
    try:
        profile = Profile.objects.filter(user=request.user).first()
        account = BankAccount.objects.filter(user=profile).first()
        res['result'] = HTTP_OK
        if account is not None:
            res['account'] = {
                'bank_name': account.bank_name,
                'bank_branch': account.bank_branch,
                'account': account.bank_account
            }
        else:
            res['account'] = {
                'bank_name': '',
                'bank_branch': '',
                'account': ''
            }
    except Exception as e:
        traceback.print_exc()
        res['result'] = HTTP_ERR
        res['msg'] = 'exception'

    return Response(res)


@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def update_bank_account(request, format=None):
    if not has_permission(request.user, 'change_bankaccount', label='rest'):
            return Response(status=550)

    res = {}
    try:
        req = json.loads(request.body.decode('utf-8'))

        profile = Profile.objects.filter(user=request.user).first()
        if profile is not None:
            account = BankAccount.objects.filter(user=profile).first()
            if account is not None:
                account.bank_name = req['bank_name']
                account.bank_account = req['account']
                account.bank_branch = req['branch_name']
                account.save()
            else:
                BankAccount.objects.create(user=profile,
                                           bank_name=req['bank_name'],
                                           bank_account=req['account'],
                                           bank_branch=req['branch_name'])
            res['result'] = HTTP_OK
        else:
            res['result'] = HTTP_ERR
            res['msg'] = 'user_not_found'
    except Exception as e:
        traceback.print_exc()
        res['result'] = HTTP_ERR
        res['msg'] = 'exception'

    return Response(res)


@api_view(['GET'])
@permission_classes((IsAuthenticated,))
def get_strategies(request, format=None):
    """
    """
    res = {}
    try:
        query_set = Strategy.objects.all()
        strategies = []
        for q in query_set:
            strategies.append({
                'id': q.pk,
                'name': q.name,
                'message': q.message
            })
        res['result'] = HTTP_OK
        res['strategies'] = strategies
    except Exception as e:
        traceback.print_exc()
        res['result'] = HTTP_ERR
        res['msg'] = 'exception'

    return Response(res)


@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def update_strategy_details(request, format=None):
    """
    # Request:
    {
        "id": 1,
        "name": "RSI",
        "message": "Time to make something happen."
    }
    # Response
    - Strategy not found:
    { "result": "ERR", "msg": "not_found" }

    - Success
    {
        "result": "OK"
    }
    """
    res = {}
    try:
        if not has_permission(request.user, 'change_strategy', label='rest'):
            return Response(status=550)

        req = json.loads(request.body.decode('utf-8'))
        strategy = Strategy.objects.filter(pk=req['id'])
        if strategy.exists():
            strategy = strategy.first()
            strategy.name = req['name']
            strategy.message = req['message']
            strategy.save()
            res['result'] = HTTP_OK
        else:
            res['result'] = HTTP_ERR
            res['msg'] = 'not_found'
    except Exception as e:
        traceback.print_exc()
        res['result'] = HTTP_ERR
        res['msg'] = 'exception'

    return Response(res)