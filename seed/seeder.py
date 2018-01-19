from django.contrib.auth.models import User, Group, Permission

from best_django.settings import GROUP_ADMIN, GROUP_LEADER, GROUP_USER
from rest.models import *


def create_groups():
    Group.objects.create(name=GROUP_ADMIN)
    Group.objects.create(name=GROUP_LEADER)
    Group.objects.create(name=GROUP_USER)


def create_extend_permissions():
    permission = Permission.objects.create(codename='can_add_project',
                                           name='Can add project')


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
