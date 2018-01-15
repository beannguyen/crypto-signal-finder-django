from django.conf.urls import url

from rest import views


urlpatterns = [

    # Markets
    url(r'^getmarkets/$', view=views.getmarkets, name='getmarkets'),
    url(r'^getmarketsummaries/$', view=views.getmarketsummaries, name='getmarketsummaries'),
    url(r'^get-tick/$', view=views.get_tick, name='get_tick'),
    url(r'^get-latest-tick/$', view=views.get_latest_tick, name='get_latest_tick'),

    # Membership

]