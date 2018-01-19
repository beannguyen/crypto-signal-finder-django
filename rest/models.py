from datetime import timedelta, datetime

from django.contrib.auth.models import User
from django.db import models

from best_django.settings import ADMIN_REF_UID, STT_ACCOUNT_UNPAID, STT_PAYMENT_PENDING


class WalletCurrency(models.Model):
    """
    Currencies used in payment system.
    """
    name = models.CharField(max_length=50)
    symbol = models.CharField(max_length=50, unique=True)


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
    refer = models.ForeignKey('self', on_delete=models.CASCADE, null=True)
    is_email_verified = models.BooleanField(default=False)
    status = models.IntegerField(default=STT_ACCOUNT_UNPAID)


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


class Payment(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE)
    hash = models.CharField(max_length=500)
    updated_on = models.DateTimeField(auto_now_add=True)
    status = models.IntegerField(default=STT_PAYMENT_PENDING)
    wallet_type = models.ForeignKey(WalletCurrency, on_delete=models.CASCADE, default=1)