from bittrex import Bittrex, API_V2_0
from bs4 import BeautifulSoup
from celery import shared_task, task
import dateutil.parser
import requests
import traceback
import numpy as np
import pandas as pd
import talib
import threading
import time
from queue import Queue
from datetime import datetime, date

from best_django.celery import app
from summary_writer.models import *
from rest.models import *
from best_django import settings
from utils import send_mail
from talib import MA_Type
from decimal import *
from django import db

bittrex_api = Bittrex(settings.BITTREX_API_KEY, settings.BITTREX_SECRET_KEY)
bittrex_api_v2 = Bittrex(settings.BITTREX_API_KEY, settings.BITTREX_SECRET_KEY, api_version=API_V2_0)


@task()
def plan_pricing_calculate():
    print('Plan pricing calculating....')

    start_time = time.time()
    db.connections.close_all()
    
    plans = MemberShipPlan.objects.all()
    base_currency = WalletCurrency.objects.filter(is_base=True).first()

    for plan in plans:
        pricing_obj = MemberShipPlanPricing.objects.filter(plan=plan, wallet_currency=base_currency).first()
        for currency in WalletCurrency.objects.filter(is_base=False):
            market = Market.objects.filter(base_currency=base_currency.symbol, market_currency=currency.symbol).first()
            pricing_obj = MemberShipPlanPricing.objects.filter(plan=plan, wallet_currency=base_currency).first()
            if pricing_obj is not None:
                tick = Ticker.objects.filter(market=market).order_by('-timestamp').first()
                price = (tick.bid + tick.ask) / 2
                plan_price = Decimal(pricing_obj.price) / price
                # update plan pricing
                p = MemberShipPlanPricing.objects.filter(plan=plan, wallet_currency=currency).first()
                if p is not None:
                    p.price = plan_price
                    p.save()
                else:
                    MemberShipPlanPricing.objects.create(plan=plan, wallet_currency=currency, price=plan_price)
    print("Execution time = {0:.5f}".format(time.time() - start_time))