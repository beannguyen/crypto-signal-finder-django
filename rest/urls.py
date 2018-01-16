from django.conf.urls import url
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions
from rest_framework_jwt.views import obtain_jwt_token, refresh_jwt_token, verify_jwt_token

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
    url(r'^auth/', obtain_jwt_token),
    url(r'^auth-jwt-refresh/', refresh_jwt_token),
    url(r'^auth-jwt-verify/', verify_jwt_token),
    url(r'^register', view=views.register, name='register'),

    # Markets
    url(r'^getmarkets/$', view=views.getmarkets, name='getmarkets'),
    url(r'^getmarketsummaries/$', view=views.getmarketsummaries, name='getmarketsummaries'),
    url(r'^get-tick/$', view=views.get_tick, name='get_tick'),
    url(r'^get-latest-tick/$', view=views.get_latest_tick, name='get_latest_tick'),

    # Membership
    url(r'^create-user/', view=views.CreateUserView.as_view(), name='create_user'),
    url(r'^request-plan', view=views.request_plan, name='request_plan'),

]
