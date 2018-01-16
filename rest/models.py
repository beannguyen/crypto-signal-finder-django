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


class MemberShipPlanPricing(models.Model):
    """
    Each plan can include many price in a list of diff currencies.
    """
    wallet_currency = models.ForeignKey(WalletCurrency, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=50, decimal_places=8)


class Profile(models.Model):
    user = models.OneToOneField(User, related_name='primary', on_delete=models.CASCADE, primary_key=True)
    plan = models.ForeignKey(MemberShipPlan, on_delete=models.CASCADE)


class Wallet(models.Model):
    """
    User's wallet
    """
    user = models.ForeignKey(Profile, on_delete=models.CASCADE)
    wallet_currency = models.ForeignKey(WalletCurrency, on_delete=models.CASCADE)
    address = models.CharField(max_length=500)
    updated_at = models.DateTimeField(auto_now_add=True)
