from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType

from best_django.settings import GROUP_ADMIN, GROUP_LEADER, GROUP_USER
from rest.models import *
from summary_writer.models import *
from decimal import *


def create_groups():
    Group.objects.create(name=GROUP_ADMIN)
    Group.objects.create(name=GROUP_LEADER)
    Group.objects.create(name=GROUP_USER)


def create_extend_permissions():
    permissions = [
        {
            'codename': 'can_view_payment_history',
            'name': 'Can view payment history',
            'content_type': ContentType.objects.filter(app_label='rest', model='payment').first()
        },
        {
            'codename': 'can_assign_sale_package',
            'name': 'Can assign sale package',
            'content_type': ContentType.objects.filter(app_label='rest', model='payment').first()
        },
        {
            'codename': 'can_confirm_payment',
            'name': 'Can confirm payment',
            'content_type': ContentType.objects.filter(app_label='rest', model='payment').first()
        },
        {
            'codename': 'can_activate_user',
            'name': 'Can activate user',
            'content_type': ContentType.objects.filter(app_label='auth', model='user').first()
        }
        
    ]

    for perm in permissions:
        if not Permission.objects.filter(codename=perm['codename']).exists():
            permission = Permission.objects.create(codename=perm['codename'], name=perm['name'], content_type=perm['content_type'])


def create_superadmin():
    User.objects.create_superuser(username='bean', email='beanchanel@gmail.com', password='@nhdeptrai123')


def create_admin():
    user = User.objects.create_user(username='admin', email='admin@gmail.com', password='123465', is_active=True)
    profile = Profile.objects.create(user=user, ref='1111')


def create_wallet_type():
    types = [
        {
            'name': 'Bitcoin',
            'symbol': 'BTC',
            'is_disabled': False,
            'is_base': False
        },
        {
            'name': 'Etherum',
            'symbol': 'ETH',
            'is_disabled': False,
            'is_base': False
        },
        {
            'name': 'Dollar',
            'symbol': 'USDT',
            'is_disabled': False,
            'is_base': True
        }
    ]

    for t in types:
        if not WalletCurrency.objects.filter(symbol=t['symbol']).exists():
            WalletCurrency.objects.create(name=t['name'], symbol=t['symbol'], is_disabled=t['is_disabled'], is_base=t['is_base'])


def create_plan():
    plans = [
        {
            'name': 'Plan A',
            'duration': 1,
            'market_subscription_limit': 5,
            'pricing': 50
        },
        {
            'name': 'Plan B',
            'duration': 1,
            'market_subscription_limit': -1,
            'pricing': 80
        },
        {
            'name': 'Plan C',
            'duration': 7,
            'market_subscription_limit': 5,
            'pricing': 300
        }
    ]
    for pl in plans:
        plan = MemberShipPlan.objects.create(name=pl['name'], duration=pl['duration'], market_subscription_limit=pl['market_subscription_limit'])
        base_pricing = pl['pricing']
        base_currency = WalletCurrency.objects.filter(is_base=True).first()
        MemberShipPlanPricing.objects.create(plan=plan, wallet_currency=base_currency, price=base_pricing)

        for currency in WalletCurrency.objects.filter(is_base=False):
            market = Market.objects.filter(base_currency=base_currency.symbol, market_currency=currency.symbol).first()
            tick = Ticker.objects.filter(market=market).order_by('-timestamp').first()
            price = (tick.bid + tick.ask) / 2
            plan_price = Decimal(base_pricing) / price
            MemberShipPlanPricing.objects.create(plan=plan, wallet_currency=currency, price=plan_price)


def create_strategy_list():
    strategies = [
        {
            'name': 'BB&RSI'
        },
        {
            'name': 'ClosePrice'
        }
    ]

    for strategy in strategies:
        Strategy.objects.create(name=strategy['name'])


def add_leader_permissions():
    permissions = [
        {
            'model': 'user',
            'app_label': 'auth',
            'codename': 'add_user'
        },
        {
            'model': 'user',
            'app_label': 'auth',
            'codename': 'change_user'
        },
        {
            'model': 'user',
            'app_label': 'auth',
            'codename': 'delete_user'
        },
        {
            'model': 'membershipplan',
            'app_label': 'rest',
            'codename': 'change_membershipplan'
        },
        {
            'model': 'profile',
            'app_label': 'rest',
            'codename': 'add_profile'
        },
        {
            'model': 'profile',
            'app_label': 'rest',
            'codename': 'change_profile'
        },
        {
            'model': 'profile',
            'app_label': 'rest',
            'codename': 'delete_profile'
        },
        {
            'model': 'wallet',
            'app_label': 'rest',
            'codename': 'add_wallet'
        },
        {
            'model': 'wallet',
            'app_label': 'rest',
            'codename': 'change_wallet'
        },
        {
            'model': 'wallet',
            'app_label': 'rest',
            'codename': 'delete_wallet'
        },
        {
            'model': 'payment',
            'app_label': 'rest',
            'codename': 'add_payment'
        },
        {
            'model': 'payment',
            'app_label': 'rest',
            'codename': 'change_payment'
        },
        {
            'model': 'payment',
            'app_label': 'rest',
            'codename': 'can_view_payment_history'
        },
        {
            'model': 'payment',
            'app_label': 'rest',
            'codename': 'can_confirm_payment'
        },
        {
            'model': 'user',
            'app_label': 'auth',
            'codename': 'can_activate_user'
        },
        {
            'model': 'bankaccount',
            'app_label': 'rest',
            'codename': 'add_bankaccount'
        },
        {
            'model': 'bankaccount',
            'app_label': 'rest',
            'codename': 'change_bankaccount'
        },
        {
            'model': 'bankaccount',
            'app_label': 'rest',
            'codename': 'delete_bankaccount'
        }
    ]
    for perm in permissions:
        content_type = ContentType.objects.filter(model=perm['model'], app_label=perm['app_label']).first()
        if content_type is not None:
            permission = Permission.objects.filter(content_type=content_type, codename=perm['codename']).first()
            leader_group = Group.objects.get(pk=2)
            if permission is not None:
                leader_group.permissions.add(permission)


def run():
    create_superadmin()
    create_admin()
    create_groups()
    create_extend_permissions()
    create_wallet_type()
    create_strategy_list()
    create_plan()
    add_leader_permissions()
