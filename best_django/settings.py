"""
Django settings for best_django project.

Generated by 'django-admin startproject' using Django 2.0.

For more information on this file, see
https://docs.djangoproject.com/en/2.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.0/ref/settings/
"""

import os

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
from datetime import timedelta
from best_django.nogitsettings import *

from celery.schedules import crontab

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'h6i1_o9&5=psqbdm2rg2$3)3)ko4kacfj0%en^$kg)5gitv-h-'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = [
    '*'
]

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'summary_writer',
    'rest',
    'drf_yasg',
    'seed'
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'best_django.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')]
        ,
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'best_django.wsgi.application'

# Database
# https://docs.djangoproject.com/en/2.0/ref/settings/#databases


# Password validation
# https://docs.djangoproject.com/en/2.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
# https://docs.djangoproject.com/en/2.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.0/howto/static-files/

STATIC_URL = '/static/'

# CORS SETTINGS
CORS_ORIGIN_WHITELIST = (
    'localhost:4200'
)

CORS_ALLOW_HEADERS = (
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
)

# CELERY CONFIG
CELERY_BROKER_URL = 'redis://localhost:6379'
CELERY_RESULT_BACKEND = 'redis://localhost:6379'
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TASK_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'

CELERY_BEAT_SCHEDULE = {
    'update-markets': {
        'task': 'summary_writer.tasks.update_markets',
        'schedule': crontab(minute=55, hour=23)
    },
    'update-market-summaries': {
        'task': 'summary_writer.tasks.update_market_summary',
        'schedule': crontab(minute=0, hour='*/1')
    },
    'get-latest-tick': {
        'task': 'summary_writer.tasks.get_latest_tick',
        'schedule': crontab(minute='*/15')
    }
}

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_jwt.authentication.JSONWebTokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
    ),
}

JWT_SECRET_KEY = 'CCADD99B16CD3D200C22D6DB45D8B6630EF3D936767127347EC8A76AB992C2EA'

JWT_AUTH = {
    'JWT_SECRET_KEY': JWT_SECRET_KEY,
    'JWT_ALGORITHM': 'HS256',
    'JWT_VERIFY': True,
    'JWT_VERIFY_EXPIRATION': True,
    'JWT_LEEWAY': 0,
    'JWT_EXPIRATION_DELTA': timedelta(seconds=3000),
    'JWT_AUDIENCE': None,
    'JWT_ISSUER': None,
    'JWT_AUTH_HEADER_PREFIX': 'Bearer',
}

# BITTREX API KEY
BITTREX_API_KEY = 'cbcfce018d144dfdbedfcc1f17a7565c'
BITTREX_SECRET_KEY = '42fdf442ad114d83a3f53c240dfe19fd'

HTTP_OK = 'OK'
HTTP_ERR = 'ERR'

GROUP_ADMIN = 'Admin'
GROUP_LEADER = 'Leader'
GROUP_USER = 'User'
ADMIN_REF_UID = '1111'

EMAIL_HOST = 'smtp.gmail.com'
EMAIL_HOST_USER = 'SignalFinder <admin@example.com>'
EMAIL_HOST_PASSWORD = 'glrotflbbtgaaiqb'
EMAIL_PORT = 587
EMAIL_USE_TLS = True

HOME_URL = 'http://localhost:4200'

try:
    from best_django.nogitsettings import *
except:
    print('nogit settings not found')

if not IS_PRODUCTION:
    try:
        from best_django.localsettings import *
    except Exception as e:
        print(e)
        print('local settings not found')
else:
    try:
        from best_django.livesettings import *
    except:
        print('live settings not found')
