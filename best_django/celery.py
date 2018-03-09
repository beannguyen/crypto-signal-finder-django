# set the default Django settings module for the 'celery' program.
from __future__ import absolute_import, unicode_literals
import os

from best_django import settings
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'best_django.settings')
app = Celery('best_django',
             include=['summary_writer.tasks', 'summary_writer.signal_finder', 'summary_writer.exchange_rate_cal'])

# Using a string here means the worker will not have to
# pickle the object when using Windows.
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)


# Load task modules from all registered Django app configs.
# app.autodiscover_tasks()


app.conf.enable_utc = False
app.conf.timezone = 'Asia/Ho_Chi_Minh'


@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))
