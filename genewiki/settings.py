# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os, djcelery
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
PROJECT_PATH = os.path.realpath(os.path.join(os.path.dirname(__file__), os.path.pardir))

# Make Celery work
from celery.schedules import crontab
djcelery.setup_loader()

SECRET_KEY = 'n#qw)xiu^!wzos+tll=&%3i4raw_^=m%$p(@ee$mly7$pdgbmk'

DEBUG = True
LOCAL = True
SANDBOX = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    ('Max Nanis', 'max@maxnanis.com'),
)
MANAGERS = ADMINS
VERSION ='0.1'
SITE_ID = 1
ALLOWED_HOSTS = ['*']
INTERNAL_IPS = ('127.0.0.1',)


INSTALLED_APPS = (
    'grappelli',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'debug_toolbar',
    'rest_framework',

    'genewiki.mapping',
    'genewiki.wiki',
    'genewiki.scheduler',

    'djcelery',
    'django.contrib.humanize',
    'widget_tweaks',
    'django_extensions',
    'south',
    'gunicorn'
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'genewiki.urls'
WSGI_APPLICATION = 'genewiki.wsgi.application'

# Database
DATABASES = {}

if LOCAL:
    DOMAIN = 'localhost:8000'
    DEBUG_FILENAME = 'corkscrew-local-debug.log'
    VERSION += ' (Local)'
    DATABASES['default'] = {
        'ENGINE':   'django.db.backends.mysql',
        'NAME':     'genewiki',
        'USER':     'root',
        'PASSWORD': '',
        'HOST':     'localhost',
        'PORT':     '3306',
        'ENCODING': 'utf-8',
        'COLLATION': 'utf8_general_ci'
    }

else:
    DOMAIN = 'corkscrew.me'
    DEBUG_FILENAME = 'corkscrew-prod.log'
    VERSION += ' (Prod)'
    DATABASES['default'] = {
        'ENGINE':   'django.db.backends.mysql',
        'NAME':     '',
        'USER':     '',
        'PASSWORD': '',
        'HOST':     '',
        'PORT':     '3306',
        'ENCODING': 'utf-8',
        'COLLATION': 'utf8_general_ci'
    }



# Internationalization
# https://docs.djangoproject.com/en/1.6/topics/i18n/

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'America/Los_Angeles'
USE_I18N = True
USE_L10N = True
USE_TZ = True

# Content
TEMPLATE_DIRS = (
    PROJECT_PATH + '/templates/', 'templates'
)

TEMPLATE_LOADERS = (
    ('pyjade.ext.django.Loader', (
        'django.template.loaders.filesystem.Loader',
        'django.template.loaders.app_directories.Loader',
        'django.template.loaders.eggs.Loader',
    )),
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.core.context_processors.debug',
    'django.core.context_processors.i18n',
    'django.core.context_processors.media',
    'django.core.context_processors.static',
    'django.contrib.auth.context_processors.auth',
    'django.contrib.messages.context_processors.messages',
    'django.core.context_processors.request'
)

STATIC_ROOT = 'staticfiles'
STATIC_URL = '/static/'

STATICFILES_DIRS = (
    PROJECT_PATH + '/static', 'static'
)

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)


# Celery Settings
BROKER_URL = 'amqp://'
CELERYBEAT_SCHEDULER = 'djcelery.schedulers.DatabaseScheduler'
CELERY_TIMEZONE = 'America/Los_Angeles'
CELERY_SEND_TASK_ERROR_EMAILS = True


# Email Settings
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_USE_TLS = True
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_HOST_USER = 'su.lab.logger'
EMAIL_HOST_PASSWORD = 'phQ3ABTWdHbWBC4A7CEzQCY8j8n6XP'
DEFAULT_FROM_EMAIL = 'su.lab.logger@gmail.com'
SERVER_EMAIL = DEFAULT_FROM_EMAIL


try:
    from genewiki.genewiki_settings import *
except ImportError:
    print '[!] You need to configure GeneWiki Settings'

try:
    from genewiki.beat_settings import *
except ImportError:
    print '[!] You need to configure Celery Beats'


