from django.conf.urls import url

from rest import views

urlpatterns = [
    url(r'^markets/$', view=views.get_markets, name='get_markets'),
    url(r'^get-tick/$', view=views.get_tick, name='get_tick'),
    url(r'^get-latest-tick/$', view=views.get_latest_tick, name='get_latest_tick'),
]