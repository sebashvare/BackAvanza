# settings.py
from pathlib import Path
import os
import dj_database_url
from datetime import timedelta
from dotenv import load_dotenv

# Cargar variables de entorno desde .env (solo en desarrollo)
if os.path.exists(Path(__file__).resolve().parent.parent / '.env'):
    load_dotenv(Path(__file__).resolve().parent.parent / '.env')

# --- Paths
BASE_DIR = Path(__file__).resolve().parent.parent

# --- Seguridad / entorno
# En Render: define SECRET_KEY en Environment (OBLIGATORIO)
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    if os.getenv("DEBUG", "False").lower() == "true":
        # Solo en desarrollo local permitir clave por defecto
        SECRET_KEY = "dev-insecure-key-only-for-localhost"
        print("⚠️  [WARNING] Usando SECRET_KEY por defecto - SOLO para desarrollo local")
    else:
        # En producción es OBLIGATORIO definir SECRET_KEY
        raise ValueError("SECRET_KEY no está definida en variables de entorno. Define SECRET_KEY en tu plataforma de hosting.")

# Detectar entorno: False por defecto (producción)
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
    
    # Cloudinary DEBE ir antes de otros apps que usen archivos
    "cloudinary_storage",
    "cloudinary",

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
        # ssl_require=not DEBUG,  # en prod True; en local False
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

# --- Configuración de almacenamiento de archivos media
# Detecta automáticamente si estamos en Render (producción) o localhost (desarrollo)
USE_CLOUDINARY = os.getenv("USE_CLOUDINARY", "False").lower() == "true"

if USE_CLOUDINARY:
    # ========================================
    # PRODUCCIÓN: Cloudinary
    # ========================================
    print("✅ [PRODUCCIÓN] Configurando Cloudinary para archivos media")
    
    CLOUDINARY_STORAGE = {
        'CLOUD_NAME': os.getenv('CLOUDINARY_CLOUD_NAME'),
        'API_KEY': os.getenv('CLOUDINARY_API_KEY'),
        'API_SECRET': os.getenv('CLOUDINARY_API_SECRET'),
    }
    
    # Configuración para Django 4.2+
    STORAGES = {
        "default": {
            "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
        },
    }
    
    # URLs de archivos media
    MEDIA_URL = '/media/'  # Cloudinary maneja la URL real
    
    print(f"   Cloud Name: {os.getenv('CLOUDINARY_CLOUD_NAME', '❌ NO CONFIGURADO')}")
    
else:
    # ========================================
    # DESARROLLO LOCAL: FileSystem
    # ========================================
    print("⚠️  [DESARROLLO] Usando almacenamiento LOCAL para archivos media")
    
    MEDIA_URL = "/media/"
    MEDIA_ROOT = BASE_DIR / "media"
    
    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
            "OPTIONS": {
                "location": str(MEDIA_ROOT)
            }
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
        },
    }
    
    print(f"   Ruta: {MEDIA_ROOT}")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- CORS / CSRF
# En producción, CORS debe ser restrictivo y solo permitir el frontend real
if DEBUG:
    # Desarrollo: permitir localhost en varios puertos
    CORS_ALLOWED_ORIGINS = [
        "http://localhost:5173",
        "http://127.0.0.1:5173", 
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:3000",  # Next.js
        "http://127.0.0.1:3000"
    ]
    print("🔧 [DESARROLLO] CORS permitido para localhost en múltiples puertos")
else:
    # Producción: configuración más explícita y robusta
    cors_origins_env = os.getenv("CORS_ALLOWED_ORIGINS", "")
    if cors_origins_env:
        CORS_ALLOWED_ORIGINS = [o.strip() for o in cors_origins_env.split(",") if o.strip()]
    else:
        # Fallback: dominios por defecto conocidos
        CORS_ALLOWED_ORIGINS = [
            "https://front-avanza.vercel.app",
            "https://frontavanza.vercel.app",  # Por si acaso hay variaciones
        ]
        # 🚨 TEMPORAL: Si no hay variable configurada, permitir todo para diagnosticar
        print("🚨 [WARNING] CORS_ALLOWED_ORIGINS no configurada - usando fallback temporal")
        print("� [WARNING] ACTIVANDO CORS_ALLOW_ALL_ORIGINS temporalmente para debug")
        CORS_ALLOW_ALL_ORIGINS = True  # ⚠️ TEMPORAL SOLO PARA DEBUG
    
    print(f"�🔒 [PRODUCCIÓN] CORS configurado para: {CORS_ALLOWED_ORIGINS}")
    print(f"🔍 [PRODUCCIÓN] Variable CORS_ALLOWED_ORIGINS: '{cors_origins_env}'")
    print(f"🔍 [PRODUCCIÓN] CORS_ALLOW_ALL_ORIGINS: {globals().get('CORS_ALLOW_ALL_ORIGINS', False)}")

# Configuración adicional de CORS para asegurar compatibilidad
CORS_ALLOW_CREDENTIALS = True

# ⚠️ CORS_ALLOW_ALL_ORIGINS se configura dinámicamente arriba según si hay variable de entorno
# Solo se activa si no hay CORS_ALLOWED_ORIGINS configurada
if not globals().get('CORS_ALLOW_ALL_ORIGINS', False):
    CORS_ALLOW_ALL_ORIGINS = False  # Explícitamente False para seguridad

CORS_ALLOWED_HEADERS = [
    'accept',
    'accept-encoding', 
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]
CORS_ALLOWED_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH', 
    'POST',
    'PUT',
]

CSRF_TRUSTED_ORIGINS = [
    u.strip() for u in os.getenv(
        "CSRF_TRUSTED_ORIGINS",
        "https://backavanza.onrender.com,https://front-avanza.vercel.app"
    ).split(",") if u.strip()
]

# Validar configuración crítica en producción
if not DEBUG:
    # Verificar que las variables críticas estén configuradas
    required_env_vars = {
        'DATABASE_URL': 'URL de base de datos PostgreSQL',
        'CLOUDINARY_CLOUD_NAME': 'Nombre del cloud de Cloudinary', 
        'CLOUDINARY_API_KEY': 'API Key de Cloudinary',
        'CLOUDINARY_API_SECRET': 'API Secret de Cloudinary'
    }
    
    missing_vars = []
    for var, description in required_env_vars.items():
        if not os.getenv(var):
            missing_vars.append(f"{var} ({description})")
    
    if missing_vars:
        raise ValueError(
            f"Variables de entorno faltantes para producción:\n" + 
            "\n".join(f"- {var}" for var in missing_vars)
        )

# --- DRF
REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",  # ← Cambiado: requiere autenticación por defecto
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
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

# --- Seguridad y configuración según entorno
if DEBUG:
    # ========================================
    # DESARROLLO LOCAL (localhost)
    # ========================================
    print("🔧 [DESARROLLO] Configuración de seguridad relajada para localhost")
    
    # Sin redirección SSL ni configuraciones de seguridad estrictas
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
    SESSION_COOKIE_SAMESITE = "Lax"
    CSRF_COOKIE_SAMESITE = "Lax"
    
else:
    # ========================================
    # PRODUCCIÓN (Render + Vercel)
    # ========================================
    print("🔒 [PRODUCCIÓN] Configuración de seguridad estricta activada")
    
    # Configuración de seguridad detrás del proxy de Render
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    
    # Configuración adicional de seguridad HTTPS
    SECURE_HSTS_SECONDS = 31536000  # 1 año
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
    X_FRAME_OPTIONS = 'DENY'
    
    # Cookies cross-site (front en Vercel, backend en Render)
    SESSION_COOKIE_SAMESITE = "None"
    CSRF_COOKIE_SAMESITE = "None"

# --- Logging para producción
if not DEBUG:
    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': 'INFO',
            },
        },
        'loggers': {
            'django': {
                'handlers': ['console'],
                'level': 'INFO',
                'propagate': True,
            },
            'core': {  # Logs de tu app
                'handlers': ['console'],
                'level': 'INFO',
                'propagate': True,
            },
        },
    }

