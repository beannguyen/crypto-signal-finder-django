from django.contrib.auth.models import User

from rest.models import *


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
