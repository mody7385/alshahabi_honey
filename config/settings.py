import os
from pathlib import Path
import dj_database_url

# تأكد من أنك قد قمت بتحديد المسار بشكل صحيح
BASE_DIR = Path(__file__).resolve().parent.parent

# إعدادات الأمان
SECRET_KEY = os.environ.get('SECRET_KEY', 'default-secret-key')  # استخدم متغير بيئي
DEBUG = os.environ.get('DEBUG', 'False') == 'False'  # تأكد من أنه False في بيئة الإنتاج

ALLOWED_HOSTS = ['127.0.0.1', 'localhost', os.environ.get('RENDER_EXTERNAL_HOSTNAME')]  # للسماح بكل النطاقات في حالة النشر
if os.environ.get('RENDER_EXTERNAL_HOSTNAME'):
    ALLOWED_HOSTS.append(os.environ.get('RENDER_EXTERNAL_HOSTNAME'))

CSRF_TRUSTED_ORIGINS = []
if os.environ.get('RENDER_EXTERNAL_HOSTNAME'):
    CSRF_TRUSTED_ORIGINS.append(f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME')}")

# Static files (CSS, JavaScript, Images)
# سيجمع هذا جميع الملفات الثابتة
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# إذا كنت تستخدم ملفات ثابتة عبر internet
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # لتحسين التعامل مع الملفات الثابتة في الإنتاج
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# إعدادات قاعدة البيانات
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# إعدادات المزامنة في الإنتاج
if not DEBUG:
    SECURE_SSL_REDIRECT = True  # يتم تحويل جميع الطلبات إلى HTTPS
    SESSION_COOKIE_SECURE = True  # استخدام ملفات تعريف ارتباط آمنة فقط
    CSRF_COOKIE_SECURE = True  # تأمين ملفات تعريف ارتباط CSRF

# إعدادات اللغة والوقت
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# إعدادات المصادقة وتسجيل الدخول
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'login'

# إعدادات كلمة المرور
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

# إعدادات التطبيقات المثبتة
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'accounts',
    'warehouses',
    'products',
    'inventory.apps.InventoryConfig',
    'customers',
    'sales',
    'finance',
    'core',
]

# إعدادات ملفات النموذج
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# WSGI Application
WSGI_APPLICATION = 'config.wsgi.application'

# إعدادات الامان الأخرى
SECURE_HSTS_SECONDS = 31536000  # Force HTTPS
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True