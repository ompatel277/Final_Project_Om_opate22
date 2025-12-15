from .base import *

DEBUG = False

ALLOWED_HOSTS = ['localhost', '127.0.0.1', 'ompatel277.pythonanywhere.com']

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'ompatel277$info390finalmg-msql-database',
        'USER': 'ompatel277',
        'PASSWORD': 'graingerlibrary',
        'HOST': 'ompatel277.mysql.pythonanywhere-services.com',
        'PORT': '3306',
    }
}