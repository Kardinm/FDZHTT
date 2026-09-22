import os
from pathlib import Path

from django.core.management.utils import get_random_secret_key

# ---------------------------------------------------------------- базовые пути

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "temporary"
DEBUG = True
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = "ru-ru"
TIME_ZONE = "Europe/Minsk"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --------------------------------------------------------- настройки пространства

# Ключ, который открывает режим быстрых правок (вводится замком слева внизу).
# В проде задайте переменную окружения FDZHTT_EDIT_CODE.
EDIT_CODE = os.environ.get("FDZHTT_EDIT_CODE", "friday")

# Секрет Django: окружение → файл .django-secret (не в git) → генерация.
_secret_file = BASE_DIR / ".django-secret"
if os.environ.get("FDZHTT_SECRET_KEY"):
    SECRET_KEY = os.environ["FDZHTT_SECRET_KEY"]
elif _secret_file.exists():
    SECRET_KEY = _secret_file.read_text().strip()
else:
    _secret_key = get_random_secret_key()
    _secret_file.write_text(_secret_key)
    SECRET_KEY = _secret_key

DEBUG = os.environ.get("FDZHTT_DEBUG", "1") == "1"
