from .base import *

DEBUG = False

ALLOWED_HOSTS = ['ompatel277.pythonanywhere.com',  '127.0.0.1', 'localhost']

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