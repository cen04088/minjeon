import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-change-me-in-production')
DEBUG = os.environ.get('DEBUG', 'False') == 'True'
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '*').split(',')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'whitenoise.runserver_nostatic',
    'django.contrib.staticfiles',
    'rest_framework',
    'offices',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
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

WSGI_APPLICATION = 'config.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
        # 'ENGINE': 'django.db.backends.postgresql',
        # 'NAME':     os.environ.get('PGDATABASE', 'minjeon'),
        # 'USER':     os.environ.get('PGUSER', 'postgres'),
        # 'PASSWORD': os.environ.get('PGPASSWORD', ''),
        # 'HOST':     os.environ.get('PGHOST', 'localhost'),
        # 'PORT':     os.environ.get('PGPORT', '5432'),
    }
}

LANGUAGE_CODE = 'ko-kr'
TIME_ZONE = 'Asia/Seoul'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# 공공데이터포털 API 키
PUBLIC_DATA_API_KEY = os.environ.get('PUBLIC_DATA_API_KEY', '')

# data.go.kr 에서 발급받은 실제 엔드포인트로 교체하세요
WAITING_API_URL     = os.environ.get('WAITING_API_URL',     'https://api.odcloud.kr/api/WAITING_ENDPOINT')
OFFICE_INFO_API_URL = os.environ.get('OFFICE_INFO_API_URL', 'https://api.odcloud.kr/api/OFFICE_ENDPOINT')

# 카카오내비 REST API 키 (총 소요시간 계산용)
KAKAO_REST_API_KEY = os.environ.get('KAKAO_REST_API_KEY', '')

# OpenAI API 키 (서류 도우미 챗봇용)
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
