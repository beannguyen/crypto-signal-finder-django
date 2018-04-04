import time
import traceback
from decimal import *

import requests
from bittrex import Bittrex, API_V2_0
from celery import task
from django import db

from best_django import settings
from rest.models import *
from summary_writer.models import *

bittrex_api = Bittrex(settings.BITTREX_API_KEY, settings.BITTREX_SECRET_KEY)
bittrex_api_v2 = Bittrex(settings.BITTREX_API_KEY, settings.BITTREX_SECRET_KEY, api_version=API_V2_0)


def get_ofx_quote():
    try:
        url = "https://adsynth-ofx-quotewidget-prod.herokuapp.com/api/1"
        payload = "{\"method\":\"spotRateHistory\",\"data\":{\"base\":\"USD\",\"term\":\"VND\",\"period\":\"week\"}}"

        headers = {
            'Content-Type': "application/json"
        }
        result = requests.request("POST", url, data=payload, headers=headers).json()
        price = Decimal(result['data']['CurrentInterbankRate'])
        return price
    except:
        traceback.print_exc()


@task()
def plan_pricing_calculate():
    print('Plan pricing calculating....')

    start_time = time.time()
    db.connections.close_all()

    plans = MemberShipPlan.objects.all()
    base_currency = WalletCurrency.objects.filter(is_base=True).first()

    for plan in plans:
        # get base currency price
        pricing_obj = MemberShipPlanPricing.objects.filter(plan=plan, wallet_currency=base_currency).first()
        for currency in WalletCurrency.objects.filter(is_base=False, is_disabled=False):
            if currency.symbol != 'VND':
                market = Market.objects.filter(base_currency=base_currency.symbol,
                                               market_currency=currency.symbol).first()
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
            else:
                p = MemberShipPlanPricing.objects.filter(plan=plan, wallet_currency=currency).first()
                price = get_ofx_quote()
                plan_price = Decimal(pricing_obj.price) * price
                print('price in vnd ', plan_price)
                if p is not None:
                    p.price = plan_price
                    p.save()
                else:
                    MemberShipPlanPricing.objects.create(plan=plan, wallet_currency=currency, price=plan_price)
    print("Execution time = {0:.5f}".format(time.time() - start_time))
