DEBUG = True

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'be_signal_finder',
        'USER': 'bsfuser',
        'PASSWORD': 'Th3NeWorld@@@1893',
        'HOST': 'localhost',
        'PORT': '',
    }
}

CORS_ORIGIN_WHITELIST = (
    '103.68.81.39',
    'localhost:4200'
)

ALLOWED_HOSTS = [
    '103.68.81.39',
    'localhost:4200'
]