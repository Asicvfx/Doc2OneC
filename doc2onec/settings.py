import json
import sys
from pathlib import Path

import environ


BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    AI_TIMEOUT=(float, 30.0),
    OCR_TIMEOUT=(float, 30.0),
    OCR_MAX_PDF_PAGES=(int, 3),
    AUTO_PROCESS_ON_UPLOAD=(bool, True),
    SECURE_SSL_REDIRECT=(bool, False),
    SECURE_HSTS_SECONDS=(int, 0),
    SECURE_HSTS_INCLUDE_SUBDOMAINS=(bool, False),
    SECURE_HSTS_PRELOAD=(bool, False),
    CELERY_TASK_ALWAYS_EAGER=(bool, False),
    CELERY_TASK_EAGER_PROPAGATES=(bool, True),
    REDIS_PORT=(int, 6379),
    REDIS_DB=(int, 0),
    AWS_QUERYSTRING_AUTH=(bool, True),
    AWS_S3_FILE_OVERWRITE=(bool, False),
)
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY", default="").strip() or "dev-only-doc2onec-secret-key"
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

render_external_hostname = env("RENDER_EXTERNAL_HOSTNAME", default="").strip()
if render_external_hostname and render_external_hostname not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(render_external_hostname)
render_external_origin = f"https://{render_external_hostname}" if render_external_hostname else ""
if render_external_origin and render_external_origin not in CSRF_TRUSTED_ORIGINS:
    CSRF_TRUSTED_ORIGINS.append(render_external_origin)

FILE_STORAGE_BACKEND = env("FILE_STORAGE_BACKEND", default="filesystem").strip().lower()
if FILE_STORAGE_BACKEND not in {"filesystem", "s3"}:
    raise ValueError("FILE_STORAGE_BACKEND must be either 'filesystem' or 's3'.")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_spectacular",
    "storages",
    "core",
    "directories",
    "documents",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "doc2onec.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "doc2onec.wsgi.application"

database_url = env("DATABASE_URL", default="").strip()
DATABASES = {
    "default": env.db_url_config(database_url or f"sqlite:///{BASE_DIR / 'db.sqlite3'}"),
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "ru-ru"
TIME_ZONE = "Asia/Qyzylorda"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_URL = "media/"
MEDIA_ROOT = Path(env("MEDIA_ROOT", default=str(BASE_DIR / "media")))

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID", default="")
AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY", default="")
AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME", default="")
AWS_S3_REGION_NAME = env("AWS_S3_REGION_NAME", default="")
AWS_S3_ENDPOINT_URL = env("AWS_S3_ENDPOINT_URL", default="")
AWS_S3_CUSTOM_DOMAIN = env("AWS_S3_CUSTOM_DOMAIN", default="")
AWS_DEFAULT_ACL = env("AWS_DEFAULT_ACL", default="") or None
AWS_QUERYSTRING_AUTH = env("AWS_QUERYSTRING_AUTH")
AWS_S3_FILE_OVERWRITE = env("AWS_S3_FILE_OVERWRITE")
AWS_LOCATION = env("AWS_LOCATION", default="")
AWS_S3_ADDRESSING_STYLE = env("AWS_S3_ADDRESSING_STYLE", default="") or None
AWS_S3_URL_PROTOCOL = env("AWS_S3_URL_PROTOCOL", default="https:")
_aws_object_parameters = env("AWS_S3_OBJECT_PARAMETERS", default="").strip()
AWS_S3_OBJECT_PARAMETERS = json.loads(_aws_object_parameters) if _aws_object_parameters else {}

STATICFILES_BACKEND = (
    "django.contrib.staticfiles.storage.StaticFilesStorage"
    if "test" in sys.argv
    else "whitenoise.storage.CompressedManifestStaticFilesStorage"
)
STORAGES = {
    "staticfiles": {
        "BACKEND": STATICFILES_BACKEND,
    }
}
if FILE_STORAGE_BACKEND == "s3":
    STORAGES["default"] = {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "bucket_name": AWS_STORAGE_BUCKET_NAME,
            "region_name": AWS_S3_REGION_NAME or None,
            "endpoint_url": AWS_S3_ENDPOINT_URL or None,
            "custom_domain": AWS_S3_CUSTOM_DOMAIN or None,
            "default_acl": AWS_DEFAULT_ACL,
            "querystring_auth": AWS_QUERYSTRING_AUTH,
            "object_parameters": AWS_S3_OBJECT_PARAMETERS,
            "file_overwrite": AWS_S3_FILE_OVERWRITE,
            "location": AWS_LOCATION,
            "addressing_style": AWS_S3_ADDRESSING_STYLE,
        },
    }
else:
    STORAGES["default"] = {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
        "OPTIONS": {
            "location": str(MEDIA_ROOT),
            "base_url": MEDIA_URL,
        },
    }

AI_PROVIDER = env("AI_PROVIDER", default="mock")
AI_API_KEY = env("AI_API_KEY", default="")
AI_MODEL = env("AI_MODEL", default="gpt-5.5")
AI_TIMEOUT = env("AI_TIMEOUT")
OCR_PROVIDER = env("OCR_PROVIDER", default="openai" if AI_PROVIDER == "openai" else "disabled")
OCR_MODEL = env("OCR_MODEL", default=AI_MODEL)
OCR_TIMEOUT = env("OCR_TIMEOUT")
OCR_MAX_PDF_PAGES = env("OCR_MAX_PDF_PAGES")
PROCESSING_MODE = env("PROCESSING_MODE", default="thread")
REDIS_SCHEME = env("REDIS_SCHEME", default="redis")
REDIS_HOST = env("REDIS_HOST", default="").strip()
REDIS_PORT = env("REDIS_PORT")
REDIS_DB = env("REDIS_DB")
REDIS_PASSWORD = env("REDIS_PASSWORD", default="")
redis_credentials = f":{REDIS_PASSWORD}@" if REDIS_PASSWORD else ""
redis_url = f"{REDIS_SCHEME}://{redis_credentials}{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}" if REDIS_HOST else ""
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default=env("REDIS_URL", default=redis_url))
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default=CELERY_BROKER_URL)
CELERY_TASK_ALWAYS_EAGER = env("CELERY_TASK_ALWAYS_EAGER")
CELERY_TASK_EAGER_PROPAGATES = env("CELERY_TASK_EAGER_PROPAGATES")
AUTO_PROCESS_ON_UPLOAD = env("AUTO_PROCESS_ON_UPLOAD")
SECURE_SSL_REDIRECT = env("SECURE_SSL_REDIRECT")
SECURE_HSTS_SECONDS = env("SECURE_HSTS_SECONDS")
SECURE_HSTS_INCLUDE_SUBDOMAINS = env("SECURE_HSTS_INCLUDE_SUBDOMAINS")
SECURE_HSTS_PRELOAD = env("SECURE_HSTS_PRELOAD")
ONE_C_BASE_URL = env("ONE_C_BASE_URL", default="")
ONE_C_USERNAME = env("ONE_C_USERNAME", default="")
ONE_C_PASSWORD = env("ONE_C_PASSWORD", default="")

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 10,
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Doc2OneC API",
    "DESCRIPTION": "API for processing employee work documents and preparing structured data for 1C.",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SWAGGER_UI_SETTINGS": {
        "deepLinking": True,
        "displayOperationId": True,
    },
}

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "same-origin"