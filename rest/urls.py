from django.conf.urls import url
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions
from rest_framework_jwt.views import refresh_jwt_token, verify_jwt_token, obtain_jwt_token

from rest import views

schema_view = get_schema_view(
    openapi.Info(
        title="Snippets API",
        default_version='v1',
        description="Test description",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="contact@snippets.local"),
        license=openapi.License(name="BSD License"),
    ),
    validators=['flex', 'ssv'],
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    # swagger
    url(r'^swagger(?P<format>.json|.yaml)$', schema_view.without_ui(cache_timeout=None), name='schema-json'),
    url(r'^swagger/$', schema_view.with_ui('swagger', cache_timeout=None), name='schema-swagger-ui'),
    url(r'^redoc/$', schema_view.with_ui('redoc', cache_timeout=None), name='schema-redoc'),

    # Authentication
    url(r'^auth/login', views.obtain_jwt_token, name='auth'),
    url(r'^auth-jwt-refresh/', refresh_jwt_token),
    url(r'^auth-jwt-verify/', verify_jwt_token),
    url(r'^register', view=views.register, name='register'),
    url(r'^email-verification', view=views.verify_email, name='email-verification'),
    url(r'^auth/forgot-password/', view=views.forgot_password, name='forgot_password'),
    url(r'^auth/reset-password/', view=views.reset_password, name='reset_password'),

    # Markets
    url(r'^getmarkets/$', view=views.getmarkets, name='getmarkets'),
    url(r'^getmarketsummaries/$', view=views.getmarketsummaries, name='getmarketsummaries'),
    url(r'^get-tick/$', view=views.get_tick, name='get_tick'),
    url(r'^get-latest-tick/$', view=views.get_latest_tick, name='get_latest_tick'),

    # Membership
    url(r'^create-user/', view=views.CreateUserView.as_view(), name='create_user'),
    url(r'^request-plan', view=views.request_plan, name='request_plan'),
    url(r'^payment/prepare', view=views.prepare_payment, name='prepare_payment'),
    url(r'^payment/submit', view=views.submit_payment, name='submit_payment'),
    url(r'^get-list-user', view=views.get_user_list, name='get_user_list'),
    url(r'^user/search-by-invoice', view=views.search_user_by_invoice, name='search_user_by_invoice'),
    url(r'^get-groups', view=views.get_groups, name='get_groups'),
    url(r'^assign-sale-package', view=views.assign_sale_package, name='assign_sale_package'),
    url(r'^get-sale-package', view=views.get_sale_package, name='get_sale_package'),
    url(r'^user/activate', view=views.activate_user, name='activate_user'),
    url(r'^user/renew', view=views.renew_user, name='renew_user'),
    url(r'^user/ban', view=views.ban_user, name='ban_user'),
    url(r'^user/my-profile/', view=views.get_user_profile, name='get_user_profile'),
    url(r'^user/update-profile/', view=views.update_profile, name='update_profile'),
    url(r'^user/get-leader-info/', view=views.get_leader_info, name='get_leader_info'),
    url(r'^market/subscribe', view=views.user_subscribe, name='user_subscribe'),
    url(r'^market/unsubscribe', view=views.unsubscribe_market, name='unsubscribe_market'),

    # Pricing plan
    url(r'^get-plan-list', view=views.get_pricing_plans, name='get_pricing_plans'),
    url(r'^plan/pricing/by-wallet-type', view=views.get_pricing_plans_by_wallet, name='get_pricing_plans_by_wallet'),
    url(r'^get-my-plan-list', view=views.get_my_pricing_plans, name='get_my_pricing_plans'),
    url(r'^create-plan', view=views.create_plan, name='create_plan'),
    url(r'^update-plan', view=views.update_plan, name='update_plan'),
    url(r'^add-pricing-to-plan', view=views.add_pricing_to_plan, name='add_pricing_to_plan'),
    url(r'^update-user-plan', view=views.update_user_plan, name='update_user_plan'),

    # Wallet Type
    url(r'^create-wallet-type', view=views.create_wallet_type, name='create_wallet_type'),
    url(r'^list-wallet-type', view=views.get_wallet_type_list, name='get_wallet_type_list'),
    url(r'^bank-account/get', view=views.get_bank_account, name='get_bank_account'),
    url(r'^bank-account/update', view=views.update_bank_account, name='update_bank_account'),

    # Person wallet
    url(r'^update-user-wallet', view=views.update_user_wallet, name='update_user_wallet'),
    url(r'^get-leader-wallet', view=views.get_leader_wallet, name='get_leader_wallet'),
    url(r'^get-my-wallet', view=views.get_my_wallet, name='get_my_wallet'),

    # Payment
    url(r'^get-user-payment-history', view=views.get_user_payment_history, name='get_user_payment_history'),
    url(r'^confirm-payment', view=views.confirm_payment, name='confirm_payment'),

    # News
    url(r'^news/', view=views.get_news, name='get_news'),
    url(r'^newscategory/', view=views.get_news_categories, name='get_news_categories'),

    # Strategy Configuration
    url(r'^strategy/list', view=views.get_strategies, name='get_strategies'),
    url(r'^strategy/update', view=views.update_strategy_details, name='update_strategy_details'),
]
