from datetime import timedelta, datetime

from django.contrib.auth.models import User
from django.db import models


class WalletCurrency(models.Model):
    """
    Currencies used in payment system.
    """
    name = models.CharField(max_length=50)
    symbol = models.CharField(max_length=50)


class MemberShipPlan(models.Model):
    """
    The basic information of plan
    """
    name = models.CharField(max_length=200)
    duration = models.IntegerField()
    market_subscription_limit = models.IntegerField(default=20)


class MemberShipPlanPricing(models.Model):
    """
    Each plan can include many price in a list of diff currencies.
    """
    plan = models.ForeignKey(MemberShipPlan, on_delete=models.CASCADE, default=1)
    wallet_currency = models.ForeignKey(WalletCurrency, on_delete=models.CASCADE, default=1)
    price = models.DecimalField(max_digits=50, decimal_places=8)


class Profile(models.Model):
    user = models.OneToOneField(User, related_name='primary', on_delete=models.CASCADE, primary_key=True)
    plan = models.ForeignKey(MemberShipPlan, on_delete=models.CASCADE, null=True)
    activated_date = models.DateTimeField(auto_now_add=True, null=True)
    ref = models.CharField(max_length=4, unique=True, null=True)


class Wallet(models.Model):
    """
    User's wallet
    """
    user = models.ForeignKey(Profile, on_delete=models.CASCADE)
    wallet_currency = models.ForeignKey(WalletCurrency, on_delete=models.CASCADE)
    address = models.CharField(max_length=500)
    updated_at = models.DateTimeField(auto_now_add=True)


class AccountVerificationCode(models.Model):
    user = models.ForeignKey(Profile, on_delete=models.CASCADE)
    verify_code = models.CharField(max_length=16)
    expire_on = models.DateTimeField(default=datetime.now() + timedelta(days=1))
