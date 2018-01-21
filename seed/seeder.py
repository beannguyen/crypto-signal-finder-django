from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType

from best_django.settings import GROUP_ADMIN, GROUP_LEADER, GROUP_USER
from rest.models import *


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
        }
    ]

    for perm in permissions:
        if not Permission.objects.filter(codename=perm['codename']).exists():
            permission = Permission.objects.create(codename=perm['codename'], name=perm['name'], content_type=perm['content_type'])


def create_superadmin():
    User.objects.create_superuser(username='bean', email='admin@gmail.com', password='123465')


def create_admin():
    user = User.objects.create(username='admin', email='admin@gmail.com', password='123465', is_active=True)
    profile = Profile.objects.create(user=user, ref='1111')


def create_wallet_type():
    WalletCurrency.objects.create(name='BTC Wallet', symbol='BTC')
    WalletCurrency.objects.create(name='ETH Wallet', symbol='ETH')


def create_plan():
    plans = [
        {
            'name': 'Plan A',
            'duration': 1
        },
        {
            'name': 'Plan B',
            'duration': 4
        },
        {
            'name': 'Plan C',
            'duration': -1
        }
    ]
    for pl in plans:
        MemberShipPlan.objects.create(name=pl['name'], duration=pl['duration'])
