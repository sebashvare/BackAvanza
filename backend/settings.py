# settings.py
from pathlib import Path
import os
import dj_database_url
from datetime import timedelta

# --- Paths
BASE_DIR = Path(__file__).resolve().parent.parent

# --- Seguridad / entorno
# En Render: define SECRET_KEY en Environment
SECRET_KEY = os.getenv("SECRET_KEY", "dev-insecure-key")  # <-- cámbiala en prod

DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# Hosts permitidos (Render + Vercel + localhost)
ALLOWED_HOSTS = [
    h.strip() for h in os.getenv(
        "ALLOWED_HOSTS",
        "localhost,127.0.0.1,backavanza.onrender.com,front-avanza.vercel.app"
    ).split(",") if h.strip()
]

# --- Apps
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "rest_framework",
    # "django.contrib.postgres",  # déjalo si lo usas explícitamente

    "corsheaders",
    "core",
]

# --- Middleware
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",

    # WhiteNoise inmediatamente después de SecurityMiddleware
    "whitenoise.middleware.WhiteNoiseMiddleware",

    # CORS debe ir lo más arriba posible, antes de CommonMiddleware
    "corsheaders.middleware.CorsMiddleware",

    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "backend.urls"

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

WSGI_APPLICATION = "backend.wsgi.application"

# --- Base de datos
# En Render define DATABASE_URL (usa Internal URL). En local, se queda con SQLite.
DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
        ssl_require=not DEBUG,  # en prod True; en local False
    )
}

# --- Password validators
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --- i18n
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# --- Static files (admin/DRF UI)
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Django 4.2+ storage API (recomendado)
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
    }
}

# --- Media (si lo usas)
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- CORS / CSRF
CORS_ALLOWED_ORIGINS = [
    o.strip() for o in os.getenv(
        "CORS_ALLOWED_ORIGINS",
        # Prod:
        "https://front-avanza.vercel.app"
        # Dev (descomenta estas para localhost):
        # ",http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174"
    ).split(",") if o.strip()
]
CORS_ALLOW_CREDENTIALS = True

CSRF_TRUSTED_ORIGINS = [
    u.strip() for u in os.getenv(
        "CSRF_TRUSTED_ORIGINS",
        "https://backavanza.onrender.com,https://front-avanza.vercel.app"
        # Dev (descomenta si usas sesión/CSRF desde localhost):
        # ",http://localhost:5173,http://127.0.0.1:5173"
    ).split(",") if u.strip()
]

# --- DRF
REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",  # en prod considera IsAuthenticated
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        # "rest_framework.authentication.SessionAuthentication",
        # "rest_framework.authentication.BasicAuthentication",
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    # Si quieres UI de DRF en prod, deja BrowsableRenderer activo
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ),
}

# --- Simple JWT
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
}

# --- Seguridad detrás del proxy de Render
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG

# Si usas cookies cross-site (front en Vercel):
SESSION_COOKIE_SAMESITE = "None" if not DEBUG else "Lax"
CSRF_COOKIE_SAMESITE = "None" if not DEBUG else "Lax"

