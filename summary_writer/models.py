from django.db import models


# Create your models here.
class Market(models.Model):
    market_currency = models.CharField(max_length=50)
    base_currency = models.CharField(max_length=50)
    market_currency_long = models.CharField(max_length=100)
    base_currency_long = models.CharField(max_length=100)
    min_trade_size = models.IntegerField()
    market_name = models.CharField(max_length=255)
    is_active = models.BooleanField()
    created_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return 'market {}'.format(self.market_name)


class MarketSummary(models.Model):
    market = models.OneToOneField(to=Market, on_delete=models.CASCADE, primary_key=True)
    high = models.DecimalField(max_digits=50, decimal_places=8)
    low = models.DecimalField(max_digits=50, decimal_places=8)
    last = models.DecimalField(max_digits=50, decimal_places=8)
    volume = models.DecimalField(max_digits=50, decimal_places=8)
    base_volume = models.DecimalField(max_digits=50, decimal_places=8)
    updated_on = models.DateTimeField()
    bid = models.DecimalField(max_digits=50, decimal_places=8)
    ask = models.DecimalField(max_digits=50, decimal_places=8)
    prev_day = models.DecimalField(max_digits=50, decimal_places=8)
    created_on = models.DateTimeField(auto_now_add=True)


class Candle(models.Model):
    market = models.ForeignKey(to=Market, on_delete=models.CASCADE)
    open = models.DecimalField(max_digits=50, decimal_places=8)
    high = models.DecimalField(max_digits=50, decimal_places=8)
    low = models.DecimalField(max_digits=50, decimal_places=8)
    close = models.DecimalField(max_digits=50, decimal_places=8)
    base_volume = models.DecimalField(max_digits=50, decimal_places=8)
    volume = models.DecimalField(max_digits=50, decimal_places=8)
    timestamp = models.DateTimeField()
    created_on = models.DateTimeField(auto_now_add=True)
    timeframe = models.CharField(max_length=100, default='thirtyMin')


class Ticker(models.Model):
    market = models.ForeignKey(to=Market, on_delete=models.CASCADE)
    bid = models.DecimalField(max_digits=50, decimal_places=8)
    ask = models.DecimalField(max_digits=50, decimal_places=8)
    timestamp = models.DateTimeField(auto_now_add=True)


class ErrorLog(models.Model):
    error = models.CharField(max_length=5000)
    created_on = models.DateTimeField(auto_now_add=True)