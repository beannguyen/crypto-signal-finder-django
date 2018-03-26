from datetime import timedelta, datetime

from django.contrib.auth.models import User
from django.db import models
from summary_writer.models import Market

from best_django.settings import ADMIN_REF_UID, STT_ACCOUNT_UNPAID, STT_PAYMENT_PENDING


class WalletCurrency(models.Model):
    """
    Currencies used in payment system.
    """
    name = models.CharField(max_length=50)
    symbol = models.CharField(max_length=50, unique=True)
    is_disabled = models.BooleanField(default=True)
    is_base = models.BooleanField(default=False)


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
    activated_date = models.DateTimeField(null=True)
    ref = models.CharField(max_length=4, unique=True, null=True)
    refer = models.ForeignKey('self', on_delete=models.CASCADE, null=True)
    is_email_verified = models.BooleanField(default=False)
    phone_number = models.CharField(max_length=20, default='')
    avatar = models.CharField(max_length=500, default='http://vvcexpl.com/wordpress/wp-content/uploads/2013/09/profile-default-male.png')
    status = models.IntegerField(default=STT_ACCOUNT_UNPAID)


class SalePackageAssignment(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE)
    plan = models.ForeignKey(MemberShipPlan, on_delete=models.CASCADE, null=True)
    package_count = models.IntegerField(default=0)


class Wallet(models.Model):
    """
    User's wallet
    """
    user = models.ForeignKey(Profile, on_delete=models.CASCADE)
    wallet_currency = models.ForeignKey(WalletCurrency, on_delete=models.CASCADE)
    address = models.CharField(max_length=500)
    updated_at = models.DateTimeField(auto_now_add=True)


class BankAccount(models.Model):
    user = models.ForeignKey(Profile, on_delete=models.CASCADE)
    bank_name = models.CharField(max_length=500)
    bank_account = models.CharField(max_length=500)
    bank_branch = models.CharField(max_length=500)


class AccountVerificationCode(models.Model):
    user = models.ForeignKey(Profile, on_delete=models.CASCADE)
    verify_code = models.CharField(max_length=16)
    expire_on = models.DateTimeField(auto_now_add=True)
    type = models.IntegerField(default=1)


class Payment(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE)
    hash = models.CharField(max_length=500)
    updated_on = models.DateTimeField(auto_now_add=True)
    status = models.IntegerField(default=STT_PAYMENT_PENDING)
    wallet_type = models.ForeignKey(WalletCurrency, on_delete=models.CASCADE, default=1, null=True)


class UserSubscription(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE)
    market = models.ForeignKey(Market, on_delete=models.CASCADE)
    subscribed_on = models.DateTimeField(auto_now_add=True)


class SignalSendLog(models.Model):
    # profile = models.ForeignKey(Profile, on_delete=models.CASCADE, null=True)
    market = models.ForeignKey(Market, on_delete=models.CASCADE)
    action = models.CharField(max_length=50)
    timestamp = models.DateTimeField(auto_now_add=True)


class NewsItem(models.Model):
    title = models.CharField(max_length=500)
    url = models.CharField(max_length=500)
    img = models.CharField(max_length=500)
    short_desc = models.CharField(max_length=1000)
    category_title = models.CharField(max_length=500)
    category_url = models.CharField(max_length=500, default='')
    date = models.CharField(max_length=100)


class NewsCategory(models.Model):
    title = models.CharField(max_length=500)
    url = models.CharField(max_length=500)


class Strategy(models.Model):
    name = models.CharField(max_length=500)
    message = models.CharField(max_length=1000, default='')
